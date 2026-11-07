from decimal import Decimal
from unittest.mock import patch

from rest_framework import status

from apps.common.exceptions import BadGatewayError
from apps.orders.models import Order, OrderEvent
from apps.payments.models import PaymentCheckout
from apps.payments.tests.base import PayPalTestCase

CLIENT = "apps.payments.services.paypal_client"


def captured_summary(capture_id: str = "CAP-1") -> dict:
    return {
        "id": "PP-OPEN",
        "status": "COMPLETED",
        "capture_id": capture_id,
        "capture_status": "COMPLETED",
        "raw": {},
    }


class CheckoutWebhookTests(PayPalTestCase):
    def _open_checkout(self, order_id: int, status_=PaymentCheckout.Status.CREATED):
        return PaymentCheckout.objects.create(
            order_id=order_id,
            paypal_order_id="PP-OPEN",
            status=status_,
            approve_url="https://example.com/approve",
            amount=Decimal("49.00"),
            currency="USD",
        )

    def _approved(self, order_id: int, event_id: str | None = None):
        return self.deliver(
            "CHECKOUT.ORDER.APPROVED",
            {"id": "PP-OPEN", "purchase_units": [{"custom_id": str(order_id)}]},
            event_id=event_id,
        )

    @patch(f"{CLIENT}.capture_order")
    def test_approval_captures_on_the_server_even_if_the_buyer_never_returns(self, capture):
        capture.return_value = captured_summary()
        order_id = self.confirmed_order()
        checkout = self._open_checkout(order_id)

        event = self._approved(order_id)

        self.assertIsNotNone(event.processed_at)
        capture.assert_called_once_with(paypal_order_id="PP-OPEN")
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.CAPTURED)
        self.assertEqual(checkout.capture_id, "CAP-1")
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
        self.assertTrue(
            OrderEvent.objects.filter(
                order_id=order_id, event_type=OrderEvent.EventType.PAYMENT_APPROVED
            ).exists()
        )

    @patch(f"{CLIENT}.capture_order")
    def test_duplicate_approval_delivery_captures_once(self, capture):
        capture.return_value = captured_summary()
        order_id = self.confirmed_order()
        self._open_checkout(order_id)

        self._approved(order_id, event_id="WH-A")
        self._approved(order_id, event_id="WH-B")

        self.assertEqual(capture.call_count, 1)
        self.assertEqual(
            OrderEvent.objects.filter(
                order_id=order_id, event_type=OrderEvent.EventType.PAYMENT_APPROVED
            ).count(),
            1,
        )

    @patch(f"{CLIENT}.capture_order")
    def test_a_superseded_checkout_is_never_captured(self, capture):
        order_id = self.confirmed_order()
        self._open_checkout(order_id, status_=PaymentCheckout.Status.CANCELLED)

        self._approved(order_id)

        capture.assert_not_called()
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "pending")

    @patch(f"{CLIENT}.capture_order")
    def test_failed_auto_capture_is_recorded_not_raised(self, capture):
        capture.side_effect = BadGatewayError("PayPal is temporarily unavailable.")
        order_id = self.confirmed_order()
        checkout = self._open_checkout(order_id)

        event = self._approved(order_id)

        self.assertIsNotNone(event.processed_at)
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.FAILED)
        self.assertIn("temporarily unavailable", checkout.last_error)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "failed")

    @patch(f"{CLIENT}.capture_order")
    def test_a_failed_capture_is_healed_by_the_completed_webhook(self, capture):
        capture.side_effect = BadGatewayError("PayPal is temporarily unavailable.")
        order_id = self.confirmed_order()
        checkout = self._open_checkout(order_id)
        self._approved(order_id)

        self.deliver(
            "PAYMENT.CAPTURE.COMPLETED",
            {
                "id": "CAP-LATE",
                "status": "COMPLETED",
                "custom_id": str(order_id),
                "supplementary_data": {"related_ids": {"order_id": "PP-OPEN"}},
            },
        )

        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.CAPTURED)
        self.assertEqual(checkout.capture_id, "CAP-LATE")
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")

    @patch(f"{CLIENT}.get_order")
    @patch(f"{CLIENT}.capture_order")
    def test_capture_race_is_settled_as_paid_not_failed(self, capture, get_order):
        capture.side_effect = BadGatewayError(
            "This PayPal order was already captured.",
            extra={"paypal_issue": "ORDER_ALREADY_CAPTURED"},
        )
        get_order.return_value = {
            "id": "PP-OPEN",
            "status": "COMPLETED",
            "purchase_units": [
                {"payments": {"captures": [{"id": "CAP-RACE", "status": "COMPLETED"}]}}
            ],
        }
        order_id = self.confirmed_order()
        checkout = self._open_checkout(order_id, status_=PaymentCheckout.Status.APPROVED)

        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/capture/", {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_status"], "paid")
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.CAPTURED)
        self.assertEqual(checkout.capture_id, "CAP-RACE")
        self.assertEqual(checkout.last_error, "")

    def test_declined_checkout_marks_the_payment_failed(self):
        order_id = self.confirmed_order()
        checkout = self._open_checkout(order_id)

        self.deliver(
            "CHECKOUT.ORDER.DECLINED",
            {"id": "PP-OPEN", "purchase_units": [{"custom_id": str(order_id)}]},
        )

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "failed")
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.FAILED)
        self.assertIn("CHECKOUT.ORDER.DECLINED", checkout.last_error)

    def test_payment_for_a_cancelled_order_is_surfaced_on_the_order(self):
        order_id = self.confirmed_order()
        self._open_checkout(order_id)
        self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")

        event = self.deliver(
            "PAYMENT.CAPTURE.COMPLETED",
            {"id": "CAP-1", "status": "COMPLETED", "custom_id": str(order_id)},
        )

        self.assertIsNotNone(event.processed_at)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "cancelled")
        note = OrderEvent.objects.get(order_id=order_id, event_type=OrderEvent.EventType.NOTE)
        self.assertIn("could not be applied", note.message)

    def test_unrelated_events_are_stored_and_ignored(self):
        order_id = self.confirmed_order()

        event = self.deliver("VAULT.PAYMENT-TOKEN.CREATED", {"id": "TOKEN-1"})

        self.assertIsNotNone(event.processed_at)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "pending")


class CurrencyGuardTests(PayPalTestCase):
    @patch(f"{CLIENT}.create_order")
    def test_checkout_for_an_unsupported_currency_never_reaches_paypal(self, create_order):
        order_id = self.confirmed_order()
        Order.objects.filter(pk=order_id).update(currency="PKR")

        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("PKR", response.data["detail"])
        create_order.assert_not_called()
        self.assertFalse(PaymentCheckout.objects.filter(order_id=order_id).exists())

    def test_order_detail_reports_currency_support(self):
        order_id = self.confirmed_order()
        supported = self.client.get(f"/api/v1/orders/{order_id}/")
        self.assertTrue(supported.data["paypal_currency_supported"])

        Order.objects.filter(pk=order_id).update(currency="PKR")
        unsupported = self.client.get(f"/api/v1/orders/{order_id}/")
        self.assertFalse(unsupported.data["paypal_currency_supported"])
