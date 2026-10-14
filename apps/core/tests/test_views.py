from unittest.mock import patch

import pytest
from django.db.utils import OperationalError
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_reports_database_ok(client):
    response = client.get(reverse("core:health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


def test_health_endpoint_reports_degraded_when_database_is_down(client):
    with patch("apps.core.views.connection") as mock_connection:
        mock_connection.cursor.side_effect = OperationalError("down")
        response = client.get(reverse("core:health"))
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": False}


def test_home_redirects_to_the_dashboard(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 302
    assert response["Location"] == reverse("analytics:dashboard")


def test_admin_login_page_is_reachable(client):
    response = client.get("/admin/login/")
    assert response.status_code == 200
