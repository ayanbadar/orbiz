from decimal import Decimal
from unittest.mock import patch

from rest_framework import status

from apps.common.exceptions import BadGatewayError
from apps.orders.models import Order, OrderEvent
from apps.payments.models import PaymentCheckout, PaymentInvoice
from apps.payments.tests.base import PayPalTestCase

CLIENT = "apps.payments.services.paypal_client"
VIEW_URL = "https://www.sandbox.paypal.com/invoice/p/#INV2-1"


def invoice_url(order_id: int) -> str:
    return f"/api/v1/payments/orders/{order_id}/invoice/"


def remote_invoice(status_: str = "SENT", payment_id: str = "") -> dict:
    invoice = {
        "id": "INV2-1",
        "status": status_,
        "detail": {"metadata": {"recipient_view_url": VIEW_URL}},
    }
    if payment_id:
        invoice["payments"] = {"transactions": [{"type": "PAYPAL", "payment_id": payment_id}]}
    return invoice


@patch(f"{CLIENT}.get_invoice")
@patch(f"{CLIENT}.send_invoice")
@patch(f"{CLIENT}.create_invoice")
class InvoiceSendTests(PayPalTestCase):
    def test_invoice_with_an_email_is_emailed_by_paypal(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()

        response = self.client.post(
            invoice_url(order_id), {"recipient_email": "Buyer@Example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send.assert_called_once_with(invoice_id="INV2-1", send_to_recipient=True)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["recipient_email"], "buyer@example.com")
        self.assertEqual(kwargs["recipient_name"], "Ayesha Khan")
        self.assertEqual(kwargs["reference"], f"orbiz-order:{order_id}")
        self.assertEqual(
            kwargs["items"],
            [{"name": "Black Hoodie", "quantity": 1, "unit_price": Decimal("49.00")}],
        )
        invoice = PaymentInvoice.objects.get(order_id=order_id)
        self.assertEqual(invoice.status, PaymentInvoice.Status.SENT)
        self.assertEqual(invoice.paypal_invoice_id, "INV2-1")
        self.assertEqual(invoice.recipient_view_url, VIEW_URL)
        self.assertEqual(invoice.amount, Decimal("49.00"))
        self.assertIsNotNone(invoice.sent_at)
        self.assertEqual(response.data["paypal_invoice"]["status"], "sent")
        self.assertEqual(response.data["payment_status"], "pending")
        event = OrderEvent.objects.get(
            order_id=order_id, event_type=OrderEvent.EventType.INVOICE_SENT
        )
        self.assertIn("buyer@example.com", event.message)

    def test_blank_email_makes_a_link_only_invoice(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()

        response = self.client.post(invoice_url(order_id), {"recipient_email": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send.assert_called_once_with(invoice_id="INV2-1", send_to_recipient=False)
        self.assertEqual(create.call_args.kwargs["recipient_email"], "")
        self.assertEqual(response.data["paypal_invoice"]["status"], "shared")
        self.assertEqual(response.data["paypal_invoice"]["recipient_view_url"], VIEW_URL)

    def test_email_is_optional_in_the_request_body(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()

        response = self.client.post(invoice_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send.assert_called_once_with(invoice_id="INV2-1", send_to_recipient=False)

    def test_invalid_email_is_rejected(self, create, send, get):
        order_id = self.confirmed_order()

        response = self.client.post(
            invoice_url(order_id), {"recipient_email": "not-an-email"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        create.assert_not_called()

    def test_sending_an_invoice_supersedes_the_open_checkout(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()
        checkout = PaymentCheckout.objects.create(
            order_id=order_id,
            paypal_order_id="PP-OPEN",
            status=PaymentCheckout.Status.CREATED,
            amount=Decimal("49.00"),
            currency="USD",
        )

        self.client.post(invoice_url(order_id), {}, format="json")

        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.CANCELLED)

    def test_resending_cancels_the_previous_invoice_first(self, create, send, get):
        create.side_effect = [{"id": "INV2-1", "raw": {}}, {"id": "INV2-2", "raw": {}}]
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()
        self.client.post(invoice_url(order_id), {}, format="json")

        with patch(f"{CLIENT}.cancel_invoice") as cancel:
            response = self.client.post(invoice_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cancel.assert_called_once_with(invoice_id="INV2-1")
        statuses = list(
            PaymentInvoice.objects.filter(order_id=order_id)
            .order_by("id")
            .values_list("status", flat=True)
        )
        self.assertEqual(statuses, ["cancelled", "shared"])
        numbers = set(
            PaymentInvoice.objects.filter(order_id=order_id).values_list(
                "invoice_number", flat=True
            )
        )
        self.assertEqual(len(numbers), 2)

    def test_paypal_failure_is_recorded_and_leaves_the_order_alone(self, create, send, get):
        create.side_effect = BadGatewayError(
            "PayPal denied the request.", extra={"paypal_issue": "PERMISSION_DENIED"}
        )
        order_id = self.confirmed_order()

        response = self.client.post(invoice_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["paypal_issue"], "PERMISSION_DENIED")
        invoice = PaymentInvoice.objects.get(order_id=order_id)
        self.assertEqual(invoice.status, PaymentInvoice.Status.FAILED)
        self.assertIn("denied", invoice.last_error)
        send.assert_not_called()
        self.assertFalse(
            OrderEvent.objects.filter(
                order_id=order_id, event_type=OrderEvent.EventType.INVOICE_SENT
            ).exists()
        )

    def test_failed_send_keeps_the_created_draft_id_for_reference(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        send.side_effect = BadGatewayError("PayPal is temporarily unavailable.")
        order_id = self.confirmed_order()

        response = self.client.post(invoice_url(order_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        invoice = PaymentInvoice.objects.get(order_id=order_id)
        self.assertEqual(invoice.status, PaymentInvoice.Status.FAILED)
        self.assertEqual(invoice.paypal_invoice_id, "INV2-1")

    def test_guards(self, create, send, get):
        # draft
        created = self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": self.customer.id,
                "lines": [{"product_id": self.product.id, "quantity": 1}],
            },
            format="json",
        )
        draft = self.client.post(invoice_url(created.data["id"]), {}, format="json")
        self.assertEqual(draft.status_code, status.HTTP_409_CONFLICT)

        # paid
        paid_id = self.paid_order()
        paid = self.client.post(invoice_url(paid_id), {}, format="json")
        self.assertEqual(paid.status_code, status.HTTP_409_CONFLICT)

        # unsupported currency
        pkr_id = self.confirmed_order()
        Order.objects.filter(pk=pkr_id).update(currency="PKR")
        pkr = self.client.post(invoice_url(pkr_id), {}, format="json")
        self.assertEqual(pkr.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("PKR", pkr.data["detail"])

        # another store
        other_id = self.confirmed_order()
        self.client.force_authenticate(self.other)
        foreign = self.client.post(invoice_url(other_id), {}, format="json")
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)

        create.assert_not_called()


@patch(f"{CLIENT}.cancel_invoice")
class InvoiceCancelTests(PayPalTestCase):
    def _sent_invoice(self, order_id: int, status_=PaymentInvoice.Status.SENT):
        return PaymentInvoice.objects.create(
            order_id=order_id,
            paypal_invoice_id="INV2-1",
            invoice_number="ORB-1-1",
            status=status_,
            amount=Decimal("49.00"),
            currency="USD",
        )

    def test_cancel_cancels_at_paypal_and_locally(self, cancel):
        order_id = self.confirmed_order()
        invoice = self._sent_invoice(order_id)

        response = self.client.post(f"{invoice_url(order_id)}cancel/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cancel.assert_called_once_with(invoice_id="INV2-1")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.CANCELLED)
        self.assertEqual(response.data["paypal_invoice"]["status"], "cancelled")
        self.assertTrue(
            OrderEvent.objects.filter(
                order_id=order_id, event_type=OrderEvent.EventType.INVOICE_CANCELLED
            ).exists()
        )

    def test_cancelling_twice_is_a_conflict(self, cancel):
        order_id = self.confirmed_order()
        self._sent_invoice(order_id)
        self.client.post(f"{invoice_url(order_id)}cancel/", {}, format="json")

        again = self.client.post(f"{invoice_url(order_id)}cancel/", {}, format="json")

        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(cancel.call_count, 1)

    def test_already_cancelled_at_paypal_still_cancels_locally(self, cancel):
        cancel.side_effect = BadGatewayError(
            "PayPal rejected.", extra={"paypal_issue": "INVOICE_CANCELED_ALREADY"}
        )
        order_id = self.confirmed_order()
        invoice = self._sent_invoice(order_id)

        response = self.client.post(f"{invoice_url(order_id)}cancel/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.CANCELLED)

    def test_invoice_already_paid_at_paypal_is_a_conflict(self, cancel):
        cancel.side_effect = BadGatewayError(
            "PayPal rejected.", extra={"paypal_issue": "CANNOT_CANCEL_PAID_INVOICE"}
        )
        order_id = self.confirmed_order()
        invoice = self._sent_invoice(order_id)

        response = self.client.post(f"{invoice_url(order_id)}cancel/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.SENT)

    def test_nothing_open_to_cancel_is_a_conflict(self, cancel):
        order_id = self.confirmed_order()

        response = self.client.post(f"{invoice_url(order_id)}cancel/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        cancel.assert_not_called()

    def test_creating_a_checkout_cancels_the_open_invoice(self, cancel):
        order_id = self.confirmed_order()
        invoice = self._sent_invoice(order_id)

        with patch(f"{CLIENT}.create_order") as create_order:
            create_order.return_value = {
                "id": "PP-NEW",
                "status": "CREATED",
                "approve_url": "https://example.com/approve",
                "raw": {},
            }
            response = self.client.post(
                f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cancel.assert_called_once_with(invoice_id="INV2-1")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.CANCELLED)

    def test_checkout_fails_cleanly_when_the_invoice_cannot_be_cancelled(self, cancel):
        cancel.side_effect = BadGatewayError("PayPal is temporarily unavailable.")
        order_id = self.confirmed_order()
        invoice = self._sent_invoice(order_id)

        with patch(f"{CLIENT}.create_order") as create_order:
            response = self.client.post(
                f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
            )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        create_order.assert_not_called()
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.SENT)
        self.assertFalse(PaymentCheckout.objects.filter(order_id=order_id).exists())


class InvoiceWebhookTests(PayPalTestCase):
    def _open_invoice(self, order_id: int) -> PaymentInvoice:
        return PaymentInvoice.objects.create(
            order_id=order_id,
            paypal_invoice_id="INV2-1",
            invoice_number="ORB-1-1",
            status=PaymentInvoice.Status.SENT,
            recipient_email="buyer@example.com",
            amount=Decimal("49.00"),
            currency="USD",
        )

    @patch(f"{CLIENT}.get_invoice")
    def test_paid_invoice_marks_the_order_paid_once(self, get):
        get.return_value = remote_invoice("PAID", payment_id="CAP-INV-1")
        order_id = self.confirmed_order()
        invoice = self._open_invoice(order_id)

        event = self.deliver("INVOICING.INVOICE.PAID", {"id": "INV2-1"}, event_id="WH-1")
        self.deliver("INVOICING.INVOICE.PAID", {"id": "INV2-1"}, event_id="WH-2")

        self.assertEqual(event.order_id, order_id)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.PAID)
        self.assertEqual(invoice.capture_id, "CAP-INV-1")
        self.assertIsNotNone(invoice.paid_at)
        paid_events = OrderEvent.objects.filter(
            order_id=order_id,
            event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
            to_value="paid",
        )
        self.assertEqual(paid_events.count(), 1)
        self.assertIn("invoice ORB-1-1", paid_events.get().message)

    @patch(f"{CLIENT}.get_invoice")
    def test_nested_invoice_payload_is_understood(self, get):
        get.return_value = remote_invoice("PAID", payment_id="CAP-INV-1")
        order_id = self.confirmed_order()
        self._open_invoice(order_id)

        self.deliver("INVOICING.INVOICE.PAID", {"invoice": {"id": "INV2-1"}})

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")

    @patch(f"{CLIENT}.get_invoice")
    def test_cancelled_at_paypal_closes_the_invoice(self, get):
        get.return_value = remote_invoice("CANCELLED")
        order_id = self.confirmed_order()
        invoice = self._open_invoice(order_id)

        self.deliver("INVOICING.INVOICE.CANCELLED", {"id": "INV2-1"})

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.CANCELLED)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "pending")

    @patch(f"{CLIENT}.get_invoice")
    def test_invoices_orbiz_did_not_create_are_ignored_without_calling_paypal(self, get):
        event = self.deliver("INVOICING.INVOICE.PAID", {"id": "INV2-FOREIGN"})

        get.assert_not_called()
        self.assertIsNotNone(event.processed_at)

    @patch(f"{CLIENT}.get_invoice")
    def test_paypal_outage_leaves_the_event_unprocessed_for_retry(self, get):
        get.side_effect = BadGatewayError("PayPal is temporarily unavailable.")
        order_id = self.confirmed_order()
        self._open_invoice(order_id)

        with self.assertRaises(BadGatewayError):
            self.deliver("INVOICING.INVOICE.PAID", {"id": "INV2-1"}, event_id="WH-RETRY")

        from apps.payments.models import PayPalWebhookEvent

        self.assertIsNone(PayPalWebhookEvent.objects.get(event_id="WH-RETRY").processed_at)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "pending")

    def test_capture_for_an_invoice_number_pays_the_order(self):
        order_id = self.confirmed_order()
        self._open_invoice(order_id)

        self.deliver(
            "PAYMENT.CAPTURE.COMPLETED",
            {"id": "CAP-INV-1", "status": "COMPLETED", "invoice_id": "ORB-1-1"},
        )

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
