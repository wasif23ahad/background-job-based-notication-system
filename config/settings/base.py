from __future__ import annotations

import os
import ssl
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import dj_database_url
from dotenv import load_dotenv


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def ensure_rediss_ssl_param(url: str, default_req: str = "required") -> str:
    if not url.startswith("rediss://"):
        return url

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("ssl_cert_reqs", default_req)
    return urlunparse(parsed._replace(query=urlencode(query)))


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")
DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts.apps.AccountsConfig",
    "apps.common.apps.CommonConfig",
    "apps.notifications.apps.NotificationsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

database_url = os.getenv("DATABASE_URL")
if database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=600,
            ssl_require=database_url.startswith("postgres"),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Webbly Notification API",
    "DESCRIPTION": "Background job based notification system backend",
    "VERSION": "1.0.0",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME", "900"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME", "86400"))
    ),
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ssl_cert_reqs = os.getenv("CELERY_REDIS_SSL_CERT_REQS", "required")
CELERY_BROKER_URL = ensure_rediss_ssl_param(
    os.getenv("CELERY_BROKER_URL", REDIS_URL),
    default_req=ssl_cert_reqs,
)
CELERY_RESULT_BACKEND = ensure_rediss_ssl_param(
    os.getenv("CELERY_RESULT_BACKEND", REDIS_URL),
    default_req=ssl_cert_reqs,
)
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", TIME_ZONE)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = env_bool("CELERY_TASK_EAGER_PROPAGATES", False)
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_TIMEOUT = float(
    os.getenv("CELERY_BROKER_CONNECTION_TIMEOUT", "3")
)
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_connect_timeout": float(
        os.getenv("CELERY_REDIS_SOCKET_CONNECT_TIMEOUT", "2")
    ),
    "socket_timeout": float(os.getenv("CELERY_REDIS_SOCKET_TIMEOUT", "2")),
}
ssl_cert_req_map = {
    "required": ssl.CERT_REQUIRED,
    "optional": ssl.CERT_OPTIONAL,
    "none": ssl.CERT_NONE,
    "CERT_REQUIRED": ssl.CERT_REQUIRED,
    "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
    "CERT_NONE": ssl.CERT_NONE,
}
ssl_cert_req_value = ssl_cert_req_map.get(ssl_cert_reqs, ssl.CERT_REQUIRED)
if CELERY_BROKER_URL.startswith("rediss://"):
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl_cert_req_value}
if CELERY_RESULT_BACKEND.startswith("rediss://"):
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl_cert_req_value}

UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

NOTIFICATION_FAILURE_KEYWORD = os.getenv("NOTIFICATION_FAILURE_KEYWORD", "__FAIL__")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.common.logging_filters.RequestIDFilter"},
    },
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s [%(request_id)s] [%(name)s] %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
