"""Browser-based accessibility audit with axe-core (WCAG 2.2 AA plus best practices).

It renders every page in English and French, then checks each one in light and dark mode at a
desktop width and at 320 CSS pixels wide (the WCAG reflow width), where it also checks that the
page does not scroll sideways, which axe cannot see. It needs Playwright with Chromium
and a copy of axe-core, so it only runs when ``AXE_JS`` points at ``axe.min.js``. CI sets that up;
see ``docs/accessibility.md`` for running it locally.
"""

import os
from pathlib import Path

import pytest

from apps.core.tests.site_pages import render_pages, seed_site

AXE_JS = os.environ.get("AXE_JS", "")
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]
VIEWPORTS = {"desktop": {"width": 1280, "height": 900}, "reflow": {"width": 320, "height": 800}}

pytestmark = pytest.mark.skipif(not AXE_JS, reason="set AXE_JS to the path of axe.min.js to run")


def test_no_axe_violations_on_any_page(client, db, tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    axe_source = Path(AXE_JS).read_text()
    seed_site()
    files = {}
    for name, html in render_pages(client).items():
        path = tmp_path / f"{name}.html"
        path.write_text(html)
        files[name] = path

    problems = []
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for scheme in ("light", "dark"):
            for viewport_name, viewport in VIEWPORTS.items():
                context = browser.new_context(color_scheme=scheme, viewport=viewport)
                for name, path in files.items():
                    page = context.new_page()
                    page.goto(path.as_uri())
                    scroll_width = page.evaluate("document.documentElement.scrollWidth")
                    if scroll_width > viewport["width"]:
                        problems.append(
                            f"{name} [{scheme}, {viewport_name}]: page scrolls sideways "
                            f"({scroll_width}px wide in a {viewport['width']}px window)"
                        )
                    page.evaluate(axe_source)
                    result = page.evaluate(
                        "tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS
                    )
                    for violation in result["violations"]:
                        targets = [node["target"] for node in violation["nodes"][:3]]
                        problems.append(
                            f"{name} [{scheme}, {viewport_name}]: {violation['id']} "
                            f"({violation['impact']}) {targets}"
                        )
                    page.close()
                context.close()
        browser.close()
    assert not problems, "\n".join(problems)


def test_browser_reports_no_csp_violations_and_still_applies_styles(live_server, transactional_db):
    """The strict Content-Security-Policy must not break the pages in a real browser."""
    from apps.core.tests.site_pages import page_urls

    sync_api = pytest.importorskip("playwright.sync_api")
    seed_site()
    problems = []
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for scheme in ("light", "dark"):
            context = browser.new_context(color_scheme=scheme)
            for name, url in page_urls().items():
                page = context.new_page()
                messages = []
                page.on("console", lambda msg, messages=messages: messages.append(msg.text))
                page.goto(live_server.url + url)
                background = page.evaluate("getComputedStyle(document.body).backgroundColor")
                chart_stroke = page.evaluate(
                    "(() => { const p = document.querySelector('svg path.line');"
                    " return p ? getComputedStyle(p).stroke : 'none'; })()"
                )
                violations = [m for m in messages if "Content Security Policy" in m]
                if violations:
                    problems.append(f"{name} [{scheme}]: {violations[:2]}")
                if background == "rgba(0, 0, 0, 0)":
                    problems.append(f"{name} [{scheme}]: page styles were blocked")
                if name != "freshness" and chart_stroke in ("none", "rgb(0, 0, 0)"):
                    problems.append(f"{name} [{scheme}]: chart style attributes were blocked")
                page.close()
            context.close()
        browser.close()
    assert not problems, "\n".join(problems)
