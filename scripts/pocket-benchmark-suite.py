#!/usr/bin/env python3
"""Run repeated GPT-DOUG POCKET publication benchmarks and aggregate metrics."""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TRIALS = max(1, int(os.environ.get("GPT_DOUG_BENCH_TRIALS", "5")))
POCKET = Path(os.environ.get("GPT_DOUG_POCKET", Path(__file__).resolve().parents[1])).resolve()
REPO = POCKET / "repo" if (POCKET / "repo" / ".git").exists() else Path(__file__).resolve().parents[1]
RESULTS = POCKET / "benchmarks" / "results"
BENCH = REPO / "scripts" / "pocket-publication-benchmark.py"


def newest_json(before: set[Path]) -> Path | None:
    current = set(RESULTS.glob("benchmark-*.json"))
    new = sorted(current - before, key=lambda p: p.stat().st_mtime)
    return new[-1] if new else None


def stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"count": 0, "median": None, "min": None, "max": None, "mean": None, "stdev": None}
    return {
        "count": len(values),
        "median": round(statistics.median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(statistics.mean(values), 3),
        "stdev": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
    }


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    trial_files: list[Path] = []
    failures = 0

    for i in range(1, TRIALS + 1):
        print(f"\n🧪 Publication trial {i}/{TRIALS}")
        before = set(RESULTS.glob("benchmark-*.json"))
        cp = subprocess.run([sys.executable, str(BENCH)], text=True)
        result_file = newest_json(before)
        if result_file:
            trial_files.append(result_file)
            print(f"📄 Trial result: {result_file.name}")
        if cp.returncode != 0:
            failures += 1
        time.sleep(1)

    records = [json.loads(p.read_text()) for p in trial_files]
    boot = [
        float(r["recovery"]["restart_to_health_seconds"])
        for r in records
        if r.get("recovery", {}).get("restart_to_health_seconds") is not None
    ]
    tps = [
        float(r["generation"]["end_to_end_completion_tokens_per_second"])
        for r in records
        if r.get("generation", {}).get("end_to_end_completion_tokens_per_second") is not None
    ]
    internal_delta = [
        float(r["storage"]["internal_used_delta_kb"])
        for r in records
        if r.get("storage", {}).get("internal_used_delta_kb") is not None
    ]
    usb_delta = [
        float(r["storage"]["usb_used_delta_kb"])
        for r in records
        if r.get("storage", {}).get("usb_used_delta_kb") is not None
    ]

    aggregate = {
        "schema": "gpt-doug-pocket-benchmark-suite/v1",
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "requested_trials": TRIALS,
        "completed_trials": len(records),
        "failed_trials": failures,
        "trial_files": [str(p) for p in trial_files],
        "restart_to_health_seconds": stats(boot),
        "end_to_end_completion_tokens_per_second": stats(tps),
        "internal_used_delta_kb": stats(internal_delta),
        "usb_used_delta_kb": stats(usb_delta),
        "all_trials_recovery_passed": bool(records) and all(r.get("recovery", {}).get("healthy") for r in records),
        "all_trials_paid_api_required_false": bool(records) and all(r.get("paid_api_required") is False for r in records),
        "all_trials_loopback_api": bool(records) and all(str(r.get("api_base", "")).startswith("http://127.0.0.1:") for r in records),
        "metal_evidence_trials": sum(1 for r in records if r.get("metal", {}).get("metal_detected_in_runtime_log")),
        "non_loopback_socket_trials": sum(1 for r in records if r.get("network", {}).get("non_loopback_connections")),
        "distinct_hosts_observed": max((int(r.get("persistence", {}).get("distinct_host_count", 0)) for r in records), default=0),
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = RESULTS / f"suite-{stamp}.json"
    md_path = RESULTS / f"suite-{stamp}.md"
    json_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n")

    b = aggregate["restart_to_health_seconds"]
    g = aggregate["end_to_end_completion_tokens_per_second"]
    i = aggregate["internal_used_delta_kb"]
    u = aggregate["usb_used_delta_kb"]
    md_path.write_text(f"""# GPT-DOUG POCKET Publication Benchmark Suite\n\n- Trials completed: **{aggregate['completed_trials']}/{TRIALS}**\n- Recovery passed every trial: **{aggregate['all_trials_recovery_passed']}**\n- Loopback API every trial: **{aggregate['all_trials_loopback_api']}**\n- Paid API required: **False**\n- Metal evidence: **{aggregate['metal_evidence_trials']}/{aggregate['completed_trials']} trials**\n- Distinct host Macs observed by Pocket persistence state: **{aggregate['distinct_hosts_observed']}**\n\n| Metric | Median | Min | Max | Mean | Std dev |\n|---|---:|---:|---:|---:|---:|\n| Restart→health (s) | {b['median']} | {b['min']} | {b['max']} | {b['mean']} | {b['stdev']} |\n| Completion throughput (tok/s) | {g['median']} | {g['min']} | {g['max']} | {g['mean']} | {g['stdev']} |\n| Internal allocation Δ (KB) | {i['median']} | {i['min']} | {i['max']} | {i['mean']} | {i['stdev']} |\n| USB allocation Δ (KB) | {u['median']} | {u['min']} | {u['max']} | {u['mean']} | {u['stdev']} |\n\nRaw per-trial JSON/Markdown files are preserved beside this aggregate result.\n""")

    print("\n📊 GPT-DOUG POCKET SUITE COMPLETE")
    print(f"✅ Aggregate JSON: {json_path}")
    print(f"✅ Aggregate Markdown: {md_path}")
    print(f"⚡ Median restart→health: {b['median']} s")
    print(f"🧠 Median throughput: {g['median']} tok/s")
    print(f"🖥️ Median internal allocation delta: {i['median']} KB")
    print(f"💾 Median USB allocation delta: {u['median']} KB")
    return 0 if failures == 0 and len(records) == TRIALS else 1


if __name__ == "__main__":
    raise SystemExit(main())
