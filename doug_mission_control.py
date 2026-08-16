#!/usr/bin/env python3

import os
import socket
import subprocess
import time
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agents import llm_backend

ROOT = Path.home() / "gpt-doug-llm"
LOGS = ROOT / ".doug-logs"
AGENT_LOG = LOGS / "terminal-agent.log"

console = Console()

def port_alive(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=.25):
            return True
    except Exception:
        return False

def process_alive(pattern):
    result = subprocess.run(
        ["pgrep", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def cmd(command):
    try:
        return subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3
        ).strip()
    except Exception:
        return ""

def status(ok):
    return "[bold green]● ONLINE[/]" if ok else "[bold red]● OFFLINE[/]"

def get_model():
    return llm_backend.health().get("model") or "offline"

def recent_activity():
    if not AGENT_LOG.exists():
        return ["Waiting for GPT-Doug activity..."]

    lines = AGENT_LOG.read_text(
        errors="ignore"
    ).splitlines()

    return lines[-14:] or ["No activity yet."]

def project_count():
    candidates = [
        ROOT / "doug-lab",
        ROOT / "web" / "projects"
    ]

    total = 0

    for directory in candidates:
        if directory.exists():
            if directory.is_dir():
                total += len(list(directory.iterdir()))

    return total

def test_status():
    log = LOGS / "tests.log"

    if not log.exists():
        return "not run"

    lines = log.read_text(errors="ignore").splitlines()

    return lines[-1] if lines else "unknown"

def sound(name):
    path = f"/System/Library/Sounds/{name}.aiff"

    if os.path.exists(path):
        subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

def speak(text):
    if os.getenv("DOUG_VOICE", "1") == "1":
        subprocess.Popen(
            ["say", "-r", "205", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

def build_layout():

    provider = llm_backend.health()
    web = port_alive(8787)
    daemon = process_alive("workers/agent-daemon.py")
    agent = process_alive("doug_terminal_agent.py")

    layout = Layout()

    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )

    layout["main"].split_row(
        Layout(name="systems", ratio=1),
        Layout(name="activity", ratio=2)
    )

    title = Text()
    title.append(" GPT DOUG ", style="bold black on bright_green")
    title.append(" // MISSION CONTROL", style="bold bright_cyan")
    title.append("\n")
    title.append(
        "LOCAL AGENTIC COMPUTE • PROVIDERS • ZYRA • TERMINAL",
        style="green"
    )

    layout["header"].update(
        Panel(title, border_style="bright_green")
    )

    table = Table(show_header=False, expand=True)
    table.add_column("System")
    table.add_column("State")

    table.add_row("AI PROVIDER", provider["provider"].upper())
    table.add_row("WEB UI :8787", status(web))
    table.add_row("AGENT DAEMON", status(daemon))
    table.add_row("TERMINAL AGENT", status(agent))
    table.add_row(
        "MODEL",
        f"[bright_cyan]{get_model()}[/]"
    )
    table.add_row(
        "PROJECT OBJECTS",
        str(project_count())
    )
    table.add_row(
        "TESTS",
        f"[green]{test_status()}[/]"
    )

    layout["systems"].update(
        Panel(
            table,
            title="SYSTEM MATRIX",
            border_style="cyan"
        )
    )

    activity = Text()

    for line in recent_activity():
        if "VERIFIED COMPLETE" in line or "[done]" in line:
            style = "bold green"
        elif (
            "ERROR" in line.upper()
            or "FAILED" in line.upper()
            or "exit=1" in line
        ):
            style = "red"
        elif "TERMINAL" in line or "$ " in line:
            style = "yellow"
        else:
            style = "white"

        activity.append(line[-150:] + "\n", style=style)

    layout["activity"].update(
        Panel(
            activity,
            title="LIVE AGENT STREAM",
            border_style="bright_magenta"
        )
    )

    footer = Text(
        " ♥ GPT-DOUG ALIVE   "
        "doug-agent \"YOUR OBJECTIVE\"   "
        "WEB: http://127.0.0.1:8787   "
        "CTRL+C EXIT",
        style="bold bright_green"
    )

    layout["footer"].update(
        Panel(footer, border_style="green")
    )

    return layout

def main():

    console.clear()

    sound("Glass")
    speak("GPT Doug Mission Control online")

    previous = ""

    with Live(
        build_layout(),
        refresh_per_second=4,
        screen=True
    ) as live:

        while True:

            live.update(build_layout())

            if AGENT_LOG.exists():
                lines = AGENT_LOG.read_text(
                    errors="ignore"
                ).splitlines()

                latest = lines[-1] if lines else ""

                if latest != previous:

                    if "VERIFIED COMPLETE" in latest:
                        sound("Hero")
                        speak("Build verified complete")

                    elif (
                        "FAILED" in latest.upper()
                        or "ERROR" in latest.upper()
                    ):
                        sound("Basso")

                    previous = latest

            time.sleep(.25)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGPT DOUG MISSION CONTROL CLOSED")
