from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import MAX_RETRY_ATTEMPTS, Notification, NotificationStatus

logger = logging.getLogger(__name__)


def _dispatch_notification(notification: Notification, force_fail: bool = False):
    failure_keyword = settings.NOTIFICATION_FAILURE_KEYWORD
    if (
        force_fail
        or failure_keyword in notification.title
        or failure_keyword in notification.message
    ):
        raise RuntimeError("Simulated notification delivery failure.")


@shared_task(name="notifications.send_notification")
def send_notification_task(notification_id: int, force_fail: bool = False):
    try:
        with transaction.atomic():
            notification = Notification.objects.select_for_update().get(id=notification_id)
            if notification.status in {
                NotificationStatus.SENT,
                NotificationStatus.PERMANENTLY_FAILED,
            }:
                return {"notification_id": notification_id, "status": notification.status}

            notification.status = NotificationStatus.PROCESSING
            notification.save(update_fields=["status", "updated_at"])
    except Notification.DoesNotExist:
        logger.warning("Notification %s not found during task processing.", notification_id)
        return {"notification_id": notification_id, "status": "missing"}

    try:
        _dispatch_notification(notification, force_fail=force_fail)
    except Exception as exc:  # noqa: BLE001
        with transaction.atomic():
            notification = Notification.objects.select_for_update().get(id=notification_id)
            notification.retry_count += 1
            notification.last_error = str(exc)
            notification.processed_at = timezone.now()
            if notification.retry_count >= MAX_RETRY_ATTEMPTS:
                notification.status = NotificationStatus.PERMANENTLY_FAILED
            else:
                notification.status = NotificationStatus.FAILED
            notification.save(
                update_fields=[
                    "retry_count",
                    "last_error",
                    "processed_at",
                    "status",
                    "updated_at",
                ]
            )
        logger.exception("Notification %s failed to send.", notification_id)
        return {"notification_id": notification_id, "status": notification.status}

    with transaction.atomic():
        notification = Notification.objects.select_for_update().get(id=notification_id)
        notification.status = NotificationStatus.SENT
        notification.last_error = ""
        notification.processed_at = timezone.now()
        notification.save(update_fields=["status", "last_error", "processed_at", "updated_at"])

    logger.info("Notification %s delivered successfully.", notification_id)
    return {"notification_id": notification_id, "status": NotificationStatus.SENT}
