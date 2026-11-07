import smtplib
from io import StringIO
from unittest.mock import patch

from celery.exceptions import Retry
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from apps.notifications import checks
from apps.notifications.models import EmailLog, EmailStatus
from apps.notifications.services import queue_email
from apps.notifications.tasks import deliver_email, describe_failure, is_permanent_failure

SEND = "apps.notifications.tasks.EmailMultiAlternatives.send"

LOCMEM = dict(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Orbiz <noreply@orbiz.local>",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
SMTP = dict(
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    EMAIL_HOST="smtp.example.com",
    EMAIL_PORT=587,
    EMAIL_USE_TLS=True,
    EMAIL_USE_SSL=False,
    EMAIL_HOST_USER="orbiz.sender@example.com",
    EMAIL_HOST_PASSWORD="s3cret-app-password",
    DEFAULT_FROM_EMAIL="Orbiz <orbiz.sender@example.com>",
)


@override_settings(**LOCMEM)
class MultipartDeliveryTests(TestCase):
    def test_html_alternative_reply_to_and_reference_are_delivered(self):
        with self.captureOnCommitCallbacks(execute=True):
            logs = queue_email(
                to="buyer@example.com",
                subject="Payment request ORD-1",
                body="Pay here: https://pay.example/1",
                html_body="<p>Pay <a href='https://pay.example/1'>here</a></p>",
                reply_to="Seller@Example.com",
                reference="order:1:invoice:1",
                kind="payment_request",
            )

        log = EmailLog.objects.get(pk=logs[0].pk)
        self.assertEqual(log.status, EmailStatus.SENT)
        self.assertEqual(log.reference, "order:1:invoice:1")
        self.assertEqual(log.reply_to, "seller@example.com")
        message = mail.outbox[0]
        self.assertEqual(message.reply_to, ["seller@example.com"])
        self.assertEqual(message.body, "Pay here: https://pay.example/1")
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0].mimetype, "text/html")

    def test_plain_email_has_no_html_alternative_or_reply_to(self):
        with self.captureOnCommitCallbacks(execute=True):
            queue_email(to="a@example.com", subject="Hi", body="Plain.")

        message = mail.outbox[0]
        self.assertEqual(message.alternatives, [])
        self.assertEqual(message.reply_to, [])


@override_settings(**LOCMEM)
class FailureHandlingTests(TestCase):
    def test_classification(self):
        self.assertTrue(is_permanent_failure(smtplib.SMTPAuthenticationError(535, b"bad")))
        self.assertTrue(is_permanent_failure(smtplib.SMTPRecipientsRefused({})))
        self.assertTrue(is_permanent_failure(smtplib.SMTPSenderRefused(550, b"no", "a@b.c")))
        # Gmail daily quota: 550 5.4.5
        self.assertTrue(is_permanent_failure(smtplib.SMTPDataError(550, b"5.4.5 quota")))
        self.assertFalse(is_permanent_failure(smtplib.SMTPResponseException(451, b"try later")))
        self.assertFalse(is_permanent_failure(smtplib.SMTPServerDisconnected("gone")))
        self.assertFalse(is_permanent_failure(ConnectionError("down")))
        self.assertFalse(is_permanent_failure(TimeoutError("slow")))

    def test_describe_failure_is_short_and_readable(self):
        self.assertEqual(
            describe_failure(smtplib.SMTPAuthenticationError(535, b"5.7.8 Not accepted")),
            "SMTP 535: 5.7.8 Not accepted",
        )
        self.assertEqual(
            describe_failure(smtplib.SMTPRecipientsRefused({"x@y.z": (550, b"no")})),
            "The recipient address was refused by the mail server.",
        )
        self.assertEqual(describe_failure(ConnectionError("down")), "ConnectionError: down")

    @override_settings(EMAIL_HOST_PASSWORD="s3cret-app-password")
    def test_permanent_failure_is_not_retried_and_never_stores_the_password(self):
        error = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        with patch(SEND, side_effect=error) as send:
            with self.captureOnCommitCallbacks(execute=True):
                logs = queue_email(to="a@example.com", subject="Hi", body="Body.")

        log = EmailLog.objects.get(pk=logs[0].pk)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(log.status, EmailStatus.FAILED)
        self.assertIn("SMTP 535", log.error_message)
        self.assertNotIn("s3cret-app-password", log.error_message)

    def test_transient_failure_schedules_a_retry(self):
        # In eager mode Celery surfaces the scheduled retry as Retry instead of re-running.
        with patch(SEND, side_effect=smtplib.SMTPServerDisconnected("gone")) as send:
            with self.assertRaises(Retry):
                with self.captureOnCommitCallbacks(execute=True):
                    queue_email(to="a@example.com", subject="Hi", body="Body.")

        log = EmailLog.objects.get()
        self.assertEqual(send.call_count, 1)
        self.assertEqual(log.status, EmailStatus.FAILED)
        self.assertIn("SMTPServerDisconnected", log.error_message)

    def test_a_failed_log_is_delivered_when_the_next_attempt_succeeds(self):
        log = EmailLog.objects.create(
            recipient="a@example.com",
            sender="Orbiz <noreply@orbiz.local>",
            subject="Hi",
            body="Body.",
            status=EmailStatus.FAILED,
            error_message="SMTPServerDisconnected: gone",
        )

        deliver_email(log)

        log.refresh_from_db()
        self.assertEqual(log.status, EmailStatus.SENT)
        self.assertEqual(log.error_message, "")
        self.assertEqual(len(mail.outbox), 1)


class SendTestEmailCommandTests(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("send_test_email", *args, stdout=out)
        return out.getvalue()

    @override_settings(**LOCMEM)
    def test_sends_multipart_message_and_warns_when_not_a_real_backend(self):
        output = self.run_command("--to", "me@example.com")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["me@example.com"])
        self.assertEqual(mail.outbox[0].alternatives[0].mimetype, "text/html")
        self.assertIn("does not deliver to a real inbox", output)
        self.assertIn("me***@example.com", output)
        self.assertNotIn("me@example.com", output)

    @override_settings(**SMTP)
    def test_defaults_to_the_smtp_login_and_never_prints_the_password(self):
        with patch(SEND) as send:
            output = self.run_command()

        send.assert_called_once()
        self.assertIn("smtp.example.com:587 (STARTTLS)", output)
        self.assertIn("password: <set>", output)
        self.assertIn("or***@example.com", output)
        self.assertNotIn("s3cret-app-password", output)
        self.assertIn("Accepted by the SMTP server", output)

    @override_settings(**SMTP)
    def test_reports_the_smtp_error_without_leaking_secrets(self):
        error = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        with patch(SEND, side_effect=error):
            with self.assertRaises(CommandError) as raised:
                self.run_command("--to", "me@example.com")

        self.assertIn("SMTP 535", str(raised.exception))
        self.assertNotIn("s3cret-app-password", str(raised.exception))

    @override_settings(**LOCMEM, EMAIL_HOST_USER="")
    def test_rejects_a_missing_or_invalid_address(self):
        with self.assertRaisesMessage(CommandError, "Pass --to"):
            self.run_command()
        with self.assertRaisesMessage(CommandError, "not a valid email"):
            self.run_command("--to", "nope")


class SmtpSystemCheckTests(SimpleTestCase):
    def ids(self):
        return [issue.id for issue in checks.smtp_settings(None)]

    @override_settings(**LOCMEM)
    def test_silent_for_non_smtp_backends(self):
        self.assertEqual(self.ids(), [])

    @override_settings(**SMTP)
    def test_silent_for_a_complete_setup(self):
        self.assertEqual(self.ids(), [])

    @override_settings(**{**SMTP, "EMAIL_USE_SSL": True})
    def test_tls_and_ssl_together_is_an_error(self):
        self.assertEqual(self.ids(), ["notifications.E001"])

    @override_settings(**{**SMTP, "EMAIL_HOST_PASSWORD": ""})
    def test_remote_host_without_credentials_warns(self):
        self.assertEqual(self.ids(), ["notifications.W002"])

    @override_settings(**{**SMTP, "EMAIL_HOST": ""})
    def test_empty_host_warns(self):
        self.assertEqual(self.ids(), ["notifications.W001"])

    @override_settings(
        **{**SMTP, "EMAIL_HOST": "localhost", "EMAIL_HOST_USER": "", "EMAIL_HOST_PASSWORD": ""}
    )
    def test_local_relay_needs_no_credentials(self):
        self.assertEqual(self.ids(), [])
