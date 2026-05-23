from django.contrib import admin

from apps.notifications.models import Notification, NotificationAttempt


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "title", "status", "retry_count", "scheduled_time")
    list_filter = ("status",)
    search_fields = ("title", "message", "owner__username")


@admin.register(NotificationAttempt)
class NotificationAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "notification",
        "attempt_number",
        "outcome",
        "status_before",
        "status_after",
        "started_at",
    )
    list_filter = ("outcome", "status_after")
