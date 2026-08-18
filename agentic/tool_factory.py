import subprocess
from typing import Callable, Dict

TOOLS: Dict[str, Callable] = {}


def tool(name=None):
    """Turn any Python function into a Doug tool with one decorator."""
    def register(fn):
        TOOLS[name or fn.__name__] = fn
        return fn
    return register


def command_tool(name, command):
    """Create a safe command-backed tool with one line."""
    allowed = {"git", "python3", "sysctl", "pwd", "ls"}
    if not command or command[0] not in allowed:
        raise ValueError("Command is not allowlisted")

    @tool(name)
    def runner():
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return (result.stdout or result.stderr).strip()

    return runner


def run_tool(name, *args, **kwargs):
    if name not in TOOLS:
        raise KeyError("Unknown tool: " + name)
    return TOOLS[name](*args, **kwargs)


def list_tools():
    return sorted(TOOLS)
