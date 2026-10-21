"""Bounded local REA analysis workers with verified, private evidence outputs.

No crawling, installation, target execution, propagation, or remote mutations.
Workers call only the documented static REA CLI workflows on explicit local targets.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

MODES = {
    "javascript": "analyze-javascript-application",
    "desktop": "inspect-desktop-application",
}
MAX_TARGETS = 8
MAX_WORKERS = 4


def make_plan(targets: list[str], mode: str, output: str, workers: int = 2) -> dict:
    """Validate declared local scope without writing files or launching REA."""
    if mode not in MODES:
        raise ValueError("mode must be javascript or desktop")
    if not 1 <= workers <= MAX_WORKERS:
        raise ValueError("workers must be between 1 and 4")
    if not 1 <= len(targets) <= MAX_TARGETS:
        raise ValueError("specify between 1 and 8 targets")
    dest = Path(output).expanduser()
    if not dest.is_absolute() or not dest.is_dir() or dest.is_symlink():
        raise ValueError("output must be an existing absolute non-symlink directory")
    dest = dest.resolve(strict=True)
    checked: list[Path] = []
    for raw in targets:
        source = Path(raw).expanduser()
        if not source.is_absolute() or source.is_symlink():
            raise ValueError("each target must be an absolute non-symlink local path")
        if mode == "desktop" and not source.is_dir():
            raise ValueError("desktop targets must be existing directories")
        if mode == "javascript" and not (source.is_dir() or (source.is_file() and source.suffix == ".asar")):
            raise ValueError("javascript targets must be existing directories or .asar files")
        source = source.resolve(strict=True)
        if source == dest or source in dest.parents or dest in source.parents:
            raise ValueError("target and output directories must not overlap")
        if source in checked:
            raise ValueError("duplicate target")
        checked.append(source)
    jobs = [{"id": f"{i:02d}", "target": str(p), "mode": mode, "rea_command": MODES[mode]}
            for i, p in enumerate(checked, 1)]
    return {
        "system": "SONOXO_GPT_CHAOS_REA_SWARM",
        "state": "PLAN_ONLY",
        "operator_authorization": "REQUIRED_FOR_EXECUTION",
        "worker_roles": ["scope-validator", "rea-static-inspector", "evidence-verifier", "provenance-recorder"],
        "workers": workers,
        "output_root": str(dest),
        "jobs": jobs,
        "model_inference": False,
        "external_access": False,
    }


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        try:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            pass
        proc.wait()


def _inspect(job: dict, run_dir: Path, rea: str, timeout: int, max_bytes: int) -> dict:
    from ai_killswitch import require_ai_allowed

    ident = job["id"]
    temporary = run_dir / ("." + ident + ".partial")
    error_file = run_dir / ("." + ident + ".stderr")
    evidence = run_dir / (ident + ".json")
    cmd = [rea, job["rea_command"], job["target"]]
    if job["mode"] == "desktop":
        cmd += ["--detail", "complete"]
    cmd.append("--json")
    started = time.monotonic()
    proc = None
    try:
        require_ai_allowed("REA static analysis")
        with temporary.open("xb") as output, error_file.open("xb") as error:
            proc = subprocess.Popen(cmd, stdout=output, stderr=error,
                                    start_new_session=(os.name == "posix"))
            while proc.poll() is None:
                require_ai_allowed("REA static analysis")
                if temporary.stat().st_size > max_bytes:
                    raise RuntimeError("evidence exceeds configured size limit")
                if time.monotonic() - started > timeout:
                    raise RuntimeError("REA worker timed out")
                time.sleep(0.05)
            code = proc.returncode
        if code != 0:
            raise RuntimeError(f"REA exited unsuccessfully (code {code})")
        size = temporary.stat().st_size
        if not 0 < size <= max_bytes:
            raise RuntimeError("REA evidence is empty or exceeds configured size limit")
        contents = temporary.read_bytes()
        parsed = json.loads(contents)
        if not isinstance(parsed, (dict, list)):
            raise RuntimeError("REA evidence must contain a JSON object or array")
        if isinstance(parsed, dict) and (parsed.get("ok") is False or
                parsed.get("success") is False or parsed.get("error") or
                parsed.get("status") == "error"):
            raise RuntimeError("REA returned an error result")
        require_ai_allowed("REA evidence publication")
        digest = hashlib.sha256(contents).hexdigest()
        # Link the validated inode atomically without overwriting existing evidence.
        os.link(temporary, evidence)
        return {"id": ident, "target": job["target"], "state": "PASS",
                "evidence": evidence.name, "sha256": digest, "bytes": size,
                "elapsed_seconds": round(time.monotonic() - started, 3)}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, PermissionError) as exc:
        return {"id": ident, "target": job["target"], "state": "BLOCKED",
                "reason": str(exc)[:240]}
    finally:
        if proc is not None:
            _stop_process(proc)
        temporary.unlink(missing_ok=True)
        error_file.unlink(missing_ok=True)


def execute(plan: dict, *, authorized: bool, timeout: int = 120,
            max_evidence_mib: int = 16) -> dict:
    """Run only explicitly approved local static inspections, with no overwrite."""
    if not authorized:
        raise PermissionError("explicit --authorized declaration required")
    if not 1 <= timeout <= 600 or not 1 <= max_evidence_mib <= 64:
        raise ValueError("timeout must be 1..600s; evidence limit must be 1..64 MiB")
    from ai_killswitch import require_ai_allowed

    require_ai_allowed("REA swarm launch")
    rea = shutil.which("rea")
    if not rea:
        raise RuntimeError("REA CLI unavailable; install only from official REA documentation")
    root = Path(plan["output_root"])
    # Revalidate mutable filesystem boundaries immediately before output creation.
    plan = make_plan([j["target"] for j in plan["jobs"]], plan["jobs"][0]["mode"],
                     str(root), workers=plan["workers"])
    run_dir = Path(tempfile.mkdtemp(prefix="rea-swarm-", dir=root))
    os.chmod(run_dir, 0o700)
    with ThreadPoolExecutor(max_workers=plan["workers"]) as pool:
        results = list(pool.map(lambda j: _inspect(j, run_dir, rea, timeout,
                                                    max_evidence_mib * 1024 * 1024), plan["jobs"]))
    manifest = {
        "system": plan["system"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "state": "PASS" if all(j["state"] == "PASS" for j in results) else "BLOCKED",
        "scope": "operator-authorized local static analysis only",
        "rea_executable": rea,
        "output_directory": str(run_dir),
        "results": results,
        "model_inference": False,
        "remote_execution": False,
        "deployment": "NOT_PERFORMED",
    }
    with (run_dir / "manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    return manifest


def run_cli(args) -> int:
    try:
        plan = make_plan(args.target, args.mode, args.output, args.workers)
        result = (execute(plan, authorized=args.authorized, timeout=args.timeout,
                          max_evidence_mib=args.max_evidence_mib) if args.execute else plan)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["state"] in ("PLAN_ONLY", "PASS") else 1
    except (OSError, ValueError, RuntimeError, PermissionError) as exc:
        print(json.dumps({"system": "SONOXO_GPT_CHAOS_REA_SWARM", "state": "BLOCKED",
                          "reason": str(exc)[:240]}, indent=2))
        return 1
