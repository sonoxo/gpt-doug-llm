#!/usr/bin/env python3
"""GPT-Doug MAX terminal orchestrator.

This is the human-facing command shell that composes the project's existing
capabilities instead of replacing them:

* agents.llm_backend -> provider-neutral reasoning (XUNIA/ASTRA/Ollama/etc.)
* xunia_godis        -> local RAG + Ollama profiles
* zyra_agent         -> bounded repository coding missions
* palantir_terminal  -> Foundry/Ontology grounded commands with approval gates
* workers.revenue_swarm -> bounded draft-only multi-agent workflows
* local git/system probes -> operator visibility

The shell never silently turns natural-language text into an arbitrary shell
command. Explicit shell commands use a '$ ' prefix. Read-only commands may run
immediately; mutating commands require a short-lived arm plus confirmation.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
STATE_DIR = Path.home() / ".gpt-doug"
STATE_FILE = STATE_DIR / "max-shell-state.json"

CYAN = "\033[38;5;51m"
MAGENTA = "\033[38;5;201m"
GREEN = "\033[38;5;154m"
YELLOW = "\033[38;5;220m"
RED = "\033[38;5;196m"
DIM = "\033[2m"
RESET = "\033[0m"

READ_ONLY_COMMANDS = {
    "pwd", "ls", "cat", "head", "tail", "grep", "rg", "which", "type", "printenv",
    "uname", "whoami", "id", "date", "df", "du", "ps", "pgrep", "git", "ollama",
}
READ_ONLY_GIT = {
    "status", "diff", "log", "show", "rev-parse", "ls-files", "grep", "describe",
}
READ_ONLY_OLLAMA = {"list", "ps", "show"}
MUTATION_TOKENS = {
    "rm", "mv", "cp", "chmod", "chown", "mkdir", "touch", "tee", "dd", "kill",
    "pkill", "launchctl", "brew", "pip", "pip3", "install", "uninstall", "push",
    "commit", "merge", "rebase", "reset", "checkout", "switch", "restore", "add",
    "apply", "delete", "create", "deploy", "publish", "release", "write", "POST",
    "PUT", "PATCH", "DELETE",
}
SHELL_META = {"|", ">", ">>", "<", "<<", ";", "&&", "||", "`", "$("}


@dataclass
class VisualState:
    state: str = "IDLE"
    detail: str = "ready"
    voice: bool = True
    armed: bool = False
    provider: str = "unknown"
    model: str = "unknown"
    ts: float = 0.0


class StateBus:
    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.state = VisualState(ts=time.time())
        self.write()

    def set(self, state: str, detail: str = "", **updates: Any) -> None:
        with self._lock:
            self.state.state = state.upper()
            if detail:
                self.state.detail = detail[:240]
            for key, value in updates.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
            self.state.ts = time.time()
            self._write_unlocked()

    def write(self) -> None:
        with self._lock:
            self._write_unlocked()

    def _write_unlocked(self) -> None:
        payload = asdict(self.state)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)


class VoiceEngine:
    def __init__(self, enabled: bool = True, rate: int = 190):
        self.enabled = enabled
        self.rate = rate
        self._proc: subprocess.Popen[str] | None = None

    @property
    def available(self) -> bool:
        return shutil.which("say") is not None

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def speak(self, text: str, *, block: bool = False) -> None:
        if not self.enabled or not self.available or not text.strip():
            return
        self.stop()
        voice_name = os.getenv("GPT_DOUG_VOICE_NAME", "Alex").strip() or "Alex"
        self._proc = subprocess.Popen(
            ["say", "-v", voice_name, "-r", str(self.rate), text[:4000]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if block:
            self._proc.wait()

    def transcribe_local(self, seconds: float = 5.0) -> str:
        """Local microphone transcription using optional sounddevice + faster-whisper.

        No cloud speech service is used here. The optional dependency path is
        deliberately explicit so audio is not silently sent to a third party.
        """
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "Local mic needs optional packages: pip install sounddevice numpy faster-whisper"
            ) from exc

        sample_rate = 16000
        frames = int(max(1.0, min(seconds, 30.0)) * sample_rate)
        audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
        sd.wait()
        audio = np.squeeze(audio)

        import wave

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            wav_path = Path(handle.name)
        try:
            pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("int16")
            with wave.open(str(wav_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(pcm.tobytes())
            model_name = os.getenv("GPT_DOUG_WHISPER_MODEL", "base.en")
            model = WhisperModel(model_name, device="auto", compute_type="int8")
            segments, _info = model.transcribe(str(wav_path), beam_size=1)
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            wav_path.unlink(missing_ok=True)


class ArmGate:
    def __init__(self):
        self.until = 0.0

    def arm(self, seconds: int = 300) -> int:
        seconds = max(15, min(int(seconds), 1800))
        self.until = time.time() + seconds
        return seconds

    def disarm(self) -> None:
        self.until = 0.0

    def active(self) -> bool:
        return time.time() < self.until

    def remaining(self) -> int:
        return max(0, int(self.until - time.time()))


def run_capture(argv: list[str], cwd: Path = ROOT, timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip()
    except FileNotFoundError:
        return 127, f"command not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"


def git_snapshot() -> dict[str, Any]:
    code, branch = run_capture(["git", "branch", "--show-current"], timeout=3)
    _, status = run_capture(["git", "status", "--short"], timeout=3)
    _, remote = run_capture(["git", "remote", "-v"], timeout=3)
    _, sha = run_capture(["git", "rev-parse", "--short", "HEAD"], timeout=3)
    return {
        "branch": branch if code == 0 else "not-a-repo",
        "sha": sha,
        "dirty": bool(status),
        "changes": status.splitlines()[:30] if status else [],
        "remote": remote.splitlines()[:6] if remote else [],
    }


def system_snapshot() -> dict[str, Any]:
    disk = shutil.disk_usage(ROOT)
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cwd": str(Path.cwd()),
        "load": [round(x, 2) for x in load],
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        "ollama": bool(shutil.which("ollama")),
        "gh": bool(shutil.which("gh")),
        "say": bool(shutil.which("say")),
    }


def shell_is_read_only(command: str) -> bool:
    if any(token in command for token in SHELL_META):
        return False
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return True
    if any(part in MUTATION_TOKENS for part in parts):
        return False
    tool = Path(parts[0]).name
    if tool not in READ_ONLY_COMMANDS:
        return False
    if tool == "git":
        if len(parts) < 2:
            return False
        if parts[1] in READ_ONLY_GIT:
            return True
        if parts[1] == "branch":
            return parts[2:] == ["--show-current"]
        if parts[1] == "remote":
            return parts[2:] in ([], ["-v"], ["show"])
        return False
    if tool == "ollama":
        return len(parts) > 1 and parts[1] in READ_ONLY_OLLAMA
    return True


class Brain:
    def __init__(self):
        from agents import llm_backend

        self.backend = llm_backend
        self.history: list[dict[str, str]] = []
        self.system = (
            "You are GPT-Doug MAX, the concise terminal operator for this repository. "
            "XUNIA provides local/multi-provider reasoning and retrieval; ZYRA provides "
            "bounded agent execution; Palantir Foundry provides governed ontology/data "
            "grounding when configured; Git/local workspace provides code context. "
            "Never claim a command, deployment, message, purchase, or external action "
            "happened unless the terminal actually returns a successful receipt. "
            "Prefer short actionable answers. Human approval remains required for mutations."
        )

    def health(self) -> dict[str, Any]:
        return self.backend.health()

    def ask(self, prompt: str, context: str = "") -> str:
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system}]
        if context:
            messages.append({"role": "system", "content": "CURRENT LOCAL CONTEXT\n" + context[:10000]})
        messages.extend(self.history[-12:])
        messages.append({"role": "user", "content": prompt})
        result = self.backend.chat_once(messages, None, {"temperature": 0.35})
        if result.get("error"):
            return f"BRAIN ERROR // {result.get('error')} // {(result.get('message') or {}).get('content', '')}"
        answer = str((result.get("message") or {}).get("content") or "").strip()
        if answer:
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": answer})
        return answer or "No response."


class MaxShell:
    def __init__(self, voice: bool = True):
        self.bus = StateBus()
        self.voice = VoiceEngine(enabled=voice)
        self.gate = ArmGate()
        self.brain = Brain()
        self.running = True
        self._speech_epoch = 0
        state = self.brain.health()
        self.bus.set(
            "IDLE",
            "GPT-Doug MAX online",
            voice=self.voice.enabled,
            provider=str(state.get("provider") or state.get("backend") or "unknown"),
            model=str(state.get("model") or "unknown"),
        )

    def banner(self) -> None:
        state = self.brain.health()
        print(CYAN + "24K // GPT-DOUG MAX // AGENTIC TERMINAL" + RESET)
        print(MAGENTA + "XUNIA brain // ZYRA runtime // PALANTIR grounding // GIT workspace" + RESET)
        print(
            GREEN
            + f"provider={state.get('provider')} model={state.get('model')} "
            + f"voice={'on' if self.voice.enabled else 'off'}"
            + RESET
        )
        print(DIM + "Type /help. Plain English talks to the brain. Prefix shell commands with $." + RESET)

    def set_state(self, state: str, detail: str = "") -> None:
        self.bus.set(
            state,
            detail,
            voice=self.voice.enabled,
            armed=self.gate.active(),
        )

    def speak_response(self, text: str, detail: str = "speaking") -> None:
        self._speech_epoch += 1
        epoch = self._speech_epoch
        self.set_state("TALK", detail)
        self.voice.speak(text)
        proc = self.voice._proc
        if proc is None:
            self.set_state("IDLE", "ready")
            return

        def waiter() -> None:
            try:
                proc.wait()
            except Exception:
                return
            if epoch == self._speech_epoch and self.bus.state.state == "TALK":
                self.set_state("IDLE", "ready")

        threading.Thread(target=waiter, daemon=True, name="gpt-doug-voice-state").start()

    def confirm(self, message: str) -> bool:
        try:
            return input(YELLOW + f"{message} [y/N] " + RESET).strip().lower() in {"y", "yes"}
        except (EOFError, KeyboardInterrupt):
            return False

    def execute_shell(self, command: str) -> None:
        command = command.strip()
        if not command:
            return
        read_only = shell_is_read_only(command)
        if not read_only:
            if not self.gate.active():
                print(RED + "BLOCKED // mutating shell command requires /arm" + RESET)
                return
            if not self.confirm(f"Run mutating shell command: {command!r}?"):
                print("Cancelled.")
                return
        self.set_state("ACT", command)
        try:
            proc = subprocess.run(command, cwd=ROOT, shell=True, executable="/bin/zsh")
            print(f"exit={proc.returncode}")
            self.set_state("IDLE", f"shell exit {proc.returncode}")
        except KeyboardInterrupt:
            print("\nInterrupted.")
            self.set_state("IDLE", "shell interrupted")

    def context(self) -> str:
        return json.dumps(
            {
                "git": git_snapshot(),
                "system": system_snapshot(),
                "brain": self.brain.health(),
                "armed_seconds": self.gate.remaining(),
            },
            indent=2,
            default=str,
        )

    def cmd_status(self) -> None:
        payload = {
            "system": system_snapshot(),
            "git": git_snapshot(),
            "brain": self.brain.health(),
            "visual_state": asdict(self.bus.state),
            "armed_seconds": self.gate.remaining(),
            "state_file": str(STATE_FILE),
        }
        print(json.dumps(payload, indent=2, default=str))

    def cmd_xunia(self, prompt: str) -> None:
        try:
            from xunia_godis import OllamaClient, PROFILES

            self.set_state("THINK", "XUNIA local brain")
            client = OllamaClient()
            answer = client.chat(PROFILES["godis"].model, prompt)
            print(GREEN + "XUNIA > " + RESET + answer)
            self.speak_response(answer, "XUNIA response")
        except Exception as exc:
            self.set_state("ERROR", str(exc))
            print(RED + f"XUNIA ERROR // {exc}" + RESET)

    def cmd_rag(self, question: str) -> None:
        try:
            from xunia_godis import OllamaClient, run_rag

            self.set_state("THINK", "local RAG")
            answer = run_rag(OllamaClient(), ROOT, question, top_k=8)
            print(GREEN + "RAG > " + RESET + answer)
            self.speak_response(answer, "RAG answer")
        except Exception as exc:
            self.set_state("ERROR", str(exc))
            print(RED + f"RAG ERROR // {exc}" + RESET)

    def cmd_agent(self, goal: str) -> None:
        if not self.gate.active():
            print(RED + "BLOCKED // /agent can edit repository files. Use /arm first." + RESET)
            return
        if not self.confirm(f"Run bounded ZYRA coding mission in {ROOT.name}: {goal!r}?"):
            print("Cancelled.")
            return
        try:
            from zyra_agent import ZyraAgent, print_agent_report

            model = os.getenv("GPT_DOUG_AGENT_MODEL", "gpt-xunia-agent")
            self.set_state("ACT", "ZYRA coding mission")
            result = ZyraAgent(ROOT, model=model).run(goal, evolve=False)
            print_agent_report(result)
            self.set_state("IDLE", f"ZYRA mission {getattr(result, 'status', 'done')}")
        except Exception as exc:
            self.set_state("ERROR", str(exc))
            print(RED + f"ZYRA ERROR // {exc}" + RESET)

    def cmd_agents(self) -> None:
        checks = {
            "xunia_godis": (ROOT / "xunia_godis.py").exists(),
            "zyra_agent": (ROOT / "zyra_agent.py").exists(),
            "palantir_terminal": (ROOT / "palantir_terminal.py").exists(),
            "revenue_swarm": (ROOT / "workers" / "revenue_swarm.py").exists(),
            "mission_control": (ROOT / "doug_mission_control.py").exists(),
        }
        print(json.dumps(checks, indent=2))

    def cmd_swarm(self, rest: str) -> None:
        try:
            from workers.revenue_swarm import Prospect, RevenueSwarm, SwarmConfig, _demo_prospects, _load_prospects

            args = shlex.split(rest)
            workers = int(os.getenv("GPT_DOUG_SWARM_WORKERS", "8"))
            prospects: Iterable[Prospect]
            if not args or args[0] == "demo":
                prospects = _demo_prospects()
            else:
                prospects = _load_prospects(Path(args[0]).expanduser())
            self.set_state("ACT", "bounded agent swarm")
            result = RevenueSwarm(SwarmConfig(requested_workers=workers)).run(prospects)
            print(json.dumps(result["metrics"], indent=2, sort_keys=True))
            print(YELLOW + "External outreach/payment actions remain approval-required." + RESET)
            self.set_state("IDLE", "swarm complete")
        except Exception as exc:
            self.set_state("ERROR", str(exc))
            print(RED + f"SWARM ERROR // {exc}" + RESET)

    def cmd_palantir(self, raw: str) -> None:
        try:
            from palantir_bridge import DougPalantirBridge
            from palantir_foundry import FoundryError
            from palantir_terminal import handle_palantir_command

            try:
                bridge = DougPalantirBridge.from_environment()
            except FoundryError as exc:
                print(RED + f"PALANTIR ERROR // {exc}" + RESET)
                return
            self.set_state("THINK", "Palantir grounding")
            result = handle_palantir_command(
                "/palantir " + raw,
                bridge,
                approve_write=lambda message: self.gate.active() and self.confirm(message),
            )
            if result.grounded_prompt:
                answer = self.brain.ask(result.grounded_prompt, context=self.context())
                print(GREEN + "DOUG > " + RESET + answer)
                self.speak_response(answer, "Palantir grounded answer")
            elif result.handled:
                print(result.output)
            self.set_state("IDLE", "Palantir complete")
        except Exception as exc:
            self.set_state("ERROR", str(exc))
            print(RED + f"PALANTIR ERROR // {exc}" + RESET)

    def cmd_test(self, rest: str) -> None:
        target = shlex.split(rest) if rest.strip() else ["tests/"]
        argv = [sys.executable, "-m", "pytest", "-q", *target]
        self.set_state("ACT", "pytest")
        print(CYAN + "$ " + " ".join(shlex.quote(x) for x in argv) + RESET)
        try:
            rc = subprocess.call(argv, cwd=ROOT)
            self.set_state("IDLE" if rc == 0 else "ERROR", f"pytest exit {rc}")
        except KeyboardInterrupt:
            self.set_state("IDLE", "pytest interrupted")

    def cmd_build(self, rest: str) -> None:
        command = rest.strip() or os.getenv("GPT_DOUG_BUILD_CMD", "")
        if not command:
            print("Set GPT_DOUG_BUILD_CMD or use /build <command>.")
            return
        if not self.gate.active():
            print(RED + "BLOCKED // builds may mutate artifacts. Use /arm first." + RESET)
            return
        if self.confirm(f"Run build command {command!r}?"):
            self.execute_shell(command)

    def cmd_deploy(self, rest: str) -> None:
        command = rest.strip() or os.getenv("GPT_DOUG_DEPLOY_CMD", "")
        if not command:
            print("No deployment command configured. Set GPT_DOUG_DEPLOY_CMD explicitly.")
            return
        if not self.gate.active():
            print(RED + "BLOCKED // deployment requires /arm." + RESET)
            return
        if not self.confirm(f"DEPLOY using {command!r}?"):
            print("Cancelled.")
            return
        self.execute_shell(command)

    def cmd_listen(self, rest: str) -> None:
        seconds = 5.0
        if rest.strip():
            try:
                seconds = float(rest.strip())
            except ValueError:
                pass
        self.set_state("LISTEN", f"microphone {seconds:.1f}s")
        print(CYAN + f"Listening locally for {seconds:.1f}s..." + RESET)
        try:
            text = self.voice.transcribe_local(seconds)
        except Exception as exc:
            self.set_state("ERROR", str(exc))
            print(RED + f"VOICE INPUT ERROR // {exc}" + RESET)
            return
        if not text:
            print("No speech detected.")
            self.set_state("IDLE", "no speech")
            return
        print(MAGENTA + "YOU (voice) > " + RESET + text)
        self.handle_plain(text)

    def handle_plain(self, prompt: str) -> None:
        self.set_state("THINK", prompt)
        answer = self.brain.ask(prompt, context=self.context())
        print(GREEN + "DOUG > " + RESET + answer)
        self.speak_response(answer, answer[:160])

    def help(self) -> None:
        print(
            """Commands
  /status                  system + git + provider + visual-state health
  /brain                   provider health
  /xunia <prompt>          local GPT-XUNIA-GODIS prompt
  /rag <question>          local repository-grounded answer
  /agent <goal>            bounded ZYRA coding mission (requires /arm)
  /agents                  show installed agent surfaces
  /swarm [demo|file.json]  bounded revenue swarm; drafts only
  /palantir <command>      Foundry/Ontology command; writes need arm+approval
  /github                  git/GitHub local status
  /test [targets...]       run pytest
  /build [command]         run configured build (requires /arm)
  /deploy [command]        run explicit deploy command (requires /arm)
  /voice on|off            macOS say output
  /listen [seconds]        local mic STT (optional faster-whisper stack)
  /joke                    ask brain for one joke and speak it
  /power                   visual-state POWER surge + spoken acknowledgement
  /arm [seconds]           enable mutating actions temporarily (15-1800s)
  /disarm                  revoke mutation authority
  $ <command>              explicit shell; mutations require arm + confirmation
  /clear                   clear brain conversation history
  /quit /kill              clean exit

Plain English is sent to the configured GPT-Doug provider. It is never silently
converted into a shell command.
"""
        )

    def handle_command(self, line: str) -> bool:
        if not line.startswith("/"):
            return False
        cmd, _, rest = line.partition(" ")
        rest = rest.strip()
        if cmd in {"/quit", "/kill"}:
            self.running = False
            return True
        if cmd == "/help":
            self.help()
        elif cmd == "/status":
            self.cmd_status()
        elif cmd == "/brain":
            print(json.dumps(self.brain.health(), indent=2, default=str))
        elif cmd == "/xunia":
            self.cmd_xunia(rest or "Report your current capabilities in one paragraph.")
        elif cmd == "/rag":
            if not rest:
                print("usage: /rag <question>")
            else:
                self.cmd_rag(rest)
        elif cmd == "/agent":
            if not rest:
                print("usage: /agent <goal>")
            else:
                self.cmd_agent(rest)
        elif cmd == "/agents":
            self.cmd_agents()
        elif cmd == "/swarm":
            self.cmd_swarm(rest)
        elif cmd == "/palantir":
            self.cmd_palantir(rest or "status")
        elif cmd == "/github":
            print(json.dumps(git_snapshot(), indent=2))
            if shutil.which("gh"):
                _, out = run_capture(["gh", "auth", "status"], timeout=5)
                if out:
                    print(out)
        elif cmd == "/test":
            self.cmd_test(rest)
        elif cmd == "/build":
            self.cmd_build(rest)
        elif cmd == "/deploy":
            self.cmd_deploy(rest)
        elif cmd == "/voice":
            if rest.lower() in {"off", "0", "false"}:
                self.voice.enabled = False
            elif rest.lower() in {"on", "1", "true", ""}:
                self.voice.enabled = True
            print(f"VOICE // {'ON' if self.voice.enabled else 'OFF'}")
            self.set_state("IDLE", "voice toggled")
        elif cmd == "/listen":
            self.cmd_listen(rest)
        elif cmd == "/joke":
            self.handle_plain("Tell me one short clever joke about software engineering.")
        elif cmd == "/power":
            self.set_state("POWER", "maximum ether power")
            print(YELLOW + "POWER CORE // MAXIMUM OUTPUT" + RESET)
            self.voice.speak("Power core rising. GPT Doug maximum shell online.")
        elif cmd == "/arm":
            seconds = 300
            if rest:
                try:
                    seconds = int(rest)
                except ValueError:
                    pass
            actual = self.gate.arm(seconds)
            self.set_state("READY", f"armed {actual}s")
            print(YELLOW + f"ARMED // {actual}s // mutations still require confirmation" + RESET)
        elif cmd == "/disarm":
            self.gate.disarm()
            self.set_state("IDLE", "disarmed")
            print("DISARMED")
        elif cmd == "/clear":
            self.brain.history.clear()
            print("Conversation history cleared.")
        else:
            print(f"Unknown command: {cmd}. Use /help.")
        return True

    def run(self) -> int:
        self.banner()
        self.voice.speak("GPT Doug Max online.")
        while self.running:
            try:
                line = input(CYAN + "\ngpt-doug > " + RESET).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line.startswith("$"):
                self.execute_shell(line[1:].strip())
                continue
            if self.handle_command(line):
                continue
            self.handle_plain(line)
        self.shutdown()
        return 0

    def shutdown(self) -> None:
        self.voice.stop()
        self.gate.disarm()
        self.bus.set("OFFLINE", "shell closed", armed=False)
        print(DIM + "GPT-Doug MAX offline. Normal shell control returned." + RESET)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GPT-Doug MAX agentic terminal")
    parser.add_argument("--no-voice", action="store_true", help="disable macOS speech output")
    parser.add_argument("--status", action="store_true", help="print status once and exit")
    args = parser.parse_args(argv)
    shell = MaxShell(voice=not args.no_voice)
    if args.status:
        shell.cmd_status()
        shell.shutdown()
        return 0
    return shell.run()


if __name__ == "__main__":
    raise SystemExit(main())
