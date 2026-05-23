from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path
from django.views.decorators.http import require_GET
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def _wants_strict_json(request) -> bool:
    accept = request.headers.get("Accept", "")
    return (
        "application/json" in accept
        and "text/html" not in accept
        and "*/*" not in accept
    )


@require_GET
def api_root(request):
    if _wants_strict_json(request):
        return JsonResponse(
            {
                "name": "Webbly Notification API",
                "docs": "/api/docs/",
                "schema": "/api/schema/",
                "health": "/api/v1/health/",
            }
        )
    return redirect("swagger-ui")


@require_GET
def api_docs(request):
    if _wants_strict_json(request):
        return JsonResponse(
            {
                "detail": "Swagger UI is HTML. Use /api/schema/ for machine-readable JSON.",
                "docs": "/api/docs/",
                "schema": "/api/schema/",
            }
        )
    return SpectacularSwaggerView.as_view(url_name="schema")(request)


urlpatterns = [
    path("", api_root, name="root"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", api_docs, name="swagger-ui"),
    path("api/v1/health/", include("apps.common.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
]
