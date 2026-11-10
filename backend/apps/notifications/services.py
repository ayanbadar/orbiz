from collections.abc import Iterable

from django.conf import settings
from django.db import transaction

from apps.notifications.models import EmailLog
from apps.notifications.tasks import send_email_task


def queue_email(
    *,
    to: str | Iterable[str],
    subject: str,
    body: str,
    from_email: str | None = None,
    kind: str = "",
    html_body: str = "",
    reply_to: str = "",
    reference: str = "",
) -> list[EmailLog]:
    """Store an email log and send it on the Celery worker after the current transaction commits."""
    recipients = _recipients(to)
    if not recipients:
        raise ValueError("At least one recipient is required.")

    sender = from_email or settings.DEFAULT_FROM_EMAIL
    logs: list[EmailLog] = []
    for recipient in recipients:
        log = EmailLog.objects.create(
            kind=kind,
            reference=reference,
            recipient=recipient,
            sender=sender,
            reply_to=reply_to.strip().lower(),
            subject=subject,
            body=body,
            html_body=html_body,
        )
        transaction.on_commit(lambda email_log_id=log.pk: send_email_task.delay(email_log_id))
        logs.append(log)
    return logs


def _recipients(to: str | Iterable[str]) -> list[str]:
    raw = [to] if isinstance(to, str) else list(to)
    recipients: list[str] = []
    for address in raw:
        cleaned = address.strip().lower()
        if cleaned:
            recipients.append(cleaned)
    return recipients
