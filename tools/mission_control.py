
import itertools
import subprocess
import sys
import threading
import time

SPINNER = itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])

def animate(label, done):
    while not done[0]:
        sys.stdout.write(f"\r{next(SPINNER)} {label}")
        sys.stdout.flush()
        time.sleep(0.08)
    sys.stdout.write("\r✓ " + label + " " * 20 + "\n")

def run(label, cmd):
    done = [False]
    t = threading.Thread(target=animate, args=(label, done))
    t.start()
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    done[0] = True
    t.join()
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode

print("\n╔══════════════════════════════════════╗")
print("║      GPT-DOUG MISSION CONTROL        ║")
print("╚══════════════════════════════════════╝\n")

run("Scanning Doug launcher", "type doug && command -v doug")
run(
    "Finding real fleet files",
    "find . -path './.git' -prune -o -path './.doug' -prune -o -path './.venv' -prune -o "
    "-type f \\( -iname '*doug*.py' -o -iname '*fleet*.py' -o -iname '*agent*.py' \\) -print | head -120"
)

print("\n★ Scan complete. Send the output here and we wire the fleet next.")
