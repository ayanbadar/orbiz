import logging

from celery import shared_task

from apps.common.exceptions import BadGatewayError, ServiceUnavailableError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=55,
    time_limit=60,
)
def process_paypal_webhook_event(self, event_pk: int) -> dict:
    # Import inside body to avoid circular imports with services.
    from apps.payments.services import process_webhook_event

    try:
        event = process_webhook_event(event_pk=event_pk)
    except (BadGatewayError, ServiceUnavailableError) as exc:
        logger.warning(
            "PayPal webhook event %s retriable failure: %s", event_pk, exc
        )
        raise self.retry(exc=exc) from exc

    return {
        "event_pk": event.pk,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "processed_at": event.processed_at.isoformat() if event.processed_at else None,
        "order_id": event.order_id,
    }
