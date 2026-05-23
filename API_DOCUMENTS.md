# API Documentation

This document describes all currently implemented API endpoints for the Webbly Notification API.

## 1. Base URLs

- Local: `http://127.0.0.1:8000`
- Live (Render example): `https://background-job-based-notication-system.onrender.com`

## 2. Authentication

Protected endpoints use JWT Bearer tokens.

Header format:

```http
Authorization: Bearer <access_token>
```

## 3. Common Request/Response Notes

- `Content-Type: application/json` for JSON request bodies.
- Every response includes `X-Request-ID`.
- Root/docs endpoints support both browser HTML and strict JSON clients.

Common status codes:

- `200` OK
- `201` Created
- `400` Validation or business rule failure
- `401` Authentication required or token invalid
- `404` Resource not found (including owner-scope protection)
- `503` Health degraded (DB or Redis down)

## 4. API Endpoints

## 4.1 Root and API Discovery

### GET `/`

Behavior:
- Browser-style requests: redirects to `/api/docs/`
- `Accept: application/json` requests: returns API index JSON

Example JSON response (`200`):

```json
{
  "name": "Webbly Notification API",
  "docs": "/api/docs/",
  "schema": "/api/schema/",
  "health": "/api/v1/health/"
}
```

### GET `/api/docs/`

Behavior:
- Browser-style requests: Swagger UI HTML
- `Accept: application/json` requests: JSON hint

Example JSON response (`200`):

```json
{
  "detail": "Swagger UI is HTML. Use /api/schema/ for machine-readable JSON.",
  "docs": "/api/docs/",
  "schema": "/api/schema/"
}
```

### GET `/api/schema/`

Returns OpenAPI schema (JSON/YAML depending negotiation).

## 4.2 Health

### GET `/api/v1/health/`

Public endpoint.

Healthy response (`200`):

```json
{
  "status": "ok",
  "services": {
    "database": "ok",
    "redis": "ok"
  }
}
```

Degraded response (`503`):

```json
{
  "status": "degraded",
  "services": {
    "database": "ok",
    "redis": "down"
  }
}
```

## 4.3 Auth

### POST `/api/v1/auth/register/`

Public endpoint.

Request:

```json
{
  "username": "demo_user",
  "email": "demo@example.com",
  "password": "StrongPass123!"
}
```

Success response (`201`):

```json
{
  "id": 1,
  "username": "demo_user",
  "email": "demo@example.com"
}
```

Validation examples (`400`):

```json
{
  "username": [
    "A user with that username already exists."
  ]
}
```

```json
{
  "password": [
    "Ensure this field has at least 8 characters."
  ]
}
```

### POST `/api/v1/auth/token/`

Public endpoint.

Request:

```json
{
  "username": "demo_user",
  "password": "StrongPass123!"
}
```

Success response (`200`):

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

Invalid credentials (`401`):

```json
{
  "detail": "No active account found with the given credentials"
}
```

### POST `/api/v1/auth/token/refresh/`

Public endpoint.

Request:

```json
{
  "refresh": "<refresh_token>"
}
```

Success response (`200`):

```json
{
  "access": "<new_access_token>"
}
```

## 4.4 Notifications

All endpoints below require JWT authentication.

Notification status enum:
- `pending`
- `processing`
- `sent`
- `failed`
- `permanently_failed`

Attempt outcome enum:
- `sent`
- `failed`

### POST `/api/v1/notifications/`

Create and schedule a notification.

Request:

```json
{
  "title": "Payment Reminder",
  "message": "Your payment is due tomorrow.",
  "scheduled_time": "2026-05-24T10:00:00Z"
}
```

Success response (`201`):

```json
{
  "id": 12,
  "title": "Payment Reminder",
  "message": "Your payment is due tomorrow.",
  "scheduled_time": "2026-05-24T10:00:00Z"
}
```

Validation example (`400`):

```json
{
  "scheduled_time": [
    "Scheduled time must be in the future."
  ]
}
```

### GET `/api/v1/notifications/`

List current user notifications. Sorted newest first by `created_at`.

Optional query param:
- `status`: `pending|processing|sent|failed|permanently_failed`

Example:

```text
GET /api/v1/notifications/?status=failed
```

Success response (`200`):

```json
[
  {
    "id": 12,
    "title": "Payment Reminder",
    "message": "Your payment is due tomorrow.",
    "scheduled_time": "2026-05-24T10:00:00Z",
    "status": "pending",
    "retry_count": 0,
    "last_error": "",
    "processed_at": null,
    "created_at": "2026-05-23T15:30:00Z",
    "updated_at": "2026-05-23T15:30:00Z"
  }
]
```

### GET `/api/v1/notifications/{id}/`

Fetch a single notification owned by the authenticated user.

Success response (`200`): same object shape as list items.

Not found / unauthorized owner (`404`):

```json
{
  "detail": "No Notification matches the given query."
}
```

### GET `/api/v1/notifications/history/`

Returns current user notification history (same response shape as list).

### POST `/api/v1/notifications/{id}/schedule/`

Reschedule a notification.

Request:

```json
{
  "scheduled_time": "2026-05-24T12:00:00Z"
}
```

Success response (`200`): full notification object.

Business rule errors (`400`):

```json
{
  "scheduled_time": [
    "Scheduled time must be in the future."
  ]
}
```

```json
{
  "detail": "Sent or permanently failed notifications cannot be rescheduled."
}
```

### POST `/api/v1/notifications/{id}/retry/`

Retries a failed notification.

Request body:
- No body required (you may send `{}`).

Success response (`200`): full notification object.

Business rule errors (`400`):

```json
{
  "detail": "Only failed notifications can be retried."
}
```

```json
{
  "detail": "Notification is permanently failed and cannot be retried."
}
```

```json
{
  "detail": "Notification has reached max retries."
}
```

### GET `/api/v1/notifications/{id}/attempts/`

Returns delivery attempt history for one notification (newest first).

Success response (`200`):

```json
[
  {
    "id": 8,
    "attempt_number": 2,
    "status_before": "pending",
    "status_after": "sent",
    "outcome": "sent",
    "error_message": "",
    "started_at": "2026-05-24T10:05:10Z",
    "finished_at": "2026-05-24T10:05:12Z"
  }
]
```

## 5. Manual Postman Flow

1. `POST /api/v1/auth/register/`
2. `POST /api/v1/auth/token/` and save `access` and `refresh`
3. `GET /api/v1/health/`
4. `POST /api/v1/notifications/` with future `scheduled_time`
5. `GET /api/v1/notifications/`
6. `GET /api/v1/notifications/{id}/`
7. `POST /api/v1/notifications/{id}/schedule/`
8. `GET /api/v1/notifications/history/`
9. `GET /api/v1/notifications/{id}/attempts/`

## 6. Failure Simulation for QA

To force delivery failure for testing, include the configured failure keyword in title or message.

Default keyword:

```text
__FAIL__
```

Example create payload:

```json
{
  "title": "Test __FAIL__",
  "message": "Force background failure",
  "scheduled_time": "2026-05-24T10:00:00Z"
}
```

Expected behavior:
- Task marks notification as `failed` (or `permanently_failed` if max retries reached)
- `retry_count` increments
- `last_error` is populated
- Attempt record is created with `outcome: "failed"`

## 7. Example cURL Commands

Register:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"demo_user\",\"email\":\"demo@example.com\",\"password\":\"StrongPass123!\"}"
```

Get token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"demo_user\",\"password\":\"StrongPass123!\"}"
```

Create notification:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/notifications/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d "{\"title\":\"Reminder\",\"message\":\"Meeting at 3 PM\",\"scheduled_time\":\"2026-05-24T10:00:00Z\"}"
```
