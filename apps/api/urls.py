from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import SimpleRouter

from . import views

app_name = "api"

router = SimpleRouter()
router.register("indicators", views.IndicatorViewSet, basename="indicator")
router.register("observations", views.ObservationViewSet, basename="observation")
router.register("forecasts", views.ForecastViewSet, basename="forecast")

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="docs"),
    *router.urls,
]
