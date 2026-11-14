"""Offline regression tests for CL1's fail-closed, zero-billing AI routing."""

import os
import unittest
import urllib.request
from unittest.mock import patch

from agents import llm_backend
from agents.cl1_free_policy import free_policy_status, is_local_inference_url, is_local_ollama_model


class FreeOnlyTests(unittest.TestCase):
    def test_local_only_urls(self):
        self.assertTrue(is_local_inference_url("http://127.0.0.1:11434/api/tags"))
        self.assertTrue(is_local_inference_url("http://localhost:8000/v1"))
        for url in (
            "https://api.openai.com/v1/chat/completions",
            "https://generativelanguage.googleapis.com/v1beta/models",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "http://localhost.evil.example/api",
            "file:///tmp/secret",
            "http://user:pass@127.0.0.1:11434/api",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_local_inference_url(url))

    def test_paid_providers_blocked_even_when_keys_present(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "example-placeholder-unused-000",
            "ANTHROPIC_API_KEY": "example-placeholder-unused-000",
            "GEMINI_API_KEY": "example-placeholder-unused-000",
            "PAID_MODE": "true",
        }):
            for provider in ("openai", "claude", "anthropic", "gemini"):
                with self.subTest(provider=provider):
                    impl = llm_backend._make_provider(provider)
                    self.assertFalse(impl.health()["configured"])
                    self.assertEqual(
                        impl.chat_once([{"role": "user", "content": "hello"}], None, {})["error"],
                        "paid_provider_blocked",
                    )

    def test_auto_router_never_selects_cloud_provider(self):
        with patch.dict(os.environ, {
            "GPT_DOUG_PROVIDER_ORDER": "openai,claude,gemini,ollama",
            "PAID_MODE": "true",
        }):
            router = llm_backend.AutoProvider()
            self.assertEqual([p.config.name for p in router.providers], ["ollama"])

    def test_transport_rejects_remote_before_network_access(self):
        request = urllib.request.Request("https://api.openai.com/v1/chat/completions")
        with patch.object(urllib.request, "urlopen", side_effect=AssertionError("network called")):
            with self.assertRaisesRegex(ValueError, "Refusing unsafe provider URL"):
                llm_backend._safe_urlopen(request, timeout=1)

    def test_ollama_cloud_models_are_blocked(self):
        self.assertTrue(is_local_ollama_model("qwen2.5-coder:3b"))
        self.assertFalse(is_local_ollama_model("gemma4:cloud"))
        with patch.dict(os.environ, {"OLLAMA_MODEL": "gemma4:cloud"}):
            provider = llm_backend.OllamaProvider()
            result = provider.chat_once([{"role": "user", "content": "test"}], None, {})
            self.assertEqual(result["error"], "cloud_model_blocked")

    def test_checkout_and_webhooks_never_accept_payments(self):
        from web import stripe_checkout

        self.assertFalse(stripe_checkout.enabled())
        with self.assertRaisesRegex(RuntimeError, "disables Stripe checkout"):
            stripe_checkout.create_checkout_session("id", "task", "https://example.org", "https://example.org")
        with self.assertRaisesRegex(ValueError, "rejects Stripe payment webhooks"):
            stripe_checkout.verify_webhook_signature(b"{}", "t=123,v1=abc")

    def test_stream_refuses_cloud_model_before_network(self):
        from agents.xunia_stream import stream_ollama

        provider = llm_backend.OllamaProvider()
        with patch.object(urllib.request, "urlopen", side_effect=AssertionError("network called")):
            events = list(stream_ollama(provider, [{"role": "user", "content": "test"}], "gemma4:cloud", {}))
        self.assertEqual(events[-1]["error"], "cloud_model_blocked")

    def test_free_policy_cannot_be_overridden_by_paid_mode(self):
        with patch.dict(os.environ, {"PAID_MODE": "true", "GPT_DOUG_FREE_ONLY": "false"}):
            self.assertFalse(free_policy_status()["paid_inference_allowed"])


if __name__ == "__main__":
    unittest.main()
