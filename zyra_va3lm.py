#!/usr/bin/env python3
"""Launch ZYRA MAX with native VA3LM Red Hat defensive intelligence commands."""
from __future__ import annotations

import builtins
import json
import os

import zyra_max as _zyra_max
from agents.va3lm_redhat_defense import CONTROL_CATALOG, print_audit, write_locked_evidence
from agents.va3lm_redhat_ontology import Va3lmOntologyError, gaps, graph, run_lock, status

_BASE_INPUT = builtins.input


def _va3lm_input(prompt: str = "") -> str:
    root = os.path.dirname(os.path.abspath(__file__))
    while True:
        value = _BASE_INPUT(prompt)
        stripped = value.strip()
        lowered = stripped.lower()

        if lowered == "/help":
            print(
                "🛡️ VA3LM Red Hat Intelligence: /va3lm-lock /va3lm-status /va3lm-audit "
                "/va3lm-graph /va3lm-gaps /va3lm-catalog"
            )
            return value

        if lowered == "/va3lm-lock":
            try:
                manifest = run_lock(root)
            except Va3lmOntologyError as exc:
                print(f"🛡️ VA3LM RED HAT LOCK HOLD ❌ // {exc}")
            except Exception as exc:
                print(f"🛡️ VA3LM RED HAT LOCK ERROR ❌ // {type(exc).__name__}: {exc}")
            else:
                print("🛡️ VA3LM RED HAT ONTOLOGY MASTER LOCK ✅")
                print(f"Lock ID: {manifest['lockId']}")
                print("Subagents: " + ", ".join(item["subagent"] for item in manifest["subagents"]))
                print("Remote scanning OFF // exploit execution OFF // retaliation OFF")
            continue

        if lowered == "/va3lm-status":
            print(status(root))
            continue

        if lowered == "/va3lm-audit":
            try:
                print_audit(write_locked_evidence(root))
            except Exception as exc:
                print(f"🛡️ VA3LM HOST AUDIT ERROR ❌ // {type(exc).__name__}: {exc}")
            continue

        if lowered == "/va3lm-graph":
            try:
                print(graph(root))
            except Va3lmOntologyError as exc:
                print(f"🕸️ VA3LM GRAPH HOLD ❌ // {exc}")
                print("   Run /va3lm-lock first.")
            continue

        if lowered == "/va3lm-gaps":
            try:
                print(gaps(root))
            except Va3lmOntologyError as exc:
                print(f"🧩 VA3LM GAPS HOLD ❌ // {exc}")
                print("   Run /va3lm-lock first.")
            continue

        if lowered == "/va3lm-catalog":
            print(json.dumps(list(CONTROL_CATALOG), indent=2, ensure_ascii=False))
            continue

        return value


builtins.input = _va3lm_input
main = _zyra_max.main


if __name__ == "__main__":
    raise SystemExit(main())
