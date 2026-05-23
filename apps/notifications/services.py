from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.notifications.models import MAX_RETRY_ATTEMPTS, Notification, NotificationStatus
from apps.notifications.tasks import send_notification_task

logger = logging.getLogger(__name__)


def _redis_hint() -> str:
    broker_url = getattr(settings, "CELERY_BROKER_URL", "") or ""

    if broker_url.startswith(("redis://", "rediss://")):
        return (
            "Redis broker connection failed. Verify REDIS_URL/CELERY_BROKER_URL reachability "
            "and TLS options (ssl_cert_reqs) for rediss://."
        )

    if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
        return (
            "Upstash REST credentials are present, but Celery broker requires a Redis TCP URL "
            "(redis:// or rediss://) in REDIS_URL/CELERY_BROKER_URL."
        )
    return (
        "Redis broker is unavailable. Ensure REDIS_URL/CELERY_BROKER_URL points to a reachable "
        "redis:// or rediss:// endpoint."
    )


def schedule_notification(notification_id: int, eta=None, force_fail: bool = False):
    eta = eta or timezone.now()

    if settings.CELERY_TASK_ALWAYS_EAGER and eta > timezone.now():
        logger.info(
            "Skipping immediate task execution in eager mode for notification_id=%s eta=%s",
            notification_id,
            eta,
        )
        return None

    if settings.CELERY_TASK_ALWAYS_EAGER:
        return send_notification_task.run(
            notification_id=notification_id,
            force_fail=force_fail,
        )

    try:
        return send_notification_task.apply_async(
            kwargs={"notification_id": notification_id, "force_fail": force_fail},
            eta=eta,
            ignore_result=True,
        )
    except Exception as exc:  # noqa: BLE001
        hint = _redis_hint()
        logger.exception(
            "Failed to enqueue notification_id=%s. %s error=%s",
            notification_id,
            hint,
            exc,
        )
        if eta <= timezone.now():
            logger.warning(
                "Running notification task locally for notification_id=%s due broker failure.",
                notification_id,
            )
            return send_notification_task.run(
                notification_id=notification_id,
                force_fail=force_fail,
            )

        Notification.objects.filter(id=notification_id).update(last_error=hint)
        return None


def retry_notification(notification: Notification):
    if notification.status == NotificationStatus.PERMANENTLY_FAILED:
        raise ValidationError("Notification is permanently failed and cannot be retried.")

    if notification.status != NotificationStatus.FAILED:
        raise ValidationError("Only failed notifications can be retried.")

    if notification.retry_count >= MAX_RETRY_ATTEMPTS:
        notification.status = NotificationStatus.PERMANENTLY_FAILED
        notification.save(update_fields=["status", "updated_at"])
        raise ValidationError("Notification has reached max retries.")

    notification.status = NotificationStatus.PENDING
    notification.last_error = ""
    notification.save(update_fields=["status", "last_error", "updated_at"])

    schedule_notification(notification_id=notification.id, eta=timezone.now())
