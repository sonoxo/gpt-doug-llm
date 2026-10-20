"""Desktop/mobile visual and interaction verification, requires Playwright+Chromium."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://watchtower.example.test/"
try:
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox", "--disable-dev-shm-usage"])
        for kind, viewport in [("desktop", {"width": 1480, "height": 980}), ("mobile", {"width": 390, "height": 844})]:
            page = browser.new_page(viewport=viewport, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda err: errors.append(str(err)))
            html = (ROOT / 'docs' / 'watchtower' / 'index.html').read_text()
            html = html.replace('<link rel="stylesheet" href="./style.css">', '')
            html = html.replace('<script defer src="./app.js"></script>', '')
            page.set_content(html, wait_until='load')
            page.add_style_tag(content=(ROOT / 'docs' / 'watchtower' / 'style.css').read_text())
            page.add_script_tag(content=(ROOT / 'docs' / 'watchtower' / 'app.js').read_text())
            page.wait_for_timeout(400)
            assert "WATCHTOWER" in page.title()
            assert page.locator("#metricModels").inner_text() == "6"
            assert page.locator("#eventFeed .feed-item").count() == 8
            assert "SYNTHETIC" in page.locator("#modePill").inner_text()
            page.screenshot(path=str(ROOT / f"watchtower-{kind}.png"), full_page=True)
            page.locator("#runScenario").click()
            assert page.locator("#eventFeed .feed-item").count() == 11
            assert page.locator("#metricEvents").inner_text() == "11"
            page.locator("#stopBtn").click()
            assert "STOP LATCHED" in page.locator("#controlLabel").inner_text()
            page.locator("#rearmBtn").click()
            assert "GUARD ACTIVE" in page.locator("#controlLabel").inner_text()
            page.locator('[data-panel="fleet"]').click()
            assert page.locator("#modelGrid .model-card").count() == 6
            page.locator('[data-panel="approvals"]').click()
            assert page.locator("#approvalQueue .approval-item").count() >= 2
            page.locator('[data-panel="audit"]').click()
            assert "SIMULATED" in page.locator("#auditValidity").inner_text()
            page.locator("#verifyAudit").click()
            assert "Public demo" in page.locator("#toast").inner_text()
            dimensions = page.evaluate("({width:document.documentElement.scrollWidth, viewport:innerWidth})")
            assert dimensions["width"] <= dimensions["viewport"] + 1, dimensions
            assert not errors, errors
            results[kind] = {"page_errors": errors, "horizontal_overflow": dimensions["width"] > dimensions["viewport"], "tested": ["initial", "drill", "stop", "rearm", "model_fleet", "approvals", "audit"]}
            page.close()
        browser.close()
    (ROOT / "browser-results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
finally:
    pass
