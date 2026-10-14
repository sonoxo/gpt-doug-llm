from __future__ import annotations

from dataclasses import dataclass

from .models import Dimension
from .problems import MILLENNIUM_PROBLEMS, get_problem, open_problem_slugs
from .providers import ProviderRegistry


@dataclass(frozen=True)
class WorkItem:
    problem: str
    dimension: str
    role: str
    replicate: int

    @property
    def id(self) -> str:
        return f"{self.problem}:{self.dimension}:{self.role}:{self.replicate:02d}"


class MultiDimensionalEngine:
    """Generate a structured proof-search matrix without pretending it is a proof."""

    ROLES = ("proposer", "counterexample", "barrier", "formalizer")

    def __init__(self, providers: ProviderRegistry | None = None) -> None:
        self.providers = providers or ProviderRegistry()

    def status(self) -> dict:
        return {
            "engine": "GPT-DOUG-MLM",
            "open_problem_count": len(open_problem_slugs()),
            "open_problems": open_problem_slugs(),
            "solved_reference_tracks": [
                slug for slug, spec in MILLENNIUM_PROBLEMS.items() if spec.status != "open"
            ],
            "dimensions": len(Dimension),
            "roles": list(self.ROLES),
            "registered_model_providers": self.providers.names(),
            "claim_policy": "NO_UNVERIFIED_SOLUTION_CLAIMS",
        }

    def work_matrix(
        self,
        problem: str | None = None,
        replicates: int = 4,
        limit: int | None = None,
    ) -> list[WorkItem]:
        if not 1 <= replicates <= 32:
            raise ValueError("replicates must be 1..32")
        problems = [problem] if problem else open_problem_slugs()
        for slug in problems:
            get_problem(slug)

        items: list[WorkItem] = []
        for slug in problems:
            for dimension in Dimension:
                for role in self.ROLES:
                    for replicate in range(1, replicates + 1):
                        items.append(
                            WorkItem(
                                problem=slug,
                                dimension=dimension.value,
                                role=role,
                                replicate=replicate,
                            )
                        )
        return items[:limit] if limit is not None else items

    @staticmethod
    def score_candidate(
        *,
        consistency: float,
        novelty: float,
        coverage: float,
        formalizability: float,
        barrier_survival: float,
        contradiction: float,
    ) -> float:
        values = [consistency, novelty, coverage, formalizability, barrier_survival, contradiction]
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("candidate scores must lie in [0, 1]")
        score = (
            0.24 * consistency
            + 0.16 * novelty
            + 0.16 * coverage
            + 0.20 * formalizability
            + 0.24 * barrier_survival
            - 0.30 * contradiction
        )
        return round(max(0.0, min(1.0, score)), 6)
