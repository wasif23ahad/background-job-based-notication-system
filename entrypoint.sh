#!/bin/sh
set -e

echo "Applying database migrations..."
uv run python manage.py migrate --noinput

if [ "${RUN_CELERY_WORKER:-false}" = "true" ]; then
  echo "Starting Celery worker in background (RUN_CELERY_WORKER=true)..."
  uv run celery -A config worker -l "${CELERY_LOG_LEVEL:-info}" &
fi

exec "$@"
