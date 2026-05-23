from __future__ import annotations

import os

from celery import Celery
from django.conf import settings as django_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.update(
    broker_url=getattr(django_settings, "CELERY_BROKER_URL", None),
    result_backend=getattr(django_settings, "CELERY_RESULT_BACKEND", None),
    task_always_eager=getattr(django_settings, "CELERY_TASK_ALWAYS_EAGER", False),
    task_eager_propagates=getattr(
        django_settings, "CELERY_TASK_EAGER_PROPAGATES", False
    ),
    task_ignore_result=getattr(django_settings, "CELERY_TASK_IGNORE_RESULT", True),
)
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
