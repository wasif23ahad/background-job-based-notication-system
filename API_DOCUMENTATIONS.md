# API Documentation

Base URL for local development:

```text
http://127.0.0.1:8000
```

For protected endpoints, send:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
X-Request-ID: optional-client-request-id
```

Every response includes `X-Request-ID`.

## Health Check
### GET `/api/v1/health/`
Auth: not required

Expected `200`:

```json
{
  "status": "ok",
  "services": {
    "database": "ok",
    "redis": "ok"
  }
}
```

Expected `503` when a dependency is down:

```json
{
  "status": "degraded",
  "services": {
    "database": "ok",
    "redis": "down"
  }
}
```

## Authentication
### POST `/api/v1/auth/register/`
Auth: not required

Request:

```json
{
  "username": "demo-user",
  "email": "demo@example.com",
  "password": "strong-pass-123"
}
```

Expected `201`:

```json
{
  "id": 1,
  "username": "demo-user",
  "email": "demo@example.com"
}
```

Expected `400` for duplicate username:

```json
{
  "username": [
    "A user with that username already exists."
  ]
}
```

### POST `/api/v1/auth/token/`
Auth: not required

Request:

```json
{
  "username": "demo-user",
  "password": "strong-pass-123"
}
```

Expected `200`:

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

Expected `401` for invalid credentials:

```json
{
  "detail": "No active account found with the given credentials"
}
```

### POST `/api/v1/auth/token/refresh/`
Auth: not required

Request:

```json
{
  "refresh": "<refresh_token>"
}
```

Expected `200`:

```json
{
  "access": "<new_access_token>"
}
```

## Notifications
### POST `/api/v1/notifications/`
Auth: required

Request:

```json
{
  "title": "Payment reminder",
  "message": "Your payment is due tomorrow.",
  "scheduled_time": "2026-05-24T10:00:00Z"
}
```

Expected `201`:

```json
{
  "id": 1,
  "title": "Payment reminder",
  "message": "Your payment is due tomorrow.",
  "scheduled_time": "2026-05-24T10:00:00Z"
}
```

Expected `400` for past time:

```json
{
  "scheduled_time": [
    "Scheduled time must be in the future."
  ]
}
```

Expected `401` without token:

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### GET `/api/v1/notifications/`
Auth: required

Optional query:

```text
?status=failed
```

Expected `200`:

```json
[
  {
    "id": 1,
    "title": "Payment reminder",
    "message": "Your payment is due tomorrow.",
    "scheduled_time": "2026-05-24T10:00:00Z",
    "status": "pending",
    "retry_count": 0,
    "last_error": "",
    "processed_at": null,
    "created_at": "2026-05-23T08:00:00Z",
    "updated_at": "2026-05-23T08:00:00Z"
  }
]
```

### GET `/api/v1/notifications/{id}/`
Auth: required

Expected `200`:

```json
{
  "id": 1,
  "title": "Payment reminder",
  "message": "Your payment is due tomorrow.",
  "scheduled_time": "2026-05-24T10:00:00Z",
  "status": "pending",
  "retry_count": 0,
  "last_error": "",
  "processed_at": null,
  "created_at": "2026-05-23T08:00:00Z",
  "updated_at": "2026-05-23T08:00:00Z"
}
```

Expected `404` for another user's notification:

```json
{
  "detail": "No Notification matches the given query."
}
```

### GET `/api/v1/notifications/history/`
Auth: required

Expected `200`:

```json
[
  {
    "id": 1,
    "title": "Payment reminder",
    "message": "Your payment is due tomorrow.",
    "scheduled_time": "2026-05-24T10:00:00Z",
    "status": "sent",
    "retry_count": 0,
    "last_error": "",
    "processed_at": "2026-05-24T10:00:02Z",
    "created_at": "2026-05-23T08:00:00Z",
    "updated_at": "2026-05-24T10:00:02Z"
  }
]
```

### POST `/api/v1/notifications/{id}/schedule/`
Auth: required

Request:

```json
{
  "scheduled_time": "2026-05-24T11:00:00Z"
}
```

Expected `200`:

```json
{
  "id": 1,
  "title": "Payment reminder",
  "message": "Your payment is due tomorrow.",
  "scheduled_time": "2026-05-24T11:00:00Z",
  "status": "pending",
  "retry_count": 0,
  "last_error": "",
  "processed_at": null,
  "created_at": "2026-05-23T08:00:00Z",
  "updated_at": "2026-05-23T09:00:00Z"
}
```

Expected `400` for sent or permanently failed notification:

```json
{
  "detail": "Sent or permanently failed notifications cannot be rescheduled."
}
```

### POST `/api/v1/notifications/{id}/retry/`
Auth: required

Request body: empty

Expected `200` after successful retry:

```json
{
  "id": 1,
  "title": "Payment reminder",
  "message": "Your payment is due tomorrow.",
  "scheduled_time": "2026-05-24T10:00:00Z",
  "status": "sent",
  "retry_count": 1,
  "last_error": "",
  "processed_at": "2026-05-23T09:15:00Z",
  "created_at": "2026-05-23T08:00:00Z",
  "updated_at": "2026-05-23T09:15:00Z"
}
```

Expected `400` when notification is not failed:

```json
{
  "detail": "Only failed notifications can be retried."
}
```

Expected `400` after permanent failure:

```json
{
  "detail": "Notification is permanently failed and cannot be retried."
}
```

### GET `/api/v1/notifications/{id}/attempts/`
Auth: required

Expected `200`:

```json
[
  {
    "id": 1,
    "attempt_number": 1,
    "status_before": "pending",
    "status_after": "sent",
    "outcome": "sent",
    "error_message": "",
    "started_at": "2026-05-24T10:00:00Z",
    "finished_at": "2026-05-24T10:00:02Z"
  }
]
```

Expected failed attempt:

```json
[
  {
    "id": 2,
    "attempt_number": 3,
    "status_before": "pending",
    "status_after": "permanently_failed",
    "outcome": "failed",
    "error_message": "Simulated notification delivery failure.",
    "started_at": "2026-05-24T10:05:00Z",
    "finished_at": "2026-05-24T10:05:01Z"
  }
]
```

## API Schema and Swagger
### GET `/api/schema/`
Auth: not required

Expected `200`: OpenAPI schema document.

### GET `/api/docs/`
Auth: not required

Expected `200`: Swagger UI HTML page.

## Postman Flow
1. `POST /api/v1/auth/register/`
2. `POST /api/v1/auth/token/`
3. Store `access` token as `{{access_token}}`.
4. Add `Authorization: Bearer {{access_token}}` to protected requests.
5. `POST /api/v1/notifications/` with a future `scheduled_time`.
6. `GET /api/v1/notifications/` and `GET /api/v1/notifications/history/`.
7. Use `POST /api/v1/notifications/{id}/schedule/` to reschedule.
8. Use `POST /api/v1/notifications/{id}/retry/` after a notification has failed.
9. Use `GET /api/v1/notifications/{id}/attempts/` to inspect send attempts.
10. Check `GET /api/v1/health/` before running queue-dependent tests.
