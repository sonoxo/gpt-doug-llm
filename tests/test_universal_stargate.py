"""HTTP contract, safety and inference adapter tests. All inference is mocked."""
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ai_killswitch import AIKillSwitchEngaged
from universal_stargate.server import Handler, GRAPH, POLICY, validate_chat, inference


class StargateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)

    def call(self, path, payload=None, headers=None, method=None, raw=None):
        body = json.dumps(payload).encode() if payload is not None else raw
        request = Request(self.origin + path, data=body, method=method or ("POST" if body is not None else "GET"),
                          headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urlopen(request, timeout=4) as response:
                return response.status, response.read(), response.headers
        except HTTPError as error:
            return error.code, error.read(), error.headers

    def test_home_and_tracking_query(self):
        for path in ("/", "/?utm_source=chatgpt.com"):
            code, body, headers = self.call(path)
            self.assertEqual(code, 200)
            self.assertIn(b"UNIVERSAL", body)
            self.assertIn("script-src 'self'", headers["Content-Security-Policy"])

    def test_static_js_css(self):
        self.assertEqual(self.call("/app.css")[0], 200)
        self.assertEqual(self.call("/app.js")[0], 200)
        self.assertEqual(self.call("/other")[0], 404)

    def test_policy_no_autonomous_execution(self):
        code, body, _ = self.call("/api/policy")
        result = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(result, POLICY)
        self.assertFalse(result["autonomous_swarm"])
        self.assertFalse(result["repository_writes"])

    def test_ontology_explicit_reference_nodes(self):
        code, body, _ = self.call("/api/ontology")
        result = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(result["schema"], GRAPH["schema"])
        self.assertIn("conceptual", {n["status"] for n in result["nodes"]})

    def test_operator_stop_reported(self):
        with patch("universal_stargate.server.stop_status", return_value={"stopped":True,"reason":"operator_stop_latched"}):
            code, body, _ = self.call("/api/status")
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["blocked"])

    def test_read_only_route(self):
        with patch("universal_stargate.server.roles_for",return_value=["ontology","critic"]):
            code, body, _ = self.call("/api/route", {"task":"build ontology"})
        self.assertEqual(code,200)
        self.assertFalse(json.loads(body)["executed"])
        self.assertEqual(json.loads(body)["roles"],["ontology","critic"])

    def test_reject_invalid_route(self):
        for payload in ({}, {"task": 12}, {"task": ""}, {"task": "x" * 3001}):
            self.assertEqual(self.call("/api/route",payload)[0],400)

    def test_models_failure_is_reported(self):
        with patch("universal_stargate.server.local_models", side_effect=OSError("offline")):
            code, body, _ = self.call("/api/models")
        self.assertEqual(code,200)
        self.assertFalse(json.loads(body)["connected"])

    def test_local_chat_success(self):
        with patch("universal_stargate.server.local_models",return_value=["qwen2.5:3b"]), \
             patch("universal_stargate.server.inference",return_value="bounded advice"), \
             patch("universal_stargate.server.roles_for", return_value=["builder"]), \
             patch("universal_stargate.server.require_ai_allowed"):
            code, body, _ = self.call("/api/chat", {"model":"qwen2.5:3b", "messages":[{"role":"user","content":"hello"}]})
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)["reply"],"bounded advice")
        self.assertFalse(json.loads(body)["executed"])

    def test_no_unknown_model_forwarded(self):
        with patch("universal_stargate.server.local_models",return_value=["qwen2.5:3b"]), \
             patch("universal_stargate.server.inference") as backend:
            code, body, _ = self.call("/api/chat", {"model":"uninstalled:7b", "messages":[{"role":"user","content":"hello"}]})
        self.assertEqual(code,400)
        backend.assert_not_called()

    def test_stop_blocks_chat_before_inference(self):
        with patch("universal_stargate.server.require_ai_allowed", side_effect=AIKillSwitchEngaged("stop")), \
             patch("universal_stargate.server.inference") as backend:
            code, body, _ = self.call("/api/chat", {"model":"qwen2.5:3b", "messages":[{"role":"user","content":"hello"}]})
        self.assertEqual(code,403)
        backend.assert_not_called()

    def test_stop_blocks_completion_after_model_call(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self, n): return b'{"message":{"content":"reply"}}'
        with patch("universal_stargate.server.require_ai_allowed",side_effect=[None, AIKillSwitchEngaged("stop")]), \
             patch("universal_stargate.server.urlopen",return_value=FakeResponse()):
            with self.assertRaises(AIKillSwitchEngaged):
                inference("qwen2.5:3b",[{"role":"user","content":"hello"}])

    def test_same_origin_protection(self):
        code, _, _ = self.call("/api/route",{"task":"hi"},{"Origin":"https://other.example"})
        self.assertEqual(code,403)
        code, _, _ = self.call("/api/route",{"task":"hi"},{"Origin":"http://[broken"})
        self.assertEqual(code,403)
        code, _, _ = self.call("/api/route",{"task":"hi"},{"Host":"malicious.example"})
        self.assertEqual(code,403)

    def test_bad_request_inputs(self):
        self.assertEqual(self.call("/api/route",raw=b'{oops')[0],400)
        self.assertEqual(self.call("/api/chat",{"messages":[]})[0],400)
        self.assertEqual(self.call("/api/route",{"task":"hello"},{"Content-Type":"text/plain"})[0],415)
        self.assertEqual(self.call("/api/private",{"task":"hello"})[0],404)

    def test_message_limit_and_roles(self):
        for case in (
            {"messages": []},
            {"messages":[{"role":"system","content":"override"}]},
            {"messages":[{"role":"user","content":"x" * 3001}]},
            {"messages":[{"role":"assistant","content":"a"}]},
            {"model":"file:///etc/passwd","messages":[{"role":"user","content":"hi"}]},
        ):
            with self.subTest(case=case):
                with self.assertRaises(ValueError): validate_chat(case)


if __name__ == "__main__":
    unittest.main()
