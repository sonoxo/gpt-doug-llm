"""GPT-DOUG bounded metacognition package."""
from .swarm import Candidate, Review, merge_review_signals, review_candidate, run_review_rounds

__all__ = ["Candidate", "Review", "review_candidate", "run_review_rounds", "merge_review_signals"]
