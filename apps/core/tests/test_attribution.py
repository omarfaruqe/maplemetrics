"""Every page must carry the data-source credit that the licences require."""

import pytest

from apps.core.tests.site_pages import page_urls, render_pages, seed_site

REQUIRED = {
    "en": [
        "Adapted from Statistics Canada",
        "This does not constitute an endorsement by Statistics Canada",
        "https://www.statcan.gc.ca/en/reference/licence",
        "Source: Bank of Canada",
        "https://www.bankofcanada.ca/terms/",
    ],
    "fr": [
        "Adapté de Statistique Canada",
        "Cela ne constitue pas une approbation de ce produit par Statistique Canada",
        "https://www.statcan.gc.ca/fr/avis/licence-ouverte",
        "Source : Banque du Canada",
        "https://www.banqueducanada.ca/conditions-utilisation-avis/",
    ],
}


@pytest.fixture
def pages(client, db):
    seed_site()
    return render_pages(client)


def test_every_page_credits_both_sources_in_its_language(pages):
    assert len(pages) == 2 * len(page_urls())
    for name, html in pages.items():
        language = name.split("-")[1]
        assert html.count("<footer") == 1, name
        for text in REQUIRED[language]:
            assert text in html, (name, text)


def test_footer_links_to_the_freshness_page(pages):
    for name, html in pages.items():
        assert 'href="/freshness/"' in html, name
