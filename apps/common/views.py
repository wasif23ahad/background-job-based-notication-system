import redis
from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def check_database() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone()[0] == 1


def check_redis() -> bool:
    client = redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    return bool(client.ping())


class HealthCheckAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        database_ok = check_database()
        redis_ok = check_redis()

        payload = {
            "status": "ok" if database_ok and redis_ok else "degraded",
            "services": {
                "database": "ok" if database_ok else "down",
                "redis": "ok" if redis_ok else "down",
            },
        }
        status_code = 200 if payload["status"] == "ok" else 503
        return Response(payload, status=status_code)
