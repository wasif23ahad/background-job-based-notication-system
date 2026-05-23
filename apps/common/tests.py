import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint_returns_200_when_dependencies_are_up(monkeypatch):
    monkeypatch.setattr("apps.common.views.check_database", lambda: True)
    monkeypatch.setattr("apps.common.views.check_redis", lambda: True)

    client = APIClient()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert response.data["services"]["database"] == "ok"
    assert response.data["services"]["redis"] == "ok"


@pytest.mark.django_db
def test_health_endpoint_returns_503_when_any_dependency_is_down(monkeypatch):
    monkeypatch.setattr("apps.common.views.check_database", lambda: True)
    monkeypatch.setattr("apps.common.views.check_redis", lambda: False)

    client = APIClient()
    response = client.get("/api/v1/health/")
    assert response.status_code == 503
    assert response.data["status"] == "degraded"
    assert response.data["services"]["database"] == "ok"
    assert response.data["services"]["redis"] == "down"


@pytest.mark.django_db
def test_health_response_includes_generated_request_id_header(monkeypatch):
    monkeypatch.setattr("apps.common.views.check_database", lambda: True)
    monkeypatch.setattr("apps.common.views.check_redis", lambda: True)

    client = APIClient()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response["X-Request-ID"]


@pytest.mark.django_db
def test_health_reuses_incoming_request_id_header(monkeypatch):
    monkeypatch.setattr("apps.common.views.check_database", lambda: True)
    monkeypatch.setattr("apps.common.views.check_redis", lambda: True)

    client = APIClient()
    expected_request_id = "external-request-id-123"
    response = client.get("/api/v1/health/", HTTP_X_REQUEST_ID=expected_request_id)
    assert response.status_code == 200
    assert response["X-Request-ID"] == expected_request_id


@pytest.mark.django_db
def test_health_logs_include_request_id(monkeypatch, caplog):
    monkeypatch.setattr("apps.common.views.check_database", lambda: True)
    monkeypatch.setattr("apps.common.views.check_redis", lambda: True)
    caplog.set_level("INFO", logger="apps.common.request")

    client = APIClient()
    request_id = "req-log-test-001"
    response = client.get("/api/v1/health/", HTTP_X_REQUEST_ID=request_id)
    assert response.status_code == 200

    matching = [
        record
        for record in caplog.records
        if record.name == "apps.common.request" and record.request_id == request_id
    ]
    assert matching


@pytest.mark.django_db
def test_openapi_schema_endpoint_is_public():
    client = APIClient()
    response = client.get("/api/schema/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_swagger_docs_endpoint_is_public():
    client = APIClient()
    response = client.get("/api/docs/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_endpoint_is_public(monkeypatch):
    monkeypatch.setattr("apps.common.views.check_database", lambda: True)
    monkeypatch.setattr("apps.common.views.check_redis", lambda: True)

    client = APIClient()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
