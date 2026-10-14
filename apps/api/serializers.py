from django.utils.translation import get_language
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.forecasting.models import Forecast, ForecastPoint
from apps.warehouse.models import Indicator, Observation


class IndicatorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(help_text="Name in the language of the request.")
    observation_count = serializers.IntegerField(read_only=True)
    first_date = serializers.DateField(read_only=True)
    latest_date = serializers.DateField(read_only=True)

    class Meta:
        model = Indicator
        fields = [
            "code",
            "source",
            "name",
            "name_en",
            "name_fr",
            "unit",
            "frequency",
            "observation_count",
            "first_date",
            "latest_date",
        ]

    @extend_schema_field(serializers.CharField())
    def get_name(self, obj: Indicator) -> str:
        return obj.name_fr if (get_language() or "en").startswith("fr") else obj.name_en


class ObservationSerializer(serializers.ModelSerializer):
    indicator = serializers.CharField(source="indicator.code")

    class Meta:
        model = Observation
        fields = ["indicator", "geography", "date", "value"]


class ForecastPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastPoint
        fields = ["date", "value", "lower", "upper"]


class ForecastSerializer(serializers.ModelSerializer):
    indicator = serializers.CharField(source="indicator.code")
    points = ForecastPointSerializer(many=True, read_only=True)

    class Meta:
        model = Forecast
        fields = [
            "id",
            "indicator",
            "geography",
            "method",
            "trained_through",
            "interval_level",
            "backtest_origins",
            "mase",
            "vs_naive",
            "updated_at",
            "points",
        ]
