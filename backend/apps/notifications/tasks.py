import logging
import smtplib

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.notifications.models import EmailLog, EmailStatus

logger = logging.getLogger(__name__)

# Errors a retry cannot fix: bad credentials, a refused address or sender, or any 5xx
# reply (this includes Gmail's "daily quota exceeded", 550 5.4.5).
_PERMANENT_SMTP_ERRORS = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
)


def is_permanent_failure(exc: Exception) -> bool:
    if isinstance(exc, _PERMANENT_SMTP_ERRORS):
        return True
    code = getattr(exc, "smtp_code", None)
    return isinstance(code, int) and 500 <= code < 600


def describe_failure(exc: Exception) -> str:
    """A short, secret-free reason for the log row and the seller-facing UI."""
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "The recipient address was refused by the mail server."
    code = getattr(exc, "smtp_code", None)
    if isinstance(code, int):
        detail = getattr(exc, "smtp_error", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        return f"SMTP {code}: {str(detail).strip()}"[:500]
    return f"{type(exc).__name__}: {exc}"[:500]


def deliver_email(log: EmailLog) -> None:
    if log.status == EmailStatus.SENT:
        return

    message = EmailMultiAlternatives(
        subject=log.subject,
        body=log.body,
        from_email=log.sender,
        to=[log.recipient],
        reply_to=[log.reply_to] if log.reply_to else None,
    )
    if log.html_body:
        message.attach_alternative(log.html_body, "text/html")

    try:
        message.send(fail_silently=False)
    except Exception as exc:
        log.status = EmailStatus.FAILED
        log.error_message = describe_failure(exc)
        log.save(update_fields=["status", "error_message", "updated_at"])
        raise

    log.status = EmailStatus.SENT
    log.sent_at = timezone.now()
    log.error_message = ""
    log.save(update_fields=["status", "sent_at", "error_message", "updated_at"])


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_email_task(self, email_log_id: int) -> None:
    log = EmailLog.objects.get(pk=email_log_id)
    try:
        deliver_email(log)
    except Exception as exc:
        if is_permanent_failure(exc):
            # The row is already marked failed; retrying would only repeat the error.
            logger.warning(
                "Email %s failed permanently (%s).", email_log_id, type(exc).__name__
            )
            return
        raise self.retry(exc=exc) from exc
