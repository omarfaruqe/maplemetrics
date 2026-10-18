from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from apps.warehouse.freshness import freshness_report

from .status import snapshot


def home(request: HttpRequest) -> HttpResponse:
    """The dashboard is the front page."""
    return redirect("analytics:dashboard")


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


def freshness(request: HttpRequest) -> HttpResponse:
    """How recent each indicator's data is, problems first."""
    today = timezone.localdate()
    context = {"rows": freshness_report(today=today), "today": today}
    return render(request, "core/freshness.html", context)


@never_cache
def status(request: HttpRequest) -> HttpResponse:
    """A page for people: is the system working, and is the data up to date?"""
    state = snapshot()
    state["freshness_url"] = reverse("core:freshness")
    state["active"] = "status"
    response = render(request, "core/status.html", state)
    response.status_code = 503 if state["overall"] == "down" else 200
    return response


@never_cache
def status_json(request: HttpRequest) -> JsonResponse:
    """The same facts for monitors and scripts. Answers 503 when something essential is down."""
    state = snapshot()
    body = {
        "status": state["overall"],
        "version": state["version"],
        "time": state["time"].isoformat(),
        "checks": {check.key: {"status": check.status, **check.data} for check in state["checks"]},
    }
    return JsonResponse(body, status=503 if state["overall"] == "down" else 200)
