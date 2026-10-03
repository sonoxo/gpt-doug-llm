#!/usr/bin/env python3
"""GPT-Doug Global Skill Lattice.

Exactly 100,000,000 deterministic skill addresses:
100 sectors × 100 capabilities × 100 workflows × 100 delivery modes.

This is a lazy metadata lattice, not 100M pretrained expert models.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable

MAJOR_DOMAINS = [
    ("global-economy", ["macroeconomic-analysis","supply-chains","small-business","labor-markets","productivity","trade-logistics","manufacturing","energy-markets","agriculture-food","economic-resilience"]),
    ("ai-infrastructure", ["compute-capacity","datacenters","model-serving","observability","accelerators","networking","storage","energy-efficiency","reliability","capacity-planning"]),
    ("public-sector", ["service-delivery","emergency-management","procurement","grants","open-data","digital-services","compliance","infrastructure","operations","program-evaluation"]),
    ("defensive-intelligence", ["threat-intelligence","osint","fraud-risk","supply-chain-risk","incident-response","vulnerability-management","resilience","provenance","information-integrity","situational-awareness"]),
    ("music", ["songwriting","production","mixing","mastering","release-strategy","rights-metadata","live-performance","fan-analytics","catalog-management","sync-licensing"]),
    ("arts", ["concept-art","illustration","brand-systems","motion-design","three-d","photography","portfolio","exhibition","licensing","archiving"]),
    ("software-development", ["architecture","backend","frontend","mobile","devops","testing","security","data-engineering","ml-engineering","documentation"]),
    ("education-research", ["curriculum","tutoring","literature-review","experiment-design","data-analysis","reproducibility","knowledge-management","research-ops","open-science","technical-writing"]),
    ("climate-infrastructure", ["grid-resilience","transportation","water","buildings","renewables","efficiency","risk-modeling","maintenance","geospatial-analysis","disaster-resilience"]),
    ("creative-economy", ["entrepreneurship","product-design","marketing","commerce","audience-development","operations","finance-ops","partnerships","community","portfolio-strategy"]),
]

CAPABILITY_VERBS = [
    "analyze","design","build","optimize","forecast",
    "map","verify","document","coordinate","teach",
]
CAPABILITY_GOALS = [
    "baseline","strategy","automation","quality","reliability",
    "discovery","risk-reduction","growth","accessibility","resilience",
]

WORKFLOW_STAGES = [
    "observe","research","plan","prototype","simulate",
    "execute","test","review","repair","measure",
]
WORKFLOW_METHODS = [
    "baseline","scenario","checklist","benchmark","experiment",
    "sandbox","peer-review","evidence-gate","rollback-ready","continuous-improvement",
]

AUDIENCES = [
    "operator","developer","artist","musician","researcher",
    "small-business","public-service-team","engineering-team","executive","community",
]
DELIVERABLES = [
    "brief","checklist","dashboard","code","runbook",
    "report","roadmap","dataset","workshop","decision-log",
]

SECTORS = [f"{domain}/{focus}" for domain, focuses in MAJOR_DOMAINS for focus in focuses]
CAPABILITIES = [f"{verb}/{goal}" for verb in CAPABILITY_VERBS for goal in CAPABILITY_GOALS]
WORKFLOWS = [f"{stage}/{method}" for stage in WORKFLOW_STAGES for method in WORKFLOW_METHODS]
DELIVERY_MODES = [f"{audience}/{artifact}" for audience in AUDIENCES for artifact in DELIVERABLES]

assert len(SECTORS) == 100
assert len(CAPABILITIES) == 100
assert len(WORKFLOWS) == 100
assert len(DELIVERY_MODES) == 100

TOTAL_SKILLS = 100 ** 4


@dataclass(frozen=True)
class SkillDescriptor:
    skill_id: int
    sector: str
    capability: str
    workflow: str
    delivery: str
    execution_policy: str = "ONTOLOGY_GROUNDED_POLICY_BOUNDED"
    authority: str = "NO_IMPLIED_EXTERNAL_AUTHORITY"

    @property
    def name(self) -> str:
        return f"{self.sector} :: {self.capability} :: {self.workflow} :: {self.delivery}"


def resolve(skill_id: int) -> SkillDescriptor:
    if not 0 <= skill_id < TOTAL_SKILLS:
        raise ValueError(f"skill_id must be between 0 and {TOTAL_SKILLS - 1}")
    n = skill_id
    delivery_i = n % 100
    n //= 100
    workflow_i = n % 100
    n //= 100
    capability_i = n % 100
    n //= 100
    sector_i = n % 100
    return SkillDescriptor(
        skill_id=skill_id,
        sector=SECTORS[sector_i],
        capability=CAPABILITIES[capability_i],
        workflow=WORKFLOWS[workflow_i],
        delivery=DELIVERY_MODES[delivery_i],
    )


def search(terms: Iterable[str], limit: int = 25):
    words = [w.lower() for w in terms if w.strip()]
    if not words:
        return
    # Search axes independently, then emit deterministic cross-products.
    sector_hits = [i for i, x in enumerate(SECTORS) if all(w in x.lower() for w in words)] or list(range(100))
    cap_hits = [i for i, x in enumerate(CAPABILITIES) if any(w in x.lower() for w in words)] or [0]
    flow_hits = [i for i, x in enumerate(WORKFLOWS) if any(w in x.lower() for w in words)] or [0]
    delivery_hits = [i for i, x in enumerate(DELIVERY_MODES) if any(w in x.lower() for w in words)] or [0]
    emitted = 0
    for si in sector_hits:
        for ci in cap_hits:
            for wi in flow_hits:
                for di in delivery_hits:
                    skill_id = (((si * 100) + ci) * 100 + wi) * 100 + di
                    yield resolve(skill_id)
                    emitted += 1
                    if emitted >= limit:
                        return


def main() -> None:
    p = argparse.ArgumentParser(prog="global_skill_lattice")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("count")

    show = sub.add_parser("show")
    show.add_argument("skill_id", type=int)

    find = sub.add_parser("search")
    find.add_argument("terms", nargs="+")
    find.add_argument("--limit", type=int, default=25)

    args = p.parse_args()

    if args.command == "count":
        print(TOTAL_SKILLS)
    elif args.command == "show":
        d = resolve(args.skill_id)
        print(json.dumps({**asdict(d), "name": d.name}, indent=2))
    elif args.command == "search":
        for d in search(args.terms, args.limit):
            print(f"{d.skill_id:08d}  {d.name}")


if __name__ == "__main__":
    main()
