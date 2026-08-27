#!/usr/bin/env python3
# ruff: noqa: I001
"""Launch ZYRA with an expanded but still bounded mission envelope.

This profile is intended for long local repository/document-analysis missions
that need more than the default eight agent steps. It does not add shell,
network, push/deploy/send, or external-targeting capabilities.

MAX mode also hardens local-model action parsing. Small local models sometimes
wrap JSON in Markdown, emit a Python-style dict, or add prose around an action.
The recovery layer below accepts those harmless formatting variations and, when
necessary, performs one bounded repair request instead of terminating a mission
on the first malformed action.

MASTER-LOCKED ontology queries are intercepted locally before model chat. Every
query verifies the publication manifest and source/ontology/analysis hashes.
"""
from __future__ import annotations

import ast
import builtins
import json
import os
import re

from agents.ontology_query import OntologyQueryError, run_query_command
from zyra_agent import MissionBudget, MissionError, ZyraAgent


_ORIGINAL_INIT = ZyraAgent.__init__
_ORIGINAL_INPUT = builtins.input
_ALLOWED_ACTIONS = {
    "list_files",
    "read_file",
    "search",
    "replace_text",
    "create_file",
    "run_check",
    "finish",
}
_ONTOLOGY_COMMANDS = {
    "/ontology-status": "status",
    "/ontology-timeline": "timeline",
    "/ontology-graph": "graph",
    "/ontology-gaps": "gaps",
    "/ontology-brief": "brief",
}


def _env_int(name: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _max_init(
    self,
    root,
    *,
    model,
    base_url="http://127.0.0.1:11434",
    budget=None,
    state_dir=None,
):
    if budget is None:
        budget = MissionBudget(
            max_steps=_env_int("ZYRA_AGENT_MAX_STEPS", 32, 16),
            max_seconds=_env_int("ZYRA_AGENT_MAX_SECONDS", 1200, 300),
            max_model_calls=_env_int("ZYRA_AGENT_MAX_MODEL_CALLS", 48, 20),
        )
    _ORIGINAL_INIT(
        self,
        root,
        model=model,
        base_url=base_url,
        budget=budget,
        state_dir=state_dir,
    )
    self._max_json_repairs = 0


def _valid_action(value):
    return isinstance(value, dict) and str(value.get("action") or "") in _ALLOWED_ACTIONS


def _candidate_strings(raw: str):
    text = (raw or "").strip()
    if not text:
        return []

    text = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )

    candidates = [text]

    for match in re.finditer(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S):
        candidates.append(match.group(1).strip())

    for index, char in enumerate(text):
        if char == "{":
            candidates.append(text[index:])

    seen = set()
    ordered = []
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _robust_extract_json(raw: str):
    decoder = json.JSONDecoder()
    for item in _candidate_strings(raw):
        try:
            value = json.loads(item)
            if _valid_action(value):
                return value
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            value, _ = decoder.raw_decode(item.lstrip())
            if _valid_action(value):
                return value
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            value = ast.literal_eval(item)
            if _valid_action(value):
                return value
        except (ValueError, SyntaxError, TypeError):
            pass

    raise MissionError("agent returned invalid JSON action")


def _max_next_action(self, goal: str, transcript, *, evolve: bool):
    system = """You are ZYRA Agent Core, a bounded autonomous coding and document-analysis agent.
Your response MUST start with { and end with }. Return exactly one JSON object. No Markdown fences. No prose.
Allowed actions:
1) {"action":"list_files","path":"."}
2) {"action":"read_file","path":"relative/path.py"}
3) {"action":"search","query":"text","path":"optional/relative/dir"}
4) {"action":"replace_text","path":"relative/file.py","old":"exact text occurring once","new":"replacement text"}
5) {"action":"create_file","path":"relative/new.py","content":"complete text"}
6) {"action":"run_check","check":"syntax|unit|ruff|diff"}
7) {"action":"finish","summary":"what was completed"}
Rules: no shell commands, no network tools, no push/deploy/send, no secrets, no deleting files, no absolute paths.
Prefer inspection before edits. For document-analysis goals, read the named evidence file first, then create the requested report.
Never repeat a failed action unchanged. When complete, return finish. Do not invent tool results."""
    if evolve:
        system += "\nEVOLVE MODE: modifications are limited to zyra*.py, agents/, doug_core/, and tests/."

    user = json.dumps(
        {"goal": goal, "recent_tool_results": list(transcript)[-6:]},
        ensure_ascii=False,
    )
    raw = self._chat(system, user)
    try:
        self._max_json_repairs = 0
        return _robust_extract_json(raw)
    except MissionError:
        self._max_json_repairs = getattr(self, "_max_json_repairs", 0) + 1
        repair_system = """Convert the supplied malformed agent response into exactly one valid JSON object.
Do not add prose or Markdown. Preserve the intended bounded action only.
Allowed action names: list_files, read_file, search, replace_text, create_file, run_check, finish.
If the intent cannot be recovered safely, return {"action":"list_files","path":"."}."""
        repair_user = json.dumps({"malformed_response": raw}, ensure_ascii=False)
        repaired = self._chat(repair_system, repair_user, num_predict=500)
        return _robust_extract_json(repaired)


def _ontology_input(prompt: str = "") -> str:
    while True:
        value = _ORIGINAL_INPUT(prompt)
        stripped = value.strip()
        lowered = stripped.lower()

        if lowered == "/help":
            print("🔐 Ontology: /master-lock /ontology-status /ontology-query <question> /ontology-timeline /ontology-graph /ontology-gaps /ontology-brief")
            return value

        query_command = _ONTOLOGY_COMMANDS.get(lowered)
        query_argument = ""
        if lowered.startswith("/ontology-query "):
            query_command = "query"
            query_argument = stripped[len("/ontology-query "):].strip()
        elif lowered == "/ontology-query":
            print("🔎 Usage: /ontology-query <question>")
            continue

        if query_command:
            try:
                print(run_query_command(os.path.dirname(os.path.abspath(__file__)), query_command, query_argument))
            except OntologyQueryError as exc:
                print(f"🔐 ONTOLOGY QUERY BLOCKED ❌ // {exc}")
                print("   Run /master-lock to regenerate and verify the locked package.")
            except Exception as exc:
                print(f"🔐 ONTOLOGY QUERY ERROR ❌ // {type(exc).__name__}: {exc}")
            continue

        return value


ZyraAgent.__init__ = _max_init
ZyraAgent._extract_json = staticmethod(_robust_extract_json)
ZyraAgent._next_action = _max_next_action
builtins.input = _ontology_input

import zyra_chat as _zyra_chat  # noqa: E402  (patches must be installed before import)

_original_dashboard = _zyra_chat.show_dashboard


def _max_dashboard(*args, **kwargs):
    _original_dashboard(*args, **kwargs)
    print("🔐 Locked ontology query layer: /ontology-status /ontology-query <question> /ontology-timeline /ontology-graph /ontology-gaps /ontology-brief\n")


_zyra_chat.show_dashboard = _max_dashboard
main = _zyra_chat.main


if __name__ == "__main__":
    raise SystemExit(main())
