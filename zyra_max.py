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
"""
from __future__ import annotations

import ast
import json
import os
import re

from zyra_agent import MissionBudget, MissionError, ZyraAgent


_ORIGINAL_INIT = ZyraAgent.__init__
_ALLOWED_ACTIONS = {
    "list_files",
    "read_file",
    "search",
    "replace_text",
    "create_file",
    "run_check",
    "finish",
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


ZyraAgent.__init__ = _max_init
ZyraAgent._extract_json = staticmethod(_robust_extract_json)
ZyraAgent._next_action = _max_next_action

from zyra_chat import main  # noqa: E402  (patch must be installed before import)


if __name__ == "__main__":
    raise SystemExit(main())
