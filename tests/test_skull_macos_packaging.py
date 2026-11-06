"""Structural checks for native macOS sources, runnable on Linux without SwiftUI."""
from pathlib import Path
import plistlib
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAC = ROOT / "macos"
SOURCES = MAC / "SkullOS" / "Sources" / "SkullOS"


class SkullMacOSPackagingTests(unittest.TestCase):
    def test_info_plist_only_allows_local_network(self):
        with (MAC / "SkullOS" / "Info.plist").open("rb") as file:
            info = plistlib.load(file)
        self.assertEqual(info["CFBundleIdentifier"], "org.sonoxo.skullos")
        self.assertEqual(info["CFBundleExecutable"], "SkullOS")
        self.assertEqual(info["LSMinimumSystemVersion"], "13.0")
        ats = info["NSAppTransportSecurity"]
        self.assertTrue(ats["NSAllowsLocalNetworking"])
        self.assertNotIn("NSAllowsArbitraryLoads", ats)

    def test_builder_has_safe_venv_and_local_bundle(self):
        script = (MAC / "build-app.sh").read_text()
        self.assertIn('.venv/bin/python', script)
        self.assertIn('swift build --package-path', script)
        self.assertIn('SkullConfig.json', script)
        self.assertIn('codesign --force --sign -', script)
        self.assertIn('SKULL OS.app', script)
        subprocess.run(["bash", "-n", str(MAC / "build-app.sh")], check=True)

    def test_swift_app_requires_local_service_and_blocks_external_pages(self):
        service = (SOURCES / "SkullSystem.swift").read_text()
        webview = (SOURCES / "SkullWebView.swift").read_text()
        app = (SOURCES / "SkullApp.swift").read_text()
        self.assertIn('URL(string: "http://127.0.0.1:', service)
        self.assertIn('status.project == "SKULL-LLM" && status.local_only', service)
        self.assertIn('proc.arguments = ["-m", "skull_llm", "serve"', service)
        self.assertIn('url?.host == "127.0.0.1"', webview)
        self.assertIn('url?.port == SkullSystem.shared.serverURL?.port', webview)
        self.assertIn('.nonPersistent()', webview)
        self.assertIn('decisionHandler(allowed ? .allow : .cancel)', webview)
        self.assertIn('.keyboardShortcut("k", modifiers: .command)', app)

    def test_native_ui_has_actions(self):
        source = (SOURCES / "SkullDesktopView.swift").read_text()
        service = (SOURCES / "SkullSystem.swift").read_text()
        for action in ("selectMode", "focusPrompt", "exportImage", "refreshStatus", "copyTerminalCommand"):
            self.assertIn(action, source)
            self.assertIn(f"func {action}(", service)
        self.assertIn("CL1 DEVICE", source)
        self.assertIn('"NOT CONNECTED"', source)


if __name__ == "__main__":
    unittest.main()
