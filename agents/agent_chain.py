#!/usr/bin/env python3
"""Autonomous multi-agent task chain.

Given one task in plain language, runs it through three specialized local
models with bounded recursion and a final reviewer.

Provider configuration is self-healing for the local runtime: legacy
LLM_PROVIDER=ollama is normalized to GPT_DOUG_PROVIDER=ollama, persisted ZYRA
runtime settings are loaded, and requested role models fall back to an
installed Ollama model when needed.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid

from zyra_self_heal import load_runtime_env

# Load ZYRA's persisted runtime settings before llm_backend creates its
# module-level provider object. This fixes the common case where the shell
# used LLM_PROVIDER=ollama while llm_backend expected GPT_DOUG_PROVIDER.
load_runtime_env()
if not os.environ.get("GPT_DOUG_PROVIDER", "").strip():
    alias = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if alias:
        os.environ["GPT_DOUG_PROVIDER"] = alias
    elif "11434" in os.environ.get("OPENAI_API_BASE", ""):
        os.environ["GPT_DOUG_PROVIDER"] = "ollama"

from agents import llm_backend
from agents import ontology

PLANNER_MODEL = os.environ.get("AGENT_PLANNER_MODEL", "gemma3")
EXECUTOR_MODEL = os.environ.get("AGENT_EXECUTOR_MODEL", "qwen2.5-coder:7b")
REVIEWER_MODEL = os.environ.get("AGENT_REVIEWER_MODEL", "qwen2.5-coder:7b")

OPTIONS = {"temperature": 0.4, "num_ctx": 8192}

RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

MAX_SPAWN_DEPTH = int(os.environ.get("AGENT_MAX_SPAWN_DEPTH", "4"))
MAX_TOTAL_SUBAGENTS = int(os.environ.get("AGENT_MAX_TOTAL_SUBAGENTS", "25"))
SPAWN_MARKER = "SPAWN_SUBAGENT:"

DEPTH_TIER_NAMES = ["chain", "micro", "meso", "nano", "neo"]


def depth_tier(depth):
    if depth < len(DEPTH_TIER_NAMES):
        return DEPTH_TIER_NAMES[depth]
    return f"tier-{depth}"


def _model_matches(name: str, wanted: str) -> bool:
    return name == wanted or name.startswith(wanted + ":")


def _resolve_model(requested: str) -> str:
    """Resolve a requested role model to one that the active provider can use.

    For Ollama, if the requested model is missing, fall back to the healed
    runtime model or the first installed local model instead of failing the
    whole chain. Other providers keep the requested model unchanged.
    """
    try:
        state = llm_backend.health()
    except Exception:
        return requested
    provider = str(state.get("provider") or state.get("backend") or "").lower()
    if provider != "ollama":
        return requested
    models = [m for m in state.get("models", []) if m]
    if not models:
        return requested
    for name in models:
        if _model_matches(name, requested):
            return name
    for fallback in (
        os.environ.get("OLLAMA_MODEL", ""),
        os.environ.get("GPT_DOUG_MODEL", ""),
        "gpt-doug",
        "qwen2.5-coder:7b",
        "llama3",
    ):
        if not fallback:
            continue
        for name in models:
            if _model_matches(name, fallback):
                return name
    return models[0]


def _call(model, system, user):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    used_model = _resolve_model(model)
    result = llm_backend.chat_once(messages, used_model, OPTIONS)
    if result.get("error"):
        error = result.get("error")
        detail = (result.get("message") or {}).get("content", "")
        raise RuntimeError(f"AI provider error: {error}: {detail}")
    return result.get("message", {}).get("content", "").strip()


def _plan_ontology(task):
    system = (
        "You are a planning agent using a formal task ontology. "
        + ontology.TASK_GRAPH_SCHEMA_DESCRIPTION
    )
    raw = _call(PLANNER_MODEL, system, task)
    graph_json = ontology.extract_json_object(raw)
    try:
        graph = json.loads(graph_json)
    except json.JSONDecodeError as err:
        raise ontology.OntologyError(f"invalid JSON: {err}") from err
    return ontology.validate_task_graph(graph), raw


def _plan_legacy(task):
    system = (
        "You are a planning agent. Break the given task into 3-6 concrete, "
        "numbered steps that another agent can execute one at a time. Output "
        "ONLY the numbered list, no preamble, no explanation."
    )
    plan_text = _call(PLANNER_MODEL, system, task)
    step_re = re.compile(r"^\d+[.)]\s")
    lines = []
    for line in plan_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if step_re.match(line):
            lines.append(line)
        elif lines:
            break
    steps = [
        {
            "id": f"s{i}",
            "description": line,
            "assigned_agent": "executor",
            "produces": "",
            "constraints": [],
            "requires_subagent": False,
        }
        for i, line in enumerate(lines, 1)
    ]
    if not steps:
        # A model may occasionally ignore numbered-list formatting. Keep the
        # chain bounded and useful by turning the task itself into one step.
        steps = [{
            "id": "s1",
            "description": task,
            "assigned_agent": "executor",
            "produces": "",
            "constraints": [],
            "requires_subagent": False,
        }]
    return {"task": task, "steps": steps}, plan_text


def _execute_step(task, step, prior_context, can_spawn):
    constraints = step.get("constraints") or []
    constraints_text = (
        "\n\nThis step's output must satisfy: " + "; ".join(constraints)
        if constraints else ""
    )
    hint = (
        "\n\nThis step was flagged at planning time as complex enough to warrant its own sub-agent chain."
        if step.get("requires_subagent") else ""
    )
    spawn_instruction = (
        f"\n\nIf this step is itself complex enough to deserve its own "
        f"plan->execute->review sub-agent chain (not just a normal answer), "
        f"respond with ONLY a single line: {SPAWN_MARKER} <clear description of "
        f"the sub-task>. Use this rarely, only for genuinely complex nested "
        f"work — most steps should just be done directly."
        if can_spawn else ""
    )
    system = (
        "You are an execution agent completing one step of a larger task. "
        "Do the work for this step directly and concretely (write the code, "
        "text, or answer — don't describe what you would do, actually do it). "
        "Keep your output focused on this step only."
        + constraints_text + hint + spawn_instruction
    )
    description = step["description"]
    user = f"Overall task: {task}\n\nPrior steps completed:\n{prior_context}\n\nCurrent step to complete:\n{description}"
    return _call(EXECUTOR_MODEL, system, user)


def _parse_review_json(raw: str):
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        value = json.loads(raw[start:end])
        if not isinstance(value, dict):
            return None
        value.setdefault("passed", None)
        value.setdefault("issues", [])
        value.setdefault("summary", "")
        return value
    except (ValueError, json.JSONDecodeError):
        return None


def _review(task, transcript, task_graph=None):
    constraint_lines = []
    if task_graph:
        for step in task_graph.get("steps", []):
            for c in step.get("constraints") or []:
                constraint_lines.append(f"- [{step['id']}] {c}")
    constraints_block = (
        "\n\nThe task's ontology defined these constraints that must all be satisfied:\n" + "\n".join(constraint_lines)
        if constraint_lines else ""
    )
    system = (
        "You are a reviewing agent. Given the original task and the full "
        "transcript of steps taken, judge whether the task was actually "
        "completed correctly." + constraints_block + " Respond with a JSON object only: "
        '{"passed": true/false, "issues": ["..."], "summary": "..."}'
    )
    user = f"Task: {task}\n\nTranscript:\n{transcript}"
    raw = _call(REVIEWER_MODEL, system, user)
    parsed = _parse_review_json(raw)
    if parsed is not None:
        return parsed

    # One bounded repair pass for malformed reviewer output. This directly
    # fixes the repeated "reviewer output was not valid JSON" failure without
    # introducing an open-ended retry loop.
    repair_system = (
        "Convert the supplied reviewer text into exactly one valid JSON object "
        "with keys passed (boolean), issues (array of strings), and summary "
        "(string). Output JSON only. Do not use markdown."
    )
    repaired_raw = _call(REVIEWER_MODEL, repair_system, raw[:4000])
    repaired = _parse_review_json(repaired_raw)
    if repaired is not None:
        repaired["self_repaired_review"] = True
        return repaired

    return {
        "passed": None,
        "issues": ["reviewer output was not valid JSON after one repair pass"],
        "summary": raw[:500],
    }


def run(task, on_event=None, _depth=0, _budget=None):
    """Runs the full plan -> execute -> review chain.

    _depth and _budget are internal and enforce hard ceilings on nested
    sub-agents so self-repair can never become a recursive runaway loop.
    """
    if _budget is None:
        _budget = {"spawned": 0}

    run_id = uuid.uuid4().hex[:12]
    started = time.time()
    trace = {"run_id": run_id, "task": task, "started_at": started, "depth": _depth, "tier": depth_tier(_depth), "events": []}

    def emit(event):
        event["ts"] = time.time()
        trace["events"].append(event)
        if on_event:
            on_event(event)

    emit({"stage": "plan_start", "model": _resolve_model(PLANNER_MODEL)})
    try:
        task_graph, plan_text = _plan_ontology(task)
        plan_mode = "ontology"
    except ontology.OntologyError as err:
        task_graph, plan_text = _plan_legacy(task)
        plan_mode = f"legacy_fallback ({err})"
    steps = task_graph["steps"]
    step_descriptions = [s["description"] for s in steps]
    emit({
        "stage": "plan_done", "model": _resolve_model(PLANNER_MODEL), "output": plan_text,
        "steps": step_descriptions, "plan_mode": plan_mode, "task_graph": task_graph,
    })

    can_spawn = _depth < MAX_SPAWN_DEPTH and _budget["spawned"] < MAX_TOTAL_SUBAGENTS

    transcript_parts = []
    for i, step in enumerate(steps, 1):
        prior = "\n\n".join(transcript_parts) or "(none yet)"
        emit({"stage": "execute_start", "model": _resolve_model(EXECUTOR_MODEL), "step_index": i, "step": step["description"]})
        output = _execute_step(task, step, prior, can_spawn)

        if can_spawn and output.strip().startswith(SPAWN_MARKER):
            subtask = output.strip()[len(SPAWN_MARKER):].strip()
            _budget["spawned"] += 1
            emit({"stage": "subagent_spawn", "step_index": i, "subtask": subtask, "depth": _depth + 1, "tier": depth_tier(_depth + 1)})
            sub_trace = run(subtask, on_event=on_event, _depth=_depth + 1, _budget=_budget)
            output = f"[sub-agent {sub_trace['run_id']}] {sub_trace.get('transcript', '')}"
            emit({"stage": "subagent_done", "step_index": i, "sub_run_id": sub_trace["run_id"], "passed": (sub_trace.get("review") or {}).get("passed")})
            can_spawn = _depth < MAX_SPAWN_DEPTH and _budget["spawned"] < MAX_TOTAL_SUBAGENTS

        transcript_parts.append(f"Step {i}: {step['description']}\nResult: {output}")
        emit({"stage": "execute_done", "model": _resolve_model(EXECUTOR_MODEL), "step_index": i, "step": step["description"], "output": output})

    full_transcript = "\n\n".join(transcript_parts)
    emit({"stage": "review_start", "model": _resolve_model(REVIEWER_MODEL)})
    review = _review(task, full_transcript, task_graph)
    emit({"stage": "review_done", "model": _resolve_model(REVIEWER_MODEL), "review": review})

    trace["finished_at"] = time.time()
    trace["duration_s"] = round(trace["finished_at"] - started, 2)
    trace["plan_mode"] = plan_mode
    trace["task_graph"] = task_graph
    trace["plan"] = step_descriptions
    trace["transcript"] = full_transcript
    trace["review"] = review

    with open(os.path.join(RUNS_DIR, f"{run_id}.json"), "w") as f:
        json.dump(trace, f, indent=2)

    return trace


if __name__ == "__main__":
    import sys
    task_arg = " ".join(sys.argv[1:]) or "Write a haiku about autonomous AI agents."
    try:
        result = run(task_arg, on_event=lambda e: print(f"[{e['stage']}]"))
        print(json.dumps(result["review"], indent=2))
    except Exception as exc:
        print(json.dumps({
            "passed": False,
            "issues": [f"{type(exc).__name__}: {exc}"],
            "summary": "Agent chain stopped cleanly; run `python3 zyra_self_heal.py` then retry.",
        }, indent=2))
        raise SystemExit(1)
