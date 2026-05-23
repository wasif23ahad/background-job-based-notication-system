from django.urls import path

from apps.common.views import HealthCheckAPIView

urlpatterns = [
    path("", HealthCheckAPIView.as_view(), name="health-check"),
]
