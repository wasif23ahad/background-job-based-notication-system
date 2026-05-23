from django.db import models


class HealthDependencyStatus(models.TextChoices):
    OK = "ok", "ok"
    DOWN = "down", "down"


class HealthOverallStatus(models.TextChoices):
    OK = "ok", "ok"
    DEGRADED = "degraded", "degraded"
