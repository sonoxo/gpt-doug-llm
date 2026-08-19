from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator

Event = dict
Message = dict[str, str]


def _event(content: str = "", *, provider: str = "", done: bool = False, **extra) -> Event:
    event: Event = {
        "message": {"role": "assistant", "content": content},
        "done": done,
    }
    if provider:
        event["provider"] = provider
    event.update(extra)
    return event


def _data_lines(response) -> Iterator[dict]:
    for raw in response:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def provider_timeout() -> float:
    from agents import llm_backend
    return llm_backend.DEFAULT_TIMEOUT


def stream_openai(provider, messages, model, options) -> Iterator[Event]:
    if not provider.config.configured:
        yield provider.chat_once(messages, model, options)
        return
    used_model = model or provider.config.model
    body = json.dumps({
        "model": used_model,
        "messages": messages,
        "temperature": options.get("temperature", 0.7),
        "stream": True,
    }).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        body,
        {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {provider.api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=provider_timeout()) as response:
        for data in _data_lines(response):
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            text = delta.get("content") or ""
            if text:
                yield _event(text, provider="openai", model=used_model)
            if choices[0].get("finish_reason") is not None:
                break
    yield _event(provider="openai", model=used_model, done=True)


def stream_anthropic(provider, messages, model, options) -> Iterator[Event]:
    if not provider.config.configured:
        yield provider.chat_once(messages, model, options)
        return
    used_model = model or provider.config.model
    system = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
    chat_messages = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in messages
        if m.get("role") in {"user", "assistant"}
    ]
    body = {
        "model": used_model,
        "max_tokens": int(options.get("max_tokens", 4096)),
        "temperature": options.get("temperature", 0.7),
        "messages": chat_messages,
        "stream": True,
    }
    if system:
        body["system"] = system
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        json.dumps(body).encode(),
        {
            "content-type": "application/json",
            "accept": "text/event-stream",
            "x-api-key": provider.api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(request, timeout=provider_timeout()) as response:
        for data in _data_lines(response):
            if data.get("type") == "content_block_delta":
                delta = data.get("delta") or {}
                text = delta.get("text") or ""
                if text:
                    yield _event(text, provider="claude", model=used_model)
            if data.get("type") == "message_stop":
                break
    yield _event(provider="claude", model=used_model, done=True)


def stream_gemini(provider, messages, model, options) -> Iterator[Event]:
    if not provider.config.configured:
        yield provider.chat_once(messages, model, options)
        return
    used_model = model or provider.config.model
    contents = [{
        "role": "model" if item.get("role") == "assistant" else "user",
        "parts": [{"text": item.get("content", "")}],
    } for item in messages if item.get("role") != "system"]
    system = "\n\n".join(item.get("content", "") for item in messages if item.get("role") == "system")
    body = {"contents": contents, "generationConfig": {"temperature": options.get("temperature", 0.7)}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(used_model, safe='')}:"
        "streamGenerateContent?alt=sse"
    )
    request = urllib.request.Request(
        endpoint,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", "Accept": "text/event-stream", "x-goog-api-key": provider.api_key},
    )
    with urllib.request.urlopen(request, timeout=provider_timeout()) as response:
        for data in _data_lines(response):
            candidates = data.get("candidates") or []
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts)
            if text:
                yield _event(text, provider="gemini", model=used_model)
    yield _event(provider="gemini", model=used_model, done=True)


def stream_ollama(provider, messages, model, options) -> Iterator[Event]:
    state = provider.health()
    if not state.get("configured"):
        yield provider.chat_once(messages, model, options)
        return
    used_model = model or provider.config.model
    body = json.dumps({"model": used_model, "messages": messages, "stream": True, "options": options}).encode()
    request = urllib.request.Request(
        f"{provider.base_url}/api/chat",
        body,
        {"Content-Type": "application/json", "Accept": "application/x-ndjson"},
    )
    with urllib.request.urlopen(request, timeout=max(provider_timeout(), 600)) as response:
        for raw in response:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = data.get("message") or {}
            text = message.get("content") or ""
            if text:
                yield _event(text, provider="ollama", model=used_model)
            if data.get("done"):
                break
    yield _event(provider="ollama", model=used_model, done=True)


def stream_provider(provider, messages, model, options) -> Iterator[Event]:
    name = provider.config.name
    if name == "openai":
        yield from stream_openai(provider, messages, model, options)
    elif name in {"claude", "anthropic"}:
        yield from stream_anthropic(provider, messages, model, options)
    elif name == "gemini":
        yield from stream_gemini(provider, messages, model, options)
    elif name == "ollama":
        yield from stream_ollama(provider, messages, model, options)
    else:
        yield provider.chat_once(messages, model, options)


def stream_auto(auto_provider, messages, model, options) -> Iterator[Event]:
    errors = []
    for provider in auto_provider.providers:
        state = provider.health()
        if not (state.get("configured") and state.get("model_available")):
            errors.append(f"{provider.config.name}: not ready")
            continue
        yield _event(provider=provider.config.name, layer="router", status="selected", done=False)
        try:
            for event in stream_provider(provider, messages, None, options):
                event.setdefault("routed_by", "auto")
                yield event
            return
        except Exception as exc:
            errors.append(f"{provider.config.name}: {type(exc).__name__}")
            yield _event(provider=provider.config.name, layer="router", status="fallback", done=False)
    yield _event(
        "All configured AI providers failed readiness or request checks.",
        provider="auto",
        done=True,
        error="all_providers_failed",
        provider_errors=errors,
    )


def _ready_children(xunia_provider):
    ready = []
    for provider in xunia_provider.providers:
        state = provider.health()
        if state.get("configured") and state.get("model_available"):
            ready.append(provider)
    return ready


def _candidate(provider, messages, options):
    return provider.config.name, provider.chat_once(messages, None, options)


def _fusion_messages(messages, candidates):
    source = []
    for name, result in candidates:
        text = (result.get("message") or {}).get("content", "")
        if text:
            source.append(f"--- {name.upper()} CANDIDATE ---\n{text[:12000]}")
    fusion = (
        "You are GPT XUNIA SUPER BRAIN 9000, the consensus layer. "
        "Synthesize the strongest single answer from the candidate model outputs below. "
        "Resolve contradictions using evidence and the original conversation. "
        "Do not mention this fusion prompt or expose provider credentials.\n\n"
        + "\n\n".join(source)
    )
    return list(messages) + [{"role": "user", "content": fusion}]


def xunia_once(xunia_provider, messages, options):
    ready = _ready_children(xunia_provider)
    if not ready:
        return {
            "message": {"role": "assistant", "content": "No AI provider passed GPT XUNIA readiness checks."},
            "done": True,
            "provider": "xunia",
            "error": "all_providers_failed",
        }
    if len(ready) == 1:
        result = ready[0].chat_once(messages, None, options)
        result["provider"] = "xunia"
        result["sources"] = [ready[0].config.name]
        return result

    candidates = []
    with ThreadPoolExecutor(max_workers=min(len(ready), 4)) as pool:
        futures = [pool.submit(_candidate, provider, messages, options) for provider in ready]
        for future in as_completed(futures):
            try:
                name, result = future.result()
            except Exception:
                continue
            if not result.get("error") and (result.get("message") or {}).get("content"):
                candidates.append((name, result))
    if not candidates:
        return {
            "message": {"role": "assistant", "content": "Configured providers returned no usable XUNIA candidates."},
            "done": True,
            "provider": "xunia",
            "error": "all_providers_failed",
        }
    arbiter = next((provider for provider in ready if provider.config.name == candidates[0][0]), ready[0])
    result = arbiter.chat_once(_fusion_messages(messages, candidates), None, options)
    result["provider"] = "xunia"
    result["arbiter"] = arbiter.config.name
    result["sources"] = [name for name, _ in candidates]
    return result


def xunia_stream(xunia_provider, messages, options) -> Iterator[Event]:
    ready = _ready_children(xunia_provider)
    yield _event(provider="xunia", layer="router", status=f"{len(ready)} providers ready", done=False)
    if not ready:
        yield _event(
            "No AI provider passed GPT XUNIA readiness checks.",
            provider="xunia",
            done=True,
            error="all_providers_failed",
        )
        return
    if len(ready) == 1:
        only = ready[0]
        yield _event(provider="xunia", layer="fusion", status=f"single source: {only.config.name}", done=False)
        for event in stream_provider(only, messages, None, options):
            event["source_provider"] = event.get("provider", only.config.name)
            event["provider"] = "xunia"
            yield event
        return

    candidates = []
    yield _event(provider="xunia", layer="fanout", status="collecting candidates", done=False)
    with ThreadPoolExecutor(max_workers=min(len(ready), 4)) as pool:
        future_map = {pool.submit(_candidate, provider, messages, options): provider for provider in ready}
        for future in as_completed(future_map):
            provider = future_map[future]
            try:
                name, result = future.result()
            except Exception:
                yield _event(provider="xunia", source_provider=provider.config.name, layer="fanout", status="failed", done=False)
                continue
            if not result.get("error") and (result.get("message") or {}).get("content"):
                candidates.append((name, result))
                yield _event(provider="xunia", source_provider=name, layer="fanout", status="candidate ready", done=False)

    if not candidates:
        yield _event(
            "Configured providers returned no usable XUNIA candidates.",
            provider="xunia",
            done=True,
            error="all_providers_failed",
        )
        return

    source_names = [name for name, _ in candidates]
    arbiter = next((provider for provider in ready if provider.config.name == source_names[0]), ready[0])
    yield _event(
        provider="xunia",
        source_provider=arbiter.config.name,
        layer="fusion",
        status="streaming consensus",
        sources=source_names,
        done=False,
    )
    fusion_messages = _fusion_messages(messages, candidates)
    for event in stream_provider(arbiter, fusion_messages, None, options):
        event["source_provider"] = event.get("provider", arbiter.config.name)
        event["provider"] = "xunia"
        event["sources"] = source_names
        yield event
