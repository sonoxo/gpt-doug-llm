#!/usr/bin/env python3
"""Responsive local-only ZYRA terminal chat for GPT-DOUG-LLM."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from zyra import Zyra
from zyra_agent import ZyraAgent, print_agent_report, run_native_agent_test
from zyra_laser import ZyraLaser, run_native_laser_test
from zyra_self_heal import load_runtime_env, print_heal_report, run_self_heal

load_runtime_env()

ROOT = Path(__file__).resolve().parent
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
REQUESTED_MODEL = os.environ.get("ZYRA_MODEL") or os.environ.get("OLLAMA_MODEL") or os.environ.get("GPT_DOUG_FAST_MODEL") or "gpt-doug"
TIMEOUT = float(os.environ.get("ZYRA_TIMEOUT", "90"))
MAX_TURNS = max(2, int(os.environ.get("ZYRA_MAX_TURNS", "10")))
CONFIG_DIR = Path.home() / ".config" / "gpt-doug"
AUTOSTART_FLAG = CONFIG_DIR / "zyra-autostart"

SYSTEM = """You are ZYRA, the responsive local conversational assistant for GPT-DOUG-LLM.
Answer ordinary user messages directly and naturally. Harmless fictional games and simulations are allowed.
Never reply with PASS or BLOCKED unless the deterministic local policy layer actually produced that status.
Do not claim background work, consciousness, government authority, or access you do not have.
The fleet means local agent/orchestration code in this repository, not a physical location.
Keep one user message to one bounded model response. No recursive self-calls or autonomous loops.
ZYRA self-heal may repair only its own local runtime provider/model configuration and restart Ollama.
ZYRA LASER is a defensive circuit breaker for ZYRA's own model path. It never retaliates, scans, exploits, or attacks another system.
ZYRA Agent Core may autonomously inspect and edit files only inside its own repository with checkpointing, hard budgets, allowlisted tools, syntax gates, and automatic rollback. It cannot use arbitrary shell, push/deploy/send, or use network tools.
Be concise by default. For terminal questions, prefer one tested command or one short next step.
"""


def _request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    return urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )


def _json_request(path, body=None, timeout=None):
    with urllib.request.urlopen(_request(path, body), timeout=timeout or TIMEOUT) as response:
        return json.loads(response.read().decode())


def installed_models():
    return [item.get("name", "") for item in _json_request("/api/tags", timeout=4).get("models", []) if item.get("name")]


def choose_model(models):
    if not models:
        raise RuntimeError("No Ollama models are installed.")
    for wanted in (os.environ.get("OLLAMA_MODEL", ""), REQUESTED_MODEL, "gpt-doug", "qwen2.5-coder", "llama3", "qwen2.5"):
        if not wanted:
            continue
        for name in models:
            if name == wanted or name.startswith(wanted + ":"):
                return name
    return models[0]


def git_run(*args):
    try:
        result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=4)
        return result.returncode, (result.stdout.strip() or result.stderr.strip())
    except Exception:
        return 1, "unavailable"


def print_laser_status(laser):
    status = laser.status()
    state = f"LOCKED {status['lock_remaining']}s" if status["locked"] else "ARMED"
    print(f"🔴 LASER {status['version']}: {state}")
    print(f"   strikes {status['strikes']}/{status['threshold']} in {status['window_seconds']}s // incidents {status['incidents']}")
    if status["last_reason"]:
        print(f"   last intercept: {status['last_reason']} // fp {status['last_fingerprint']}")


def print_agent_status(agent):
    status = agent.status()
    last = status.get("last_mission")
    mission = "NONE" if not last else f"{last['status']} {last['mission_id']}"
    print(f"🤖 Agent {status['version']}: ARMED")
    print(f"   mission budget: {status['max_steps']} steps / {status['max_seconds']}s / {status['max_model_calls']} model calls")
    print(f"   last mission: {mission}")
    print("   arbitrary shell OFF // network tools OFF // push/deploy/send OFF // auto-rollback ON")


def show_dashboard(model, mode, laser, agent, heal_report=None):
    branch_code, branch = git_run("branch", "--show-current")
    status_code, status_text = git_run("status", "--short")
    changed = len([line for line in status_text.splitlines() if line.strip()]) if status_code == 0 else "?"
    heal_state = "NOT RUN" if heal_report is None else ("HEALTHY" if heal_report.get("healthy") else "ATTENTION")
    laser_status = laser.status()
    laser_state = f"LOCKED {laser_status['lock_remaining']}s" if laser_status["locked"] else "ARMED"
    last = agent.status().get("last_mission")
    agent_state = "ARMED" if not last else f"ARMED / LAST {last['status']}"
    print("\n🟣 ZYRA // AGENTIC GPT-DOUG-LLM")
    print(f"🧠 Model: {model}")
    print(f"⚡ Mode: {mode.upper()}")
    print(f"🌿 Branch: {branch if branch_code == 0 and branch else 'unknown'}")
    print(f"📝 Working tree: {changed} changed")
    print(f"🚀 Default terminal: {'ON' if AUTOSTART_FLAG.exists() else 'OFF'}")
    print(f"🩺 Self-Heal: {heal_state} // bounded runtime repair")
    print(f"🔴 Native LASER: {laser_state} // local circuit breaker")
    print(f"🤖 Agent Core: {agent_state} // checkpoints + rollback + hard budgets")
    print("🛡️ Repository-only autonomy // no arbitrary shell // no external targeting")
    print("⌨️  /help /status /fleet /xunia /heal /laser-test /agent-test /agent-status /plan <goal> /do <goal> /evolve <goal> /mission-status /undo /fast /balanced /default-on /default-off /clear /quit\n")


def show_fleet():
    agents = sorted(path.name for path in (ROOT / "agents").glob("*.py") if not path.name.startswith("__"))
    workers_dir = ROOT / "workers"
    workers = sorted(path.name for path in workers_dir.rglob("*.py")) if workers_dir.exists() else []
    print(f"🤖 Fleet inventory: {len(agents)} agent modules + {len(workers)} worker modules")
    if agents:
        print("   agents:", ", ".join(agents[:12]))
    if workers:
        print("   workers:", ", ".join(workers[:12]))


def stream_chat(model, messages, mode):
    options = {"temperature": 0.25, "num_ctx": 4096, "num_predict": 256} if mode == "fast" else {"temperature": 0.35, "num_ctx": 8192, "num_predict": 512}
    body = {"model": model, "messages": messages, "stream": True, "keep_alive": "30m", "options": options}
    chunks = []
    done_reason = ""
    with urllib.request.urlopen(_request("/api/chat", body), timeout=TIMEOUT) as response:
        for raw in response:
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            event = json.loads(line)
            if event.get("error"):
                raise RuntimeError(str(event["error"]))
            text = (event.get("message") or {}).get("content", "")
            if text:
                print(text, end="", flush=True)
                chunks.append(text)
            if event.get("done"):
                done_reason = str(event.get("done_reason") or "")
                break
    answer = "".join(chunks).strip()
    if not answer:
        raise RuntimeError(done_reason or "empty model response")
    print()
    return answer


def _mission_goal(prompt: str, prefix: str) -> str:
    return prompt[len(prefix):].strip()


def main():
    zyra = Zyra()
    laser = ZyraLaser()
    mode = os.environ.get("ZYRA_MODE", "fast").lower()
    mode = mode if mode in {"fast", "balanced"} else "fast"
    heal_report = run_self_heal(start_ollama=True, persist=True)
    try:
        model = choose_model(installed_models())
    except Exception:
        print_heal_report(heal_report)
        print("ZYRA OFFLINE // local model chat is unavailable after self-heal. Security policy remains intact.")
        return 1

    agent = ZyraAgent(ROOT, model=model, base_url=BASE_URL)
    show_dashboard(model, mode, laser, agent, heal_report)
    history = [{"role": "system", "content": SYSTEM}]

    while True:
        try:
            prompt = input("ZYRA > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nZYRA // session closed")
            return 0
        if not prompt:
            continue
        command = prompt.lower()

        if command in {"/quit", "/exit"}:
            return 0
        if command == "/help":
            print("/status /fleet /xunia /heal /heal-status /laser-test /laser-status /laser-reset /agent-test /agent-status /plan <goal> /do <goal> /evolve <goal> /mission-status /undo /fast /balanced /default-on /default-off /clear /quit")
            continue
        if command in {"/status", "/xunia", "/dashboard"}:
            show_dashboard(model, mode, laser, agent, heal_report)
            continue
        if command == "/fleet":
            show_fleet()
            continue
        if command == "/heal":
            heal_report = run_self_heal(start_ollama=True, persist=True)
            print_heal_report(heal_report)
            if heal_report.get("healthy"):
                try:
                    model = choose_model(installed_models())
                    agent.model = model
                except Exception:
                    pass
            continue
        if command == "/heal-status":
            print_heal_report(heal_report)
            continue
        if command == "/laser-test":
            report = run_native_laser_test()
            print("\n🔴 ZYRA NATIVE LASER SELF-TEST")
            for name, ok in report["checks"].items():
                print(f"   {'✅' if ok else '❌'} {name}")
            print("🧪 Payload execution: OFF // external targeting: OFF")
            print(f"🚦 Result: {'PASS ✅' if report['passed'] else 'FAIL ❌'}\n")
            continue
        if command == "/laser-status":
            print_laser_status(laser)
            continue
        if command == "/laser-reset":
            laser.reset()
            print("🔴 LASER reset complete. ZYRA policy remains active.")
            continue
        if command == "/agent-test":
            report = run_native_agent_test()
            print("\n🤖 ZYRA AGENT NATIVE SELF-TEST")
            for name, ok in report["checks"].items():
                print(f"   {'✅' if ok else '❌'} {name}")
            print(f"🚦 Result: {'PASS ✅' if report['passed'] else 'FAIL ❌'} // model calls 0 // network calls 0\n")
            continue
        if command == "/agent-status":
            print_agent_status(agent)
            continue
        if command == "/mission-status":
            if agent.last_result is None:
                print("🤖 No agent mission has run in this session.")
            else:
                print_agent_report(agent.last_result)
            continue
        if command == "/undo":
            if agent.last_result is None:
                print("↩️ No mission checkpoint available in this session.")
            else:
                report = agent.rollback(agent.last_result.mission_id)
                if report.get("rolled_back"):
                    print("↩️ Mission rollback complete: " + ", ".join(report.get("files", [])))
                else:
                    print("↩️ Rollback unavailable: " + str(report.get("reason", "unknown")))
            continue

        if command.startswith("/plan ") or command.startswith("/do ") or command.startswith("/evolve "):
            if laser.is_locked():
                status = laser.status()
                print(f"🔴 LASER LOCK // agent model path isolated for {status['lock_remaining']}s.")
                continue
            prefix = "/plan " if command.startswith("/plan ") else ("/do " if command.startswith("/do ") else "/evolve ")
            goal = _mission_goal(prompt, prefix)
            verdict = zyra.inspect(goal, "input")
            if not verdict.allowed:
                decision = laser.observe(verdict, "input")
                print("🔴 LASER " + decision.action + " // " + "; ".join(verdict.reasons))
                continue
            if prefix != "/plan " and verdict.requires_approval:
                print("🤖 AGENT STOP // this mission requests a consequential/external action. Agent Core does not push, deploy, send, purchase, transfer, delete, or run network tools.")
                continue
            safe_goal = verdict.text
            if prefix == "/plan ":
                try:
                    print("\n🧭 ZYRA MISSION PLAN")
                    print(agent.preview(safe_goal, evolve=False))
                    print()
                except Exception as exc:
                    print(f"🤖 PLAN ERROR // {type(exc).__name__}: {exc}")
                continue
            evolve = prefix == "/evolve "
            print(f"🤖 ZYRA {'EVOLVE' if evolve else 'BUILD'} MISSION // bounded autonomous run starting…")
            mission = agent.run(safe_goal, evolve=evolve)
            print_agent_report(mission)
            continue

        if command == "/fast":
            mode = "fast"
            print("⚡ FAST mode enabled.")
            continue
        if command == "/balanced":
            mode = "balanced"
            print("🧠 BALANCED mode enabled.")
            continue
        if command == "/default-on":
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            AUTOSTART_FLAG.touch()
            print("🚀 ZYRA will open automatically in new interactive Terminal windows.")
            continue
        if command == "/default-off":
            AUTOSTART_FLAG.unlink(missing_ok=True)
            print("🛑 ZYRA terminal autostart disabled.")
            continue
        if command == "/clear":
            history = [{"role": "system", "content": SYSTEM}]
            print("🧹 Conversation memory cleared.")
            continue

        if laser.is_locked():
            status = laser.status()
            print(f"🔴 LASER LOCK // ZYRA model path isolated for {status['lock_remaining']}s. Use /laser-status or /laser-reset.")
            continue

        verdict = zyra.inspect(prompt, "input")
        if not verdict.allowed:
            decision = laser.observe(verdict, "input")
            print("🔴 LASER " + decision.action + " // " + "; ".join(verdict.reasons))
            if decision.engaged:
                history = [{"role": "system", "content": SYSTEM}]
                print(f"🔒 ZYRA model path isolated for {decision.lock_remaining}s; conversation context quarantined.")
            continue

        history.append({"role": "user", "content": verdict.text})
        request_history = history[:1] + history[-(MAX_TURNS * 2):]
        print("🧠 ZYRA thinking…", flush=True)
        try:
            answer = stream_chat(model, request_history, mode)
        except (urllib.error.URLError, TimeoutError):
            print("🩺 ZYRA detected local model failure // running one self-heal pass…")
            heal_report = run_self_heal(start_ollama=True, persist=True)
            if not heal_report.get("healthy"):
                print_heal_report(heal_report)
                continue
            try:
                model = choose_model(installed_models())
                agent.model = model
                answer = stream_chat(model, request_history, mode)
            except Exception as exc:
                print(f"ZYRA ERROR // recovery stopped cleanly: {type(exc).__name__}: {exc}")
                continue
        except urllib.error.HTTPError as exc:
            print(f"ZYRA ERROR // Ollama HTTP {exc.code}")
            continue
        except Exception as exc:
            print(f"ZYRA ERROR // {type(exc).__name__}: {exc}")
            continue

        output = zyra.inspect(answer, "output")
        if not output.allowed:
            decision = laser.observe(output, "output")
            history = [{"role": "system", "content": SYSTEM}]
            print("🔴 LASER ISOLATE // blocked model output; conversation context quarantined.")
            print(f"🔒 ZYRA model path isolated for {decision.lock_remaining}s.")
            continue
        if output.text != answer:
            print("ZYRA // output sanitized by policy")
        history.append({"role": "assistant", "content": output.text})


if __name__ == "__main__":
    raise SystemExit(main())
