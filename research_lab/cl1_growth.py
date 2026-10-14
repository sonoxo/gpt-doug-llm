"""GPT-Doug CL1 culture-growth evidence tracker (offline and non-actuating).

This tool does not culture cells, access CL1 hardware, stimulate neurons,
diagnose disease, or invent biological measurements. Longitudinal observations
must be supplied by a qualified lab; all such claims are operator-attested.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import importlib.util
import json
import math
import re
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

SCHEMA = "gpt-doug-cl1-culture-observations/v1"
METRICS = {
    "COVERAGE_PERCENT": (0, 100),
    "VIABILITY_PERCENT": (0, 100),
    "MEA_SPIKE_RATE_HZ": (0, 1000000),
}
SOURCES = [
    {
        "title": "Cortical Labs CL API Developer Guide",
        "url": "https://docs.corticallabs.com/",
        "kind": "FIRST_PARTY_API_DOCUMENTATION",
    },
    {
        "title": "Cortical Labs CL1 Product",
        "url": "https://www.corticallabs.com/cl1.html",
        "kind": "VENDOR_PRODUCT_DESCRIPTION",
    },
    {
        "title": "Cortical Labs cl-sdk Simulator",
        "url": "https://github.com/Cortical-Labs/cl-sdk",
        "kind": "FIRST_PARTY_OPEN_SOURCE",
    },
    {
        "title": "CL API device / simulator detection",
        "url": "https://docs.corticallabs.com/cl",
        "kind": "FIRST_PARTY_API_REFERENCE",
    },
]
MAX_JSON_BYTES = 1_048_576
MAX_OBSERVATIONS = 1000
ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,80}$")
SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


def template() -> dict[str, Any]:
    """Empty form, not fabricated observations."""
    return {
        "schema": SCHEMA,
        "culture_id": "REPLACE_WITH_LAB_CULTURE_ID",
        "specimen_class": "CL1_NEURAL_CULTURE",
        "observations": [],
        "data_notice": "Enter real dated lab measurements only; do not insert synthetic growth data.",
    }


def _timestamp(raw: object) -> str:
    if not isinstance(raw, str) or not raw:
        raise ValueError("measurement timestamp_utc is required")
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp_utc must be a valid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp_utc must contain a timezone")
    return parsed.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_record(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("every observation must be a JSON object")
    origin = raw.get("origin")
    if origin not in {"LAB_OPERATOR_ATTESTED", "SDK_SIMULATOR"}:
        raise ValueError("origin must be LAB_OPERATOR_ATTESTED or SDK_SIMULATOR")
    metric = raw.get("metric")
    if metric not in METRICS:
        raise ValueError("unsupported metric: use COVERAGE_PERCENT, VIABILITY_PERCENT or MEA_SPIKE_RATE_HZ")
    if origin == "SDK_SIMULATOR" and metric != "MEA_SPIKE_RATE_HZ":
        raise ValueError("simulator cannot supply biological coverage or viability measurements")

    day = raw.get("day_in_culture")
    if isinstance(day, bool) or not isinstance(day, int) or not 0 <= day <= 3650:
        raise ValueError("day_in_culture must be an integer between 0 and 3650")
    value = raw.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a numeric measurement")
    number = float(value)
    lower, upper = METRICS[metric]
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError("metric value outside supported range")

    operator = raw.get("collector", "")
    if not isinstance(operator, str) or not 1 <= len(operator) <= 80:
        raise ValueError("collector must identify the lab operator or simulator process")
    if any(ord(c) < 32 for c in operator):
        raise ValueError("collector contains control characters")
    method = raw.get("method", "")
    if not isinstance(method, str) or not 1 <= len(method) <= 180:
        raise ValueError("method must describe how this observation was obtained")
    if any(ord(c) < 32 for c in method):
        raise ValueError("method contains control characters")
    digest = raw.get("evidence_sha256")
    if origin == "LAB_OPERATOR_ATTESTED" and (
        not isinstance(digest, str) or SHA_PATTERN.fullmatch(digest) is None
    ):
        raise ValueError("lab-attested observations require a SHA-256 of the evidence artifact")
    if digest is not None and (
        not isinstance(digest, str) or SHA_PATTERN.fullmatch(digest) is None
    ):
        raise ValueError("evidence_sha256 must be a 64-character hexadecimal digest")

    return {
        "timestamp_utc": _timestamp(raw.get("timestamp_utc")),
        "origin": origin,
        "day_in_culture": day,
        "metric": metric,
        "value": number,
        "collector": operator,
        "method": method,
        "evidence_sha256": digest.lower() if digest else None,
        "independently_verified": False,
    }


def validate_document(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("unknown CL1 culture observation schema")
    culture_id = data.get("culture_id")
    if not isinstance(culture_id, str) or ID_PATTERN.fullmatch(culture_id) is None:
        raise ValueError("culture_id must be a nonempty safe identifier (3-80 characters)")
    if data.get("specimen_class") != "CL1_NEURAL_CULTURE":
        raise ValueError("specimen_class must be CL1_NEURAL_CULTURE")
    observations = data.get("observations")
    if not isinstance(observations, list) or len(observations) > MAX_OBSERVATIONS:
        raise ValueError("observations must be an array of at most 1000 records")
    return {
        "schema": SCHEMA,
        "culture_id": culture_id,
        "specimen_class": "CL1_NEURAL_CULTURE",
        "observations": sorted(
            (validate_record(rec) for rec in observations),
            key=lambda rec: (rec["day_in_culture"], rec["timestamp_utc"], rec["metric"]),
        ),
    }


def load_document(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("observation file exceeds 1 MiB")
    try:
        return validate_document(json.loads(raw.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("invalid JSON input") from exc


def assess(document: dict[str, Any]) -> dict[str, Any]:
    data = validate_document(document)
    records = data["observations"]
    lab = [r for r in records if r["origin"] == "LAB_OPERATOR_ATTESTED"]
    simulated = [r for r in records if r["origin"] == "SDK_SIMULATOR"]
    morphology = [
        r for r in lab if r["metric"] == "COVERAGE_PERCENT" and r["evidence_sha256"]
    ]
    # Distinct days and artifacts are mandatory: identical images do not prove a trend.
    timeline: dict[int, dict[str, Any]] = {}
    for rec in morphology:
        timeline[rec["day_in_culture"]] = rec
    distinct = sorted(timeline.values(), key=lambda rec: rec["day_in_culture"])
    change = None
    status = "NO_DIRECT_GROWTH_EVIDENCE"
    if records and not lab:
        status = "SIMULATOR_ONLY_NO_BIOLOGICAL_GROWTH_EVIDENCE"
    elif lab:
        status = "INSUFFICIENT_LONGITUDINAL_MICROSCOPY"
    if (
        len(distinct) >= 2
        and distinct[0]["evidence_sha256"] != distinct[-1]["evidence_sha256"]
    ):
        change = round(distinct[-1]["value"] - distinct[0]["value"], 3)
        status = (
            "LAB_RECORDED_COVERAGE_INCREASE"
            if change > 0
            else "LAB_RECORDED_COVERAGE_DECREASE"
            if change < 0
            else "LAB_RECORDED_COVERAGE_UNCHANGED"
        )
    viability = [r for r in lab if r["metric"] == "VIABILITY_PERCENT"]
    return {
        "schema": "gpt-doug-cl1-culture-growth-assessment/v1",
        "culture_id": data["culture_id"],
        "status": status,
        "culture_created_by_software": False,
        "connected_to_cl1": False,
        "measured_culture_growth_confirmed": False,
        "lab_attested_observation_count": len(lab),
        "simulator_observation_count": len(simulated),
        "total_observation_count": len(records),
        "coverage_change_percentage_points": change,
        "latest_viability_percent": viability[-1]["value"] if viability else None,
        "provenance_level": "LAB_OPERATOR_ATTESTED_NOT_INDEPENDENTLY_VERIFIED"
        if lab else "NO_LAB_BIOLOGICAL_EVIDENCE",
        "limitations": [
            "Coverage change is not proof of neuron proliferation, biological learning, or viable tissue.",
            "Spike rates alone cannot demonstrate cell growth or mitochondrial health.",
            "Lab inputs are operator-attested; artifact hashes do not establish scientific validity.",
            "No CL1 hardware session or live culture access is established by this report.",
        ],
        "observations": records,
        "source_urls": [entry["url"] for entry in SOURCES],
    }


def sdk_status() -> dict[str, Any]:
    try:
        sdk_available = importlib.util.find_spec("cl") is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        sdk_available = False
    return {
        "cl_module_discoverable": sdk_available,
        "cl1_hardware_connection_confirmed": False,
        "live_culture_measured": False,
        "sdk_synthetic_data_can_prove_growth": False,
        "hint": "Official CL API is preinstalled on CL1; local developers can use cl-sdk on Python 3.12+.",
        "sources": SOURCES,
    }


def digest_file(path: Path) -> dict[str, Any]:
    sha = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1_048_576)
            if not chunk:
                break
            length += len(chunk)
            if length > 1_073_741_824:
                raise ValueError("evidence file exceeds 1 GiB hash limit")
            sha.update(chunk)
    return {
        "path": str(path),
        "sha256": sha.hexdigest(),
        "bytes": length,
        "meaning": "Local integrity digest only; not proof of biological growth",
    }


def html_document(report: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value), quote=True)

    rows: list[str] = []
    for obs in report["observations"]:
        pct = obs["value"] if obs["metric"] in {"COVERAGE_PERCENT", "VIABILITY_PERCENT"} else None
        bar = (
            f'<div class="bar"><span style="width:{min(100, max(0, pct)):.2f}%"></span></div>'
            if pct is not None else ""
        )
        rows.append(
            "<tr><td>" + esc(obs["day_in_culture"]) + "</td><td>"
            + esc(obs["timestamp_utc"]) + "</td><td>"
            + esc(obs["metric"]) + "</td><td>"
            + esc(obs["value"]) + bar + "</td><td>"
            + esc(obs["origin"]) + "</td><td><code>"
            + esc((obs["evidence_sha256"] or "NO-DIGEST")[:12]) + "</code></td></tr>"
        )
    rendered_rows = "".join(rows) if rows else (
        '<tr><td colspan="6" class="empty">No real laboratory measurements supplied. '
        "No biological growth or organoid has been claimed.</td></tr>"
    )
    sources = "".join(
        '<li><a href="' + esc(item["url"]) + '" rel="noopener noreferrer">'
        + esc(item["title"]) + "</a><small>" + esc(item["kind"]) + "</small></li>"
        for item in SOURCES
    )
    status = esc(report["status"].replace("_", " "))
    change = (
        "Not measured"
        if report["coverage_change_percentage_points"] is None
        else f'{report["coverage_change_percentage_points"]:+.2f} percentage points'
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>GPT-Doug CL1 Culture Evidence</title><style>
:root{{color-scheme:dark;font-family:system-ui,-apple-system,sans-serif;background:#060f1a;color:#e5f6ff}}
body{{max-width:1280px;margin:auto;padding:clamp(14px,3vw,42px)}}
.header{{display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;border-bottom:1px solid #294052;padding-bottom:18px}}
h1{{font-size:clamp(25px,3vw,38px);margin:8px 0}}h2{{font-size:20px;margin-top:28px}}
p,.muted{{color:#a1bdcd;line-height:1.65}}.tag{{padding:7px 10px;border:1px solid #436577;border-radius:24px;font:700 12px monospace}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:26px 0}}
.card{{background:#101f2c;border:1px solid #294052;border-radius:14px;padding:18px}}
.card strong{{display:block;font-size:27px;margin:12px 0;color:#8ff5e6}}
.card small{{color:#9db4c4;font-weight:700;letter-spacing:.06em}}
table{{width:100%;border-collapse:collapse;background:#101e2a;border-radius:12px;overflow:hidden}}
th,td{{padding:13px 12px;text-align:left;border-bottom:1px solid #2b4454;font-size:12px}}
th{{color:#8ff5e6}}.scroll{{overflow:auto}}.empty{{text-align:center;padding:36px;color:#c5d3e0}}
.bar{{width:140px;height:6px;margin-top:5px;background:#28404d;border-radius:5px}}
.bar span{{display:block;height:6px;background:#4fdec9;border-radius:5px}}
li{{margin:12px 0}}a{{color:#a8dafa}}li small{{display:block;color:#99aebb}}
.note{{border-left:3px solid #dda66c;padding:12px 16px;background:#2b241e}}
</style></head>
<body><div class="header"><div><div class="muted">GPT-DOUG-MAX / BIOPINEAL / CL1</div>
<h1>Neural Culture Growth Evidence</h1><p>Offline evidence view • no live CL1 connection • no fabricated readings</p>
</div><span class="tag">RESEARCH / OPERATOR-ATTESTED</span></div>
<div class="grid">
<div class="card"><small>CULTURE ID</small><strong>{esc(report["culture_id"])}</strong></div>
<div class="card"><small>BIOLOGICAL GROWTH</small><strong>NOT CONFIRMED</strong></div>
<div class="card"><small>GROWTH EVIDENCE STATUS</small><strong style="font-size:16px">{status}</strong></div>
<div class="card"><small>RECORDED COVERAGE CHANGE</small><strong style="font-size:21px">{esc(change)}</strong></div>
</div>
<h2>Lab-submitted observation timeline</h2><div class="scroll"><table><thead>
<tr><th>Culture day</th><th>Timestamp (UTC)</th><th>Measurement</th>
<th>Value</th><th>Origin</th><th>Evidence SHA-256 prefix</th></tr></thead><tbody>
{rendered_rows}</tbody></table></div>
<h2>Evidence interpretation boundary</h2><div class="note">
Lab observations are operator-attested, not independently verified. Even recorded
increases in cell coverage do not establish proliferation, neural learning, viable
organoid growth, or medical efficacy. MEA spike-rate changes are not growth metrics.
</div>
<h2>What is needed for a real CL1 growth claim</h2><ol>
<li>Authorized access to an actual CL1 device or vendor-managed biology program</li>
<li>Documented culture identity and approved cell provenance</li>
<li>Repeated microscope images and viability assays collected by qualified personnel</li>
<li>Direct source files and evidence hashes, dated and independently reviewed</li>
<li>Optional CL1 MEA recordings as separate functional evidence, not morphology proof</li>
</ol>
<h2>Primary documentation</h2><ul>{sources}</ul>
<p class="muted">Standalone HTML created locally. It never contacts a server or operates biological equipment.</p>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="cmd", required=True)
    commands.add_parser("status", help="SDK discovery only, no hardware access")
    commands.add_parser("template", help="print an empty observation template")
    assess_cmd = commands.add_parser("assess", help="validate and assess a local lab record")
    assess_cmd.add_argument("input", type=Path)
    show = commands.add_parser("show", help="open a truthful offline growth dashboard")
    show.add_argument("--input", type=Path, help="optional operator-attested JSON observations")
    show.add_argument("--output", type=Path, help="HTML output path")
    show.add_argument("--no-open", action="store_true")
    hash_cmd = commands.add_parser("hash", help="hash an existing local lab evidence file")
    hash_cmd.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "status":
            output: Any = sdk_status()
        elif args.cmd == "template":
            output = template()
        elif args.cmd == "assess":
            output = assess(load_document(args.input))
        elif args.cmd == "hash":
            output = digest_file(args.file)
        else:
            report = assess(load_document(args.input) if args.input else template())
            if args.output:
                destination = args.output.expanduser().resolve()
                destination.parent.mkdir(parents=True, exist_ok=True)
            else:
                with tempfile.NamedTemporaryFile(
                    prefix="gpt-doug-cl1-growth-", suffix=".html", delete=False
                ) as handle:
                    destination = Path(handle.name)
            destination.write_text(html_document(report), encoding="utf-8")
            output = {
                "status": report["status"],
                "dashboard": destination.as_uri(),
                "hardware_connected": False,
                "biological_growth_confirmed": False,
            }
            if not args.no_open:
                output["browser_open_requested"] = webbrowser.open(destination.as_uri())
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"GPT-Doug CL1 growth: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
