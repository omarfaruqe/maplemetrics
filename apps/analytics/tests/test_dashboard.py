from django.urls import reverse


def test_empty_dashboard_explains_itself(client, db):
    response = client.get(reverse("analytics:dashboard"))
    assert response.status_code == 200
    assert "No data loaded yet" in response.content.decode()


def test_dashboard_shows_tiles_charts_and_tables(client, economy):
    html = client.get(reverse("analytics:dashboard")).content.decode()
    assert "Real policy rate" in html
    assert "\u22120.25%" in html or "-0.25%" in html
    assert "6.5%" in html
    assert html.count("<svg") == 3
    assert "Unemployment rate by province" in html
    assert "Quebec" in html and "Ontario" in html


def test_dashboard_renders_in_french(client, economy):
    html = client.get(reverse("analytics:dashboard"), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
    assert '<html lang="fr">' in html
