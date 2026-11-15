"""CL1 LLM Architecture v2: offline transport, model admission and bounds."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch

from agents import llm_backend
from agents.cl1_runtime_v2 import (
    architecture_status,
    bounded_ollama_options,
    resolve_installed_model,
)
from agents.xunia_stream import stream_ollama


class LLMArchitectureV2Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        stop = Path(tmp.name) / "stop"
        env = patch.dict(os.environ, {
            "GPT_DOUG_AI_BLOCK_ALL": "0",
            "GPT_DOUG_AI_STOP_DIR": str(stop),
            "GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY": "0",
            "OLLAMA_MODEL": "qwen2.5-coder:3b",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        })
        env.start()
        self.addCleanup(env.stop)

    def test_strictly_installed_model_no_implicit_cloud_pull(self):
        models = ["qwen2.5-coder:3b", "tiny:latest", "gemma4:cloud"]
        self.assertEqual(resolve_installed_model("qwen2.5-coder:3b", models), "qwen2.5-coder:3b")
        self.assertEqual(resolve_installed_model("tiny", models), "tiny:latest")
        for request in ("qwen2.5-coder", "not-downloaded:3b", "gemma4:cloud",
                        "model:cloud", "../remote", "model with spaces", ""):
            with self.subTest(request=request):
                self.assertIsNone(resolve_installed_model(request, models))

    def test_bounded_options_allow_resource_limited_requests(self):
        defaults = bounded_ollama_options(None)
        self.assertLessEqual(defaults["num_ctx"], 8192)
        self.assertLessEqual(defaults["num_predict"], 2048)
        payload = bounded_ollama_options({
            "temperature": 0.1, "num_ctx": 2048, "max_tokens": 500,
            "stop": ["DONE"], "cloud_base_url": "https://example.net",
        })
        self.assertEqual(payload["num_predict"], 500)
        self.assertEqual(payload["num_ctx"], 2048)
        self.assertNotIn("cloud_base_url", payload)
        for invalid in ({"num_ctx": 100000}, {"num_predict": 999999},
                        {"max_tokens": -1}, {"temperature": float("nan")},
                        {"num_ctx": True}, {"stop": ["a"] * 9}, {"stop": [""]},
                        "not an options object"):
            with self.subTest(invalid=str(invalid)):
                with self.assertRaises(ValueError):
                    bounded_ollama_options(invalid)

    def test_transport_disables_proxy_and_redirects(self):
        endpoint = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        sentinel = object()
        fake_opener = Mock()
        fake_opener.open.return_value = sentinel
        with patch.object(urllib.request, "build_opener", return_value=fake_opener) as build:
            self.assertIs(llm_backend._safe_urlopen(endpoint, timeout=2, allow_local_http=True), sentinel)
        handlers = build.call_args.args
        proxies = [h for h in handlers if isinstance(h, urllib.request.ProxyHandler)]
        self.assertEqual(len(proxies), 1)
        self.assertEqual(proxies[0].proxies, {})
        blockers = [h for h in handlers if isinstance(h, llm_backend._RejectInferenceRedirects)]
        self.assertEqual(len(blockers), 1)
        with self.assertRaisesRegex(ValueError, "Refusing inference redirect"):
            blockers[0].redirect_request(
                endpoint, None, 302, "Found", {}, "https://api.openai.com/v1/chat/completions"
            )

    def test_remote_target_rejected_before_opening(self):
        with patch.object(urllib.request, "build_opener", side_effect=AssertionError("network attempted")):
            for url in ("https://api.openai.com/v1/chat/completions",
                        "http://localhost.evil.com:11434/api/tags",
                        "file:///tmp/key"):
                with self.subTest(url=url):
                    with self.assertRaises(ValueError):
                        llm_backend._safe_urlopen(
                            urllib.request.Request(url), timeout=1, allow_local_http=True
                        )

    def test_ollama_chat_rejects_uninstalled_override_before_model_call(self):
        provider = llm_backend.OllamaProvider()
        with patch.object(provider, "health", return_value={
            "configured": True, "model_available": True, "models": ["qwen2.5-coder:3b"],
        }):
            with patch.object(llm_backend, "_safe_urlopen", side_effect=AssertionError("chat network")):
                result = provider.chat_once([{"role":"user","content":"test"}], "gemma4:2b", {})
                self.assertEqual(result["error"], "model_unavailable")
                result = provider.chat_once([{"role":"user","content":"test"}], None, {"num_ctx": 500000})
                self.assertEqual(result["error"], "invalid_inference_options")

    def test_ollama_stream_rejects_uninstalled_override(self):
        provider = llm_backend.OllamaProvider()
        with patch.object(provider, "health", return_value={
            "configured": True, "model_available": True, "models": ["qwen2.5-coder:3b"],
        }):
            with patch("agents.xunia_stream._safe_urlopen", side_effect=AssertionError("network")):
                events = list(stream_ollama(provider, [{"role":"user","content":"hi"}], "not-installed:7b", {}))
                self.assertEqual(events[-1]["error"], "model_unavailable")

    def test_ollama_chat_sends_only_installed_model_and_bounded_options(self):
        provider = llm_backend.OllamaProvider()
        response = io.BytesIO(json.dumps({
            "message": {"role": "assistant", "content": "local"},
            "done": True,
        }).encode())
        with patch.object(provider, "health", return_value={
            "configured": True, "model_available": True, "models": ["qwen2.5-coder:3b"],
        }), patch.object(llm_backend, "_safe_urlopen") as transport:
            transport.return_value.__enter__.return_value = response
            result = provider.chat_once(
                [{"role": "user", "content": "test"}],
                "qwen2.5-coder:3b",
                {"num_ctx": 2048, "max_tokens": 250, "api_key": "should_not_be_sent"},
            )
            self.assertEqual(result["message"]["content"], "local")
            request = transport.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(payload["model"], "qwen2.5-coder:3b")
            self.assertEqual(payload["options"]["num_predict"], 250)
            self.assertNotIn("api_key", payload["options"])

    def test_router_never_uses_paid_fallback_even_with_env(self):
        with patch.dict(os.environ, {
            "GPT_DOUG_PROVIDER_ORDER": "openai,claude,gemini,ollama,ollama,unknown",
            "OPENAI_API_KEY": "test-unusable-credential",
            "PAID_MODE": "true",
        }):
            router = llm_backend.AutoProvider()
            self.assertEqual(router.order, ["ollama"])
            self.assertEqual([p.config.name for p in router.providers], ["ollama"])

    def test_local_ui_catalog_has_no_cloud_choices(self):
        with patch.object(llm_backend.OllamaProvider, "health", return_value={
            "configured": True, "model_available": True, "models": ["qwen2.5-coder:3b"],
        }):
            catalog = llm_backend.available_providers()
        self.assertNotIn("openai", [p["id"] for p in catalog])
        self.assertNotIn("gemini", [p["id"] for p in catalog])
        self.assertNotIn("claude", [p["id"] for p in catalog])
        self.assertIn("ollama", [p["id"] for p in catalog])
        status = architecture_status()
        self.assertFalse(status["remote_inference_allowed"])
        self.assertFalse(status["auto_model_pull_allowed"])
        self.assertFalse(status["proxies_allowed"])


if __name__ == "__main__":
    unittest.main()
