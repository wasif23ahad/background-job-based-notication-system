from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "title", "status", "retry_count", "scheduled_time")
    list_filter = ("status",)
    search_fields = ("title", "message", "owner__username")
