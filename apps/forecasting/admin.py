from django.contrib import admin

from .models import Forecast, ForecastPoint


class ForecastPointInline(admin.TabularInline):
    model = ForecastPoint
    extra = 0


@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ("indicator", "geography", "method", "trained_through", "vs_naive", "updated_at")
    list_filter = ("indicator", "method")
    inlines = [ForecastPointInline]
