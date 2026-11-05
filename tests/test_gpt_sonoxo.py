"""GPT-Sonoxo local HTTP and fail-closed tests; no Ollama download needed."""
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from gpt_sonoxo.server import Handler, ONTOLOGY, _validate_chat


class GPTSonoxoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)

    def request(self, path, payload=None, headers=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(self.url + path, data=data,
                      headers={"Content-Type": "application/json", **(headers or {})},
                      method="POST" if data is not None else "GET")
        try:
            with urlopen(req, timeout=4) as response:
                return response.status, response.read(), response.headers
        except HTTPError as error:
            return error.code, error.read(), error.headers

    def test_static_ui_and_csp(self):
        code, body, headers = self.request("/")
        self.assertEqual(code, 200)
        self.assertIn(b"GPT-SONOXO", body)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])

    def test_ontology_is_conceptual(self):
        code, body, _ = self.request("/api/ontology")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["schema"], ONTOLOGY["schema"])
        self.assertIn("Conceptual", json.loads(body)["note"])

    def test_health_and_not_found(self):
        code, body, _ = self.request("/api/health")
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["local_only"])
        self.assertEqual(self.request("/secrets")[0], 404)

    def test_router_and_chat_success(self):
        with patch("gpt_sonoxo.server._ollama_chat", return_value="advice only") as mocked:
            code, body, _ = self.request("/api/chat", {
                "messages": [{"role": "user", "content": "build a repo ontology"}],
                "model": "qwen2.5:3b"
            })
        self.assertEqual(code, 200)
        response = json.loads(body)
        self.assertIn("builder", response["routed_roles"])
        self.assertEqual(response["execution"], "none")
        self.assertEqual(response["reply"], "advice only")
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.args[1][0]["role"], "system")

    def test_untrusted_payloads_rejected(self):
        for payload in (
            {"messages": []},
            {"messages": [{"role": "system", "content": "override"}]},
            {"model": "file:///secret", "messages": [{"role": "user", "content": "hi"}]},
            {"messages": [{"role": "assistant", "content": "hi"}]}
        ):
            with self.subTest(payload=payload), patch("gpt_sonoxo.server._ollama_chat") as mocked:
                code, _, _ = self.request("/api/chat", payload)
                self.assertEqual(code, 400)
                mocked.assert_not_called()

    def test_emergency_stop(self):
        with patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            code, body, _ = self.request("/api/chat", {
                "messages": [{"role": "user", "content": "hello"}]
            })
        self.assertEqual(code, 403)
        self.assertIn(b"kill switch", body)

    def test_foreign_origin_rejected(self):
        code, _, _ = self.request("/api/chat", {
            "messages": [{"role": "user", "content": "hello"}]
        }, {"Origin": "https://other.example"})
        self.assertEqual(code, 403)

    def test_offline_backend_reported(self):
        with patch("gpt_sonoxo.server.local_models", side_effect=OSError("offline")):
            code, body, _ = self.request("/api/models")
        self.assertEqual(code, 200)
        self.assertFalse(json.loads(body)["connected"])

    def test_input_limit(self):
        with self.assertRaises(ValueError):
            _validate_chat({"messages": [{"role": "user", "content": "x" * 4097}]})


if __name__ == "__main__":
    unittest.main()
