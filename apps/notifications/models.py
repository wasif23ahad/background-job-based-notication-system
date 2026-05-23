from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel

MAX_RETRY_ATTEMPTS = 3


class NotificationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    SENT = "sent", _("Sent")
    FAILED = "failed", _("Failed")
    PERMANENTLY_FAILED = "permanently_failed", _("Permanently Failed")


class Notification(TimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    scheduled_time = models.DateTimeField()
    status = models.CharField(
        max_length=32,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("owner", "status")),
            models.Index(fields=("scheduled_time",)),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def can_retry(self) -> bool:
        return (
            self.status == NotificationStatus.FAILED
            and self.retry_count < MAX_RETRY_ATTEMPTS
        )
