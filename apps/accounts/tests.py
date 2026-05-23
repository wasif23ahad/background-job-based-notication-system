import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_register_and_token_flow():
    client = APIClient()
    register_payload = {
        "username": "new-user",
        "email": "new-user@example.com",
        "password": "strong-pass-123",
    }
    register_response = client.post("/api/v1/auth/register/", register_payload, format="json")
    assert register_response.status_code == 201

    token_response = client.post(
        "/api/v1/auth/token/",
        {"username": "new-user", "password": "strong-pass-123"},
        format="json",
    )
    assert token_response.status_code == 200
    assert "access" in token_response.data
    assert "refresh" in token_response.data

    assert get_user_model().objects.filter(username="new-user").exists()


@pytest.mark.django_db
def test_notifications_endpoint_requires_authentication():
    client = APIClient()
    response = client.get("/api/v1/notifications/")
    assert response.status_code == 401
