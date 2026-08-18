import time

from agents import llm_backend


def test_circuit_opens_after_threshold():
    cb = llm_backend.CircuitBreaker(threshold=2, cooldown_s=60)
    assert cb.allow("x") is True
    cb.failure("x", "one")
    assert cb.status("x")["state"] == "closed"
    cb.failure("x", "two")
    assert cb.status("x")["state"] == "open"
    assert cb.allow("x") is False


def test_circuit_half_open_after_cooldown():
    cb = llm_backend.CircuitBreaker(threshold=1, cooldown_s=0.01)
    cb.failure("x", "boom")
    assert cb.status("x")["state"] == "open"
    time.sleep(0.02)
    assert cb.allow("x") is True
    assert cb.status("x")["state"] == "half_open"
    cb.success("x")
    assert cb.status("x")["state"] == "closed"


def test_placeholder_secrets_are_rejected():
    for value in ("", "...", "***", "changeme", "test"):
        assert llm_backend._valid_secret(value) is False


def test_reasonable_secret_shape_is_accepted():
    assert llm_backend._valid_secret("abcdefghijklmnop") is True


def test_no_provider_fails_closed():
    result = llm_backend.NoProvider().chat_once([], None, {})
    assert result["error"] == "provider_not_configured"
    assert result["done"] is True
