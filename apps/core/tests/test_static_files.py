"""The admin's CSS and scripts must be served by the app itself in production (WhiteNoise)."""

import re

import pytest
from django.core.management import call_command
from django.test import Client, override_settings

MANIFEST = "whitenoise.storage.CompressedManifestStaticFilesStorage"


@pytest.fixture
def collected(tmp_path):
    """Collect the static files the way the Docker build does, into a temporary folder."""
    storages = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": MANIFEST},
    }
    with override_settings(STORAGES=storages, STATIC_ROOT=tmp_path, WHITENOISE_USE_FINDERS=False):
        call_command("collectstatic", interactive=False, verbosity=0)
        yield tmp_path


def stylesheet_link(html: str, prefix: str = "") -> str:
    match = re.search(rf'href="({re.escape(prefix)}/static/admin/css/base\.[0-9a-f]+\.css)"', html)
    assert match, html[:500]
    return match.group(1)


def test_collected_files_are_hashed_and_precompressed(collected):
    hashed = list((collected / "admin" / "css").glob("base.*.css"))
    assert hashed, "base.css should have a content hash in its name"
    assert list((collected / "admin" / "css").glob("base.*.css.gz"))
    assert (collected / "staticfiles.json").exists()


def test_admin_page_links_to_a_served_hashed_stylesheet(collected, db):
    client = Client()
    link = stylesheet_link(client.get("/admin/login/").content.decode())
    response = client.get(link)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/css")
    assert "immutable" in response["Cache-Control"]
    assert "max-age=315360000" in response["Cache-Control"]


def test_compressed_copy_is_sent_to_browsers_that_accept_it(collected, db):
    client = Client()
    link = stylesheet_link(client.get("/admin/login/").content.decode())
    response = client.get(link, headers={"accept-encoding": "gzip"})
    assert response["Content-Encoding"] == "gzip"
    assert response["Vary"] == "Accept-Encoding"


def test_static_files_work_under_a_url_prefix(collected, db):
    """The gateway strips ``/maplemetrics`` before Django sees the request, but links keep it."""
    with override_settings(FORCE_SCRIPT_NAME="/maplemetrics", STATIC_URL="/maplemetrics/static/"):
        client = Client()
        link = stylesheet_link(client.get("/admin/login/").content.decode(), "/maplemetrics")
        assert link.startswith("/maplemetrics/static/admin/css/base.")
        response = client.get(link.removeprefix("/maplemetrics"))
        assert response.status_code == 200


def test_missing_static_file_is_a_404_not_an_error(collected, db):
    assert Client().get("/static/admin/css/does-not-exist.css").status_code == 404


def test_admin_policy_allows_the_served_assets(collected, db):
    response = Client().get("/admin/login/")
    policy = response["Content-Security-Policy"]
    assert "script-src 'self'" in policy and "style-src 'self'" in policy


def test_static_requests_are_logged_quietly(collected, db, caplog):
    import logging

    client = Client()
    link = stylesheet_link(client.get("/admin/login/").content.decode())
    with caplog.at_level(logging.DEBUG, logger="maplemetrics.request"):
        client.get(link)
    levels = [r.levelno for r in caplog.records if r.path.startswith("/static/")]
    assert levels == [logging.DEBUG]
