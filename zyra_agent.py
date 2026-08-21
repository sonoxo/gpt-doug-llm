#!/usr/bin/env python3
"""ZYRA Agent Core: bounded autonomous local coding missions.

The agent can inspect and edit files only inside its repository, using a small
allowlisted tool set. It cannot run arbitrary shell commands, access external
networks as a tool, push/deploy/send data, delete arbitrary files, or recurse
into unbounded sub-agents. Every write is checkpointed and failed missions are
rolled back automatically.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini",
    ".cfg", ".css", ".html", ".js", ".jsx", ".ts", ".tsx", ".sh", ".sql",
}
BLOCKED_PARTS = {".git", ".ssh", ".gnupg", "node_modules", "__pycache__", ".venv", "venv"}
MAX_FILE_BYTES = 160_000
MAX_TOOL_OUTPUT = 12_000
DEFAULT_MAX_STEPS = 8
DEFAULT_MAX_SECONDS = 240
DEFAULT_MAX_MODEL_CALLS = 12


@dataclass
class MissionBudget:
    max_steps: int = DEFAULT_MAX_STEPS
    max_seconds: int = DEFAULT_MAX_SECONDS
    max_model_calls: int = DEFAULT_MAX_MODEL_CALLS


@dataclass
class MissionResult:
    mission_id: str
    goal: str
    mode: str
    status: str
    started_at: float
    finished_at: float | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
    touched_files: list[str] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    rolled_back: bool = False
    summary: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "goal": self.goal,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": round((self.finished_at or time.time()) - self.started_at, 2),
            "steps": self.steps,
            "touched_files": self.touched_files,
            "checks": self.checks,
            "rolled_back": self.rolled_back,
            "summary": self.summary,
            "error": self.error,
        }


class MissionError(RuntimeError):
    pass


class ZyraAgent:
    VERSION = "AGENT/1.0"

    def __init__(
        self,
        root: str | Path,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        budget: MissionBudget | None = None,
        state_dir: str | Path | None = None,
    ):
        self.root = Path(root).resolve()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.budget = budget or MissionBudget()
        self.state_dir = Path(state_dir or Path.home() / ".gpt-doug" / "missions")
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.last_result: MissionResult | None = None
        self.last_checkpoint: Path | None = None

    def _safe_path(self, raw: str, *, must_exist: bool = False, evolve: bool = False) -> Path:
        if not isinstance(raw, str) or not raw.strip():
            raise MissionError("path is required")
        rel = Path(raw.strip())
        if rel.is_absolute():
            raise MissionError("absolute paths are not allowed")
        candidate = (self.root / rel).resolve(strict=False)
        if candidate != self.root and self.root not in candidate.parents:
            raise MissionError("path escapes repository")
        relative = candidate.relative_to(self.root)
        if any(part in BLOCKED_PARTS for part in relative.parts):
            raise MissionError("path targets a protected directory")
        if candidate.exists() and candidate.is_symlink():
            raise MissionError("symlink targets are not writable")
        if must_exist and not candidate.exists():
            raise MissionError("path does not exist")
        if evolve:
            text = relative.as_posix()
            allowed = (
                text.startswith("zyra") and text.endswith(".py")
            ) or text.startswith("agents/") or text.startswith("doug_core/") or text.startswith("tests/")
            if not allowed:
                raise MissionError("evolve mode may modify only ZYRA/agent/core/test code")
        return candidate

    @staticmethod
    def _is_text_file(path: Path) -> bool:
        return path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile", "Makefile", ".env.example", ".gitignore"}

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _checkpoint_dir(self, mission_id: str) -> Path:
        path = self.state_dir / mission_id / "checkpoint"
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        return path

    def _snapshot(self, mission_id: str, path: Path) -> None:
        cp = self._checkpoint_dir(mission_id)
        rel = self._relative(path)
        manifest_path = cp / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            manifest = {}
        if rel in manifest:
            return
        existed = path.exists()
        manifest[rel] = {"existed": existed}
        if existed:
            target = cp / "files" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_path.chmod(0o600)
        self.last_checkpoint = cp

    def rollback(self, mission_id: str | None = None) -> dict[str, Any]:
        cp = self.last_checkpoint if mission_id is None else self.state_dir / mission_id / "checkpoint"
        if cp is None or not cp.exists():
            return {"rolled_back": False, "reason": "no checkpoint available"}
        manifest_path = cp / "manifest.json"
        if not manifest_path.exists():
            return {"rolled_back": False, "reason": "checkpoint manifest missing"}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        restored: list[str] = []
        for rel, meta in manifest.items():
            path = self._safe_path(rel)
            if meta.get("existed"):
                backup = cp / "files" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, path)
            elif path.exists() and path.is_file():
                path.unlink()
            restored.append(rel)
        return {"rolled_back": True, "files": restored}

    def _chat(self, system: str, user: str, *, num_predict: int = 900) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.15, "num_ctx": 8192, "num_predict": num_predict},
        }).encode()
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            body,
            {"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode())
        if data.get("error"):
            raise MissionError(str(data["error"]))
        return ((data.get("message") or {}).get("content") or "").strip()

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        candidates = [raw]
        if "{" in raw and "}" in raw:
            candidates.append(raw[raw.find("{"):raw.rfind("}") + 1])
        for item in candidates:
            try:
                value = json.loads(item)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue
        raise MissionError("agent returned invalid JSON action")

    def preview(self, goal: str, *, evolve: bool = False) -> str:
        system = (
            "You are ZYRA Mission Planner. Produce a short safe coding plan only. "
            "The runtime has bounded repository-only tools: list_files, read_file, search, "
            "replace_text, create_file, run_check, finish. It cannot run arbitrary shell, "
            "network tools, push, deploy, email, purchase, or delete arbitrary files. "
            "Give 3-6 numbered steps and name likely files."
        )
        scope = "Self-evolution scope only: zyra*.py, agents/, doug_core/, tests/." if evolve else "Repository scope."
        return self._chat(system, f"Goal: {goal}\n{scope}", num_predict=500)

    def _next_action(self, goal: str, transcript: list[dict[str, Any]], *, evolve: bool) -> dict[str, Any]:
        system = """You are ZYRA Agent Core, a bounded autonomous coding agent.
Return EXACTLY one JSON object and nothing else.
Allowed actions:
1) {"action":"list_files","path":"."}
2) {"action":"read_file","path":"relative/path.py"}
3) {"action":"search","query":"text","path":"optional/relative/dir"}
4) {"action":"replace_text","path":"relative/file.py","old":"exact text occurring once","new":"replacement text"}
5) {"action":"create_file","path":"relative/new.py","content":"complete text"}
6) {"action":"run_check","check":"syntax|unit|ruff|diff"}
7) {"action":"finish","summary":"what was completed"}
Rules: no shell commands, no network tools, no push/deploy/send, no secrets, no deleting files, no absolute paths.
Prefer inspection before edits. Keep edits minimal. Never repeat a failed action unchanged.
When the goal is complete, return finish. Do not invent tool results."""
        if evolve:
            system += "\nEVOLVE MODE: modifications are limited to zyra*.py, agents/, doug_core/, and tests/."
        compact = transcript[-6:]
        user = json.dumps({"goal": goal, "recent_tool_results": compact}, ensure_ascii=False)
        return self._extract_json(self._chat(system, user))

    def _tool_list_files(self, path: str) -> dict[str, Any]:
        base = self._safe_path(path or ".", must_exist=True)
        if not base.is_dir():
            raise MissionError("list_files path must be a directory")
        files: list[str] = []
        for item in sorted(base.rglob("*")):
            if len(files) >= 250:
                break
            try:
                rel = item.relative_to(self.root)
            except ValueError:
                continue
            if any(part in BLOCKED_PARTS for part in rel.parts):
                continue
            if item.is_file() and self._is_text_file(item):
                files.append(rel.as_posix())
        return {"files": files, "truncated": len(files) >= 250}

    def _tool_read_file(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path, must_exist=True)
        if not target.is_file() or not self._is_text_file(target):
            raise MissionError("read_file supports repository text files only")
        data = target.read_bytes()
        truncated = len(data) > MAX_FILE_BYTES
        if truncated:
            data = data[:MAX_FILE_BYTES]
        return {"path": self._relative(target), "content": data.decode("utf-8", errors="replace"), "truncated": truncated}

    def _tool_search(self, query: str, path: str = ".") -> dict[str, Any]:
        if not query or len(query) > 300:
            raise MissionError("search query must be 1-300 characters")
        base = self._safe_path(path or ".", must_exist=True)
        roots = [base] if base.is_file() else base.rglob("*")
        matches: list[dict[str, Any]] = []
        for item in roots:
            if len(matches) >= 40:
                break
            if not item.is_file() or not self._is_text_file(item):
                continue
            try:
                rel = item.relative_to(self.root)
            except ValueError:
                continue
            if any(part in BLOCKED_PARTS for part in rel.parts):
                continue
            try:
                for number, line in enumerate(item.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if query.lower() in line.lower():
                        matches.append({"path": rel.as_posix(), "line": number, "text": line[:300]})
                        if len(matches) >= 40:
                            break
            except OSError:
                continue
        return {"query": query, "matches": matches, "truncated": len(matches) >= 40}

    def _tool_replace_text(self, mission_id: str, path: str, old: str, new: str, *, evolve: bool) -> dict[str, Any]:
        target = self._safe_path(path, must_exist=True, evolve=evolve)
        if not target.is_file() or not self._is_text_file(target):
            raise MissionError("replace_text supports repository text files only")
        if not old or len(old.encode()) > MAX_FILE_BYTES or len(new.encode()) > MAX_FILE_BYTES:
            raise MissionError("replacement is empty or too large")
        text = target.read_text(encoding="utf-8", errors="strict")
        count = text.count(old)
        if count != 1:
            raise MissionError(f"replace_text requires exactly one match; found {count}")
        updated = text.replace(old, new, 1)
        if len(updated.encode()) > MAX_FILE_BYTES * 4:
            raise MissionError("updated file exceeds mission size limit")
        self._snapshot(mission_id, target)
        target.write_text(updated, encoding="utf-8")
        return {"path": self._relative(target), "changed": True}

    def _tool_create_file(self, mission_id: str, path: str, content: str, *, evolve: bool) -> dict[str, Any]:
        target = self._safe_path(path, evolve=evolve)
        if target.exists():
            raise MissionError("create_file target already exists; use replace_text")
        if not self._is_text_file(target):
            raise MissionError("create_file supports text/code files only")
        encoded = content.encode()
        if not content or len(encoded) > MAX_FILE_BYTES:
            raise MissionError("new file is empty or exceeds mission size limit")
        self._snapshot(mission_id, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": self._relative(target), "created": True}

    def _run_process(self, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
        try:
            proc = subprocess.run(args, cwd=str(self.root), capture_output=True, text=True, timeout=timeout)
            output = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
            return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": output[-MAX_TOOL_OUTPUT:]}
        except FileNotFoundError:
            return {"ok": False, "returncode": 127, "output": f"tool not installed: {args[0]}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "returncode": 124, "output": f"check timed out after {timeout}s"}

    def _tool_run_check(self, check: str, touched: list[str]) -> dict[str, Any]:
        if check == "syntax":
            files = [path for path in touched if path.endswith(".py")]
            args = ["python3", "-m", "py_compile", *files] if files else ["python3", "-m", "compileall", "-q", "zyra.py", "zyra_chat.py", "agents"]
            return {"check": check, **self._run_process(args, timeout=90)}
        if check == "unit":
            candidates = [path for path in ("tests", "agents/tests") if (self.root / path).exists()]
            if not candidates:
                return {"check": check, "ok": True, "returncode": 0, "output": "no standard unit-test directories present"}
            return {"check": check, **self._run_process(["python3", "-m", "pytest", "-q", *candidates], timeout=180)}
        if check == "ruff":
            paths = touched or ["zyra_chat.py", "zyra.py", "agents"]
            return {"check": check, **self._run_process(["ruff", "check", *paths], timeout=90)}
        if check == "diff":
            return {"check": check, **self._run_process(["git", "diff", "--", *touched] if touched else ["git", "diff"], timeout=30)}
        raise MissionError("unknown check")

    def _execute_action(self, mission_id: str, action: dict[str, Any], touched: list[str], *, evolve: bool) -> dict[str, Any]:
        kind = str(action.get("action") or "")
        if kind == "list_files":
            return self._tool_list_files(str(action.get("path") or "."))
        if kind == "read_file":
            return self._tool_read_file(str(action.get("path") or ""))
        if kind == "search":
            return self._tool_search(str(action.get("query") or ""), str(action.get("path") or "."))
        if kind == "replace_text":
            result = self._tool_replace_text(mission_id, str(action.get("path") or ""), str(action.get("old") or ""), str(action.get("new") or ""), evolve=evolve)
            if result["path"] not in touched:
                touched.append(result["path"])
            return result
        if kind == "create_file":
            result = self._tool_create_file(mission_id, str(action.get("path") or ""), str(action.get("content") or ""), evolve=evolve)
            if result["path"] not in touched:
                touched.append(result["path"])
            return result
        if kind == "run_check":
            return self._tool_run_check(str(action.get("check") or ""), touched)
        if kind == "finish":
            return {"finished": True, "summary": str(action.get("summary") or "Mission complete")[:1000]}
        raise MissionError(f"unsupported action: {kind or 'missing'}")

    def run(self, goal: str, *, evolve: bool = False) -> MissionResult:
        if not goal.strip():
            raise MissionError("mission goal is required")
        mission_id = uuid.uuid4().hex[:12]
        mode = "EVOLVE" if evolve else "BUILD"
        result = MissionResult(mission_id, goal.strip(), mode, "RUNNING", time.time())
        self.last_result = result
        transcript: list[dict[str, Any]] = []
        touched: list[str] = []
        model_calls = 0
        repair_round_used = False
        deadline = result.started_at + self.budget.max_seconds

        try:
            for index in range(1, self.budget.max_steps + 1):
                if time.time() > deadline:
                    raise MissionError("mission time budget exceeded")
                if model_calls >= self.budget.max_model_calls:
                    raise MissionError("model-call budget exceeded")
                action = self._next_action(goal, transcript, evolve=evolve)
                model_calls += 1
                tool_result = self._execute_action(mission_id, action, touched, evolve=evolve)
                event = {"step": index, "action": action, "result": tool_result}
                compact = json.loads(json.dumps(event))
                if isinstance(compact.get("result", {}).get("content"), str):
                    compact["result"]["content"] = compact["result"]["content"][:MAX_TOOL_OUTPUT]
                result.steps.append(compact)
                transcript.append(compact)

                if tool_result.get("finished"):
                    syntax = self._tool_run_check("syntax", touched)
                    result.checks.append(syntax)
                    if syntax.get("ok"):
                        result.status = "PASS"
                        result.summary = tool_result.get("summary", "Mission complete")
                        break
                    if not repair_round_used and index < self.budget.max_steps:
                        repair_round_used = True
                        transcript.append({"system_gate": "syntax failed; make one minimal repair then finish", "result": syntax})
                        continue
                    raise MissionError("final syntax gate failed")
            else:
                raise MissionError("step budget exhausted before finish")

        except (MissionError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
            result.status = "FAIL"
            result.error = f"{type(exc).__name__}: {exc}"
            if touched:
                rollback = self.rollback(mission_id)
                result.rolled_back = bool(rollback.get("rolled_back"))
            result.summary = "Mission stopped safely; mission-owned file changes were rolled back." if result.rolled_back else "Mission stopped safely."

        result.touched_files = touched
        result.finished_at = time.time()
        self._persist_result(result)
        return result

    def _persist_result(self, result: MissionResult) -> None:
        path = self.state_dir / result.mission_id / "mission.json"
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)

    def status(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "model": self.model,
            "root": str(self.root),
            "bounded": True,
            "max_steps": self.budget.max_steps,
            "max_seconds": self.budget.max_seconds,
            "max_model_calls": self.budget.max_model_calls,
            "arbitrary_shell": False,
            "network_tools": False,
            "push_deploy_send": False,
            "auto_rollback": True,
            "last_mission": self.last_result.to_dict() if self.last_result else None,
        }


def run_native_agent_test() -> dict[str, Any]:
    """Deterministic self-test with no model call and no network call."""
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="zyra-agent-test-") as tmp:
        root = Path(tmp)
        (root / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        agent = ZyraAgent(root, model="test", base_url="http://127.0.0.1:1", state_dir=root / ".state")
        try:
            agent._safe_path("../escape.py")
            checks["path_escape_blocked"] = False
        except MissionError:
            checks["path_escape_blocked"] = True
        result = agent._tool_replace_text("selftest", "sample.py", "VALUE = 1", "VALUE = 2", evolve=False)
        checks["bounded_replace"] = result.get("changed") is True and (root / "sample.py").read_text() == "VALUE = 2\n"
        rollback = agent.rollback("selftest")
        checks["checkpoint_rollback"] = rollback.get("rolled_back") is True and (root / "sample.py").read_text() == "VALUE = 1\n"
        check = agent._tool_run_check("syntax", ["sample.py"])
        checks["syntax_gate"] = bool(check.get("ok"))
        try:
            agent._execute_action("selftest2", {"action": "shell", "command": "whoami"}, [], evolve=False)
            checks["arbitrary_shell_blocked"] = False
        except MissionError:
            checks["arbitrary_shell_blocked"] = True
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "model_calls": 0,
        "network_calls": 0,
        "arbitrary_shell": False,
        "external_targeting": False,
    }


def print_agent_report(report: MissionResult) -> None:
    icon = "✅" if report.status == "PASS" else "❌"
    print(f"\n🤖 ZYRA AGENT // {report.mode} MISSION {report.mission_id}")
    print(f"🚦 Status: {report.status} {icon}")
    print(f"🧭 Goal: {report.goal}")
    print(f"🪜 Steps: {len(report.steps)} // files touched: {len(report.touched_files)}")
    if report.checks:
        print("🧪 Gates: " + ", ".join(f"{check.get('check')}={'PASS' if check.get('ok') else 'FAIL'}" for check in report.checks))
    if report.rolled_back:
        print("↩️ Auto-rollback: COMPLETE")
    if report.summary:
        print(f"📝 {report.summary}")
    if report.error:
        print(f"⚠️ {report.error}")
    print("🔒 bounded tools // no arbitrary shell // no push/deploy/send // no recursive agent loops\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="ZYRA bounded autonomous agent core")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        report = run_native_agent_test()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 1
    parser.error("use --self-test; interactive missions run through zyra_chat.py")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
