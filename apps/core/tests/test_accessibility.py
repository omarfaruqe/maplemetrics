"""Structural accessibility checks that run on every test run, with no browser needed.

A browser-based audit with axe-core lives in ``test_axe_audit.py`` and runs in CI.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from apps.core.tests.site_pages import render_pages, seed_site

BASE_TEMPLATE = Path(__file__).resolve().parents[2] / "analytics/templates/analytics/base.html"


def luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def palette(block_start: str) -> dict[str, str]:
    css = BASE_TEMPLATE.read_text()
    start = css.index(block_start)
    block = css[start : css.index("}", start)]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


LIGHT = palette(":root {")
DARK = palette(':root[data-theme="dark"] {')
TEXT = ("fg", "muted", "faint", "link", "ok", "warn", "bad")
GRAPHICS = ("series-1", "series-2", "series-3", "negative", "emphasis", "context")


@pytest.mark.parametrize("colors", [LIGHT, DARK], ids=["light", "dark"])
def test_text_colors_meet_wcag_aa(colors):
    for background in ("bg", "surface"):
        for name in TEXT:
            ratio = contrast(colors[name], colors[background])
            assert ratio >= 4.5, f"{name} on {background}: {ratio:.2f}"


@pytest.mark.parametrize("colors", [LIGHT, DARK], ids=["light", "dark"])
def test_chart_colors_meet_the_non_text_minimum(colors):
    for background in ("bg", "surface"):
        for name in GRAPHICS:
            ratio = contrast(colors[name], colors[background])
            assert ratio >= 3.0, f"{name} on {background}: {ratio:.2f}"


class PageAudit(HTMLParser):
    """Collects the facts the checks below need from one page."""

    def __init__(self):
        super().__init__()
        self.lang = None
        self.ids: list[str] = []
        self.h1_count = 0
        self.svgs: list[dict] = []
        self.regions: list[dict] = []
        self.skip_links: list[str] = []
        self.label_targets: set[str] = set()
        self.select_ids: list[str] = []
        self.inline_handlers: list[str] = []
        self.tables: list[dict] = []
        self._table_stack: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a:
            self.ids.append(a["id"])
        self.inline_handlers += [name for name in a if name.startswith("on")]
        if tag == "h1":
            self.h1_count += 1
        elif tag == "svg":
            self.svgs.append(a)
        elif tag == "a" and "skip" in (a.get("class") or ""):
            self.skip_links.append(a.get("href", ""))
        elif tag == "label" and "for" in a:
            self.label_targets.add(a["for"])
        elif tag == "select":
            self.select_ids.append(a.get("id", ""))
        elif tag == "table":
            table = {"caption": False, "bad_headers": 0}
            self.tables.append(table)
            self._table_stack.append(table)
        elif tag == "caption" and self._table_stack:
            self._table_stack[-1]["caption"] = True
        elif tag == "th" and self._table_stack and "scope" not in a:
            self._table_stack[-1]["bad_headers"] += 1
        if "scroll" in (a.get("class") or "").split():
            self.regions.append(a)

    def handle_endtag(self, tag):
        if tag == "table" and self._table_stack:
            self._table_stack.pop()


@pytest.fixture
def audits(client, db):
    seed_site()
    return {name: audit(html) for name, html in render_pages(client).items()}


def audit(html: str) -> PageAudit:
    parser = PageAudit()
    parser.feed(html)
    return parser


def test_every_page_has_a_language_one_h1_and_a_skip_link(audits):
    for name, page in audits.items():
        assert page.lang == name.split("-")[1], name
        assert page.h1_count == 1, name
        assert page.skip_links == ["#main"], name
        assert "main" in page.ids, name


def test_ids_are_unique(audits):
    for name, page in audits.items():
        assert len(page.ids) == len(set(page.ids)), name


def test_every_chart_is_named_and_described(audits):
    charts = 0
    for name, page in audits.items():
        for svg in page.svgs:
            charts += 1
            assert svg.get("role") == "img", name
            assert svg.get("aria-label"), name
            assert svg.get("aria-describedby") in page.ids, name
    assert charts >= 8


def test_scrollable_areas_are_keyboard_reachable_and_named(audits):
    for name, page in audits.items():
        if page.svgs or page.tables:
            assert page.regions, name
        for region in page.regions:
            assert region.get("tabindex") == "0", name
            assert region.get("role") == "region", name
            assert region.get("aria-labelledby") in page.ids, name


def test_tables_have_captions_and_header_scopes(audits):
    for name, page in audits.items():
        for table in page.tables:
            assert table["caption"], name
            assert table["bad_headers"] == 0, name


def test_form_controls_are_labelled_and_do_not_submit_on_change(audits):
    for name, page in audits.items():
        for select_id in page.select_ids:
            assert select_id in page.label_targets, (name, select_id)
        assert not page.inline_handlers, (name, page.inline_handlers)
