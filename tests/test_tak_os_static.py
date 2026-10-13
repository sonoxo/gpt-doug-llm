"""Dependency-free contracts for the public, independent TAK-OS simulator."""
from pathlib import Path
from html.parser import HTMLParser
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "docs" / "tak-os"

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if a.get("href"):
            self.links.add(a["href"])

class FreeTAKOSContract(unittest.TestCase):
    def test_public_assets_exist(self):
        for path in ("index.html", "compose.yaml", "start.sh", "vm/launch.sh",
                     "vm/README.md", "sw.js", "manifest.webmanifest", "icon.svg", "README.md"):
            with self.subTest(path=path):
                self.assertTrue((APP / path).is_file())

    def test_working_interface_not_placeholder(self):
        html = (APP / "index.html").read_text()
        parser = Tags()
        parser.feed(html)
        for identifier in ("page-map", "page-vm", "page-feeds", "page-events",
                           "page-ontology", "page-settings", "map", "markers",
                           "pause", "speed", "incident", "timeline", "csv",
                           "validate", "vm-command", "copy-vm", "export"):
            with self.subTest(identifier=identifier):
                self.assertIn(identifier, parser.ids)
        for feature in ("function renderMap", "function renderEventList",
                        "function snapshot", "function vmtext", "DOMParser",
                        "SIMULATED", "text/csv"):
            self.assertIn(feature, html)
        self.assertIn("NOT TAK PRODUCT CENTER SOFTWARE", html)

    def test_zero_required_paid_dependencies(self):
        html = (APP / "index.html").read_text()
        self.assertNotRegex(html, r"<script[^>]+src=['\"]https?://")
        self.assertNotRegex(html, r"<link[^>]+stylesheet[^>]+https?://")
        for term in ("api.openai.com", "sk-proj-", "Authorization: Bearer", "new WebSocket("):
            self.assertNotIn(term, html)

    def test_registry_and_home_page_links(self):
        data = json.loads((ROOT / "docs" / "resources.json").read_text())
        entry = next(x for x in data["items"] if x["id"] == "gpt-doug-tak-os")
        self.assertEqual(entry["access"], "public")
        self.assertTrue(entry["free"])
        self.assertEqual(entry["url"], "./tak-os/")
        self.assertIn('href="./tak-os/"', (ROOT / "docs" / "index.html").read_text())

    def test_vm_boundaries(self):
        compose = (APP / "compose.yaml").read_text()
        self.assertIn("127.0.0.1:", compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("no-new-privileges:true", compose)
        vm = (APP / "vm/launch.sh").read_text()
        self.assertIn("hostfwd=tcp:127.0.0.1:", vm)
        self.assertIn("-:22", vm)
        self.assertNotIn("8080-:8080", vm)
        self.assertIn("ssh -p 2222", (APP / "vm/README.md").read_text())

    def test_pwa_offline_scope(self):
        manifest = json.loads((APP / "manifest.webmanifest").read_text())
        self.assertEqual(manifest["scope"], "./")
        sw = (APP / "sw.js").read_text()
        self.assertIn("url.origin !== self.location.origin", sw)
        self.assertIn("tak-os", sw)
        self.assertIn("serviceWorker.register('./sw.js')", (APP / "index.html").read_text())

if __name__ == "__main__":
    unittest.main()
