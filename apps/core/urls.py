from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("freshness/", views.freshness, name="freshness"),
    path("guide/", views.guide, name="guide"),
    path("status/", views.status, name="status"),
    path("status.json", views.status_json, name="status_json"),
]
