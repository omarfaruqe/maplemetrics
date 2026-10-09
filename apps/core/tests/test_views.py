import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_reports_database_ok(client):
    response = client.get(reverse("core:health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


def test_home_page_renders_in_english(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert b"MapleMetrics" in response.content


def test_admin_login_page_is_reachable(client):
    response = client.get("/admin/login/")
    assert response.status_code == 200