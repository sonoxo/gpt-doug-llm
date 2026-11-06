"""Read-only health matrix for the GPT-DOUG / XUNIA modular framework.

An importability check is NOT an assertion of runtime availability.
No paid API, source mutation, keys, remote GitHub access, or background
tasks. Ollama is probed only after explicit --ollama opt-in and loopback
endpoint validation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
import sys
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


# These are installable modules in pyproject.toml on main. The checks use
# find_spec, so nothing in the agent/fleet is executed by the diagnosis.
_COMPONENTS = (
    ("operator_safety", "ai_killswitch", True),
    ("brain_ontology", "gpt_brain", True),
    ("agent_orchestration", "agents", True),
    ("mlm_neural_model", "gpt_doug_mlm", True),
    ("guardian", "gpt_doug_guardian", True),
    ("chaos_resilience", "gpt_chaos", True),
    ("hivemind", "hivemind", True),
    ("cloud_nxyz", "cloud_nxyz", True),
    ("biochip_simulation", "gpt_doug_qbio", True),
    ("watchtower", "universal_watchdog", True),
    ("uap_matrix", "uap_matrix", True),
    ("skull_3d", "skull_llm", False),  # Separate PR #503 until integrated.
    ("va3lm_control_plane", "va3lm", False),  # Independently packaged.
    ("pytorch", "torch", False),  # Large optional ML dependency.
)


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, AttributeError, ValueError, ModuleNotFoundError):
        return False


def _stop_check() -> dict[str, Any]:
    try:
        from ai_killswitch import status

        result = status()
        return {
            "status": "STOPPED" if result["stopped"] else "CLEAR",
            "reason": str(result.get("reason", "unknown")),
        }
    except (ImportError, OSError, RuntimeError, KeyError, ValueError):
        return {"status": "UNKNOWN", "reason": "Operator stop state could not be read"}


def _ollama_check(base_url: str) -> dict[str, Any]:
    """Opt-in, strictly HTTP loopback only. Never forwards env credentials."""
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        return {"status": "REJECTED", "reason": "Only plain HTTP loopback is allowed"}
    try:
        request = Request(
            f"http://{parsed.netloc}/api/tags",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urlopen(request, timeout=1.5) as response:
            body = response.read(65537)
            if response.status != 200 or len(body) > 65536:
                return {"status": "INVALID_RESPONSE"}
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("models"), list):
            return {"status": "INVALID_RESPONSE"}
        model_count = len(data["models"])
        return {"status": "REACHABLE", "model_count": model_count}
    except (OSError, RuntimeError, ValueError, UnicodeError, TimeoutError):
        return {"status": "OFFLINE"}


def collect_status(*, check_ollama: bool = False) -> dict[str, Any]:
    modules = [
        {
            "component": label,
            "module": module,
            "required": required,
            "status": "IMPORTABLE" if _installed(module) else "MISSING",
        }
        for label, module, required in _COMPONENTS
    ]
    missing_required = [x["component"] for x in modules if x["required"] and x["status"] == "MISSING"]
    report: dict[str, Any] = {
        "schema": "gpt-doug-framework-health-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": "GPT-DOUG-LLM / XUNIA",
        "checks_are_read_only": True,
        "scope": "Installed Python importability only, not operational verification",
        "core_complete": not missing_required,
        "missing_required": missing_required,
        "components": modules,
        "emergency_stop": _stop_check(),
    }
    if check_ollama:
        report["ollama"] = _ollama_check(os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    else:
        report["ollama"] = {"status": "NOT_CHECKED", "reason": "Use --ollama to probe loopback"}
    return report


def format_terminal(report: dict[str, Any]) -> str:
    lines = [
        "GPT-DOUG // FRAMEWORK HEALTH / LOCAL",
        "=" * 56,
        "NOTE: IMPORTABLE IS NOT PROOF OF WORKING INFERENCE",
        "",
    ]
    for item in report["components"]:
        requirement = "CORE" if item["required"] else "OPTIONAL"
        lines.append(
            f"{item['component']:<24} {item['status']:<11} {requirement}"
        )
    lines += [
        "",
        f"CORE COMPONENTS  {'COMPLETE' if report['core_complete'] else 'INCOMPLETE'}",
        f"EMERGENCY STOP   {report['emergency_stop']['status']}",
        f"OLLAMA           {report['ollama']['status']}",
        "No jobs launched. No cloud tokens or credentials accessed.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gpt-doug-health",
        description="Read-only framework health matrix. No cloud APIs.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--strict", action="store_true", help="fail on missing core modules")
    parser.add_argument("--ollama", action="store_true", help="probe local loopback Ollama")
    args = parser.parse_args(argv)
    report = collect_status(check_ollama=args.ollama)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_terminal(report))
    return 1 if args.strict and not report["core_complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
