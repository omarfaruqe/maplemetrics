from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/v1/", include("apps.api.urls")),
    path("", include("apps.analytics.urls")),
    path("", include("apps.forecasting.urls")),
    path("", include("apps.core.urls")),
]
