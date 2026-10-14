"""GPT-Doug BioPineal: read-only patent provenance and research coordination.

Only bibliographic metadata is included; patent claims are not validated findings.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Dict, List

from .biochip_research import ResearchRouter


@dataclass(frozen=True)
class PatentReference:
    patent_id: str
    title: str
    assignee: str
    publication_date: str
    topic: str
    source: str = "user-provided USPTO Patent Public Search excerpt"
    status: str = "bibliographic reference; independent verification pending"


REFERENCES = (
    PatentReference("US12760085B1", "Enhanced T-cell receptor star and application thereof",
                    "CHINA IMMUNOTECH (BEIJING) BIOTECHNOLOGY CO., LTD.", "2026-10-13",
                    "immunotherapy"),
    PatentReference("US12760292B2",
                    "Base editors, compositions, and methods for modifying the mitochondrial genome",
                    "The Broad Institute, Inc.; University of Washington; President and Fellows of Harvard College",
                    "2026-10-13", "mitochondria"),
    PatentReference("US12757878B2",
                    "System for detecting extracellular purinergic receptor ligand, and non-human animal having the system introduced thereinto",
                    "Chugai Seiyaku Kabushiki Kaisha", "2026-10-13", "biosensor"),
)


class BioPineal:
    """Ontology-ready public patent context with no synthesis or wet-lab execution."""

    def __init__(self) -> None:
        self.references: Dict[str, PatentReference] = {p.patent_id: p for p in REFERENCES}

    def search(self, topic: str) -> List[dict]:
        needle = topic.strip().casefold()
        if not needle:
            raise ValueError("A nonempty topic is required")
        return [asdict(p) for p in self.references.values()
                if needle in p.topic.casefold() or needle in p.title.casefold()]

    def review(self, topic: str, router: ResearchRouter) -> dict:
        evidence = self.search(topic)
        question = ("Summarize the following third-party bibliographic references. "
                    "Do not assert clinical effectiveness, ownership or experimentation: "
                    + json.dumps(evidence, sort_keys=True))
        return {"topic": topic, "references": evidence,
                "model_candidates": [asdict(c) for c in router.deliberate(question)],
                "approval": "human_review_required"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-biopineal")
    parser.add_argument("command", choices=["status", "patents"])
    parser.add_argument("--topic", default="mitochondria")
    args = parser.parse_args()
    core = BioPineal()
    result = ({"name": "gpt-doug-biopineal", "backend": "gpt-doug-mlm",
               "orchestrator": "gpt-doug-llm", "mode": "offline_research",
               "reference_count": len(core.references)}
              if args.command == "status" else core.search(args.topic))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
