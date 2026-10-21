from django.urls import path

from . import downloads, views

app_name = "forecasting"

urlpatterns = [
    path("forecasts/", views.forecasts, name="forecasts"),
    path("downloads/forecast.csv", downloads.forecast, name="forecast_csv"),
]
