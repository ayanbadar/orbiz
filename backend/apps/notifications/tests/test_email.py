from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from apps.notifications.models import EmailLog, EmailStatus
from apps.notifications.services import queue_email
from apps.notifications.tasks import deliver_email

TEST_SETTINGS = dict(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Orbiz <noreply@orbiz.local>",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)


@override_settings(**TEST_SETTINGS)
class QueueEmailTests(TestCase):
    def test_queue_email_logs_and_sends_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            logs = queue_email(
                to="Seller@example.com",
                subject="Hello",
                body="A note from Orbiz.",
                kind="welcome",
            )

        self.assertEqual(len(logs), 1)
        log = EmailLog.objects.get(pk=logs[0].pk)
        self.assertEqual(log.recipient, "seller@example.com")
        self.assertEqual(log.kind, "welcome")
        self.assertEqual(log.status, EmailStatus.SENT)
        self.assertIsNotNone(log.sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["seller@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Hello")

    def test_failed_send_is_stored_on_the_log(self):
        log = EmailLog.objects.create(
            recipient="seller@example.com",
            sender="Orbiz <noreply@orbiz.local>",
            subject="Hello",
            body="A note.",
        )

        with patch("apps.notifications.tasks.send_mail", side_effect=ConnectionError("smtp down")):
            with self.assertRaises(ConnectionError):
                deliver_email(log)

        log.refresh_from_db()
        self.assertEqual(log.status, EmailStatus.FAILED)
        self.assertIn("smtp down", log.error_message)
        self.assertIsNone(log.sent_at)

    def test_sent_log_is_not_sent_again(self):
        log = EmailLog.objects.create(
            recipient="seller@example.com",
            sender="Orbiz <noreply@orbiz.local>",
            subject="Hello",
            body="A note.",
            status=EmailStatus.SENT,
        )

        deliver_email(log)

        self.assertEqual(len(mail.outbox), 0)
