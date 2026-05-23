import redis
from django.conf import settings
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.constants import HealthDependencyStatus, HealthOverallStatus


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


class HealthServicesSerializer(serializers.Serializer):
    database = serializers.ChoiceField(choices=HealthDependencyStatus.choices)
    redis = serializers.ChoiceField(choices=HealthDependencyStatus.choices)


class HealthCheckResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=HealthOverallStatus.choices)
    services = HealthServicesSerializer()


class HealthCheckAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={
            200: HealthCheckResponseSerializer,
            503: HealthCheckResponseSerializer,
        },
    )
    def get(self, request):
        database_ok = check_database()
        redis_ok = check_redis()

        payload = {
            "status": (
                HealthOverallStatus.OK
                if database_ok and redis_ok
                else HealthOverallStatus.DEGRADED
            ),
            "services": {
                "database": (
                    HealthDependencyStatus.OK if database_ok else HealthDependencyStatus.DOWN
                ),
                "redis": (
                    HealthDependencyStatus.OK if redis_ok else HealthDependencyStatus.DOWN
                ),
            },
        }
        status_code = 200 if payload["status"] == HealthOverallStatus.OK else 503
        return Response(payload, status=status_code)
