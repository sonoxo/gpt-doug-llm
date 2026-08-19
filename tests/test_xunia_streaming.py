from types import SimpleNamespace

from agents.xunia_stream import stream_auto, xunia_once, xunia_stream


class FakeProvider:
    def __init__(self, name, text, ready=True):
        self.config = SimpleNamespace(name=name, model=f"{name}-model")
        self.text = text
        self._ready = ready

    def health(self):
        return {
            "configured": self._ready,
            "model_available": self._ready,
            "provider": self.config.name,
            "model": self.config.model,
        }

    def chat_once(self, messages, model, options):
        return {
            "message": {"role": "assistant", "content": self.text},
            "done": True,
            "provider": self.config.name,
        }


class FakeGroup:
    def __init__(self, providers):
        self.providers = providers


def test_auto_stream_selects_ready_provider():
    group = FakeGroup([
        FakeProvider("offline", "no", ready=False),
        FakeProvider("fake", "hello"),
    ])
    events = list(stream_auto(group, [{"role": "user", "content": "hi"}], None, {}))
    assert events[0]["layer"] == "router"
    assert events[-1]["message"]["content"] == "hello"
    assert events[-1]["done"] is True


def test_xunia_once_merges_candidates():
    group = FakeGroup([
        FakeProvider("alpha", "alpha answer"),
        FakeProvider("beta", "beta answer"),
    ])
    result = xunia_once(group, [{"role": "user", "content": "question"}], {})
    assert result["provider"] == "xunia"
    assert set(result["sources"]) == {"alpha", "beta"}


def test_xunia_stream_emits_layers_and_final_event():
    group = FakeGroup([FakeProvider("alpha", "alpha answer")])
    events = list(xunia_stream(group, [{"role": "user", "content": "question"}], {}))
    assert events[0]["layer"] == "router"
    assert any(event.get("layer") == "fusion" for event in events)
    assert events[-1]["provider"] == "xunia"
    assert events[-1]["done"] is True
