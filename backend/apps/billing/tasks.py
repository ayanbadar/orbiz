from celery import shared_task

from apps.billing.services import expire_subscriptions


@shared_task
def expire_subscriptions_task() -> int:
    return expire_subscriptions()
