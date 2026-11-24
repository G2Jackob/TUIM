from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny


def health(request):
    """Prosty healthcheck (np. dla deployu / monitoringu) z pingiem do bazy."""
    try:
        connection.ensure_connection()
    except Exception:  # noqa: BLE001
        return JsonResponse({"status": "error", "database": "down"}, status=503)
    return JsonResponse({"status": "ok"})


_public = {"authentication_classes": [], "permission_classes": [AllowAny]}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/", include("accounts.urls")),
    path("api/", include("shopping.urls")),
    # dokumentacja API dla zespołu mobilnego (wyłącz na produkcji, jeśli nie chcesz jej wystawiać)
    path("api/schema/", SpectacularAPIView.as_view(**_public), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", **_public), name="docs"),
]
