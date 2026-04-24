#!/usr/bin/env python3
"""Smoke-test the Pyodide web app end-to-end with Playwright.

Run after ``just build-web`` with a local HTTP server on port 8000::

    cd web && python -m http.server 8000 &
    python tests/web_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SAMPLE_TEXT = (
    Path(__file__).resolve().parent / "test_data" / "matkahistoria.txt"
).read_text()

BASE_URL = "http://localhost:8000"

# Pyodide can take a while to load packages
PYODIDE_TIMEOUT_MS = 120_000
EXPORT_TIMEOUT_MS = 60_000


def main() -> int:
    """Run the end-to-end smoke test and return an exit code."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()

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

            download_links = page.locator("#results a[download]").count()
            assert download_links >= 1, (
                f"Expected at least 1 download link, got {download_links}"
            )

            print(f"OK – {download_links} download link(s) found")

        finally:
            # 6. Capture log panel for artifact upload
            try:
                log_text = page.locator("#log").inner_text()
            except Exception:
                log_text = "(could not capture log)"
            log_path = Path("web-smoke-log.txt")
            log_path.write_text(log_text)
            print(f"Log saved to {log_path}")

            browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
