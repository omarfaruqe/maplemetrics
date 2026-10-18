import re
from html.parser import HTMLParser

import pytest
from django.conf import settings
from django.urls import reverse

from apps.forecasting.service import DEFAULT_LEVEL
from apps.forecasting.views import NO_EDGE

pytestmark = pytest.mark.django_db


class Outline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1 = 0
        self.h2_ids = []
        self.anchors = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "h2" and a.get("id"):
            self.h2_ids.append(a["id"])
        if tag == "a" and (a.get("href") or "").startswith("#") and a["href"] != "#main":
            self.anchors.append(a["href"][1:])


def fetch(client, language):
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
    response = client.get(reverse("core:guide"))
    assert response.status_code == 200
    return response.content.decode()


def outline(html):
    parsed = Outline()
    parsed.feed(html)
    return parsed


def test_guide_answers_in_both_languages(client):
    assert "How to read this" in fetch(client, "en")
    assert "Comment lire ces données" in fetch(client, "fr")


def test_both_languages_have_the_same_sections(client):
    en, fr = outline(fetch(client, "en")), outline(fetch(client, "fr"))
    assert en.h2_ids == fr.h2_ids
    assert len(en.h2_ids) == 10


def test_one_h1_and_every_contents_link_resolves(client):
    for language in ("en", "fr"):
        parsed = outline(fetch(client, language))
        assert parsed.h1 == 1, language
        assert sorted(parsed.anchors) == sorted(parsed.h2_ids), language
        assert set(parsed.anchors) <= set(parsed.ids), language


def test_numbers_in_the_text_come_from_the_code(client):
    level = round(DEFAULT_LEVEL * 100)
    edge = round((1 - NO_EDGE) * 100)
    assert (level, edge) == (80, 10)
    for language in ("en", "fr"):
        text = re.sub(r"\s+", " ", fetch(client, language).replace("&nbsp;", " "))
        assert f"{level} %" in text or f"{level}%" in text, language
        assert f"{edge} %" in text or f"{edge}%" in text, language


def test_forecast_page_links_to_the_guide(client):
    from apps.core.tests.site_pages import seed_site

    seed_site()
    url = reverse("forecasting:forecasts") + "?indicator=LFS_UNEMPLOYMENT_RATE&geo=Canada"
    assert reverse("core:guide") in client.get(url).content.decode()
