from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.serializers import (
    NotificationCreateSerializer,
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
