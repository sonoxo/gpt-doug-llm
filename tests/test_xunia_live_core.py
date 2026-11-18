"""XUNIA CL1 Living Core HQ: offline portal, accessibility, and containment contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

PORTALS = {
    "cosmos": "./cosmos/",
    "xenology": "./cosmos/xenology/",
    "planets": "./cosmos/planets/",
    "biology": "./biological-data-center/",
    "glass-onion": "./darkweb/",
    "play": "./play/",
    "fleet": "./ecosystem-observatory/",
    "cinema": "./cinema-studio/",
}


class LivingCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (DOCS / "index.html").read_text(encoding="utf-8")
        cls.js = (DOCS / "cl1-live.js").read_text(encoding="utf-8")
        cls.css = (DOCS / "cl1-live.css").read_text(encoding="utf-8")

    def test_homepage_integrates_animated_living_core_without_removing_museum(self):
        html = self.html
        self.assertIn('id="cl1-live"', html)
        self.assertIn('href="./cl1-live.css"', html)
        self.assertIn('src="./cl1-live.js" defer', html)
        self.assertIn('id="cl1-live-canvas"', html)
        self.assertLess(html.index('id="cl1-live"'), html.index('id="xunia-world"'))
        self.assertIn('id="museumSearch"', html)
        self.assertIn('href="./play/"', html)

    def test_all_eight_real_portal_controls_and_on_site_urls(self):
        self.assertEqual(self.js.count('description:"'), 8)
        for portal, url in PORTALS.items():
            with self.subTest(portal=portal):
                self.assertIn('data-cl1-portal="' + portal + '"', self.html)
                self.assertIn('url:"' + url + '"', self.js)
                self.assertTrue((DOCS / url.removeprefix("./") / "index.html").exists())
        self.assertIn('id="cl1-live-enter"', self.html)
        self.assertIn('id="cl1-live-index"', self.html)

    def test_accessibility_motion_audio_and_browser_only_boundaries(self):
        html, js, css = self.html, self.js, self.css
        for identifier in [
            "cl1-live-energy", "cl1-live-energy-value", "cl1-live-pause",
            "cl1-live-audio", "cl1-live-zoom-in", "cl1-live-zoom-out",
            "cl1-live-recenter", "cl1-live-fullscreen", "cl1-live-capture",
            "cl1-live-status", "cl1-live-message",
        ]:
            self.assertIn('id="' + identifier + '"', html)
        for mode in ["ontology", "shaggoth", "signal"]:
            self.assertIn('data-cl1-mode="' + mode + '"', html)
        self.assertIn('aria-label="Interactive CL1 spatial organism', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("prefers-reduced-motion: reduce", js)
        self.assertIn("prefers-reduced-motion:reduce", css)
        self.assertIn("canvas.toBlob(", js)
        self.assertIn("function soundToggle(", js)
        self.assertIn("function drawScene(", js)
        self.assertIn("canvas.dataset.renderedNodes", js)
        self.assertIn("No actual bio-sensors", js)
        for disallowed in (
            "fetch(", "WebSocket(", "XMLHttpRequest(", "eval(",
            "innerHTML", "navigator.bluetooth", "navigator.serial",
            "navigator.usb", "api.openai.com", "vercel",
        ):
            self.assertNotIn(disallowed, js)


if __name__ == "__main__":
    unittest.main()
