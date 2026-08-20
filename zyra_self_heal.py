#!/usr/bin/env python3
"""Bounded local runtime self-healing for ZYRA.

Repairs only ZYRA's own local runtime configuration: provider aliases,
Ollama availability, model selection, and a persisted non-secret runtime env.
It does not rewrite arbitrary project code, download models automatically,
contact third-party targets, or run recursive repair loops.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "gpt-doug"
RUNTIME_ENV = CONFIG_DIR / "runtime.env"
OLLAMA_LOG = Path.home() / ".ollama" / "zyra-heal.log"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
ENV_ALLOWLIST = {
    "GPT_DOUG_PROVIDER",
    "LLM_PROVIDER",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "GPT_DOUG_MODEL",
    "AGENT_PLANNER_MODEL",
    "AGENT_EXECUTOR_MODEL",
    "AGENT_REVIEWER_MODEL",
}


def _clean_url(value: str | None) -> str:
    url = (value or DEFAULT_OLLAMA_URL).strip().rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url or DEFAULT_OLLAMA_URL


def load_runtime_env(path: Path = RUNTIME_ENV) -> dict[str, str]:
    """Load ZYRA's persisted non-secret runtime settings without shell eval."""
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key not in ENV_ALLOWLIST:
                continue
            if key not in os.environ or not os.environ[key].strip():
                os.environ[key] = value
                loaded[key] = value
    except OSError:
        return loaded
    return loaded


def _ollama_tags(base_url: str, timeout: float = 2.0) -> list[str] | None:
    try:
        req = urllib.request.Request(
            f"{base_url}/api/tags",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode())
        return [
            item.get("name", "")
            for item in data.get("models", [])
            if item.get("name")
        ]
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def _match_model(models: list[str], wanted: str) -> str | None:
    wanted = (wanted or "").strip()
    if not wanted:
        return None
    for name in models:
        if name == wanted or name.startswith(wanted + ":"):
            return name
    return None


def choose_local_model(models: list[str]) -> str | None:
    if not models:
        return None
    wanted = [
        os.environ.get("OLLAMA_MODEL", ""),
        os.environ.get("GPT_DOUG_MODEL", ""),
        os.environ.get("ZYRA_MODEL", ""),
        "gpt-doug",
        "qwen2.5-coder:7b",
        "qwen2.5-coder",
        "llama3",
        "gemma3",
    ]
    for candidate in wanted:
        matched = _match_model(models, candidate)
        if matched:
            return matched
    return models[0]


def persist_runtime_env(values: dict[str, str], path: Path = RUNTIME_ENV) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lines = ["# Managed by ZYRA self-heal. Contains no API secrets."]
    for key in sorted(values):
        if key in ENV_ALLOWLIST and values[key]:
            lines.append(f"{key}={values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _start_ollama(base_url: str, wait_seconds: int = 8) -> bool:
    if _ollama_tags(base_url) is not None:
        return True
    binary = shutil.which("ollama")
    if not binary:
        return False
    OLLAMA_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with OLLAMA_LOG.open("ab") as log:
            subprocess.Popen(
                [binary, "serve"],
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError:
        return False
    for _ in range(max(1, wait_seconds)):
        if _ollama_tags(base_url) is not None:
            return True
        time.sleep(1)
    return False


def run_self_heal(*, start_ollama: bool = True, persist: bool = True) -> dict[str, Any]:
    """Run one bounded repair pass and return a machine-readable report."""
    load_runtime_env()

    # Backward-compatible alias: the agent chain historically looked only
    # for GPT_DOUG_PROVIDER while terminal experiments used LLM_PROVIDER.
    provider = (
        os.environ.get("GPT_DOUG_PROVIDER")
        or os.environ.get("LLM_PROVIDER")
        or ""
    ).strip().lower()

    openai_base = os.environ.get("OPENAI_API_BASE", "").strip()
    base_url = _clean_url(
        os.environ.get("OLLAMA_BASE_URL")
        or (openai_base if "11434" in openai_base or "localhost" in openai_base else "")
    )

    models = _ollama_tags(base_url)
    started = False
    if models is None and start_ollama:
        started = _start_ollama(base_url)
        models = _ollama_tags(base_url)

    ollama_online = models is not None
    models = models or []

    if not provider and ollama_online:
        provider = "ollama"
    if provider == "ollama":
        os.environ["GPT_DOUG_PROVIDER"] = "ollama"
        os.environ["LLM_PROVIDER"] = "ollama"
        os.environ["OLLAMA_BASE_URL"] = base_url

    selected_model = choose_local_model(models) if ollama_online else None
    if provider == "ollama" and selected_model:
        os.environ["OLLAMA_MODEL"] = selected_model
        os.environ["GPT_DOUG_MODEL"] = selected_model
        # Keep the entire agent chain usable even when only one local model
        # is installed. Users can override these later with explicit models.
        os.environ.setdefault("AGENT_PLANNER_MODEL", selected_model)
        os.environ.setdefault("AGENT_EXECUTOR_MODEL", selected_model)
        os.environ.setdefault("AGENT_REVIEWER_MODEL", selected_model)

    persisted: dict[str, str] = {}
    if persist and provider == "ollama" and selected_model:
        persisted = {
            "GPT_DOUG_PROVIDER": "ollama",
            "LLM_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": base_url,
            "OLLAMA_MODEL": selected_model,
            "GPT_DOUG_MODEL": selected_model,
            "AGENT_PLANNER_MODEL": os.environ.get("AGENT_PLANNER_MODEL", selected_model),
            "AGENT_EXECUTOR_MODEL": os.environ.get("AGENT_EXECUTOR_MODEL", selected_model),
            "AGENT_REVIEWER_MODEL": os.environ.get("AGENT_REVIEWER_MODEL", selected_model),
        }
        persist_runtime_env(persisted)

    issues: list[str] = []
    if not shutil.which("ollama"):
        issues.append("ollama binary not found")
    if not ollama_online:
        issues.append("ollama server not reachable")
    if ollama_online and not models:
        issues.append("ollama has no installed models")
    if provider not in {"ollama", "auto", "xunia", "openai", "claude", "anthropic", "gemini"}:
        issues.append(f"unsupported provider: {provider or 'none'}")
    if provider == "ollama" and not selected_model:
        issues.append("no usable local model selected")

    healthy = provider == "ollama" and ollama_online and bool(selected_model)
    return {
        "healthy": healthy,
        "provider": provider or "none",
        "ollama_base_url": base_url,
        "ollama_online": ollama_online,
        "ollama_started": started,
        "models": models,
        "selected_model": selected_model,
        "runtime_env": str(RUNTIME_ENV),
        "persisted": bool(persisted),
        "issues": issues,
        "bounded": True,
        "auto_model_download": False,
    }


def print_heal_report(report: dict[str, Any]) -> None:
    state = "HEALTHY ✅" if report.get("healthy") else "NEEDS ATTENTION ⚠️"
    print("\n🩺 ZYRA SELF-HEAL // BOUNDED LOCAL REPAIR")
    print(f"🧠 Runtime: {state}")
    print(f"🔌 Provider: {report.get('provider')}")
    print(f"🦙 Ollama: {'ONLINE' if report.get('ollama_online') else 'OFFLINE'}")
    if report.get("ollama_started"):
        print("🔧 Repair: Ollama service restarted")
    if report.get("selected_model"):
        print(f"📦 Model: {report['selected_model']}")
    if report.get("persisted"):
        print(f"💾 Runtime config repaired: {report['runtime_env']}")
    for issue in report.get("issues", []):
        print(f"⚠️ {issue}")
    print("🔁 Repair passes: 1 // recursive loops: OFF // model auto-download: OFF\n")


if __name__ == "__main__":
    report = run_self_heal()
    print_heal_report(report)
    raise SystemExit(0 if report["healthy"] else 1)
