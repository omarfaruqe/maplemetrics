from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext as _


def home(request: HttpRequest) -> HttpResponse:
    """Landing page placeholder; dashboards arrive in Sprint 2."""
    return HttpResponse(_("MapleMetrics: Canadian economic and market intelligence"))


def health(request: HttpRequest) -> JsonResponse:
    """Liveness and database check used by Docker healthchecks and CI."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok}, status=status)
