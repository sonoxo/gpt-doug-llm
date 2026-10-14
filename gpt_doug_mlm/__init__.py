"""GPT-Doug-MLM: multi-dimensional mathematical proof-search infrastructure."""

from .engine import MultiDimensionalEngine
from .graph import ProofGraph
from .models import Dimension, EvidenceRecord, ProofClaim, ProofState
from .problems import MILLENNIUM_PROBLEMS, get_problem

__all__ = [
    "Dimension",
    "EvidenceRecord",
    "MILLENNIUM_PROBLEMS",
    "MultiDimensionalEngine",
    "ProofClaim",
    "ProofGraph",
    "ProofState",
    "get_problem",
]
