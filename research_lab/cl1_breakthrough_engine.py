"""Bounded brute-force research hypothesis search for GPT-Doug CL1 / organoid work.

This is computational hypothesis generation over public evidence. It does not
control CL1 hardware, grow organoids, prescribe treatment, or execute wet-lab
procedures. The search exhaustively enumerates a bounded Cartesian product of
research dimensions, applies evidence and falsifiability scoring, and reports
the highest-priority hypotheses with explicit validation gates.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "intel" / "sources" / "cl1-breakthrough-research-2026-10-13.json"

MODALITIES = (
    "cl1_simulator_electrophysiology",
    "cl1_bnn_electrophysiology_reference",
    "patient_derived_tumor_organoid_response",
    "molecular_profile_gmro",
    "mitochondrial_imaging_reference",
    "metabolic_assay_reference",
)
QUESTIONS = (
    "predict_response",
    "detect_resistance",
    "measure_reproducibility",
    "link_electrical_and_metabolic_state",
    "rank_candidate_interventions",
)
ENDPOINTS = (
    "replicated_response",
    "prediction_calibration",
    "network_dynamics",
    "mitochondrial_state",
    "clinical_outcome_alignment",
)
VALIDATION = (
    "independent_replication",
    "prospective_holdout",
    "orthogonal_measurement",
    "registered_clinical_evidence",
)
DOMAINS = ("oncology", "neurocomputing")


def load_corpus() -> dict[str, Any]:
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    if data.get("schema") != "gpt-doug-cl1-breakthrough-evidence/v1":
        raise ValueError("unexpected breakthrough corpus schema")
    return data


def _score(domain: str, modality: str, question: str, endpoint: str, validation: str) -> tuple[int, list[str]]:
    score = 0
    rationale: list[str] = []

    if validation in {"independent_replication", "prospective_holdout", "orthogonal_measurement"}:
        score += 3
        rationale.append("strong validation gate")
    if validation == "registered_clinical_evidence":
        score += 4
        rationale.append("human evidence linkage")

    if domain == "oncology":
        if modality == "patient_derived_tumor_organoid_response":
            score += 5
            rationale.append("direct 2026 functional-organoid evidence")
        if modality == "molecular_profile_gmro":
            score += 4
            rationale.append("molecular + clinical ontology integration")
        if endpoint == "clinical_outcome_alignment":
            score += 4
            rationale.append("translational endpoint")
        if question in {"predict_response", "detect_resistance", "rank_candidate_interventions"}:
            score += 3
            rationale.append("clinically relevant research question")
        if modality.startswith("cl1_"):
            score -= 3
            rationale.append("CL1 is not a tumor-organoid platform")

    if domain == "neurocomputing":
        if modality == "cl1_simulator_electrophysiology":
            score += 4
            rationale.append("official simulator supports reproducible software benchmarking")
        if modality == "cl1_bnn_electrophysiology_reference":
            score += 5
            rationale.append("CL1's core measured modality is electrophysiology")
        if question == "measure_reproducibility":
            score += 4
            rationale.append("high-value closed-loop benchmark")
        if endpoint == "network_dynamics":
            score += 4
            rationale.append("directly observable electrophysiology endpoint")
        if modality == "patient_derived_tumor_organoid_response":
            score -= 4
            rationale.append("oncology PDO evidence does not establish neural-computing behavior")

    if question == "link_electrical_and_metabolic_state":
        if modality in {"mitochondrial_imaging_reference", "metabolic_assay_reference"}:
            score += 2
            rationale.append("metabolic question requires orthogonal metabolic measurement")
        else:
            score -= 6
            rationale.append("do not infer mitochondrial state from spikes alone")
    if endpoint == "mitochondrial_state" and modality.startswith("cl1_"):
        score -= 7
        rationale.append("public CL1 API does not expose mitochondrion-resolved telemetry")

    if modality == "mitochondrial_imaging_reference" and validation == "orthogonal_measurement":
        score += 2
        rationale.append("explicit multimodal validation")
    return score, rationale


def enumerate_hypotheses(domain: str | None = None) -> list[dict[str, Any]]:
    domains = (domain,) if domain else DOMAINS
    rows: list[dict[str, Any]] = []
    for d, m, q, e, v in itertools.product(domains, MODALITIES, QUESTIONS, ENDPOINTS, VALIDATION):
        score, rationale = _score(d, m, q, e, v)
        rows.append({
            "id": f"{d}:{m}:{q}:{e}:{v}",
            "domain": d,
            "modality": m,
            "question": q,
            "endpoint": e,
            "validation": v,
            "score": score,
            "rationale": rationale,
            "claim_status": "HYPOTHESIS_ONLY",
        })
    rows.sort(key=lambda row: (-row["score"], row["id"]))
    return rows


def breakthroughs(domain: str | None = None, top: int = 12) -> dict[str, Any]:
    if not 1 <= top <= 50:
        raise ValueError("top must be 1..50")
    corpus = load_corpus()
    rows = enumerate_hypotheses(domain)
    return {
        "engine": "GPT-DOUG-BOUNDED-BRUTE-FORCE-RESEARCH",
        "domain": domain or "all",
        "enumerated": len(rows),
        "top": rows[:top],
        "research_gaps": corpus["research_gaps"],
        "safety_boundaries": [
            "No physical CL1 control",
            "No wet-lab organoid creation",
            "No treatment recommendation",
            "No mitochondrial inference from neural spikes alone",
            "Human review required before any experimental translation",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=DOMAINS)
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args(argv)
    print(json.dumps(breakthroughs(args.domain, args.top), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
