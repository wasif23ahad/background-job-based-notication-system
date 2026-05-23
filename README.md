# Background Job Notification System

Backend API for scheduling and processing notifications with Django, DRF, Celery, and Redis.

## Tech Stack
- Django + Django REST Framework
- JWT auth (SimpleJWT)
- Celery + Redis for background jobs
- PostgreSQL via `DATABASE_URL` (Neon or local Postgres)
- OpenAPI docs via drf-spectacular

## Quick Start (Local)
1. Install dependencies:
   - `uv sync --dev`
2. Configure environment:
   - `.env.example` documents all keys and provider URLs.
   - `.env` is already created locally; replace secrets as needed.
3. Run migrations:
   - `uv run python manage.py migrate`
4. Start API:
   - `uv run python manage.py runserver`
5. Start worker:
   - `uv run celery -A config worker -l info`

## Docker Compose
- `docker compose up --build`
- Services: `web`, `worker`, `beat`, `db`, `redis`

## API Endpoints
- Auth:
  - `POST /api/v1/auth/register/`
  - `POST /api/v1/auth/token/`
  - `POST /api/v1/auth/token/refresh/`
- Notifications:
  - `POST /api/v1/notifications/` (create + schedule)
  - `GET /api/v1/notifications/` (list current user)
  - `GET /api/v1/notifications/history/`
  - `POST /api/v1/notifications/{id}/schedule/`
  - `POST /api/v1/notifications/{id}/retry/`
- Docs:
  - `GET /api/schema/`
  - `GET /api/docs/`

## Business Rules Implemented
- Reject notifications if `scheduled_time` is in the past.
- Retry allowed only for `failed` notifications.
- On each delivery failure, increment `retry_count`.
- At 3 failures, mark as `permanently_failed` and block further retries.

## Tests
- Run full suite: `uv run pytest -q`
- Current coverage focus:
  - auth flow
  - schedule validation
  - history ownership filter
  - retry success path
  - max retry cap enforcement
