import gettext
import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import translation

from apps.analytics.tests.conftest import economy  # noqa: F401
from apps.core import i18n_tools
from apps.core.localize import geography_name, number

PO = r"""
# a comment
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\n"

#, fuzzy
msgid "Skipped"
msgstr "Ignoré"

msgid "Untranslated"
msgstr ""

msgid "Hello"
msgstr "Bonjour"

msgctxt "geography"
msgid "Quebec"
msgstr "Québec"

msgid "Long text"
msgstr ""
"Première ligne\n"
"Deuxième \"citée\""
"""


def test_parse_po_reads_contexts_multiline_and_skips_fuzzy_and_empty():
    messages = i18n_tools.parse_po(PO)
    assert messages["Hello"] == "Bonjour"
    assert messages["geography\x04Quebec"] == "Québec"
    assert messages["Long text"] == 'Première ligne\nDeuxième "citée"'
    assert "Skipped" not in messages
    assert "Untranslated" not in messages
    assert "Content-Type" in messages[""]


def test_built_mo_is_readable_by_the_standard_library():
    mo = i18n_tools.build_mo(i18n_tools.parse_po(PO))
    catalog = gettext.GNUTranslations(io.BytesIO(mo))
    assert catalog.gettext("Hello") == "Bonjour"
    assert catalog.pgettext("geography", "Quebec") == "Québec"
    assert catalog.gettext("Long text").startswith("Première")
    assert catalog.gettext("Missing") == "Missing"


def test_committed_catalogs_are_up_to_date():
    assert i18n_tools.stale_catalogs() == []


def test_every_string_in_the_code_has_a_french_translation():
    assert i18n_tools.untranslated() == []


def test_template_and_python_extraction():
    found = i18n_tools._template_messages(
        """{% trans "Plain" %}{% trans 'Single' %}"""
        """{% blocktrans with pct=level %}{{ pct }}% range{% endblocktrans %}"""
    )
    assert found == {"Plain", "Single", "%(pct)s%% range"}
    code = (
        "from django.utils.translation import gettext as _, pgettext\n"
        "a = _('One')\nb = _('Two ' 'parts')\nc = pgettext('ctx', 'Item')\nd = _(variable)\n"
    )
    assert i18n_tools._python_messages(code) == {"One", "Two parts", "ctx\x04Item"}


@pytest.fixture
def scratch_locale(tmp_path, settings):
    folder = tmp_path / "xx" / "LC_MESSAGES"
    folder.mkdir(parents=True)
    (folder / "django.po").write_text(PO, encoding="utf-8")
    settings.LOCALE_PATHS = [tmp_path]
    return folder


def test_compile_command_writes_and_check_detects_staleness(scratch_locale):
    out = io.StringIO()
    with pytest.raises(CommandError, match="stale catalog"):
        call_command("compile_translations", "--check", stdout=out)
    call_command("compile_translations", stdout=out)
    assert (scratch_locale / "django.mo").exists()
    assert "compiled" in out.getvalue()
    (scratch_locale / "django.po").write_text(PO + '\nmsgid "New"\nmsgstr "Nouveau"\n')
    with pytest.raises(CommandError, match="stale catalog"):
        call_command("compile_translations", "--check", stdout=out)


def test_check_command_passes_on_the_real_catalog():
    out = io.StringIO()
    call_command("compile_translations", "--check", stdout=out)
    assert "complete" in out.getvalue()


def test_number_follows_the_language():
    with translation.override("en"):
        assert number(6.55, 2) == "6.55"
        assert number(2.5, signed=True) == "+2.5"
    with translation.override("fr"):
        assert number(6.55, 2) == "6,55"
        assert number(-0.4, signed=True) == "-0,4"


def test_geography_names_translate_and_unknown_names_pass_through():
    with translation.override("fr"):
        assert geography_name("Quebec") == "Québec"
        assert geography_name("British Columbia") == "Colombie-Britannique"
        assert geography_name("Atlantis") == "Atlantis"
    with translation.override("en"):
        assert geography_name("Quebec") == "Quebec"


@pytest.mark.parametrize(
    ("name", "english", "french"),
    [
        ("analytics:dashboard", "Policy rate, core inflation and the real rate", "Taux directeur"),
        ("analytics:provinces", "Province comparison", "Comparaison des provinces"),
        ("core:freshness", "Data freshness", "Fraîcheur des données"),
    ],
)
def test_pages_are_translated(client, economy, name, english, french):  # noqa: F811
    assert english in client.get(reverse(name)).content.decode()
    html = client.get(reverse(name), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
    assert french in html
    assert english not in html


def test_french_dashboard_uses_french_names_and_decimal_commas(client, economy):  # noqa: F811
    html = client.get(reverse("analytics:dashboard"), HTTP_ACCEPT_LANGUAGE="fr").content.decode()
    assert "Québec" in html
    assert "Taux directeur" in html
    assert "2,25%" in html
    assert "2.25%" not in html


def test_language_switcher_sets_a_cookie_that_wins(client, economy):  # noqa: F811
    english = client.get(reverse("analytics:dashboard")).content.decode()
    assert 'name="language" value="fr"' in english
    response = client.post(
        reverse("set_language"), {"language": "fr", "next": reverse("analytics:provinces")}
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("analytics:provinces")
    page = client.get(reverse("analytics:provinces")).content.decode()
    assert '<html lang="fr">' in page
    assert 'name="language" value="en"' in page


def test_switcher_on_the_freshness_page_keeps_the_query(client, db):
    html = client.get(reverse("core:freshness") + "?x=1").content.decode()
    assert 'value="/freshness/?x=1"' in html
