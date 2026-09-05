#!/usr/bin/env python3
"""Reproducible GPT-DOUG POCKET benchmark harness for macOS.

Measures:
- restart-to-health time
- end-to-end generation throughput (tokens/s)
- USB/internal filesystem allocation deltas
- Metal backend evidence from llama.cpp logs
- USB persistence across host Macs
- recovery success
- loopback-only inference / non-loopback socket evidence

The harness writes results to the GPT-DOUG POCKET external volume and uses only
Python's standard library plus macOS command-line utilities.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PORT = int(os.environ.get("ZYRA_PORT", "9931"))
BASE = f"http://127.0.0.1:{PORT}"
POCKET = Path(os.environ.get("GPT_DOUG_POCKET", Path(__file__).resolve().parents[1])).resolve()
REPO = POCKET / "repo" if (POCKET / "repo" / ".git").exists() else Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("GPT_DOUG_HOME", POCKET / "state"))
LOGS = Path(os.environ.get("GPT_DOUG_LOGS", POCKET / "logs"))
MEMORY = Path(os.environ.get("GPT_DOUG_MEMORY", POCKET / "memory"))
RESULTS = POCKET / "benchmarks" / "results"
PERSISTENCE = POCKET / "benchmarks" / "persistence.json"
RUNNER = POCKET / "gpt-doug"

PROMPT = (
    "In exactly four concise bullet points, explain why a local AI model stored "
    "on removable media can be useful for reproducible offline workflows."
)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def run(cmd: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)


def get_json(path: str, timeout: float = 4.0) -> dict[str, Any]:
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, body: dict[str, Any], timeout: float = 180.0) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def healthy() -> bool:
    try:
        get_json("/v1/models", timeout=2.0)
        return True
    except Exception:
        return False


def df_kb(path: Path | str) -> dict[str, int | str]:
    cp = run(["df", "-Pk", str(path)])
    lines = [line for line in cp.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return {"filesystem": "unknown", "total_kb": 0, "used_kb": 0, "avail_kb": 0}
    parts = lines[-1].split()
    return {
        "filesystem": parts[0],
        "total_kb": int(parts[1]),
        "used_kb": int(parts[2]),
        "avail_kb": int(parts[3]),
    }


def folder_bytes(path: Path) -> int:
    cp = run(["du", "-sk", str(path)])
    try:
        return int(cp.stdout.split()[0]) * 1024
    except Exception:
        return 0


def host_profile() -> dict[str, Any]:
    hw_model = run(["sysctl", "-n", "hw.model"]).stdout.strip() or "unknown"
    chip = run(["sysctl", "-n", "machdep.cpu.brand_string"]).stdout.strip()
    if not chip:
        chip = run(["system_profiler", "SPHardwareDataType"], timeout=30).stdout
        match = re.search(r"Chip:\s*(.+)", chip)
        chip = match.group(1).strip() if match else platform.processor() or "unknown"
    mem_raw = run(["sysctl", "-n", "hw.memsize"]).stdout.strip()
    memory_bytes = int(mem_raw) if mem_raw.isdigit() else 0
    signature_source = f"{platform.node()}|{hw_model}|{platform.machine()}"
    signature = hashlib.sha256(signature_source.encode()).hexdigest()[:12]
    return {
        "node_signature": signature,
        "hardware_model": hw_model,
        "chip": chip,
        "architecture": platform.machine(),
        "macos": platform.mac_ver()[0],
        "memory_bytes": memory_bytes,
    }


def metal_evidence() -> dict[str, Any]:
    log = LOGS / "llama.log"
    text = log.read_text(errors="replace")[-200_000:] if log.exists() else ""
    patterns = [r"Metal", r"ggml_metal", r"GPU.*Metal", r"using.*GPU"]
    hits: list[str] = []
    for line in text.splitlines():
        if any(re.search(p, line, re.IGNORECASE) for p in patterns):
            hits.append(line.strip())
    return {
        "metal_detected_in_runtime_log": bool(hits),
        "evidence": hits[-8:],
        "powermetrics_note": "GPU utilization requires privileged powermetrics sampling; not required for this default reproducible run.",
    }


def network_evidence() -> dict[str, Any]:
    pidfile = STATE / "llama.pid"
    if not pidfile.exists():
        return {"pid": None, "non_loopback_connections": [], "raw": []}
    pid = pidfile.read_text().strip()
    if not pid.isdigit():
        return {"pid": None, "non_loopback_connections": [], "raw": []}
    cp = run(["lsof", "-nP", "-a", "-p", pid, "-i"], timeout=10)
    lines = [x for x in cp.stdout.splitlines()[1:] if x.strip()]
    non_loopback = []
    for line in lines:
        # LISTEN on 127.0.0.1 is expected; established remote endpoints are evidence to report.
        if "127.0.0.1" not in line and "localhost" not in line and "*:" not in line:
            non_loopback.append(line)
    return {"pid": int(pid), "non_loopback_connections": non_loopback, "raw": lines[:20]}


def persistence_update(host: dict[str, Any]) -> dict[str, Any]:
    PERSISTENCE.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {"created_at": now_utc(), "runs": 0, "nodes": []}
    if PERSISTENCE.exists():
        try:
            data = json.loads(PERSISTENCE.read_text())
        except Exception:
            pass
    data["runs"] = int(data.get("runs", 0)) + 1
    nodes = data.setdefault("nodes", [])
    if not any(x.get("node_signature") == host["node_signature"] for x in nodes if isinstance(x, dict)):
        nodes.append({
            "node_signature": host["node_signature"],
            "hardware_model": host["hardware_model"],
            "architecture": host["architecture"],
            "first_seen": now_utc(),
        })
    data["last_seen"] = now_utc()
    PERSISTENCE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return {
        "persistent_run_count": data["runs"],
        "distinct_host_count": len(nodes),
        "cross_mac_persistence_observed": len(nodes) >= 2,
        "record": str(PERSISTENCE),
    }


def restart_benchmark() -> dict[str, Any]:
    if not RUNNER.exists():
        return {"performed": False, "reason": f"Pocket launcher missing: {RUNNER}"}

    run([str(RUNNER), "stop"], timeout=30)
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [str(RUNNER), "start"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + 240
    while time.time() < deadline:
        if healthy():
            elapsed = time.perf_counter() - t0
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            return {"performed": True, "healthy": True, "restart_to_health_seconds": round(elapsed, 3)}
        if proc.poll() is not None and not healthy():
            output = proc.stdout.read()[-4000:] if proc.stdout else ""
            return {"performed": True, "healthy": False, "restart_to_health_seconds": None, "output": output}
        time.sleep(0.25)
    return {"performed": True, "healthy": False, "restart_to_health_seconds": None, "reason": "timeout"}


def generation_benchmark() -> dict[str, Any]:
    models = get_json("/v1/models")
    entries = models.get("data") or []
    if not entries:
        raise RuntimeError("No model reported by /v1/models")
    model = entries[0].get("id") or os.environ.get("ZYRA_MODEL", "unknown")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0,
        "max_tokens": 128,
        "stream": False,
    }
    t0 = time.perf_counter()
    response = post_json("/v1/chat/completions", body)
    elapsed = time.perf_counter() - t0
    usage = response.get("usage") or {}
    completion_tokens = int(usage.get("completion_tokens") or 0)
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    text = ""
    choices = response.get("choices") or []
    if choices:
        text = ((choices[0].get("message") or {}).get("content") or "").strip()
    tps = (completion_tokens / elapsed) if completion_tokens and elapsed > 0 else None
    result: dict[str, Any] = {
        "model": model,
        "elapsed_seconds": round(elapsed, 3),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "end_to_end_completion_tokens_per_second": round(tps, 3) if tps is not None else None,
        "response_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "response_preview": text[:280],
    }
    if "timings" in response:
        result["llama_cpp_timings"] = response["timings"]
    return result


def git_version() -> dict[str, str]:
    sha = run(["git", "-C", str(REPO), "rev-parse", "HEAD"]).stdout.strip()
    branch = run(["git", "-C", str(REPO), "branch", "--show-current"]).stdout.strip()
    return {"commit": sha, "branch": branch}


def markdown(result: dict[str, Any]) -> str:
    gen = result.get("generation", {})
    restart = result.get("recovery", {})
    storage = result.get("storage", {})
    metal = result.get("metal", {})
    pers = result.get("persistence", {})
    net = result.get("network", {})
    return f"""# GPT-DOUG POCKET Benchmark Result\n\n- Timestamp: `{result['timestamp_utc']}`\n- Commit: `{result['git']['commit']}`\n- Host model: `{result['host']['hardware_model']}`\n- Chip: `{result['host']['chip']}`\n- macOS: `{result['host']['macos']}`\n- Pocket root: `{result['pocket_root']}`\n\n## Core metrics\n\n| Metric | Result |\n|---|---:|\n| Restart → healthy | {restart.get('restart_to_health_seconds')} s |\n| End-to-end completion throughput | {gen.get('end_to_end_completion_tokens_per_second')} tok/s |\n| Completion tokens | {gen.get('completion_tokens')} |\n| Generation wall time | {gen.get('elapsed_seconds')} s |\n| USB allocation delta | {storage.get('usb_used_delta_kb')} KB |\n| Internal filesystem allocation delta | {storage.get('internal_used_delta_kb')} KB |\n| Metal runtime evidence | {metal.get('metal_detected_in_runtime_log')} |\n| Distinct Macs observed by same Pocket state | {pers.get('distinct_host_count')} |\n| Cross-Mac persistence observed | {pers.get('cross_mac_persistence_observed')} |\n| Non-loopback llama connections at capture | {len(net.get('non_loopback_connections') or [])} |\n\n## Interpretation notes\n\n- Throughput is **end-to-end completion tokens / wall-clock second**, not a kernel-only decoder benchmark.\n- Filesystem allocation deltas are a conservative observable proxy, **not raw physical write I/O**.\n- `Metal runtime evidence` is taken from llama.cpp's runtime log. Privileged `powermetrics` sampling should be added for a formal GPU-utilization figure.\n- Zero-paid-API operation is supported here by loopback inference (`127.0.0.1`) and the captured llama process socket state; it is not a claim that the host has no other networked processes.\n\n## Reproducibility\n\nRun on the same Pocket drive on another Mac:\n\n```bash\n\"$GPT_DOUG_POCKET/gpt-doug\" benchmark\n```\n\nThe USB-resident persistence record increments and records a privacy-preserving host signature.\n"""


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    MEMORY.mkdir(parents=True, exist_ok=True)

    host = host_profile()
    persistence = persistence_update(host)
    internal_before = df_kb(Path.home())
    usb_before = df_kb(POCKET)
    pocket_bytes_before = folder_bytes(POCKET)

    recovery = restart_benchmark()
    if not recovery.get("healthy"):
        print("❌ Recovery benchmark failed; see JSON result after completion.")

    generation: dict[str, Any]
    if healthy():
        try:
            generation = generation_benchmark()
        except Exception as exc:
            generation = {"error": f"{type(exc).__name__}: {exc}"}
    else:
        generation = {"error": "server unhealthy"}

    metal = metal_evidence()
    network = network_evidence()
    usb_after = df_kb(POCKET)
    internal_after = df_kb(Path.home())
    pocket_bytes_after = folder_bytes(POCKET)

    storage = {
        "usb_before": usb_before,
        "usb_after": usb_after,
        "usb_used_delta_kb": int(usb_after.get("used_kb", 0)) - int(usb_before.get("used_kb", 0)),
        "internal_before": internal_before,
        "internal_after": internal_after,
        "internal_used_delta_kb": int(internal_after.get("used_kb", 0)) - int(internal_before.get("used_kb", 0)),
        "pocket_folder_delta_bytes": pocket_bytes_after - pocket_bytes_before,
    }

    result = {
        "schema": "gpt-doug-pocket-benchmark/v1",
        "timestamp_utc": now_utc(),
        "pocket_root": str(POCKET),
        "api_base": BASE + "/v1",
        "paid_api_required": False,
        "benchmark_external_api_calls": 0,
        "git": git_version(),
        "host": host,
        "recovery": recovery,
        "generation": generation,
        "storage": storage,
        "metal": metal,
        "persistence": persistence,
        "network": network,
    }

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = RESULTS / f"benchmark-{stamp}.json"
    md_path = RESULTS / f"benchmark-{stamp}.md"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    md_path.write_text(markdown(result))

    print("\n🧪 GPT-DOUG POCKET PUBLICATION BENCHMARK")
    print(f"✅ Result JSON: {json_path}")
    print(f"✅ Result Markdown: {md_path}")
    print(f"⚡ Restart→health: {recovery.get('restart_to_health_seconds')} s")
    print(f"🧠 Throughput: {generation.get('end_to_end_completion_tokens_per_second')} tok/s")
    print(f"💾 USB allocation delta: {storage['usb_used_delta_kb']} KB")
    print(f"🖥️ Internal allocation delta: {storage['internal_used_delta_kb']} KB")
    print(f"🍎 Metal runtime evidence: {'YES' if metal['metal_detected_in_runtime_log'] else 'NOT DETECTED'}")
    print(f"🔁 Persistence runs: {persistence['persistent_run_count']} across {persistence['distinct_host_count']} host(s)")
    print(f"🌐 Non-loopback llama sockets: {len(network['non_loopback_connections'])}")
    return 0 if recovery.get("healthy") and "error" not in generation else 1


if __name__ == "__main__":
    raise SystemExit(main())
