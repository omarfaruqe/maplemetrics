import re

import pytest
from django.urls import reverse

from apps.core.security import ADMIN_POLICY, DOCS_POLICY, PERMISSIONS_POLICY, policy_for
from apps.core.tests.site_pages import page_urls, render_pages, seed_site


def directives(header: str) -> dict[str, str]:
    parts = [part.strip().split(" ", 1) for part in header.split(";") if part.strip()]
    return {name: (rest[0] if rest else "") for name, *rest in parts}


@pytest.fixture
def site(client, db):
    seed_site()
    return client


def test_site_pages_get_a_strict_policy(site):
    for name, url in page_urls().items():
        response = site.get(url)
        policy = directives(response["Content-Security-Policy"])
        assert policy["default-src"] == "'none'", name
        assert "script-src" not in policy, name
        assert policy["frame-ancestors"] == "'none'", name
        assert policy["base-uri"] == "'none'", name
        assert policy["form-action"] == "'self'", name
        assert "'unsafe-inline'" not in policy["style-src"], name
        assert response["Permissions-Policy"] == PERMISSIONS_POLICY


def test_the_nonce_in_the_header_matches_the_style_block(site):
    response = site.get(reverse("analytics:dashboard"))
    header_nonce = re.search(r"'nonce-([^']+)'", response["Content-Security-Policy"]).group(1)
    assert f'<style nonce="{header_nonce}">' in response.content.decode()


def test_the_nonce_changes_on_every_request(site):
    first = site.get(reverse("analytics:dashboard"))["Content-Security-Policy"]
    second = site.get(reverse("analytics:dashboard"))["Content-Security-Policy"]
    assert first != second


def test_pages_contain_no_script_and_no_inline_event_handlers(site):
    for name, html in render_pages(site).items():
        assert "<script" not in html.lower(), name
        assert not re.search(r"\son[a-z]+=", html), name
        assert "javascript:" not in html.lower(), name
        assert html.count("<style") == html.count("<style nonce="), name


def test_every_style_block_is_nonced_so_the_strict_policy_works(site):
    for name, html in render_pages(site).items():
        nonces = set(re.findall(r'<style nonce="([^"]+)"', html))
        assert len(nonces) == 1 and "" not in nonces, name


def test_api_responses_carry_the_policy_too(site):
    response = site.get("/api/v1/indicators/")
    assert response.status_code == 200
    assert directives(response["Content-Security-Policy"])["default-src"] == "'none'"


def test_docs_and_admin_have_their_own_looser_policies(site):
    docs = site.get(reverse("api:docs"))
    assert docs["Content-Security-Policy"] == DOCS_POLICY
    assert "https://cdn.jsdelivr.net" in directives(docs["Content-Security-Policy"])["script-src"]
    admin = site.get("/admin/login/")
    assert admin["Content-Security-Policy"] == ADMIN_POLICY


def test_policy_for_ignores_unknown_paths():
    assert "nonce-abc" in policy_for("/anything/", "abc")
    assert policy_for("/admin/x", "abc") == ADMIN_POLICY
    assert policy_for("/api/v1/docs/", "abc") == DOCS_POLICY
