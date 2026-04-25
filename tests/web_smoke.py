#!/usr/bin/env python3
"""Smoke-test the Pyodide web app end-to-end with Playwright.

Run after ``just build-web`` with a local HTTP server on port 8000::

    cd web && python -m http.server 8000 &
    python tests/web_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

SAMPLE_TEXT = (
    Path(__file__).resolve().parent / "test_data" / "matkahistoria.txt"
).read_text()

# Kept in sync with tests/test_validation_data.py::EXPECTED_MATKAHISTORIA_RIDES —
# a weaker ">= 1" assertion would silently tolerate a fixture that's missing
# stations and drops rides.
EXPECTED_DOWNLOAD_LINKS = 7

BASE_URL = "http://localhost:8000"

# Pyodide can take a while to load packages
PYODIDE_TIMEOUT_MS = 120_000
EXPORT_TIMEOUT_MS = 60_000


def _run_export_flow(page: Page) -> int:
    """Drive the export UI end-to-end and return the download-link count."""
    # 1. Open the app
    page.goto(BASE_URL)

    # 2. Wait for Pyodide to finish loading (button becomes enabled)
    export_btn = page.locator("#exportBtn")
    export_btn.wait_for(state="attached")

    # The button text changes from "Loading Pyodide…" to "Export rides"
    page.locator("#exportBtnText").filter(has_text="Export rides").wait_for(
        timeout=PYODIDE_TIMEOUT_MS,
    )
    assert not export_btn.is_disabled(), (
        "Export button should be enabled after Pyodide loads"
    )

    # 3. Paste sample ride text into the textarea
    page.locator("#textInput").fill(SAMPLE_TEXT)

    # 4. Click Export
    export_btn.click()

    # 5. Wait for at least one download link in #results
    page.locator("#results a[download]").first.wait_for(
        state="visible",
        timeout=EXPORT_TIMEOUT_MS,
    )

    links = page.locator("#results a[download]")
    links.nth(EXPECTED_DOWNLOAD_LINKS - 1).wait_for(
        state="visible", timeout=EXPORT_TIMEOUT_MS
    )
    download_links = links.count()
    assert download_links == EXPECTED_DOWNLOAD_LINKS, (
        f"Expected {EXPECTED_DOWNLOAD_LINKS} download links (one per ride in "
        f"matkahistoria.txt), got {download_links} — a ride was silently "
        "skipped, most likely because stations_fixture.json is missing a "
        "station referenced by the sample ride history."
    )
    return download_links


def _save_log(page: Page) -> None:
    """Capture the in-page log panel to a file for CI artifact upload."""
    try:
        log_text = page.locator("#log").inner_text()
    except Exception:
        log_text = "(could not capture log)"
    log_path = Path("web-smoke-log.txt")
    log_path.write_text(log_text, encoding="utf-8")
    print(f"Log saved to {log_path}")


def main() -> int:
    """Run the end-to-end smoke test and return an exit code."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = None
        try:
            # The app auto-detects the UI language from the browser locale;
            # pin it so the "Export rides" button text match is deterministic.
            page = browser.new_page(locale="en-US")
            download_links = _run_export_flow(page)
            print(f"OK – {download_links} download link(s) found")
        finally:
            if page is not None:
                _save_log(page)
            browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
