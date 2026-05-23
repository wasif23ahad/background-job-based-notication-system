from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.notifications.models import MAX_RETRY_ATTEMPTS, Notification, NotificationStatus
from apps.notifications.tasks import send_notification_task

logger = logging.getLogger(__name__)


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
        return send_notification_task.delay(
            notification_id=notification_id,
            force_fail=force_fail,
        )

    return send_notification_task.apply_async(
        kwargs={"notification_id": notification_id, "force_fail": force_fail},
        eta=eta,
    )


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

    transaction.on_commit(
        lambda: schedule_notification(notification_id=notification.id, eta=timezone.now())
    )
