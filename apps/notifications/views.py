from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.serializers import (
    NotificationAttemptSerializer,
    NotificationCreateSerializer,
    NotificationScheduleSerializer,
    NotificationSerializer,
)
from apps.notifications.services import retry_notification, schedule_notification


class NotificationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Notification.objects.all()

    def get_queryset(self):
        queryset = Notification.objects.filter(owner=self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return NotificationCreateSerializer
        if self.action == "schedule":
            return NotificationScheduleSerializer
        if self.action == "attempts":
            return NotificationAttemptSerializer
        return NotificationSerializer

    def perform_create(self, serializer):
        notification = serializer.save(owner=self.request.user)
        transaction.on_commit(
            lambda: schedule_notification(
                notification_id=notification.id, eta=notification.scheduled_time
            )
        )

    @action(detail=False, methods=["get"])
    def history(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = NotificationSerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        notification = self.get_object()
        retry_notification(notification)
        notification.refresh_from_db()
        return Response(NotificationSerializer(notification).data)

    @action(detail=True, methods=["get"])
    def attempts(self, request, pk=None):
        notification = self.get_object()
        queryset = notification.attempts.all()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        notification = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if notification.status in {
            NotificationStatus.SENT,
            NotificationStatus.PERMANENTLY_FAILED,
        }:
            return Response(
                {"detail": "Sent or permanently failed notifications cannot be rescheduled."},
                status=400,
            )

        notification.scheduled_time = serializer.validated_data["scheduled_time"]
        notification.status = NotificationStatus.PENDING
        notification.save(update_fields=["scheduled_time", "status", "updated_at"])

        transaction.on_commit(
            lambda: schedule_notification(
                notification_id=notification.id, eta=notification.scheduled_time
            )
        )
        return Response(NotificationSerializer(notification).data)
