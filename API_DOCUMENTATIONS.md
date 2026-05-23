# API Documentation (Postman Manual Testing)

## 1) Base Setup

Base URL:

```text
http://127.0.0.1:8000
```

Useful public URLs:

- `GET /` (redirects to `/api/docs/`)
- `GET /api/docs/`
- `GET /api/schema/`
- `GET /api/v1/health/`

Default headers for JSON requests:

```http
Content-Type: application/json
X-Request-ID: postman-local-001
```

For protected endpoints, also send:

```http
Authorization: Bearer <access_token>
```

All responses include an `X-Request-ID` header.

## 2) Postman Environment Variables

Create a Postman environment with:

- `base_url` = `http://127.0.0.1:8000`
- `username` = `demo-user`
- `email` = `demo-user@example.com`
- `password` = `strong-pass-123`
- `access_token` = (empty initially)
- `refresh_token` = (empty initially)
- `notification_id` = (empty initially)
- `failed_notification_id` = (empty initially)

## 3) Authentication APIs

### 3.1 Register User

`POST {{base_url}}/api/v1/auth/register/`

Body:

```json
{
  "username": "{{username}}",
  "email": "{{email}}",
  "password": "{{password}}"
}
```

Expected `201`:

```json
{
  "id": 1,
  "username": "demo-user",
  "email": "demo-user@example.com"
}
```

Common `400`:

```json
{
  "username": [
    "A user with that username already exists."
  ]
}
```

Password too short example (`< 8 chars`):

```json
{
  "password": [
    "Ensure this field has at least 8 characters."
  ]
}
```

### 3.2 Obtain JWT Token

`POST {{base_url}}/api/v1/auth/token/`

Body:

```json
{
  "username": "{{username}}",
  "password": "{{password}}"
}
```

Expected `200`:

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

Postman test script (save tokens):

```javascript
const data = pm.response.json();
pm.environment.set("access_token", data.access);
pm.environment.set("refresh_token", data.refresh);
```

Invalid credentials `401`:

```json
{
  "detail": "No active account found with the given credentials"
}
```

### 3.3 Refresh JWT Token

`POST {{base_url}}/api/v1/auth/token/refresh/`

Body:

```json
{
  "refresh": "{{refresh_token}}"
}
```

Expected `200`:

```json
{
  "access": "<new_access_token>"
}
```

## 4) Health, Schema, Docs

### 4.1 Health Check

`GET {{base_url}}/api/v1/health/` (public)

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

Possible `503` when dependency is down:

```json
{
  "status": "degraded",
  "services": {
    "database": "ok",
    "redis": "down"
  }
}
```

### 4.2 Schema

`GET {{base_url}}/api/schema/` (public, OpenAPI JSON/YAML response)

### 4.3 Swagger UI

`GET {{base_url}}/api/docs/` (public HTML UI)

## 5) Notification APIs

All notification endpoints below require:

```http
Authorization: Bearer {{access_token}}
```

### 5.1 Create Notification

`POST {{base_url}}/api/v1/notifications/`

Body:

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

Postman test script (save id):

```javascript
pm.environment.set("notification_id", pm.response.json().id);
```

Past time `400`:

```json
{
  "scheduled_time": [
    "Scheduled time must be in the future."
  ]
}
```

Missing fields `400`:

```json
{
  "title": ["This field is required."],
  "message": ["This field is required."],
  "scheduled_time": ["This field is required."]
}
```

Malformed datetime `400`:

```json
{
  "scheduled_time": [
    "Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]."
  ]
}
```

### 5.2 List Notifications

`GET {{base_url}}/api/v1/notifications/`

Query params:

- `status` (optional): `pending`, `processing`, `sent`, `failed`, `permanently_failed`

Example with query:

```text
GET {{base_url}}/api/v1/notifications/?status=failed
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

### 5.3 Retrieve One Notification

`GET {{base_url}}/api/v1/notifications/{{notification_id}}/`

Expected `200` object shape is same as list item.

Possible `404`:

```json
{
  "detail": "No Notification matches the given query."
}
```

### 5.4 History

`GET {{base_url}}/api/v1/notifications/history/`

This returns current user notifications (owner-scoped). Same JSON shape as list.

### 5.5 Reschedule Notification

`POST {{base_url}}/api/v1/notifications/{{notification_id}}/schedule/`

Body:

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

Past datetime `400`:

```json
{
  "scheduled_time": [
    "Scheduled time must be in the future."
  ]
}
```

Terminal status (sent/permanently_failed) `400`:

```json
{
  "detail": "Sent or permanently failed notifications cannot be rescheduled."
}
```

### 5.6 Retry Failed Notification

`POST {{base_url}}/api/v1/notifications/{{notification_id}}/retry/`

Body: empty `{}` is fine.

Expected `200` returns full notification object.

If notification is not in `failed` status:

```json
{
  "detail": "Only failed notifications can be retried."
}
```

If notification already permanently failed:

```json
{
  "detail": "Notification is permanently failed and cannot be retried."
}
```

### 5.7 Notification Attempt History

`GET {{base_url}}/api/v1/notifications/{{notification_id}}/attempts/`

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

Failure attempt example:

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

## 6) Manual Postman Test Sequence (End-to-End)

1. `POST /api/v1/auth/register/`
2. `POST /api/v1/auth/token/` and save `access_token`, `refresh_token`
3. `GET /api/v1/health/`
4. `POST /api/v1/notifications/` with future `scheduled_time`
5. `GET /api/v1/notifications/`
6. `GET /api/v1/notifications/{{notification_id}}/`
7. `POST /api/v1/notifications/{{notification_id}}/schedule/` with new future time
8. `GET /api/v1/notifications/history/`
9. `GET /api/v1/notifications/{{notification_id}}/attempts/`

## 7) How to Manually Force a Failure and Test Retry Rules

Use the default failure keyword `__FAIL__` in title or message.

1. Create notification:

```json
{
  "title": "Payment __FAIL__",
  "message": "Intentional failure test",
  "scheduled_time": "2026-05-24T10:00:00Z"
}
```

2. Wait for worker/beat processing.
3. Check `GET /api/v1/notifications/{{id}}/` and verify status becomes `failed` (or `permanently_failed` if max retries reached).
4. Call `POST /api/v1/notifications/{{id}}/retry/` repeatedly.
5. After 3 failed attempts, status becomes `permanently_failed` and further retry returns:

```json
{
  "detail": "Notification is permanently failed and cannot be retried."
}
```

## 8) Common Auth Errors

Missing token `401`:

```json
{
  "detail": "Authentication credentials were not provided."
}
```

Expired/invalid token `401`:

```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is invalid or expired"
    }
  ]
}
```
