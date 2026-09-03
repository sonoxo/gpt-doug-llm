import json
import os
import unittest
from unittest.mock import patch

from palantir_foundry import (
    FoundryClient,
    FoundryConfigurationError,
    FoundryWriteDisabled,
    _PinnedRedirectHandler,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class PalantirFoundryTests(unittest.TestCase):
    def test_disabled_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(FoundryClient.from_environment())

    def test_requires_https(self):
        with self.assertRaises(FoundryConfigurationError):
            FoundryClient(base_url="http://foundry.example", static_token="token")

    def test_requires_credentials(self):
        with self.assertRaises(FoundryConfigurationError):
            FoundryClient(base_url="https://foundry.example")

    def test_rejects_host_mismatch(self):
        with self.assertRaises(FoundryConfigurationError):
            FoundryClient(
                base_url="https://foundry.example",
                static_token="token",
                allowed_host="other.example",
            )

    def test_redirect_handler_rejects_cross_host(self):
        handler = _PinnedRedirectHandler("foundry.example")
        with self.assertRaises(FoundryConfigurationError):
            handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example/steal")

    def test_redirect_handler_rejects_http(self):
        handler = _PinnedRedirectHandler("foundry.example")
        with self.assertRaises(FoundryConfigurationError):
            handler.redirect_request(None, None, 302, "Found", {}, "http://foundry.example/insecure")

    @patch.object(FoundryClient, "_open")
    def test_static_token_lists_objects(self, open_response):
        open_response.return_value = FakeResponse({"data": [{"id": "1"}]})
        client = FoundryClient(base_url="https://foundry.example", static_token="secret")
        payload = client.list_objects("main", "Aircraft", page_size=10)
        self.assertEqual(payload["data"][0]["id"], "1")
        request = open_response.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertIn("/api/v2/ontologies/main/objects/Aircraft", request.full_url)

    @patch.object(FoundryClient, "_open")
    def test_oauth_client_credentials_then_api_call(self, open_response):
        open_response.side_effect = [
            FakeResponse({"access_token": "oauth-token", "expires_in": 3600}),
            FakeResponse({"data": []}),
        ]
        client = FoundryClient(
            base_url="https://foundry.example",
            client_id="client-id",
            client_secret="client-secret",
        )
        client.list_ontologies()
        token_request = open_response.call_args_list[0].args[0]
        token_body = token_request.data.decode("utf-8")
        self.assertIn("grant_type=client_credentials", token_body)
        self.assertIn("client_id=client-id", token_body)
        api_request = open_response.call_args_list[1].args[0]
        self.assertEqual(api_request.get_header("Authorization"), "Bearer oauth-token")

    def test_actions_are_blocked_by_default(self):
        client = FoundryClient(base_url="https://foundry.example", static_token="secret")
        with self.assertRaises(FoundryWriteDisabled):
            client.apply_action("main", "UpdateThing", {"id": "1"})

    @patch.object(FoundryClient, "_open")
    def test_action_requires_explicit_write_enable(self, open_response):
        open_response.return_value = FakeResponse({"validation": {"result": "VALID"}})
        client = FoundryClient(
            base_url="https://foundry.example",
            static_token="secret",
            writes_enabled=True,
        )
        payload = client.apply_action("main", "UpdateThing", {"id": "1"})
        self.assertIn("validation", payload)
        request = open_response.call_args.args[0]
        self.assertIn("/actions/UpdateThing/apply", request.full_url)
        self.assertEqual(request.get_method(), "POST")

    def test_status_exposes_transport_policy_without_secrets(self):
        client = FoundryClient(base_url="https://foundry.example", static_token="secret")
        status = client.status()
        self.assertEqual(status["transport"], "https-only")
        self.assertEqual(status["redirect_policy"], "same-host-https-only")
        self.assertNotIn("secret", json.dumps(status))


if __name__ == "__main__":
    unittest.main()
