from django.utils import timezone
from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "message",
            "scheduled_time",
            "status",
            "retry_count",
            "last_error",
            "processed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("status", "retry_count", "last_error", "processed_at")


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "message", "scheduled_time")
        read_only_fields = ("id",)

    def validate_scheduled_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value


class NotificationScheduleSerializer(serializers.Serializer):
    scheduled_time = serializers.DateTimeField()

    def validate_scheduled_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value
