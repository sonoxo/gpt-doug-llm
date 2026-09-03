from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from va3lm.planner import build_plan
from va3lm.workspace import WorkspaceError, WorkspaceRuntime


class AgentDecisionError(RuntimeError):
    """Raised when a model response cannot be validated as a VA3LM decision."""


@dataclass(frozen=True)
class AgentAction:
    kind: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentDecision:
    summary: str
    done: bool
    actions: tuple[AgentAction, ...]


_ALLOWED_ACTIONS = {
    "inspect_project",
    "list_files",
    "read_file",
    "write_file",
    "delete_file",
    "run_command",
    "restore_backup",
}
_MUTATING_ACTIONS = {"write_file", "delete_file", "run_command", "restore_backup"}
_FILE_MUTATIONS = {"write_file", "delete_file", "restore_backup"}
_MAX_ACTIONS_PER_ROUND = 12


def _allowed_model_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost"}


def _json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise AgentDecisionError("model did not return a JSON object")


def parse_decision(text: str) -> AgentDecision:
    value = _json_object(text)
    summary = value.get("summary", "")
    done = value.get("done", False)
    actions = value.get("actions", [])
    if not isinstance(summary, str):
        raise AgentDecisionError("decision summary must be a string")
    if not isinstance(done, bool):
        raise AgentDecisionError("decision done must be boolean")
    if not isinstance(actions, list):
        raise AgentDecisionError("decision actions must be a list")
    if len(actions) > _MAX_ACTIONS_PER_ROUND:
        raise AgentDecisionError(f"decision exceeds {_MAX_ACTIONS_PER_ROUND} actions")

    normalized: list[AgentAction] = []
    for index, item in enumerate(actions):
        if not isinstance(item, dict):
            raise AgentDecisionError(f"action {index} must be an object")
        kind = item.get("type")
        arguments = item.get("arguments", {})
        if kind not in _ALLOWED_ACTIONS:
            raise AgentDecisionError(f"action {index} has unsupported type: {kind!r}")
        if not isinstance(arguments, dict):
            raise AgentDecisionError(f"action {index} arguments must be an object")
        normalized.append(AgentAction(kind=kind, arguments=arguments))
    return AgentDecision(summary=summary.strip(), done=done, actions=tuple(normalized))


def _assistant_text(body: dict[str, Any]) -> str:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""
    return content.strip() if isinstance(content, str) else ""


def _decision_schema() -> str:
    return (
        '{"summary":"short reason","done":false,"actions":['
        '{"type":"inspect_project","arguments":{}},'
        '{"type":"list_files","arguments":{"path":"."}},'
        '{"type":"read_file","arguments":{"path":"relative/path"}},'
        '{"type":"write_file","arguments":{"path":"relative/path","content":"full UTF-8 content"}},'
        '{"type":"delete_file","arguments":{"path":"relative/path"}},'
        '{"type":"run_command","arguments":{"command":"pytest -q","timeout":60}},'
        '{"type":"restore_backup","arguments":{"backup_id":"id"}}]}'
    )


def _request_model(goal: str, context: dict[str, Any], *, repair_of: str = "") -> str:
    base_url = os.getenv("VA3LM_MODEL_URL", "").rstrip("/")
    if not base_url:
        raise AgentDecisionError("VA3LM_MODEL_URL is not configured")
    if not _allowed_model_url(base_url):
        raise AgentDecisionError("VA3LM_MODEL_URL must point to localhost")
    model = os.getenv("VA3LM_MODEL_NAME", "gpt-doug-llm-max")
    system = (
        "You are the VA3LM coding controller. Return exactly one JSON object and no markdown. "
        "Use only the declared action types. Never claim a file changed, command ran, test passed, preview loaded, "
        "or deployment shipped unless runtime evidence in the supplied context proves it. Prefer inspecting before "
        "editing, use relative workspace paths, keep action batches small, and run an appropriate validation command "
        "after edits. Set done=true only when the requested local coding work is complete and the runtime evidence "
        "supports that conclusion. Publishing/deployment is not available through this executor.\n"
        f"DECISION SCHEMA EXAMPLE:\n{_decision_schema()}"
    )
    if repair_of:
        system += (
            "\nYour previous output was rejected by the validator. Repair only the structure. "
            "Do not invent execution results. Rejected output:\n" + repair_of[:4000]
        )
    user = json.dumps({"goal": goal, "runtimeContext": context}, ensure_ascii=False)
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = os.getenv("VA3LM_MODEL_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:  # nosec B310 - localhost is enforced above
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise AgentDecisionError(f"model request failed: {type(exc).__name__}") from exc
    text = _assistant_text(body)
    if not text:
        raise AgentDecisionError("model response contained no assistant text")
    return text


def request_decision(goal: str, context: dict[str, Any]) -> AgentDecision:
    raw = _request_model(goal, context)
    try:
        return parse_decision(raw)
    except AgentDecisionError as first_error:
        repaired = _request_model(goal, context, repair_of=raw)
        try:
            return parse_decision(repaired)
        except AgentDecisionError as second_error:
            raise AgentDecisionError(
                f"invalid agent decision after one repair attempt: {second_error}"
            ) from first_error


def _execute_action(runtime: WorkspaceRuntime, action: AgentAction, *, approved: bool) -> dict[str, Any]:
    args = action.arguments
    if action.kind == "inspect_project":
        result = runtime.inspect_project()
    elif action.kind == "list_files":
        result = runtime.list_files(str(args.get("path", ".")), limit=int(args.get("limit", 500)))
    elif action.kind == "read_file":
        path = args.get("path")
        if not isinstance(path, str) or not path:
            raise WorkspaceError("read_file requires path")
        result = runtime.read_file(path)
    elif action.kind == "write_file":
        path = args.get("path")
        content = args.get("content")
        if not isinstance(path, str) or not path:
            raise WorkspaceError("write_file requires path")
        if not isinstance(content, str):
            raise WorkspaceError("write_file requires string content")
        result = runtime.write_file(path, content, approved=approved)
    elif action.kind == "delete_file":
        path = args.get("path")
        if not isinstance(path, str) or not path:
            raise WorkspaceError("delete_file requires path")
        result = runtime.delete_file(path, approved=approved)
    elif action.kind == "run_command":
        command = args.get("command")
        if not isinstance(command, (str, list)):
            raise WorkspaceError("run_command requires command")
        result = runtime.run_command(command, timeout=int(args.get("timeout", 60)), approved=approved)
        if result.get("timedOut") or result.get("exitCode") != 0:
            return {
                "type": action.kind,
                "ok": False,
                "state": "FAILED",
                "error": "command did not exit successfully",
                "result": result,
            }
    elif action.kind == "restore_backup":
        backup_id = args.get("backup_id")
        if not isinstance(backup_id, str) or not backup_id:
            raise WorkspaceError("restore_backup requires backup_id")
        result = runtime.restore_backup(backup_id, approved=approved)
    else:  # pragma: no cover - parse_decision rejects this
        raise WorkspaceError(f"unsupported action: {action.kind}")
    return {"type": action.kind, "ok": True, "result": result}


def execute_decision(
    decision: AgentDecision,
    runtime: WorkspaceRuntime,
    *,
    approved: bool = False,
) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    blocked = False
    failed = False
    for action in decision.actions:
        if action.kind in _MUTATING_ACTIONS and not approved:
            evidence.append(
                {
                    "type": action.kind,
                    "ok": False,
                    "state": "BLOCKED_PENDING_APPROVAL",
                    "error": "explicit approval is required",
                }
            )
            blocked = True
            break
        try:
            item = _execute_action(runtime, action, approved=approved)
        except (WorkspaceError, OSError, ValueError, json.JSONDecodeError) as exc:
            item = {"type": action.kind, "ok": False, "state": "FAILED", "error": str(exc)}
        evidence.append(item)
        if not item.get("ok"):
            failed = True
            break
    state = "BLOCKED_PENDING_APPROVAL" if blocked else "FAILED" if failed else "PASSED"
    return {"state": state, "summary": decision.summary, "doneRequested": decision.done, "evidence": evidence}


def _validation_category(command: list[str]) -> str | None:
    if not command:
        return None
    executable = Path(command[0]).name.lower()
    args = [item.lower() for item in command[1:]]
    if executable == "pytest":
        return "test"
    if executable in {"python", "python3"}:
        if len(args) >= 2 and args[0] == "-m" and args[1] == "pytest":
            return "test"
        if len(args) >= 2 and args[0] == "-m" and args[1] == "compileall":
            return "compile"
    if executable == "ruff":
        return "lint"
    if executable == "bandit":
        return "security"
    if executable in {"npm", "pnpm", "yarn"}:
        meaningful = [item for item in args if not item.startswith("-")]
        if not meaningful:
            return None
        if meaningful[0] in {"test", "lint", "build", "typecheck", "check"}:
            return "test" if meaningful[0] == "test" else meaningful[0]
        if meaningful[0] == "run" and len(meaningful) > 1:
            script = meaningful[1]
            if script in {"test", "lint", "build", "typecheck", "check"}:
                return "test" if script == "test" else script
    return None


def _verification_summary(history: list[dict[str, Any]]) -> dict[str, Any]:
    successful_commands: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    latest_file_mutation = -1
    for index, item in enumerate(history):
        if item.get("type") in _FILE_MUTATIONS and item.get("ok"):
            latest_file_mutation = index
        if item.get("type") != "run_command" or not item.get("ok"):
            continue
        result = item.get("result", {})
        if result.get("exitCode") != 0 or result.get("timedOut"):
            continue
        command = result.get("command", [])
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            continue
        successful_commands.append(item)
        category = _validation_category(command)
        if category:
            validations.append({"historyIndex": index, "category": category, "command": command})

    post_mutation_validations = [item for item in validations if item["historyIndex"] > latest_file_mutation]
    test_validations = [item for item in validations if item["category"] == "test"]
    build_validations = [item for item in validations if item["category"] == "build"]
    mutation_verified = latest_file_mutation < 0 or bool(post_mutation_validations)
    return {
        "successfulCommands": len(successful_commands),
        "successfulValidationCommands": len(validations),
        "validationCategories": sorted({item["category"] for item in validations}),
        "testsProven": bool(test_validations),
        "buildProven": bool(build_validations),
        "fileMutationOccurred": latest_file_mutation >= 0,
        "postMutationValidationProven": mutation_verified,
        "deploymentProven": False,
    }


def run_coding_agent(
    goal: str,
    *,
    workspace: str | None = None,
    approved: bool = False,
    max_rounds: int = 4,
) -> dict[str, Any]:
    clean = goal.strip()
    if not clean:
        raise ValueError("goal is required")
    runtime = WorkspaceRuntime(workspace)
    base_url = os.getenv("VA3LM_MODEL_URL", "").strip()
    if not base_url:
        return {
            "state": "MODEL_NOT_CONFIGURED",
            "executed": False,
            "workspace": runtime.status(),
            "plan": build_plan(clean),
            "truth": "No model decision or workspace mutation was executed.",
        }

    rounds = max(1, min(int(max_rounds), 8))
    history: list[dict[str, Any]] = []
    initial = runtime.inspect_project()
    for round_number in range(1, rounds + 1):
        context = {
            "round": round_number,
            "workspace": runtime.status(),
            "project": initial,
            "priorEvidence": history[-20:],
            "approvalGranted": approved,
        }
        try:
            decision = request_decision(clean, context)
        except AgentDecisionError as exc:
            return {
                "state": "INVALID_MODEL_DECISION",
                "executed": bool(history),
                "round": round_number,
                "error": str(exc),
                "workspace": runtime.status(),
                "evidence": history,
                "truth": "The model decision was rejected; VA3LM did not pretend it succeeded.",
            }

        outcome = execute_decision(decision, runtime, approved=approved)
        history.extend(outcome["evidence"])
        if outcome["state"] == "BLOCKED_PENDING_APPROVAL":
            return {
                "state": "BLOCKED_PENDING_APPROVAL",
                "executed": bool(history),
                "round": round_number,
                "workspace": runtime.status(),
                "evidence": history,
                "truth": "Read-only evidence may have been collected; requested mutation was not executed.",
            }
        if outcome["state"] == "FAILED":
            continue
        if decision.done:
            verification = _verification_summary(history)
            if verification["fileMutationOccurred"] and not verification["postMutationValidationProven"]:
                history.append(
                    {
                        "type": "verification_gate",
                        "ok": False,
                        "state": "VALIDATION_REQUIRED",
                        "error": "file mutation occurred without a successful recognized validation command afterward",
                    }
                )
                continue
            if not history:
                return {
                    "state": "COMPLETED_NO_RUNTIME_ACTIONS",
                    "executed": False,
                    "rounds": round_number,
                    "workspace": runtime.status(),
                    "evidence": [],
                    "verification": verification,
                    "truth": "The model declared the task done, but VA3LM executed no runtime action.",
                }
            return {
                "state": "COMPLETED_WITH_RUNTIME_EVIDENCE",
                "executed": True,
                "rounds": round_number,
                "workspace": runtime.status(),
                "evidence": history,
                "verification": verification,
                "truth": (
                    "The listed local runtime actions were observed. Tests/build are only marked proven when a "
                    "recognized validation command exited successfully. Deployment is not claimed."
                ),
            }

    return {
        "state": "ACTION_BUDGET_EXHAUSTED",
        "executed": bool(history),
        "rounds": rounds,
        "workspace": runtime.status(),
        "evidence": history,
        "verification": _verification_summary(history),
        "truth": "VA3LM stopped at the configured round budget instead of looping indefinitely.",
    }
