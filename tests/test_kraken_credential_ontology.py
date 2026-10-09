"""Tests for metadata-only operator-controlled Kraken credential ontology."""
import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from kraken_jutsu.credential_ontology import (
    CredentialOntology,
    KrakenServer,
    ONTOLOGY,
    initialize,
)


def good_entry():
    return {
        "provider": "aws", "alias": "amp-writer", "kind": "iam-role",
        "owner_role": "operator", "rotation_days": 90,
        "expires_on": "2027-03-01",
    }


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "state"
        self.output = initialize(self.folder)
        self.store = CredentialOntology(self.folder)

    def test_token_and_database_only_owner_access(self):
        self.assertFalse("token" in self.output and self.output["token"])
        for path in (self.folder / "operator.token", self.folder / "ontology.sqlite3"):
            self.assertTrue(path.is_file())
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.folder.stat().st_mode), 0o700)

    def test_init_does_not_reset_token(self):
        before = (self.folder / "operator.token").read_text()
        initialize(self.folder)
        self.assertEqual((self.folder / "operator.token").read_text(), before)

    def test_register_metadata_not_raw_secrets(self):
        record = self.store.register(good_entry())
        self.assertEqual(record["local_status"], "REGISTERED_PROVIDER_UNVERIFIED")
        self.assertEqual(len(self.store.credentials()), 1)
        self.assertNotIn("secret", json.dumps(self.store.credentials()).lower())

    def test_unknown_fields_fail_closed(self):
        for key in ("access_key", "api_key", "secret", "credential", "token", "private_key", "authorization"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.store.register({**good_entry(), key: "sensitive"})
        self.assertEqual(self.store.credentials(), [])

    def test_credential_like_alias_rejected(self):
        with self.assertRaises(ValueError):
            self.store.register({**good_entry(), "alias": "ghp_faketokenvalue"})

    def test_unhashable_kind_and_role_rejected(self):
        for field in ("kind", "owner_role"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.store.register({**good_entry(), field: ["not", "safe"]})

    def test_unhashable_rotation_reason_rejected(self):
        entry = self.store.register(good_entry())
        with self.assertRaises(ValueError):
            self.store.request_rotation({"credential_id": entry["credential_id"], "reason": ["not", "safe"]})

    def test_validated_date(self):
        with self.assertRaises(ValueError):
            self.store.register({**good_entry(), "expires_on": "2026-02-30"})

    def test_numeric_bool_disallowed(self):
        with self.assertRaises(ValueError):
            self.store.register({**good_entry(), "rotation_days": True})

    def test_duplicate_registration_fails(self):
        self.store.register(good_entry())
        with self.assertRaises(ValueError):
            self.store.register(good_entry())

    def test_requests_are_idempotent_and_do_not_generate_keys(self):
        entry = self.store.register(good_entry())
        payload = {"credential_id": entry["credential_id"], "reason": "scheduled"}
        one = self.store.request_rotation(payload)
        two = self.store.request_rotation(payload)
        self.assertEqual(one, two)
        self.assertEqual(one["status"], "PENDING_PROVIDER_APPROVAL")
        self.assertEqual(len(self.store.requests()), 1)
        self.assertFalse(ONTOLOGY["invariants"]["issues_provider_credentials"])

    def test_rotation_rejects_key_payloads(self):
        entry = self.store.register(good_entry())
        with self.assertRaises(ValueError):
            self.store.request_rotation({"credential_id": entry["credential_id"], "reason": "scheduled", "key": "abc"})

    def test_revocation_is_irreversible_in_api_and_cancels_pending(self):
        entry = self.store.register(good_entry())
        req = self.store.request_rotation({"credential_id": entry["credential_id"], "reason": "scheduled"})
        result = self.store.record_revocation(entry["credential_id"])
        self.assertFalse(result["provider_revocation_performed"])
        self.assertEqual(self.store.requests()[0]["status"], "CANCELLED_LOCAL_REVOCATION")
        with self.assertRaises(ValueError):
            self.store.request_rotation({"credential_id": entry["credential_id"], "reason": "scheduled"})
        self.assertEqual(len(self.store.audit()), 3)
        self.assertEqual(req["status"], "PENDING_PROVIDER_APPROVAL")

    def test_environment_keys_not_discovered(self):
        os.environ["KRKN_FAKE_AWS_SECRET_KEY_FOR_TEST"] = "NOT_FOR_DISCOVERY"
        try:
            self.assertEqual(self.store.credentials(), [])
            self.assertNotIn("NOT_FOR_DISCOVERY", json.dumps(self.store.audit()))
        finally:
            del os.environ["KRKN_FAKE_AWS_SECRET_KEY_FOR_TEST"]

    def test_local_loopback_required(self):
        with self.assertRaises(ValueError):
            KrakenServer(self.folder, port=0, host="0.0.0.0")

    def test_missing_operator_token_fails_closed(self):
        (self.folder / "operator.token").unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            CredentialOntology(self.folder)

    def test_symlink_token_rejected(self):
        token = self.folder / "operator.token"
        token.unlink()
        token.symlink_to(self.folder / "ontology.sqlite3")
        with self.assertRaises(ValueError):
            CredentialOntology(self.folder)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "state"
        self.output = initialize(self.folder)
        self.store = CredentialOntology(self.folder)
        self.server = KrakenServer(self.folder, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.token = (self.folder / "operator.token").read_text().strip()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def req(self, method, path, data=None, auth=True):
        payload = None if data is None else json.dumps(data).encode()
        headers = {"Authorization": "Bearer " + self.token} if auth else {}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base + path, data=payload, headers=headers, method=method)
        with urlopen(request, timeout=3) as result:
            return result.status, json.loads(result.read())

    def test_api_requires_token_on_every_route(self):
        for path in ("/v1/ontology", "/v1/credentials", "/v1/audit", "/v1/rotation-requests"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as failure:
                self.req("GET", path, auth=False)
            self.assertEqual(failure.exception.code, 401)

    def test_api_register_and_request_rotation(self):
        code, created = self.req("POST", "/v1/credentials", good_entry())
        self.assertEqual(code, 201)
        cid = created["data"]["credential_id"]
        code, rotation = self.req("POST", "/v1/rotation-requests", {"credential_id": cid, "reason": "manual-review"})
        self.assertEqual(code, 200)
        self.assertEqual(rotation["data"]["status"], "PENDING_PROVIDER_APPROVAL")
        code, rows = self.req("GET", "/v1/rotation-requests")
        self.assertEqual(len(rows["data"]), 1)
        self.assertEqual(rows["data"][0]["credential_id"], cid)

    def test_api_does_not_support_credential_issuance_or_export(self):
        for path in ("/v1/new-key", "/v1/issue", "/v1/export-keys", "/v1/revive", "/v1/discover"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as failure:
                self.req("POST", path, {})
            self.assertEqual(failure.exception.code, 404)

    def test_api_rejects_raw_token_field(self):
        with self.assertRaises(HTTPError) as failure:
            self.req("POST", "/v1/credentials", {**good_entry(), "access_token": "do-not-store"})
        self.assertEqual(failure.exception.code, 400)
        self.assertNotIn("do-not-store", failure.exception.read().decode())

    def test_api_revocation(self):
        _, entry = self.req("POST", "/v1/credentials", good_entry())
        _, payload = self.req("POST", "/v1/record-revocation", {"credential_id": entry["data"]["credential_id"]})
        self.assertFalse(payload["data"]["provider_revocation_performed"])
        _, creds = self.req("GET", "/v1/credentials")
        self.assertEqual(creds["data"][0]["local_status"], "REVOCATION_RECORDED_PROVIDER_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
