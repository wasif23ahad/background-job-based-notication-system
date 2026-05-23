from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationAttempt, NotificationStatus
from apps.notifications.tasks import send_notification_task


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


@pytest.fixture
def future_time():
    return timezone.now() + timedelta(minutes=10)


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
def test_create_notification_rejects_missing_required_fields(auth_client):
    response = auth_client.post("/api/v1/notifications/", {}, format="json")
    assert response.status_code == 400
    assert "title" in response.data
    assert "message" in response.data
    assert "scheduled_time" in response.data


@pytest.mark.django_db
def test_create_notification_rejects_malformed_scheduled_time(auth_client):
    response = auth_client.post(
        "/api/v1/notifications/",
        {
            "title": "Malformed time",
            "message": "Bad timestamp",
            "scheduled_time": "not-a-date",
        },
        format="json",
    )
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
def test_notification_status_filter_returns_current_user_matches(auth_client, user):
    Notification.objects.create(
        owner=user,
        title="Pending",
        message="Pending message",
        scheduled_time=timezone.now() + timedelta(minutes=10),
        status=NotificationStatus.PENDING,
    )
    Notification.objects.create(
        owner=user,
        title="Failed",
        message="Failed message",
        scheduled_time=timezone.now() + timedelta(minutes=10),
        status=NotificationStatus.FAILED,
    )

    response = auth_client.get("/api/v1/notifications/", {"status": "failed"})
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["status"] == "failed"


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
def test_retrieve_notification_is_owner_scoped(auth_client):
    other_user = get_user_model().objects.create_user(
        username="retrieve-other-user", password="strong-pass-123"
    )
    notification = Notification.objects.create(
        owner=other_user,
        title="Not yours",
        message="Private notification",
        scheduled_time=timezone.now() + timedelta(minutes=10),
    )

    response = auth_client.get(f"/api/v1/notifications/{notification.id}/")
    assert response.status_code == 404


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
def test_retry_rejects_non_failed_notification(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Pending",
        message="Cannot retry yet",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        status=NotificationStatus.PENDING,
    )

    response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert response.status_code == 400
    assert response.data["detail"] == "Only failed notifications can be retried."


@pytest.mark.django_db
def test_retry_is_owner_scoped(auth_client):
    other_user = get_user_model().objects.create_user(
        username="retry-other-user", password="strong-pass-123"
    )
    notification = Notification.objects.create(
        owner=other_user,
        title="Other failed",
        message="Cannot retry",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        status=NotificationStatus.FAILED,
        retry_count=1,
    )

    response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert response.status_code == 404


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


@pytest.mark.django_db
def test_retry_permanently_failed_notification_is_rejected(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Permanent",
        message="No more retries",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        status=NotificationStatus.PERMANENTLY_FAILED,
        retry_count=3,
    )

    response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert response.status_code == 400
    assert response.data["detail"] == "Notification is permanently failed and cannot be retried."


@pytest.mark.django_db
def test_schedule_endpoint_rejects_past_time(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Schedule me",
        message="Future only",
        scheduled_time=timezone.now() + timedelta(minutes=20),
    )
    response = auth_client.post(
        f"/api/v1/notifications/{notification.id}/schedule/",
        {"scheduled_time": (timezone.now() - timedelta(minutes=1)).isoformat()},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_schedule_endpoint_is_owner_scoped(auth_client):
    other_user = get_user_model().objects.create_user(
        username="schedule-other-user", password="strong-pass-123"
    )
    notification = Notification.objects.create(
        owner=other_user,
        title="Other schedule",
        message="Cannot schedule",
        scheduled_time=timezone.now() + timedelta(minutes=20),
    )

    response = auth_client.post(
        f"/api/v1/notifications/{notification.id}/schedule/",
        {"scheduled_time": (timezone.now() + timedelta(hours=1)).isoformat()},
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [NotificationStatus.SENT, NotificationStatus.PERMANENTLY_FAILED],
)
def test_schedule_endpoint_rejects_terminal_notifications(auth_client, user, status):
    notification = Notification.objects.create(
        owner=user,
        title="Terminal",
        message="Cannot reschedule",
        scheduled_time=timezone.now() + timedelta(minutes=20),
        status=status,
    )

    response = auth_client.post(
        f"/api/v1/notifications/{notification.id}/schedule/",
        {"scheduled_time": (timezone.now() + timedelta(hours=1)).isoformat()},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_schedule_endpoint_reschedules_pending_notification(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Schedule me",
        message="Future only",
        scheduled_time=timezone.now() + timedelta(minutes=20),
    )
    new_time = timezone.now() + timedelta(hours=1)
    response = auth_client.post(
        f"/api/v1/notifications/{notification.id}/schedule/",
        {"scheduled_time": new_time.isoformat()},
        format="json",
    )
    assert response.status_code == 200

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.PENDING
    assert abs((notification.scheduled_time - new_time).total_seconds()) < 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/notifications/"),
        ("post", "/api/v1/notifications/"),
        ("get", "/api/v1/notifications/history/"),
    ],
)
def test_collection_notification_endpoints_require_authentication(method, path):
    client = APIClient()
    response = getattr(client, method)(path, {}, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "suffix"),
    [
        ("get", ""),
        ("post", "retry/"),
        ("post", "schedule/"),
        ("get", "attempts/"),
    ],
)
def test_detail_notification_endpoints_require_authentication(user, method, suffix):
    notification = Notification.objects.create(
        owner=user,
        title="Auth required",
        message="Private",
        scheduled_time=timezone.now() + timedelta(minutes=10),
    )
    client = APIClient()
    path = f"/api/v1/notifications/{notification.id}/{suffix}"
    payload = {"scheduled_time": (timezone.now() + timedelta(hours=1)).isoformat()}
    response = getattr(client, method)(path, payload, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_attempts_endpoint_returns_delivery_attempts(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Recoverable",
        message="Attempt tracking check",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        status=NotificationStatus.FAILED,
        retry_count=1,
        last_error="Attempt 1 failed",
    )

    retry_response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert retry_response.status_code == 200

    response = auth_client.get(f"/api/v1/notifications/{notification.id}/attempts/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["attempt_number"] == 2
    assert response.data[0]["outcome"] == "sent"
    assert response.data[0]["status_before"] == "pending"
    assert response.data[0]["status_after"] == "sent"


@pytest.mark.django_db
def test_attempt_records_capture_failure_details(auth_client, user):
    notification = Notification.objects.create(
        owner=user,
        title="Will fail __FAIL__",
        message="Still failing __FAIL__",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        status=NotificationStatus.FAILED,
        retry_count=2,
        last_error="Attempt 2 failed",
    )

    retry_response = auth_client.post(f"/api/v1/notifications/{notification.id}/retry/")
    assert retry_response.status_code == 200

    attempt = NotificationAttempt.objects.get(notification=notification, attempt_number=3)
    assert attempt.outcome == "failed"
    assert attempt.status_before == "pending"
    assert attempt.status_after == "permanently_failed"
    assert "Simulated notification delivery failure." in attempt.error_message


@pytest.mark.django_db
def test_attempts_endpoint_is_owner_scoped(auth_client, user):
    other_user = get_user_model().objects.create_user(
        username="another-user", password="strong-pass-123"
    )
    notification = Notification.objects.create(
        owner=other_user,
        title="Other user notification",
        message="Should not be visible",
        scheduled_time=timezone.now() + timedelta(minutes=10),
    )

    response = auth_client.get(f"/api/v1/notifications/{notification.id}/attempts/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_send_notification_task_records_successful_attempt(user):
    notification = Notification.objects.create(
        owner=user,
        title="Direct success",
        message="Task direct success",
        scheduled_time=timezone.now() + timedelta(minutes=1),
    )

    result = send_notification_task.run(notification.id)
    notification.refresh_from_db()

    assert result["status"] == NotificationStatus.SENT
    assert notification.status == NotificationStatus.SENT
    attempt = NotificationAttempt.objects.get(notification=notification)
    assert attempt.outcome == "sent"
    assert attempt.status_after == NotificationStatus.SENT


@pytest.mark.django_db
def test_send_notification_task_records_failure_and_permanent_failure(user):
    notification = Notification.objects.create(
        owner=user,
        title="Direct failure __FAIL__",
        message="Task direct failure",
        scheduled_time=timezone.now() + timedelta(minutes=1),
        retry_count=2,
    )

    result = send_notification_task.run(notification.id)
    notification.refresh_from_db()

    assert result["status"] == NotificationStatus.PERMANENTLY_FAILED
    assert notification.status == NotificationStatus.PERMANENTLY_FAILED
    assert notification.retry_count == 3
    attempt = NotificationAttempt.objects.get(notification=notification)
    assert attempt.outcome == "failed"
    assert attempt.status_after == NotificationStatus.PERMANENTLY_FAILED


@pytest.mark.django_db
def test_send_notification_task_missing_notification_returns_missing():
    result = send_notification_task.run(999999)
    assert result == {"notification_id": 999999, "status": "missing"}
