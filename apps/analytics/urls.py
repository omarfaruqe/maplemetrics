from django.urls import path

from . import downloads, views

app_name = "analytics"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("provinces/", views.provinces, name="provinces"),
    path("downloads/policy-rate.csv", downloads.rates, name="rates_csv"),
    path("downloads/unemployment-by-province.csv", downloads.unemployment, name="unemployment_csv"),
    path("downloads/real-retail-by-province.csv", downloads.retail, name="retail_csv"),
    path("downloads/province.csv", downloads.province, name="province_csv"),
]
