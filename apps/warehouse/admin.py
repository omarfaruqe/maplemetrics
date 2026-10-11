from django.contrib import admin

from .models import Indicator, Observation


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "source", "frequency", "unit")
    list_filter = ("source", "frequency")
    search_fields = ("code", "name_en", "name_fr")


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ("indicator", "geography", "date", "value")
    list_filter = ("indicator", "geography")
    date_hierarchy = "date"
