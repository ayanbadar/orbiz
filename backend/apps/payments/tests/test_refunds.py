from decimal import Decimal
from unittest.mock import patch

from rest_framework import status

from apps.common.exceptions import BadGatewayError
from apps.orders.models import Order, OrderEvent
from apps.payments.models import PaymentCheckout, PaymentInvoice, PaymentRefund
from apps.payments.tests.base import PayPalTestCase

REFUND_PATH = "apps.payments.services.paypal_client.refund_capture"


def refund_url(order_id: int) -> str:
    return f"/api/v1/payments/orders/{order_id}/refund/"


def completed_refund(refund_id: str = "REF-1") -> dict:
    return {"id": refund_id, "status": "COMPLETED", "raw": {}}


class RefundApiTests(PayPalTestCase):
    @patch(REFUND_PATH)
    def test_full_refund_when_amount_omitted(self, mock_refund):
        mock_refund.return_value = completed_refund()
        order_id = self.paid_order()

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_status"], "refunded")
        self.assertEqual(response.data["fulfilment_status"], "unfulfilled")
        self.assertEqual(response.data["paypal_refundable_amount"], "0.00")
        _, kwargs = mock_refund.call_args
        self.assertEqual(kwargs["capture_id"], "CAP-1")
        self.assertEqual(kwargs["amount"], Decimal("49.00"))
        refund = PaymentRefund.objects.get(order_id=order_id)
        self.assertEqual(refund.status, PaymentRefund.Status.COMPLETED)
        self.assertEqual(refund.paypal_refund_id, "REF-1")
        self.assertEqual(refund.actor, self.user)
        self.assertEqual(refund.source, PaymentRefund.Source.ORBIZ)
        self.assertEqual(
            OrderEvent.objects.filter(
                order_id=order_id, event_type=OrderEvent.EventType.PAYMENT_REFUNDED
            ).count(),
            1,
        )

    @patch(REFUND_PATH)
    def test_partial_refunds_then_the_remainder(self, mock_refund):
        mock_refund.side_effect = [completed_refund("REF-1"), completed_refund("REF-2")]
        order_id = self.paid_order()

        first = self.client.post(refund_url(order_id), {"amount": "10.00"}, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["payment_status"], "partially_refunded")
        self.assertEqual(first.data["paypal_refundable_amount"], "39.00")
        self.assertEqual(len(first.data["paypal_refunds"]), 1)

        second = self.client.post(refund_url(order_id), {}, format="json")
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["payment_status"], "refunded")
        self.assertEqual(mock_refund.call_args.kwargs["amount"], Decimal("39.00"))
        self.assertEqual(PaymentRefund.objects.filter(order_id=order_id).count(), 2)

    @patch(REFUND_PATH)
    def test_cannot_refund_more_than_is_left(self, mock_refund):
        order_id = self.paid_order()

        response = self.client.post(refund_url(order_id), {"amount": "50.00"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("49.00", response.data["detail"])
        mock_refund.assert_not_called()
        self.assertFalse(PaymentRefund.objects.exists())

    @patch(REFUND_PATH)
    def test_refunding_a_fully_refunded_order_is_a_conflict(self, mock_refund):
        mock_refund.return_value = completed_refund()
        order_id = self.paid_order()
        self.client.post(refund_url(order_id), {}, format="json")

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(mock_refund.call_count, 1)

    @patch(REFUND_PATH)
    def test_rejects_non_positive_amounts(self, mock_refund):
        order_id = self.paid_order()
        for amount in ("0", "-5.00", "abc"):
            response = self.client.post(refund_url(order_id), {"amount": amount}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, amount)
        mock_refund.assert_not_called()

    @patch(REFUND_PATH)
    def test_unpaid_order_is_a_conflict(self, mock_refund):
        order_id = self.confirmed_order()

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        mock_refund.assert_not_called()

    @patch(REFUND_PATH)
    def test_order_marked_paid_offline_has_nothing_to_refund(self, mock_refund):
        order_id = self.confirmed_order()
        self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("offline", response.data["detail"])
        mock_refund.assert_not_called()

    @patch(REFUND_PATH)
    def test_other_stores_order_is_404(self, mock_refund):
        order_id = self.paid_order()
        self.client.force_authenticate(self.other)

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_refund.assert_not_called()

    @patch(REFUND_PATH)
    def test_paypal_rejection_fails_the_refund_and_keeps_the_order_paid(self, mock_refund):
        mock_refund.side_effect = BadGatewayError(
            "PayPal only allows refunds within 180 days of the payment.",
            extra={"paypal_issue": "REFUND_TIME_LIMIT_EXCEEDED"},
        )
        order_id = self.paid_order()

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["paypal_issue"], "REFUND_TIME_LIMIT_EXCEEDED")
        refund = PaymentRefund.objects.get(order_id=order_id)
        self.assertEqual(refund.status, PaymentRefund.Status.FAILED)
        self.assertIn("180 days", refund.last_error)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
        # The failed attempt frees the amount, so the seller can retry.
        mock_refund.side_effect = None
        mock_refund.return_value = completed_refund()
        retry = self.client.post(refund_url(order_id), {}, format="json")
        self.assertEqual(retry.status_code, status.HTTP_200_OK)

    @patch(REFUND_PATH)
    def test_pending_paypal_refund_is_counted_and_applied(self, mock_refund):
        mock_refund.return_value = {"id": "REF-P", "status": "PENDING", "raw": {}}
        order_id = self.paid_order()

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_status"], "refunded")
        self.assertEqual(
            PaymentRefund.objects.get(order_id=order_id).status, PaymentRefund.Status.PENDING
        )

    @patch(REFUND_PATH)
    def test_failed_paypal_refund_status_is_a_conflict_and_changes_nothing(self, mock_refund):
        mock_refund.return_value = {"id": "REF-F", "status": "FAILED", "raw": {}}
        order_id = self.paid_order()

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
        self.assertEqual(
            PaymentRefund.objects.get(order_id=order_id).status, PaymentRefund.Status.FAILED
        )

    @patch(REFUND_PATH)
    def test_invoice_payment_is_refunded_through_its_payment_id(self, mock_refund):
        mock_refund.return_value = completed_refund()
        order_id = self.confirmed_order()
        PaymentInvoice.objects.create(
            order_id=order_id,
            paypal_invoice_id="INV2-1",
            invoice_number="ORB-1-1",
            status=PaymentInvoice.Status.PAID,
            capture_id="CAP-INV-1",
            amount=Decimal("49.00"),
            currency="USD",
        )
        self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_refund.call_args.kwargs["capture_id"], "CAP-INV-1")

    @patch(REFUND_PATH)
    def test_fulfilment_follows_the_refund_state(self, mock_refund):
        mock_refund.side_effect = [completed_refund("REF-1"), completed_refund("REF-2")]
        order_id = self.paid_order()
        advance = {"fulfilment_status": "processing"}

        self.client.post(refund_url(order_id), {"amount": "10.00"}, format="json")
        partly = self.client.post(
            f"/api/v1/orders/{order_id}/transition/", advance, format="json"
        )
        self.assertEqual(partly.status_code, status.HTTP_200_OK)

        self.client.post(refund_url(order_id), {}, format="json")
        shipped = self.client.post(
            f"/api/v1/orders/{order_id}/transition/",
            {"fulfilment_status": "shipped"},
            format="json",
        )
        self.assertEqual(shipped.status_code, status.HTTP_409_CONFLICT)

    @patch(REFUND_PATH)
    def test_a_cancelled_paid_order_can_still_be_refunded(self, mock_refund):
        mock_refund.return_value = completed_refund()
        order_id = self.paid_order()
        cancelled = self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelled.data["payment_status"], "paid")

        response = self.client.post(refund_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_status"], "refunded")
        self.assertEqual(response.data["fulfilment_status"], "cancelled")


class RefundWebhookTests(PayPalTestCase):
    @patch(REFUND_PATH)
    def test_webhook_echo_of_our_refund_is_not_counted_twice(self, mock_refund):
        mock_refund.return_value = completed_refund("REF-1")
        order_id = self.paid_order()
        self.client.post(refund_url(order_id), {"amount": "10.00"}, format="json")

        self.deliver(
            "PAYMENT.CAPTURE.REFUNDED",
            {"id": "REF-1", "status": "COMPLETED", "amount": {"currency_code": "USD", "value": "10.00"}},
        )

        self.assertEqual(PaymentRefund.objects.filter(order_id=order_id).count(), 1)
        self.assertEqual(
            OrderEvent.objects.filter(
                order_id=order_id, event_type=OrderEvent.EventType.PAYMENT_REFUNDED
            ).count(),
            1,
        )
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "partially_refunded")

    def test_refund_made_in_the_paypal_dashboard_syncs_to_the_order(self):
        order_id = self.paid_order(capture_id="CAP-1")

        event = self.deliver(
            "PAYMENT.CAPTURE.REFUNDED",
            {
                "id": "REF-DASH",
                "status": "COMPLETED",
                "amount": {"currency_code": "USD", "value": "49.00"},
                "links": [
                    {
                        "rel": "up",
                        "href": "https://api.sandbox.paypal.com/v2/payments/captures/CAP-1",
                    }
                ],
            },
        )

        self.assertEqual(event.order_id, order_id)
        refund = PaymentRefund.objects.get(order_id=order_id)
        self.assertEqual(refund.source, PaymentRefund.Source.PAYPAL)
        self.assertEqual(refund.paypal_refund_id, "REF-DASH")
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "refunded")

    def test_duplicate_dashboard_refund_delivery_changes_nothing_more(self):
        order_id = self.paid_order(capture_id="CAP-1")
        resource = {
            "id": "REF-DASH",
            "status": "COMPLETED",
            "amount": {"currency_code": "USD", "value": "20.00"},
            "links": [
                {"rel": "up", "href": "https://api.sandbox.paypal.com/v2/payments/captures/CAP-1"}
            ],
        }

        self.deliver("PAYMENT.CAPTURE.REFUNDED", resource, event_id="WH-A")
        self.deliver("PAYMENT.CAPTURE.REFUNDED", resource, event_id="WH-B")

        self.assertEqual(PaymentRefund.objects.filter(order_id=order_id).count(), 1)
        self.assertEqual(
            OrderEvent.objects.filter(
                order_id=order_id, event_type=OrderEvent.EventType.PAYMENT_REFUNDED
            ).count(),
            1,
        )

    def test_a_refund_webhook_never_marks_an_order_paid(self):
        # A refund resource is status COMPLETED too; it must not read as a capture.
        order_id = self.confirmed_order()
        checkout = PaymentCheckout.objects.create(
            order_id=order_id,
            paypal_order_id="PP-OPEN",
            status=PaymentCheckout.Status.CREATED,
            amount=Decimal("49.00"),
            currency="USD",
        )

        self.deliver(
            "PAYMENT.CAPTURE.REFUNDED",
            {
                "id": "REF-X",
                "status": "COMPLETED",
                "custom_id": str(order_id),
                "amount": {"currency_code": "USD", "value": "49.00"},
            },
        )

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "pending")
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.CREATED)
        self.assertEqual(checkout.capture_id, "")
