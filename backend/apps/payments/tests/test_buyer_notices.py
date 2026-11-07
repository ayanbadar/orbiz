from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from rest_framework import status

from apps.notifications.models import EmailLog
from apps.orders.models import Order
from apps.payments.models import PaymentCheckout, PaymentInvoice
from apps.payments.tests.base import PayPalTestCase
from apps.stores.models import StoreMembership

CLIENT = "apps.payments.services.paypal_client"


@override_settings(DEFAULT_FROM_EMAIL="Orbiz <noreply@orbiz.local>", NOTIFY_SELLER_ON_PAYMENT=False)
class BuyerNoticeTestCase(PayPalTestCase):
    def post(self, url: str, data: dict | None = None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, data or {}, format="json")

    def open_invoice(self, order_id: int) -> PaymentInvoice:
        return PaymentInvoice.objects.create(
            order_id=order_id,
            paypal_invoice_id="INV2-1",
            invoice_number=f"ORB-{order_id}-1",
            status=PaymentInvoice.Status.SENT,
            amount=Decimal("49.00"),
            currency="USD",
        )

    def pay_invoice_by_webhook(self, event_id: str):
        with self.captureOnCommitCallbacks(execute=True), patch(f"{CLIENT}.get_invoice") as get:
            get.return_value = {
                "id": "INV2-1",
                "status": "PAID",
                "payments": {"transactions": [{"type": "PAYPAL", "payment_id": "CAP-INV-1"}]},
            }
            return self.deliver("INVOICING.INVOICE.PAID", {"id": "INV2-1"}, event_id=event_id)


class PaymentReceiptTests(BuyerNoticeTestCase):
    def test_paying_an_invoice_sends_the_buyer_one_receipt(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        self.pay_invoice_by_webhook("WH-1")
        self.pay_invoice_by_webhook("WH-2")  # PayPal retries; the buyer must not get a second one

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["a@example.com"])
        self.assertTrue(message.subject.startswith("[Sandbox] Payment received for ORD-"))
        self.assertIn("USD 49.00", message.subject)
        self.assertIn("Black Hoodie", message.body)
        self.assertIn("Thank you", message.body)
        self.assertEqual(message.alternatives[0].mimetype, "text/html")
        self.assertIn("Demo Store via Orbiz", message.from_email)
        log = EmailLog.objects.get()
        self.assertEqual(log.kind, "payment_receipt")
        self.assertEqual(log.reference, f"order:{order_id}:paid")

    @patch(f"{CLIENT}.capture_order")
    @patch(f"{CLIENT}.create_order")
    def test_a_seller_capture_sends_a_receipt_replying_to_the_seller(self, create, capture):
        create.return_value = {
            "id": "PP-1",
            "status": "CREATED",
            "approve_url": "https://paypal.example/approve",
            "raw": {},
        }
        capture.return_value = {
            "id": "PP-1",
            "status": "COMPLETED",
            "capture_id": "CAP-1",
            "capture_status": "COMPLETED",
            "raw": {},
        }
        order_id = self.confirmed_order()
        self.post(f"/api/v1/payments/orders/{order_id}/checkout/")

        response = self.post(f"/api/v1/payments/orders/{order_id}/capture/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].reply_to, ["seller@example.com"])

    def test_a_webhook_after_the_capture_does_not_send_a_second_receipt(self):
        order_id = self.confirmed_order()
        PaymentCheckout.objects.create(
            order_id=order_id,
            paypal_order_id="PP-1",
            status=PaymentCheckout.Status.CREATED,
            amount=Decimal("49.00"),
            currency="USD",
        )
        resource = {"id": "CAP-1", "status": "COMPLETED", "custom_id": str(order_id)}

        with self.captureOnCommitCallbacks(execute=True):
            self.deliver("PAYMENT.CAPTURE.COMPLETED", resource, event_id="WH-A")
        with self.captureOnCommitCallbacks(execute=True):
            self.deliver("PAYMENT.CAPTURE.COMPLETED", resource, event_id="WH-B")

        self.assertEqual(len(mail.outbox), 1)

    def test_no_customer_email_means_no_receipt_but_the_order_is_still_paid(self):
        self.customer.email = ""
        self.customer.save(update_fields=["email"])
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        self.pay_invoice_by_webhook("WH-1")

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
        self.assertEqual(len(mail.outbox), 0)

    def test_marking_an_order_paid_offline_sends_no_paypal_receipt(self):
        order_id = self.confirmed_order()

        self.post(f"/api/v1/orders/{order_id}/mark-paid/")

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
        self.assertEqual(len(mail.outbox), 0)

    def test_a_failure_to_queue_the_email_never_blocks_the_payment(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        with patch("apps.payments.services.queue_email", side_effect=RuntimeError("db down")):
            self.pay_invoice_by_webhook("WH-1")

        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "paid")
        self.assertEqual(len(mail.outbox), 0)


class RefundNoticeTests(BuyerNoticeTestCase):
    @patch(f"{CLIENT}.refund_capture")
    def test_a_refund_emails_the_buyer_once(self, refund):
        refund.return_value = {"id": "REF-1", "status": "COMPLETED", "raw": {}}
        order_id = self.paid_order()

        response = self.post(f"/api/v1/payments/orders/{order_id}/refund/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["a@example.com"])
        self.assertTrue(message.subject.startswith("[Sandbox] Refund issued for ORD-"))
        self.assertIn("fully refunded", message.body)
        self.assertIn("Refunded: USD 49.00", message.body)
        self.assertEqual(message.reply_to, ["seller@example.com"])
        self.assertEqual(EmailLog.objects.get().kind, "refund_notice")

    @patch(f"{CLIENT}.refund_capture")
    def test_a_partial_refund_says_so_and_each_refund_gets_its_own_notice(self, refund):
        refund.side_effect = [
            {"id": "REF-1", "status": "COMPLETED", "raw": {}},
            {"id": "REF-2", "status": "COMPLETED", "raw": {}},
        ]
        order_id = self.paid_order()

        self.post(f"/api/v1/payments/orders/{order_id}/refund/", {"amount": "10.00"})
        self.post(f"/api/v1/payments/orders/{order_id}/refund/")

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("partially refunded", mail.outbox[0].body)
        self.assertIn("Refunded: USD 10.00", mail.outbox[0].body)
        self.assertIn("fully refunded", mail.outbox[1].body)
        self.assertIn("Refunded: USD 39.00", mail.outbox[1].body)

    @patch(f"{CLIENT}.refund_capture")
    def test_the_webhook_echo_of_our_own_refund_sends_no_second_notice(self, refund):
        refund.return_value = {"id": "REF-1", "status": "COMPLETED", "raw": {}}
        order_id = self.paid_order()
        self.post(f"/api/v1/payments/orders/{order_id}/refund/")

        with self.captureOnCommitCallbacks(execute=True):
            self.deliver(
                "PAYMENT.CAPTURE.REFUNDED",
                {
                    "id": "REF-1",
                    "status": "COMPLETED",
                    "amount": {"value": "49.00", "currency_code": "USD"},
                    "links": [
                        {"rel": "up", "href": "https://api.sandbox.paypal.com/v2/payments/captures/CAP-1"}
                    ],
                },
                event_id="WH-REF",
            )

        self.assertEqual(len(mail.outbox), 1)


@override_settings(NOTIFY_SELLER_ON_PAYMENT=True, FRONTEND_URL="https://app.example.com")
class SellerPaymentNoticeTests(BuyerNoticeTestCase):
    def seller_mail(self):
        return [m for m in mail.outbox if m.subject.find("You got paid") != -1]

    def test_the_seller_is_told_once_when_an_invoice_is_paid(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        self.pay_invoice_by_webhook("WH-1")
        self.pay_invoice_by_webhook("WH-2")  # PayPal retries

        notices = self.seller_mail()
        self.assertEqual(len(notices), 1)
        message = notices[0]
        self.assertEqual(message.to, ["seller@example.com"])
        self.assertTrue(message.subject.startswith("[Sandbox] You got paid: ORD-"))
        self.assertIn("USD 49.00", message.subject)
        self.assertIn("Ayesha Khan paid order", message.body)
        self.assertIn(f"through PayPal invoice ORB-{order_id}-1", message.body)
        self.assertIn(f"View order: https://app.example.com/orders/{order_id}", message.body)
        self.assertIn("Black Hoodie", message.body)
        self.assertIn("View order", message.alternatives[0].content)
        self.assertEqual(message.from_email, "Orbiz <noreply@orbiz.local>")
        log = EmailLog.objects.get(kind="seller_payment_notice")
        self.assertEqual(log.reference, f"order:{order_id}:paid:seller")

    @patch(f"{CLIENT}.capture_order")
    @patch(f"{CLIENT}.create_order")
    def test_a_checkout_capture_says_it_was_a_checkout(self, create, capture):
        create.return_value = {
            "id": "PP-1",
            "status": "CREATED",
            "approve_url": "https://paypal.example/approve",
            "raw": {},
        }
        capture.return_value = {
            "id": "PP-1",
            "status": "COMPLETED",
            "capture_id": "CAP-1",
            "capture_status": "COMPLETED",
            "raw": {},
        }
        order_id = self.confirmed_order()
        self.post(f"/api/v1/payments/orders/{order_id}/checkout/")

        self.post(f"/api/v1/payments/orders/{order_id}/capture/")

        self.assertIn("through PayPal checkout", self.seller_mail()[0].body)

    def test_every_store_member_is_told_and_other_stores_are_not(self):
        StoreMembership.objects.create(store=self.store, user=self.other, role="member")
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        self.pay_invoice_by_webhook("WH-1")

        recipients = sorted(address for m in self.seller_mail() for address in m.to)
        self.assertEqual(recipients, ["other@example.com", "seller@example.com"])

    def test_the_seller_is_told_even_when_the_customer_has_no_email(self):
        self.customer.email = ""
        self.customer.save(update_fields=["email"])
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        self.pay_invoice_by_webhook("WH-1")

        self.assertEqual(len(self.seller_mail()), 1)
        self.assertEqual(len(mail.outbox), 1)  # no buyer receipt

    @override_settings(NOTIFY_SELLER_ON_PAYMENT=False)
    def test_it_can_be_switched_off(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        self.pay_invoice_by_webhook("WH-1")

        self.assertEqual(self.seller_mail(), [])

    def test_marking_paid_offline_does_not_email_the_seller(self):
        order_id = self.confirmed_order()

        self.post(f"/api/v1/orders/{order_id}/mark-paid/")

        self.assertEqual(self.seller_mail(), [])


class OrderConfirmedNoticeTests(BuyerNoticeTestCase):
    def draft_order(self) -> int:
        created = self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": self.customer.id,
                "lines": [{"product_id": self.product.id, "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        return created.data["id"]

    def test_confirming_with_the_box_ticked_emails_the_customer(self):
        order_id = self.draft_order()

        response = self.post(f"/api/v1/orders/{order_id}/confirm/", {"notify_customer": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fulfilment_status"], "unfulfilled")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["a@example.com"])
        self.assertTrue(message.subject.startswith("[Sandbox] Order confirmed: ORD-"))
        self.assertIn("USD 49.00", message.subject)
        self.assertIn("Black Hoodie", message.body)
        self.assertIn("Order total: USD 49.00", message.body)
        self.assertIn("payment link separately", message.body)
        self.assertEqual(message.reply_to, ["seller@example.com"])
        self.assertEqual(EmailLog.objects.get().reference, f"order:{order_id}:confirmed")

    def test_confirming_without_the_box_sends_nothing(self):
        order_id = self.draft_order()

        plain = self.post(f"/api/v1/orders/{order_id}/confirm/")

        self.assertEqual(plain.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_ticking_the_box_for_a_customer_without_email_is_refused_before_confirming(self):
        self.customer.email = ""
        self.customer.save(update_fields=["email"])
        order_id = self.draft_order()

        response = self.post(f"/api/v1/orders/{order_id}/confirm/", {"notify_customer": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("notify_customer", response.data)
        self.assertEqual(Order.objects.get(pk=order_id).fulfilment_status, "draft")
        self.assertEqual(len(mail.outbox), 0)

    def test_a_second_confirm_conflicts_and_sends_no_second_email(self):
        order_id = self.draft_order()
        self.post(f"/api/v1/orders/{order_id}/confirm/", {"notify_customer": True})

        again = self.post(f"/api/v1/orders/{order_id}/confirm/", {"notify_customer": True})

        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(len(mail.outbox), 1)
