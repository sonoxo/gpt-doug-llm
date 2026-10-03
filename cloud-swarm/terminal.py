#!/usr/bin/env python3
import argparse, json, os, queue, random, shutil, sys, threading, time
from urllib import request, error

BASE = os.environ.get("GPTDOUG_CLOUD_URL", "https://gpt-doug-cloud-swarm.onrender.com").rstrip("/")
ESC = "\x1b["
RESET = ESC + "0m"
BOLD = ESC + "1m"
DIM = ESC + "2m"
GREEN = ESC + "38;5;82m"
LIME = ESC + "38;5;118m"
GOLD = ESC + "38;5;220m"
ORANGE = ESC + "38;5;208m"
RED = ESC + "38;5;196m"
CYAN = ESC + "38;5;51m"
VIOLET = ESC + "38;5;141m"
WHITE = ESC + "38;5;255m"
FALL = ESC + "38;5;172m"

FACE = [
"            ╭────────────────────╮",
"            │   ◢████████████◣   │",
"            │  ███  ◉    ◉  ███  │",
"            │  ███    ▄▄    ███  │",
"            │   ███  ╰──╯  ███   │",
"            │    ◥██████████◤    │",
"            ╰──────╥────╥────────╯",
"                   ║    ║",
"              ╭────╨────╨────╮",
"              │ GPT‑DOUG MAX │",
"              ╰──────────────╯",
]

def get_json(path, timeout=8):
    req = request.Request(BASE + path, headers={"User-Agent":"GPT-DOUG-Terminal/2.0","Accept":"application/json"})
    with request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def post_json(path, timeout=120):
    req = request.Request(BASE + path, data=b"", method="POST",
                          headers={"User-Agent":"GPT-DOUG-Terminal/2.0","Accept":"application/json"})
    with request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def clear():
    sys.stdout.write(ESC + "2J" + ESC + "H")

def lightforce(active, max_workers, queued):
    if queued > max_workers * 8: return "CRITICAL", RED
    ratio = (active / max_workers) if max_workers else 0
    if ratio >= .85: return "HOT", ORANGE
    if ratio >= .50: return "WARM", GOLD
    if ratio > 0: return "COOL", CYAN
    return "COLD", VIOLET

def bar(value, total, width=26):
    total = max(total, 1)
    fill = max(0, min(width, int(width * value / total)))
    return "█" * fill + "░" * (width-fill)

def matrix_line(width):
    chars = "01ΔΣΨΩ∴⋮✦◇◆░▒▓"
    return "".join(random.choice(chars + "      ") for _ in range(max(1, width)))

def render(status, frame=0, message="LIVE CLOUD TELEMETRY"):
    cols = shutil.get_terminal_size((100, 30)).columns
    active = int(status.get("activeWorkers", 0))
    queued = int(status.get("queuedTasks", 0))
    done = int(status.get("completedTasks", 0))
    maxw = int(status.get("max_real_workers", 1))
    lf, lfcolor = lightforce(active, maxw, queued)
    pulse = ["◐","◓","◑","◒"][frame % 4]
    clear()
    print(FALL + BOLD + "🍂 GPT‑DOUG // DARK FALL ONLINE 🍁" + RESET)
    print(DIM + matrix_line(min(cols, 96)) + RESET)
    face_color = [CYAN, VIOLET, GOLD, GREEN][frame % 4]
    for line in FACE:
        print(face_color + line + RESET)
    print()
    print(BOLD + WHITE + "┌─ CLOUD SWARM HUD " + "─" * max(1, min(60, cols-20)) + "┐" + RESET)
    print(f"{CYAN}{pulse} CLOUD{RESET}  {BASE}")
    print(f"{GREEN}● AUTHORITY{RESET} HUMAN_FIRST    {GREEN}● REPLICATION{RESET} OFF")
    print(f"{LIME}∞ VIRTUAL{RESET} gpt-doug00 → gpt-doug999999999999999")
    print(f"{lfcolor}⚡ LIGHTFORCE {lf}{RESET}")
    print()
    print(f"REAL WORKERS   [{bar(active,maxw)}] {active:>3}/{maxw:<3}")
    print(f"QUEUE          [{bar(min(queued,maxw),maxw)}] {queued:>6}")
    print(f"COMPLETED      {done:,}")
    print(f"LAST RUN       {status.get('lastRunAt') or '—'}")
    print()
    print(f"{GOLD}HIVE{RESET}  {'◉' * max(1, min(8, active or 1))}   "
          f"{VIOLET}SWARM{RESET}  {'✦' * max(1, min(16, active + (1 if queued else 0)))}")
    print(DIM + message + RESET)
    print()
    print(f"{WHITE}commands:{RESET} run <n> | status | matrix | clear | help | quit")
    print(DIM + matrix_line(min(cols, 96)) + RESET)

def run_batch(n, results_q):
    try:
        results_q.put(("ok", post_json(f"/swarm/run?count={int(n)}")))
    except Exception as exc:
        results_q.put(("error", str(exc)))

def live(seconds=None, run_count=None):
    q = queue.Queue()
    worker = None
    if run_count:
        worker = threading.Thread(target=run_batch, args=(run_count,q), daemon=True)
        worker.start()
    start = time.time()
    frame = 0
    last_message = "LIVE CLOUD TELEMETRY"
    while True:
        try:
            status = get_json("/swarm/status")
            if not q.empty():
                kind, payload = q.get_nowait()
                last_message = ("BATCH COMPLETE: " + str(payload.get("executed"))) if kind == "ok" else ("ERROR: " + payload)
            render(status, frame, last_message)
        except Exception as exc:
            clear()
            print(RED + BOLD + "⚠ CLOUD LINK DEGRADED" + RESET)
            print(str(exc))
        frame += 1
        if seconds is not None and time.time()-start >= seconds: break
        if worker and not worker.is_alive() and q.empty():
            time.sleep(.8)
            try: render(get_json("/swarm/status"), frame, last_message)
            except Exception: pass
            break
        time.sleep(.7)

def matrix_mode(seconds=8):
    start = time.time()
    frame = 0
    while time.time()-start < seconds:
        clear()
        cols, rows = shutil.get_terminal_size((100,30))
        print(GREEN + BOLD + "GPT‑DOUG // MATRIX DIAGNOSTIC STREAM" + RESET)
        for _ in range(max(5, rows-3)):
            print(GREEN + matrix_line(cols) + RESET)
        frame += 1
        time.sleep(.09)

def interactive():
    try:
        health = get_json("/health")
        status = get_json("/swarm/status")
        render(status, 0, f"ONLINE · {health.get('host_cpus','?')} CLOUD CPU LOGICAL CORES")
    except Exception as exc:
        print(RED + "Cloud link unavailable: " + str(exc) + RESET)
    while True:
        try:
            raw = input(FALL + "gpt-doug-cloud> " + RESET).strip()
        except (EOFError, KeyboardInterrupt):
            print(); return
        if not raw: continue
        parts = raw.split()
        cmd = parts[0].lower()
        if cmd in {"quit","exit","q"}: return
        if cmd == "status": live(seconds=3); continue
        if cmd == "matrix": matrix_mode(); continue
        if cmd == "clear": clear(); continue
        if cmd == "run":
            try: n = int(parts[1]) if len(parts)>1 else 100
            except ValueError:
                print("usage: run <integer>"); continue
            n = max(1, min(n,1000))
            live(run_count=n)
            continue
        if cmd == "help":
            print("run <1-1000>  status  matrix  clear  quit")
            continue
        print("Unknown command. Type help.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--run", type=int)
    args = ap.parse_args()
    if args.once:
        render(get_json("/swarm/status"),0)
    elif args.demo:
        matrix_mode(3); live(seconds=7)
    elif args.run:
        live(run_count=max(1,min(args.run,1000)))
    else:
        interactive()

if __name__ == "__main__":
    main()
