# Webbly Notification API

> **Live API:** [https://background-job-based-notication-system.onrender.com](https://background-job-based-notication-system.onrender.com)
>
> **Note:** Since it is deployed on Tender, the service may take some time to load on first access.

Production-ready backend for a background job based notification system built with Django, DRF, Celery, and Redis.

## Overview
- JWT-secured API for creating and managing scheduled notifications.
- Async delivery pipeline with retry and permanent-failure handling.
- Owner-scoped notification access (users can only access their own data).
- OpenAPI schema and Swagger UI included.

Detailed endpoint usage is documented in [API_DOCUMENTS.md](./API_DOCUMENTS.md).

## Tech Stack
- Python 3.12
- Django + Django REST Framework
- SimpleJWT (authentication)
- Celery + Redis (background jobs)
- PostgreSQL (via `DATABASE_URL`)
- drf-spectacular (OpenAPI/Swagger)
- `uv` (dependency and command runner)

## Project Structure
```text
apps/
  accounts/        # registration + JWT integration
  notifications/   # models, API, services, celery tasks
  common/          # health checks, middleware, shared utilities
config/
  settings/        # base/local/production/test settings
  urls.py          # root routes + API wiring
```

## Local Setup
1. Install dependencies:
   - `uv sync --dev`
2. Create environment file:
   - `cp .env.example .env` (or copy manually on Windows)
3. Apply migrations:
   - `uv run python manage.py migrate`
4. Run API:
   - `uv run python manage.py runserver`
5. Run worker (separate terminal):
   - `uv run celery -A config worker -l info`

## Local Setup with Docker
Use this when you want to run the full stack (API + Celery worker + Celery beat + Postgres + Redis) locally.

1. Ensure Docker Desktop is running.
2. Create `.env` from `.env.example`.
3. For Docker local networking, keep these values:
   - `DATABASE_URL=postgresql://postgres:postgres@db:5432/webbly_notifications`
   - `REDIS_URL=redis://redis:6379/0`
4. Build and start all services:
   - `docker compose up --build`
5. Run in detached mode (optional):
   - `docker compose up -d --build`

Services started by compose:
- `web` (Django API on port `8000`)
- `worker` (Celery worker)
- `beat` (Celery beat scheduler)
- `db` (Postgres on `5432`)
- `redis` (Redis on `6379`)

Useful Docker commands:
- View logs for all services: `docker compose logs -f`
- View only API logs: `docker compose logs -f web`
- Stop services: `docker compose down`
- Stop and remove volumes (full reset): `docker compose down -v`

### Docker Quick Verify
After `docker compose up --build`, run this quick checklist:

1. Check health:
   - Open `http://127.0.0.1:8000/api/v1/health/`
   - Expect `status: "ok"` with `database: "ok"` and `redis: "ok"`.
2. Open docs:
   - Open `http://127.0.0.1:8000/api/docs/`
   - Confirm Swagger UI loads.
3. Create user:
   - `POST /api/v1/auth/register/` from Swagger or Postman.
4. Obtain token:
   - `POST /api/v1/auth/token/`
   - Copy the `access` token and click **Authorize** in Swagger.
5. Create notification:
   - `POST /api/v1/notifications/` with a future `scheduled_time`.
6. Verify background processing:
   - Watch worker logs: `docker compose logs -f worker`
   - Confirm task execution and notification status transition.
7. Verify API state:
   - `GET /api/v1/notifications/`
   - `GET /api/v1/notifications/{id}/attempts/`

## Useful Local URLs
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/docs/`
- `http://127.0.0.1:8000/api/schema/`
- `http://127.0.0.1:8000/api/v1/health/`

## Environment Variables
Minimum required for production:
- `DJANGO_SECRET_KEY`
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `DATABASE_URL`
- `REDIS_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

Important worker/runtime controls:
- `RUN_CELERY_WORKER=true`
- `CELERY_WORKER_POOL=solo`
- `CELERY_WORKER_CONCURRENCY=1`
- `WEB_CONCURRENCY=1`
- `WEB_TIMEOUT=120`

Use `.env.example` for full variable reference and provider URLs.

## API Summary
- Auth:
  - `POST /api/v1/auth/register/`
  - `POST /api/v1/auth/token/`
  - `POST /api/v1/auth/token/refresh/`
- Notifications:
  - `POST /api/v1/notifications/`
  - `GET /api/v1/notifications/`
  - `GET /api/v1/notifications/{id}/`
  - `GET /api/v1/notifications/history/`
  - `POST /api/v1/notifications/{id}/schedule/`
  - `POST /api/v1/notifications/{id}/retry/`
  - `GET /api/v1/notifications/{id}/attempts/`
- System:
  - `GET /api/v1/health/`
  - `GET /api/schema/`
  - `GET /api/docs/`

## Business Rules
- `scheduled_time` must be in the future.
- Retries are allowed only when notification status is `failed`.
- Max retry attempts: `3`.
- After max failures, status becomes `permanently_failed`.

## Testing
- Run all tests:
  - `uv run pytest -q`
- Run Django checks:
  - `uv run python manage.py check --settings=config.settings.local`

## Deployment (Render)
The repository includes `Dockerfile`, `entrypoint.sh`, and `render.yaml` for Render deployment.

Recommended Render settings:
- Health check path: `/api/v1/health/`
- `RUN_CELERY_WORKER=true`
- `WEB_CONCURRENCY=1`
- `CELERY_WORKER_POOL=solo`
- `CELERY_WORKER_CONCURRENCY=1`
