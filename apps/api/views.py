from datetime import date

from django.db.models import Count, Max, Min
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.forecasting.models import Forecast
from apps.warehouse.models import Indicator, Observation

from .serializers import ForecastSerializer, IndicatorSerializer, ObservationSerializer


def _text(name: str, description: str) -> OpenApiParameter:
    return OpenApiParameter(name, str, description=description)


def _parse_date(raw: str, name: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: "Use the format YYYY-MM-DD."}) from None


@extend_schema_view(
    list=extend_schema(summary="List indicators", tags=["indicators"]),
    retrieve=extend_schema(summary="One indicator, by code", tags=["indicators"]),
)
class IndicatorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IndicatorSerializer
    lookup_field = "code"
    lookup_value_regex = "[^/]+"
    queryset = Indicator.objects.annotate(
        observation_count=Count("observations"),
        first_date=Min("observations__date"),
        latest_date=Max("observations__date"),
    ).order_by("code")


@extend_schema_view(
    list=extend_schema(
        summary="List observations",
        tags=["observations"],
        parameters=[
            _text("indicator", "Indicator code, for example LFS_UNEMPLOYMENT_RATE."),
            _text("geography", "Exact geography name, for example Quebec."),
            _text("start", "Earliest date, YYYY-MM-DD."),
            _text("end", "Latest date, YYYY-MM-DD."),
        ],
    )
)
class ObservationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ObservationSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        queryset = Observation.objects.select_related("indicator").order_by(
            "indicator__code", "geography", "date"
        )
        params = self.request.query_params
        if code := params.get("indicator"):
            queryset = queryset.filter(indicator__code=code)
        if geography := params.get("geography"):
            queryset = queryset.filter(geography=geography)
        if start := params.get("start"):
            queryset = queryset.filter(date__gte=_parse_date(start, "start"))
        if end := params.get("end"):
            queryset = queryset.filter(date__lte=_parse_date(end, "end"))
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List stored forecasts",
        tags=["forecasts"],
        parameters=[
            _text("indicator", "Indicator code."),
            _text("geography", "Exact geography name."),
        ],
    ),
    retrieve=extend_schema(summary="One forecast with its monthly points", tags=["forecasts"]),
)
class ForecastViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ForecastSerializer

    def get_queryset(self):
        queryset = (
            Forecast.objects.select_related("indicator")
            .prefetch_related("points")
            .order_by("indicator__code", "geography")
        )
        params = self.request.query_params
        if code := params.get("indicator"):
            queryset = queryset.filter(indicator__code=code)
        if geography := params.get("geography"):
            queryset = queryset.filter(geography=geography)
        return queryset
