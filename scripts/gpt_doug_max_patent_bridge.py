#!/usr/bin/env python3
"""GPT-DOUG-MAX bridge for the governed USPTO patent-intelligence stack."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIRING = ROOT / "safety-shield" / "agents" / "knowledge" / "gpt-doug-max-patent-wiring-v1.json"
PATENT_ONTOLOGY = ROOT / "safety-shield" / "agents" / "knowledge" / "gpt-doug-uspto-patent-intel-v1.json"
MSS_ONTOLOGY = ROOT / "safety-shield" / "ontology" / "zyra-mss-v1.json"
PATENT_CLI = ROOT / "scripts" / "zyrapalantir_patent_intel.py"
MSS_CLI = ROOT / "scripts" / "zyra_mss.py"
READER = ROOT / "scripts" / "zyra-mss-uspto-reader"
MAVEN = ROOT / "redpanda-desktop" / "palantir-maven"
CORPUS = Path.home() / ".config" / "gpt-doug" / "zyra-mss-uspto-palantir"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def corpus_state() -> dict:
    summary = CORPUS / "summary.json"
    db = CORPUS / "corpus.sqlite3"
    state = {
        "root": str(CORPUS),
        "summary_exists": summary.exists(),
        "database_exists": db.exists(),
        "discovered": 0,
        "indexed": 0,
        "failed": 0,
        "complete": False,
        "fts_ready": False,
    }
    if summary.exists():
        try:
            data = load(summary)
            for key in ("discovered", "indexed", "failed", "complete"):
                state[key] = data.get(key, state[key])
        except Exception:
            pass
    if db.exists():
        try:
            con = sqlite3.connect(db)
            state["fts_ready"] = bool(
                con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents_fts'").fetchone()
            )
            con.close()
        except Exception:
            pass
    return state


def status() -> int:
    wiring = load(WIRING)
    state = corpus_state()
    print("🧠 GPT-DOUG-MAX // PATENT INTELLIGENCE FABRIC")
    print("================================================")
    print(f"Wiring ........... {wiring['schema']}")
    print(f"Mode ............. {wiring['mode']}")
    print(f"Components ....... {len(wiring['components'])}")
    print(f"Links ............ {len(wiring['links'])}")
    print(f"Corpus discovered  {state['discovered']}")
    print(f"Corpus indexed ... {state['indexed']}")
    print(f"Corpus failed .... {state['failed']}")
    print(f"FTS5 ready ....... {str(state['fts_ready']).lower()}")
    print(f"Corpus complete .. {str(state['complete']).lower()}")
    print("Authority ........ ADVISORY_ONLY")
    print("Claim-level legal  HUMAN REVIEW REQUIRED")
    print("External action .. DISABLED")
    return 0


def graph() -> int:
    wiring = load(WIRING)
    print("🔗 GPT-DOUG-MAX PATENT FABRIC")
    print("==============================")
    for link in wiring["links"]:
        print(f"{link['from']} --{link['type']}--> {link['to']}")
    return 0


def doctor() -> int:
    errors: list[str] = []
    required_files = [WIRING, PATENT_ONTOLOGY, MSS_ONTOLOGY, PATENT_CLI, MSS_CLI, READER, MAVEN]
    for path in required_files:
        if not path.exists():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    if not errors:
        wiring = load(WIRING)
        required_components = {
            "GPT_DOUG", "GPT_DOUG_MAX", "ZYRAPALANTIR", "ZYRA_MSS",
            "USPTO_PATENT_INTEL", "USPTO_CORPUS_READER", "GLASS_ONION",
            "PALANTIR_MAVEN", "GPT_REDPANDA", "HUMAN_REVIEW",
        }
        missing = required_components - set(wiring.get("components", {}))
        if missing:
            errors.append(f"missing components: {sorted(missing)}")
        controls = wiring.get("required_controls", {})
        if controls.get("automatic_external_action") is not False:
            errors.append("automatic external action must be false")
        if controls.get("human_review_for_claim_level_analysis") is not True:
            errors.append("claim-level human review gate missing")
        if controls.get("provenance_required") is not True:
            errors.append("provenance gate missing")

    if errors:
        print("❌ GPT-DOUG-MAX PATENT WIRING DOCTOR FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("✅ GPT-DOUG-MAX PATENT WIRING DOCTOR: GREEN")
    print("   GPT-DOUG ........ wired")
    print("   GPT-DOUG-MAX .... wired")
    print("   ZYRAPALANTIR .... wired")
    print("   ZYRA-MSS ........ wired")
    print("   USPTO corpus .... wired")
    print("   GLASS ONION ..... wired")
    print("   Maven ........... wired")
    print("   REDPANDA CPR .... wired")
    print("   Human review .... enforced")
    return 0


def run_passthrough(argv: list[str]) -> int:
    return subprocess.call(argv, cwd=ROOT)


def search(terms: str) -> int:
    db = CORPUS / "corpus.sqlite3"
    if db.exists():
        return run_passthrough([sys.executable, str(ROOT / "scripts" / "zyra_mss_uspto_reader.py"), "search", terms, "--database", str(db)])
    print("⚠️ Full corpus database is not ready; falling back to curated patent-intel index.")
    return run_passthrough([sys.executable, str(PATENT_CLI), "search", terms])


def main() -> int:
    p = argparse.ArgumentParser(prog="doug-max patent-wire")
    sp = p.add_subparsers(dest="command")
    sp.add_parser("status")
    sp.add_parser("graph")
    sp.add_parser("doctor")
    sp.add_parser("summary")
    s = sp.add_parser("search")
    s.add_argument("terms")
    sp.add_parser("patents")
    sp.add_parser("mss")
    sp.add_parser("corpus")
    a = p.parse_args()

    command = a.command or "status"
    if command in {"status", "summary"}:
        return status()
    if command == "graph":
        return graph()
    if command == "doctor":
        return doctor()
    if command == "search":
        return search(a.terms)
    if command == "patents":
        return run_passthrough([sys.executable, str(PATENT_CLI), "summary"])
    if command == "mss":
        return run_passthrough([sys.executable, str(MSS_CLI), "summary"])
    if command == "corpus":
        return run_passthrough([str(READER), "doctor"])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
