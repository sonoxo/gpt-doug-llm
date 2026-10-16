import json
import unittest
from unittest.mock import patch
from biochip.models import Model, ModelRouter

class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = ModelRouter()
    def test_discovery_multiple_backends(self):
        def fake(provider, path, payload=None):
            if provider == "ollama":
                return {"models": [{"name": "qwen:test"}, {"name": "deepseek:test"}]}
            return {"data": [{"id": "local-llama"}]}
        with patch.object(self.router, "_request", side_effect=fake):
            models, errors = self.router.discover()
        self.assertEqual(len(models), 3)
        self.assertEqual(errors, {})
    def test_chat_ollama(self):
        with patch.object(self.router, "_request", return_value={"message": {"content": "ok"}}) as call:
            self.assertEqual(self.router.chat(Model("ollama", "gemma:test"), "hi"), "ok")
            self.assertEqual(call.call_args.args[1], "/api/chat")
    def test_chat_compatible(self):
        with patch.object(self.router, "_request", return_value={"choices": [{"message": {"content": "yes"}}]}):
            self.assertEqual(self.router.chat(Model("openai_compatible", "any"), "hi"), "yes")
    def test_no_remote_hosts(self):
        for url in ("https://localhost:443", "http://example.com", "file:///etc/passwd",
                    "http://user:pass@localhost:8000"):
            with self.assertRaises(ValueError):
                ModelRouter({"unsafe": url})
    def test_explicit_memory(self):
        class Memory:
            def __init__(self): self.writes = []
            def recall(self, key, *, actor): return {"value": {"note": "safe"}}
            def remember(self, key, value, **kwargs): self.writes.append((key, value, kwargs))
        chip = Memory()
        with patch.object(self.router, "chat", return_value="answer") as call:
            result = self.router.chat_with_memory(Model("ollama", "test"), "question",
                           chip=chip, actor="owner", memory_key="note")
            self.assertEqual(result, "answer")
            self.assertEqual(chip.writes, [])
            self.assertIn("untrusted", call.call_args.kwargs["system"])
            self.router.chat_with_memory(Model("ollama", "test"), "question",
                           chip=chip, actor="owner", save_reply_key="answer")
            self.assertEqual(chip.writes[0][0], "answer")
if __name__ == "__main__":
    unittest.main()
