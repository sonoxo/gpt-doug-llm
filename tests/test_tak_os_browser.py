"""Optional browser E2E tests; runs with free Playwright+Chromium when installed.

No network: HTML/CSS/JS source is inlined into an about:blank browser frame,
which avoids external tiles and protects against accidental live CoT traffic.
Run: python3 -m unittest tests/test_tak_os_browser.py -v
"""
from pathlib import Path
import json
import unittest
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1] / 'docs' / 'tak-os'
HTML = (ROOT / 'index.html').read_text().replace(
    '<link rel="stylesheet" href="./styles.css">',
    '<style>' + (ROOT / 'styles.css').read_text() + '</style>'
).replace(
    '<script defer src="./app.js"></script>',
    '<script>' + (ROOT / 'app.js').read_text() + '</script>'
)

@unittest.skipUnless(sync_playwright, "Optional Playwright not installed")
class BrowserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path='/usr/bin/chromium', headless=True,
            args=['--no-sandbox', '--disable-background-networking'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1365, 'height': 900}, accept_downloads=True)
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.set_content(HTML, wait_until='domcontentloaded')
        self.page.locator('#toggle-tiles').uncheck()

    def tearDown(self):
        self.assertEqual(self.errors, [], 'Uncaught browser script error')
        self.page.close()

    def test_initial_map_pause_resume_and_speed(self):
        self.assertEqual(self.page.locator('#stat-units').inner_text(), '12')
        self.assertGreaterEqual(self.page.locator('#map-markers .marker').count(), 6)
        self.page.locator('#sim-play').click()
        self.assertIn('PAUSED', self.page.locator('#sim-run-state').inner_text())
        self.page.locator('#sim-play').click()
        self.assertIn('RUNNING', self.page.locator('#sim-run-state').inner_text())
        self.page.locator('#speed-select').select_option('8')
        self.assertEqual(self.page.locator('#speed-select').input_value(), '8')
        self.page.locator('#unit-search').fill('CIV-RESCUE-01')
        self.assertEqual(self.page.locator('#map-markers .marker').count(), 1)

    def test_events_ack_and_exports(self):
        self.page.locator('[data-view="events"]').click()
        n = self.page.locator('#events-list .timeline-item').count()
        self.page.locator('#create-incident').click()
        self.assertEqual(self.page.locator('#events-list .timeline-item').count(), n + 1)
        self.page.locator('#event-unacked').check()
        self.assertGreaterEqual(self.page.locator('.timeline-ack:not([disabled])').count(), 1)
        self.page.locator('.timeline-ack:not([disabled])').first.click()
        with self.page.expect_download() as download:
            self.page.locator('#export-events').click()
        self.assertEqual(download.value.suggested_filename, 'tak-os-events.csv')
        self.page.locator('[data-view="map"]').click()
        with self.page.expect_download() as download:
            self.page.locator('#export-map').click()
        self.assertEqual(download.value.suggested_filename, 'tak-os-synthetic-scenario.json')

    def test_cot_security_and_ontology(self):
        self.page.locator('[data-view="feeds"]').click()
        self.page.locator('#cot-validate').click()
        self.assertIn('VALID', self.page.locator('#cot-output').inner_text())
        self.page.locator('#cot-input').fill('<!DOCTYPE event [<!ENTITY x SYSTEM "file:///etc/passwd">]><event/>')
        self.page.locator('#cot-validate').click()
        self.assertIn('Rejected', self.page.locator('#cot-output').inner_text())
        self.page.locator('#cot-input').fill('<event uid="a" type="b"><point lat="9999" lon="1"/></event>')
        self.page.locator('#cot-validate').click()
        self.assertNotIn('VALID', self.page.locator('#cot-output').inner_text())
        self.page.locator('[data-view="ontology"]').click()
        self.assertGreater(self.page.locator('.ontology-entry').count(), 4)

    def test_vm_and_controls_and_keyboard(self):
        self.page.locator('[data-view="system"]').click()
        self.assertIn('Virtual Machine Control', self.page.locator('#system-title').inner_text())
        self.page.locator('#vm-cpus').select_option('4')
        self.assertEqual(self.page.locator('#vm-cpus').input_value(), '4')
        self.page.locator('#quick-help').click()
        self.assertTrue(self.page.locator('#help-dialog').evaluate('(d) => d.open'))
        self.page.locator('#help-done').click()
        self.assertFalse(self.page.locator('#help-dialog').evaluate('(d) => d.open'))
        self.page.keyboard.press('1')
        self.assertIn('LIVE OPERATIONS', self.page.locator('#breadcrumb-view').inner_text())

    def test_mobile_navigation(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.locator('#mobile-menu').click()
        self.assertEqual(self.page.locator('#mobile-menu').get_attribute('aria-expanded'), 'true')
        self.page.locator('[data-view="feeds"]').click()
        self.assertIn('DATA FEEDS', self.page.locator('#breadcrumb-view').inner_text())
        self.assertEqual(self.page.locator('#mobile-menu').get_attribute('aria-expanded'), 'false')

if __name__ == '__main__':
    unittest.main()
