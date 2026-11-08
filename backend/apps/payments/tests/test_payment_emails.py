import smtplib
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status

from apps.common.exceptions import BadGatewayError
from apps.notifications.models import EmailLog, EmailStatus
from apps.orders.models import Order, OrderEvent
from apps.payments.emails import sender_for
from apps.payments.models import PaymentCheckout, PaymentInvoice
from apps.payments.tests.base import PayPalTestCase
from apps.payments.tests.test_invoices import VIEW_URL, invoice_url, remote_invoice

CLIENT = "apps.payments.services.paypal_client"
APPROVE_URL = "https://www.sandbox.paypal.com/checkoutnow?token=PP-OPEN"

EMAIL_SETTINGS = dict(
    DEFAULT_FROM_EMAIL="Orbiz <noreply@orbiz.local>",
    PAYPAL_INVOICE_DELIVERY="orbiz",
    PAYMENT_EMAIL_COOLDOWN_SECONDS=120,
)


def email_link_url(order_id: int) -> str:
    return f"/api/v1/payments/orders/{order_id}/email-link/"


@override_settings(**EMAIL_SETTINGS)
class PayPalEmailTestCase(PayPalTestCase):
    def post(self, url: str, data: dict | None = None):
        """POST and run the queued email task, as the Celery worker would after commit."""
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, data or {}, format="json")

    def request_summary(self, order_id: int) -> dict:
        return self.client.get(f"/api/v1/orders/{order_id}/").data["paypal_payment_request"]

    def open_invoice(self, order_id: int, **overrides) -> PaymentInvoice:
        values = dict(
            order_id=order_id,
            paypal_invoice_id="INV2-1",
            invoice_number=f"ORB-{order_id}-1",
            status=PaymentInvoice.Status.SHARED,
            recipient_view_url=VIEW_URL,
            amount=Decimal("49.00"),
            currency="USD",
        )
        values.update(overrides)
        return PaymentInvoice.objects.create(**values)

    def open_checkout(self, order_id: int, **overrides) -> PaymentCheckout:
        values = dict(
            order_id=order_id,
            paypal_order_id="PP-OPEN",
            status=PaymentCheckout.Status.CREATED,
            approve_url=APPROVE_URL,
            amount=Decimal("49.00"),
            currency="USD",
        )
        values.update(overrides)
        return PaymentCheckout.objects.create(**values)


@patch(f"{CLIENT}.get_invoice")
@patch(f"{CLIENT}.send_invoice")
@patch(f"{CLIENT}.create_invoice")
class RequestPaymentEmailTests(PayPalEmailTestCase):
    def test_orbiz_delivery_creates_a_link_only_invoice_and_emails_the_buyer(
        self, create, send, get
    ):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()

        response = self.post(invoice_url(order_id), {"recipient_email": "Buyer@Example.com"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # PayPal must not email as well, or the buyer gets two.
        send.assert_called_once_with(invoice_id="INV2-1", send_to_recipient=False)
        invoice = PaymentInvoice.objects.get(order_id=order_id)
        self.assertEqual(invoice.status, PaymentInvoice.Status.SENT)
        self.assertEqual(invoice.delivered_via, PaymentInvoice.Delivery.ORBIZ)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["buyer@example.com"])
        self.assertEqual(
            message.subject,
            f"[Sandbox] Invoice {invoice.invoice_number} from Demo Store - USD 49.00 due",
        )
        self.assertIn(VIEW_URL, message.body)
        self.assertIn("no real money moves", message.body)
        self.assertIn("Black Hoodie", message.body)
        self.assertEqual(message.alternatives[0].mimetype, "text/html")
        self.assertIn(VIEW_URL, message.alternatives[0].content)
        self.assertEqual(message.reply_to, ["seller@example.com"])
        self.assertIn("Demo Store via Orbiz", message.from_email)
        self.assertIn("noreply@orbiz.local", message.from_email)

        log = EmailLog.objects.get()
        self.assertEqual(log.status, EmailStatus.SENT)
        self.assertEqual(log.kind, "payment_request")
        self.assertEqual(log.reference, f"order:{order_id}:invoice:{invoice.invoice_number}")
        event = OrderEvent.objects.get(
            order_id=order_id, event_type=OrderEvent.EventType.INVOICE_SENT
        )
        self.assertIn("buyer@example.com", event.message)
        self.assertIn("by Orbiz", event.message)

    @override_settings(PAYPAL_INVOICE_DELIVERY="paypal")
    def test_paypal_delivery_sends_no_orbiz_email(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()

        response = self.post(invoice_url(order_id), {"recipient_email": "buyer@example.com"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send.assert_called_once_with(invoice_id="INV2-1", send_to_recipient=True)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EmailLog.objects.exists())

    def test_no_address_means_no_email_in_either_mode(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = remote_invoice()
        order_id = self.confirmed_order()

        response = self.post(invoice_url(order_id), {"recipient_email": ""})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send.assert_called_once_with(invoice_id="INV2-1", send_to_recipient=False)
        self.assertEqual(response.data["paypal_invoice"]["delivered_via"], "none")
        self.assertEqual(len(mail.outbox), 0)

    def test_an_invoice_without_a_payable_link_cannot_be_emailed(self, create, send, get):
        create.return_value = {"id": "INV2-1", "raw": {}}
        get.return_value = {"id": "INV2-1", "status": "UNPAID", "detail": {}}
        order_id = self.confirmed_order()

        response = self.post(invoice_url(order_id), {"recipient_email": "buyer@example.com"})

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            PaymentInvoice.objects.get(order_id=order_id).status, PaymentInvoice.Status.FAILED
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_a_paypal_failure_sends_nothing(self, create, send, get):
        create.side_effect = BadGatewayError("PayPal is temporarily unavailable.")
        order_id = self.confirmed_order()

        response = self.post(invoice_url(order_id), {"recipient_email": "buyer@example.com"})

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(len(mail.outbox), 0)


class EmailLinkTests(PayPalEmailTestCase):
    def test_emails_the_open_checkout_link_to_the_customer_by_default(self):
        order_id = self.confirmed_order()
        self.open_checkout(order_id)

        response = self.post(email_link_url(order_id), {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["a@example.com"])  # the customer on file
        self.assertIn(APPROVE_URL, message.body)
        self.assertIn(APPROVE_URL, message.alternatives[0].content)
        event = OrderEvent.objects.get(
            order_id=order_id, event_type=OrderEvent.EventType.PAYMENT_LINK_EMAILED
        )
        self.assertIn("a@example.com", event.message)
        self.assertIn("checkout link", event.message)
        # The response is built before the worker runs, so it reports the email as queued.
        self.assertEqual(response.data["paypal_payment_request"]["kind"], "checkout")
        self.assertEqual(response.data["paypal_payment_request"]["last_email_status"], "queued")
        self.assertEqual(self.request_summary(order_id)["last_email_status"], "sent")

    def test_emailing_a_link_only_invoice_turns_it_into_a_sent_one(self):
        order_id = self.confirmed_order()
        invoice = self.open_invoice(order_id)

        response = self.post(email_link_url(order_id), {"recipient_email": "Other@Example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(VIEW_URL, mail.outbox[0].body)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PaymentInvoice.Status.SENT)
        self.assertEqual(invoice.recipient_email, "other@example.com")
        self.assertEqual(invoice.delivered_via, PaymentInvoice.Delivery.ORBIZ)
        self.assertEqual(response.data["paypal_payment_request"]["kind"], "invoice")

    def test_a_reminder_is_labelled_as_one(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id, status=PaymentInvoice.Status.SENT)

        response = self.post(email_link_url(order_id), {"kind": "reminder"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Reminder:", mail.outbox[0].subject)
        self.assertEqual(EmailLog.objects.get().kind, "payment_reminder")
        event = OrderEvent.objects.get(
            order_id=order_id, event_type=OrderEvent.EventType.PAYMENT_LINK_EMAILED
        )
        self.assertIn("reminder", event.message)

    def test_the_same_address_is_refused_during_the_cooldown(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id)
        self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})

        again = self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})

        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(again.data["code"], "email_cooldown")
        self.assertEqual(len(mail.outbox), 1)

    def test_another_address_or_an_expired_cooldown_is_allowed(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id)
        self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})

        other = self.post(email_link_url(order_id), {"recipient_email": "c@example.com"})
        EmailLog.objects.update(created_at=timezone.now() - timedelta(minutes=5))
        later = self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})

        self.assertEqual(other.status_code, status.HTTP_200_OK)
        self.assertEqual(later.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 3)

    def test_the_initial_send_counts_towards_the_cooldown(self):
        order_id = self.confirmed_order()
        with patch(f"{CLIENT}.create_invoice") as create, patch(
            f"{CLIENT}.send_invoice"
        ), patch(f"{CLIENT}.get_invoice") as get:
            create.return_value = {"id": "INV2-1", "raw": {}}
            get.return_value = remote_invoice()
            self.post(invoice_url(order_id), {"recipient_email": "b@example.com"})

        double_click = self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})

        self.assertEqual(double_click.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_failed_email_can_be_resent_immediately(self):
        order_id = self.confirmed_order()
        invoice = self.open_invoice(order_id)
        EmailLog.objects.create(
            kind="payment_request",
            reference=f"order:{order_id}:invoice:{invoice.invoice_number}",
            recipient="b@example.com",
            sender="Orbiz <noreply@orbiz.local>",
            subject="x",
            body="x",
            status=EmailStatus.FAILED,
            error_message="SMTP 535: bad credentials",
        )

        response = self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_stale_checkout_is_replaced_before_it_is_emailed(self):
        order_id = self.confirmed_order()
        old = self.open_checkout(order_id)
        PaymentCheckout.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(hours=30)
        )
        fresh_url = "https://www.sandbox.paypal.com/checkoutnow?token=PP-FRESH"

        with patch(f"{CLIENT}.create_order") as create_order:
            create_order.return_value = {
                "id": "PP-FRESH",
                "status": "CREATED",
                "approve_url": fresh_url,
                "raw": {},
            }
            response = self.post(email_link_url(order_id), {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        old.refresh_from_db()
        self.assertEqual(old.status, PaymentCheckout.Status.CANCELLED)
        self.assertIn(fresh_url, mail.outbox[0].body)
        self.assertNotIn(APPROVE_URL, mail.outbox[0].body)

    def test_a_recent_checkout_is_not_replaced(self):
        order_id = self.confirmed_order()
        self.open_checkout(order_id)

        with patch(f"{CLIENT}.create_order") as create_order:
            self.post(email_link_url(order_id), {})

        create_order.assert_not_called()

    def test_guards(self):
        # nothing open to email
        order_id = self.confirmed_order()
        nothing = self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})
        self.assertEqual(nothing.status_code, status.HTTP_409_CONFLICT)

        # no address anywhere
        self.customer.email = ""
        self.customer.save(update_fields=["email"])
        self.open_checkout(order_id)
        missing = self.post(email_link_url(order_id), {})
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing.data["code"], "recipient_required")

        # invalid address
        invalid = self.post(email_link_url(order_id), {"recipient_email": "nope"})
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        # already paid
        paid_id = self.paid_order()
        self.open_checkout(paid_id, paypal_order_id="PP-PAID", status="captured")
        paid = self.post(email_link_url(paid_id), {"recipient_email": "b@example.com"})
        self.assertEqual(paid.status_code, status.HTTP_409_CONFLICT)

        # another store's order
        other_id = self.confirmed_order()
        self.open_checkout(other_id, paypal_order_id="PP-OTHER")
        self.client.force_authenticate(self.other)
        foreign = self.post(email_link_url(other_id), {"recipient_email": "b@example.com"})
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(len(mail.outbox), 0)

    def test_a_dead_smtp_server_leaves_a_failed_log_and_the_request_is_still_recorded(self):
        order_id = self.confirmed_order()
        self.open_invoice(order_id)

        with patch(
            "apps.notifications.tasks.EmailMultiAlternatives.send",
            side_effect=smtplib.SMTPAuthenticationError(535, b"bad credentials"),
        ):
            response = self.post(email_link_url(order_id), {"recipient_email": "b@example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summary = self.request_summary(order_id)
        self.assertEqual(summary["last_email_status"], "failed")
        self.assertIn("SMTP 535", summary["last_email_error"])


class PaymentRequestSummaryTests(PayPalEmailTestCase):
    def summary(self, order_id: int) -> dict:
        return self.request_summary(order_id)

    def test_none_when_nothing_is_open(self):
        order_id = self.confirmed_order()

        summary = self.summary(order_id)

        self.assertEqual(summary["kind"], "none")
        self.assertFalse(summary["can_email"])
        self.assertEqual(summary["delivery_mode"], "orbiz")

    def test_describes_an_open_invoice_and_its_latest_email(self):
        order_id = self.confirmed_order()
        invoice = self.open_invoice(
            order_id,
            status=PaymentInvoice.Status.SENT,
            recipient_email="b@example.com",
            delivered_via=PaymentInvoice.Delivery.ORBIZ,
        )
        EmailLog.objects.create(
            reference=f"order:{order_id}:invoice:{invoice.invoice_number}",
            recipient="b@example.com",
            sender="x",
            subject="x",
            body="x",
            status=EmailStatus.QUEUED,
        )

        summary = self.summary(order_id)

        self.assertEqual(summary["kind"], "invoice")
        self.assertEqual(summary["url"], VIEW_URL)
        self.assertEqual(summary["delivered_via"], "orbiz")
        self.assertEqual(summary["last_email_status"], "queued")
        self.assertTrue(summary["can_email"])

    def test_none_once_the_order_is_paid(self):
        order_id = self.paid_order()
        self.open_invoice(order_id, status=PaymentInvoice.Status.SENT)

        self.assertEqual(self.summary(order_id)["kind"], "none")


class SenderTests(PayPalEmailTestCase):
    def test_store_names_cannot_inject_headers(self):
        self.store.name = "Evil\nBcc: victim@example.com"

        sender = sender_for(self.store)

        self.assertNotIn("\n", sender)
        self.assertTrue(sender.endswith("<noreply@orbiz.local>"))


class EmailContentTests(PayPalEmailTestCase):
    """An invoice reads like an invoice; a checkout link is a short pay-now nudge."""

    def sent(self, order_id: int, **data):
        response = self.post(email_link_url(order_id), {"recipient_email": "b@example.com", **data})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return mail.outbox[-1]

    def test_invoice_email_has_invoice_details(self):
        order_id = self.confirmed_order()
        invoice = self.open_invoice(order_id)

        message = self.sent(order_id)

        self.assertEqual(
            message.subject,
            f"[Sandbox] Invoice {invoice.invoice_number} from Demo Store - USD 49.00 due",
        )
        for expected in (
            f"INVOICE {invoice.invoice_number}",
            "Billed to: Ayesha Khan <a@example.com>",
            "Due:     On receipt",
            f"Order:   ORD-",
            "1 x Black Hoodie  @ USD 49.00  =  USD 49.00",
            "TOTAL DUE: USD 49.00",
            VIEW_URL,
        ):
            self.assertIn(expected, message.body)
        html = message.alternatives[0].content
        for expected in ("Pay invoice", "Total due", "Description", "On receipt", "BILLED TO"):
            self.assertIn(expected, html)
        self.assertNotIn("Pay now on PayPal", message.body)

    def test_checkout_email_is_a_short_pay_now_nudge(self):
        order_id = self.confirmed_order()
        self.open_checkout(order_id)

        message = self.sent(order_id)

        self.assertRegex(message.subject, r"^\[Sandbox\] Pay USD 49\.00 to Demo Store for order ORD-")
        self.assertIn("Pay now on PayPal:", message.body)
        self.assertIn(APPROVE_URL, message.body)
        self.assertIn("Black Hoodie", message.body)  # a one-line summary, not a priced table
        self.assertIn("may stop working after a while", message.body)
        self.assertNotIn("INVOICE", message.body)
        self.assertNotIn("TOTAL DUE", message.body)
        html = message.alternatives[0].content
        self.assertIn("Pay USD 49.00 on PayPal", html)
        self.assertNotIn("Description", html)
        self.assertLess(len(message.body), 700)

    def test_long_product_titles_are_shortened_in_the_pay_now_summary(self):
        order_id = self.confirmed_order()
        self.product.name = "Watches For Men's Fashion Stainless Steel Watches Men Gift Set " * 2
        self.product.save(update_fields=["name"])
        order = Order.objects.get(pk=order_id)
        order.lines.update(product_name=self.product.name)
        self.open_checkout(order_id)

        message = self.sent(order_id)

        summary_line = next(line for line in message.body.splitlines() if "is asking for" in line)
        self.assertIn("…", summary_line)
        self.assertLess(len(summary_line), 160)

    def test_reminders_are_labelled_for_both_kinds(self):
        invoice_order = self.confirmed_order()
        self.open_invoice(invoice_order, status=PaymentInvoice.Status.SENT)
        reminder = self.sent(invoice_order, kind="reminder")
        self.assertIn("[Sandbox] Reminder: Invoice ", reminder.subject)
        self.assertIn("still unpaid", reminder.body)

        checkout_order = self.confirmed_order()
        self.open_checkout(checkout_order, paypal_order_id="PP-REMIND")
        nudge = self.sent(checkout_order, kind="reminder")
        self.assertIn("[Sandbox] Reminder: Pay USD 49.00", nudge.subject)
        self.assertIn("still waiting for your payment", nudge.body)

    def test_the_invoice_issue_date_is_the_invoice_date_not_the_send_date(self):
        order_id = self.confirmed_order()
        invoice = self.open_invoice(order_id)
        PaymentInvoice.objects.filter(pk=invoice.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )

        message = self.sent(order_id)

        self.assertIn("Issued:", message.body)
        expected = timezone.localdate(timezone.now() - timedelta(days=3))
        self.assertIn(f"{expected.day} {expected.strftime('%b %Y')}", message.body)
