from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationStatus


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = False


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        username="notification-user", password="strong-pass-123"
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_create_notification_rejects_past_scheduled_time(auth_client):
    payload = {
        "title": "Past schedule",
        "message": "Should fail",
        "scheduled_time": (timezone.now() - timedelta(minutes=5)).isoformat(),
    }
    response = auth_client.post("/api/v1/notifications/", payload, format="json")
    assert response.status_code == 400
    assert "scheduled_time" in response.data


@pytest.mark.django_db
def test_create_notification_future_saves_pending_status(auth_client):
    payload = {
        "title": "Future schedule",
        "message": "Should remain pending until worker handles ETA.",
        "scheduled_time": (timezone.now() + timedelta(minutes=10)).isoformat(),
    }
    response = auth_client.post("/api/v1/notifications/", payload, format="json")
    assert response.status_code == 201

    notification = Notification.objects.get(id=response.data["id"])
    assert notification.status == NotificationStatus.PENDING
    assert notification.retry_count == 0


@pytest.mark.django_db
def test_history_returns_only_current_user_notifications(auth_client, user):
    Notification.objects.create(
        owner=user,
        title="Mine",
        message="Owned by authenticated user",
        scheduled_time=timezone.now() + timedelta(minutes=10),
    )
    other_user = get_user_model().objects.create_user(
        username="other-user", password="strong-pass-123"
    )
    Notification.objects.create(
        owner=other_user,
        title="Not mine",
        message="Owned by another user",
        scheduled_time=timezone.now() + timedelta(minutes=10),
    )

    response = auth_client.get("/api/v1/notifications/history/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["title"] == "Mine"


@pytest.mark.django_db
def test_retry_failed_notification_succeeds(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Recoverable",
        message="This retry should pass",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        status=NotificationStatus.FAILED,
        retry_count=1,
        last_error="Temporary failure",
    )

    response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert response.status_code == 200

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert notification.retry_count == 1
    assert notification.last_error == ""


@pytest.mark.django_db
def test_retry_limits_to_three_failures(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Will fail __FAIL__",
        message="Still failing __FAIL__",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        status=NotificationStatus.FAILED,
        retry_count=2,
        last_error="Attempt 2 failed",
    )

    response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert response.status_code == 200

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.PERMANENTLY_FAILED
    assert notification.retry_count == 3

    second_response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert second_response.status_code == 400
