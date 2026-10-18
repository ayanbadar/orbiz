from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from apps.notifications.models import EmailLog, EmailStatus


def deliver_email(log: EmailLog) -> None:
    if log.status == EmailStatus.SENT:
        return

    try:
        send_mail(
            subject=log.subject,
            message=log.body,
            from_email=log.sender,
            recipient_list=[log.recipient],
            fail_silently=False,
        )
    except Exception as exc:
        log.status = EmailStatus.FAILED
        log.error_message = str(exc)
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
        raise self.retry(exc=exc) from exc
