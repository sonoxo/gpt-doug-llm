import os
import platform
import subprocess

from .tool_factory import command_tool, list_tools, run_tool


command_tool("repo_status", ["git", "status", "--short"])
command_tool("repo_branch", ["git", "branch", "--show-current"])
command_tool("repo_root", ["pwd"])


def sysctl(name):
    try:
        return subprocess.check_output(
            ["sysctl", "-n", name],
            text=True
        ).strip()
    except Exception:
        return "unknown"


def main():
    cpu = os.cpu_count() or 1

    try:
        ram_bytes = int(sysctl("hw.memsize"))
        ram_gb = ram_bytes / (1024 ** 3)
    except Exception:
        ram_gb = 0

    print("=" * 60)
    print("GPT6-DOUG-ZYRA-LLM :: AGENTIC MAX")
    print("=" * 60)
    print("Machine:", platform.machine())
    print("CPU workers:", cpu)
    print("RAM:", "{:.1f} GB".format(ram_gb))
    print("RAM budget:", os.getenv("DOUG_RAM_BUDGET_GB", "auto"))
    print("Accelerator:", os.getenv("DOUG_ACCELERATOR", "cpu"))
    print("Branch:", run_tool("repo_branch"))
    print()
    print("ACTIVE TOOLS:")
    for name in list_tools():
        print(" -", name)

    print()
    print("REPO CHANGES:")
    status = run_tool("repo_status")
    print(status if status else "clean")

    test = "tests/test_agentic_ontology_loop.py"
    if os.path.exists(test):
        print()
        print("AGENTIC TEST:")
        subprocess.run(["python3", "-m", "pytest", "-q", test])
    else:
        print()
        print("Agentic test not installed yet.")

    print()
    print("DOUG AGENTIC RUNTIME: READY")


if __name__ == "__main__":
    main()
