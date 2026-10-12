from django.urls import reverse


def get(client, **params):
    return client.get(reverse("analytics:provinces"), params).content.decode()


def test_empty_warehouse_shows_the_empty_state(client, db):
    assert "No data loaded yet" in get(client)


def test_default_province_is_quebec_and_compared_with_canada(client, economy):
    html = get(client)
    assert '<option value="Quebec" selected>' in html
    assert "−1.1 pts vs Canada" in html or "-1.1 pts vs Canada" in html
    assert html.count("<svg") == 3


def test_selector_lists_every_geography_canada_first(client, economy):
    html = get(client)
    assert (
        html.index('value="Canada"') < html.index('value="Ontario"') < html.index('value="Quebec"')
    )


def test_unknown_province_falls_back_to_the_default(client, economy):
    assert '<option value="Quebec" selected>' in get(client, geo="Atlantis")


def test_canada_alone_has_no_comparison(client, economy):
    html = get(client, geo="Canada")
    assert '<option value="Canada" selected>' in html
    assert "pts vs Canada" not in html


def test_province_without_history_says_so(client, economy):
    html = get(client, geo="Ontario")
    assert "No data for this province yet." in html


def test_french_page(client, economy):
    html = client.get(reverse("analytics:provinces"), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
    assert '<html lang="fr">' in html


def test_dashboard_links_to_the_provinces_page(client, economy):
    html = client.get(reverse("analytics:dashboard")).content.decode()
    assert reverse("analytics:provinces") in html
