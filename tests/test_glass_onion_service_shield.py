"""Glass Onion music & bank policy tests: no accounts, network or paid APIs."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kraken_shield import KrakenShield
from kraken_shield.service_policy import (
    MUSIC_DESTINATIONS,
    evaluate_service_access,
    service_catalog,
)


class ServicePolicyTests(unittest.TestCase):
    def test_known_public_music_destinations_only(self):
        samples = {
            "soundcloud": "https://soundcloud.com/search?q=lofi",
            "youtube": "https://www.youtube.com/results?search_query=music",
            "bandcamp": "https://bandcamp.com/search?q=ambient",
            "audius": "https://audius.co/search/",
            "internet-archive": "https://archive.org/metadata/sample",
            "jamendo": "https://www.jamendo.com/search?q=jazz",
            "spotify": "https://open.spotify.com/",
            "apple-music": "https://music.apple.com/",
            "distrokid": "https://distrokid.com/",
            "suno": "https://suno.com/",
        }
        for service, url in samples.items():
            with self.subTest(service=service):
                d = evaluate_service_access("music", service, "open_public_link", url=url)
                self.assertEqual(d.decision, "ALLOW")
                self.assertFalse(d.executed)
                self.assertFalse(d.connected)
        self.assertGreaterEqual(len(MUSIC_DESTINATIONS), 10)

    def test_lookalike_hosts_are_blocked(self):
        for url in (
            "https://soundcloud.com.evil.example/track",
            "https://notyoutube.com/watch?v=abc",
            "http://soundcloud.com/track",
            "file:///etc/passwd",
            "https://soundcloud.com:444/track",
            "https://user:secret@soundcloud.com/track",
            "https://127.0.0.1/music",
            "https://soundcloud.com./track",
            "https://soundcloud.com\\@evil.example/",
        ):
            with self.subTest(url=url):
                d = evaluate_service_access("music", "soundcloud", "open_public_link", url=url)
                self.assertEqual(d.decision, "BLOCK")

    def test_query_secrets_never_permitted(self):
        for param in ("access_token", "api_key", "code", "password", "account_number"):
            url = f"https://www.youtube.com/watch?v=abc&{param}=sensitive-data"
            self.assertEqual(
                evaluate_service_access("music", "youtube", "open_public_link", url=url).decision,
                "BLOCK",
            )

    def test_unregistered_and_mutating_music_actions_denied(self):
        self.assertEqual(
            evaluate_service_access("music", "unknown-service", "open_public_link", url="https://example.com/").reason_code,
            "unregistered_music_service",
        )
        for operation in ("upload_track", "publish", "payout", "delete_catalog", "create_checkout", "modify_account"):
            with self.subTest(operation=operation):
                d = evaluate_service_access("music", "distrokid", operation, url="https://distrokid.com/")
                self.assertEqual(d.decision, "BLOCK")

    def test_bank_actions_all_blocked_without_verified_adapter(self):
        for operation in ("read_balance", "read_transactions", "transfer", "withdraw", "change_payee",
                          "create_payment", "get_account_number", "oauth", "export_records"):
            with self.subTest(operation=operation):
                d = evaluate_service_access("bank", "any-financial-institution", operation)
                self.assertEqual(d.decision, "BLOCK")
                self.assertEqual(d.reason_code, "bank_connector_not_authorized")
        d = evaluate_service_access("bank", "bank", "status")
        self.assertEqual(d.decision, "ALLOW")
        self.assertFalse(d.connected)

    def test_public_catalog_never_claims_account_protection(self):
        c = service_catalog()
        self.assertFalse(c["external_services_controlled"])
        self.assertFalse(c["bank_transactions_allowed"])
        self.assertFalse(c["credentials_stored"])
        self.assertEqual(c["banking"], "NO_CONNECTED_BANK_ADAPTER")


class AuditedGlassOnionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        env = mock.patch.dict(os.environ, {
            "GPT_DOUG_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
            "OLLAMA_MODEL": "qwen2.5-coder:3b",
            "GPT_DOUG_AI_BLOCK_ALL": "0",
            "GPT_DOUG_AI_STOP_DIR": str(self.root / "stop"),
            "GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY": "0",
        })
        env.start()
        self.addCleanup(env.stop)
        self.shield = KrakenShield(state_dir=self.root / "audit")

    def test_approved_music_link_audited_without_url(self):
        url = "https://www.youtube.com/watch?v=mRMj0"
        decision = self.shield.check_service("music", "youtube", "open_public_link", url=url)
        self.assertEqual(decision["decision"], "ALLOW")
        self.assertEqual(decision["scope"], "policy_only")
        self.assertFalse(decision["executed"])
        audit = self.shield.audit_path.read_text()
        self.assertNotIn("youtube", audit)
        self.assertNotIn("mRMj0", audit)
        self.assertNotIn(url, json.dumps(decision))
        self.assertTrue(self.shield.verify_audit()["valid"])

    def test_banking_denied_and_does_not_store_sensitive_details(self):
        secret = "account_123456789012"
        decision = self.shield.check_service("bank", secret, "transfer", url="https://bad.example?token=secret")
        self.assertEqual(decision["decision"], "BLOCK")
        self.assertNotIn(secret, self.shield.audit_path.read_text())
        self.assertNotIn("secret", self.shield.audit_path.read_text())

    def test_global_emergency_stop_overrides_allowed_music(self):
        with mock.patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            result = self.shield.check_service("music", "soundcloud", "open_public_link", url="https://soundcloud.com/search?q=jazz")
            self.assertEqual(result["decision"], "BLOCK")
            self.assertEqual(result["reason_code"], "operator_stop")

    def test_untrusted_local_provider_blocks_service_policy(self):
        with mock.patch.dict(os.environ, {"GPT_DOUG_PROVIDER": "openai"}):
            self.assertEqual(
                self.shield.check_service("music", "soundcloud", "open_public_link", url="https://soundcloud.com/")["decision"],
                "BLOCK",
            )

    def test_audit_corruption_fails_closed(self):
        self.shield.check_service("bank", "bank", "transfer")
        path = self.shield.audit_path
        path.write_text(path.read_text().replace('"BLOCK"', '"ALLOW"'))
        self.assertFalse(self.shield.verify_audit()["valid"])
        from kraken_shield import KrakenShieldError
        with self.assertRaises(KrakenShieldError):
            self.shield.check_service("bank", "bank", "status")


if __name__ == "__main__":
    unittest.main()
