import pytest

from gpt_doug_mlm.barriers import evaluate_barriers
from gpt_doug_mlm.engine import MultiDimensionalEngine
from gpt_doug_mlm.graph import ProofGraph
from gpt_doug_mlm.models import Dimension, EvidenceRecord, ProofClaim, ProofState
from gpt_doug_mlm.problems import MILLENNIUM_PROBLEMS, open_problem_slugs
from gpt_doug_mlm.providers import CallableProvider, ProviderRegistry


def test_six_open_problems_and_poincare_reference():
    assert len(open_problem_slugs()) == 6
    assert MILLENNIUM_PROBLEMS["poincare"].status == "solved_reference"


def test_sixteen_dimensions():
    assert len(Dimension) == 16


def test_default_matrix_covers_all_open_tracks():
    engine = MultiDimensionalEngine()
    items = engine.work_matrix(replicates=1)
    assert len(items) == 6 * 16 * 4
    assert {item.problem for item in items} == set(open_problem_slugs())


def test_p_vs_np_barriers_fail_closed():
    report = evaluate_barriers("p-vs-np", ["relativization"])
    assert report.passed is False
    assert set(report.missing) == {"natural_proofs", "algebrization"}

    report = evaluate_barriers(
        "p-vs-np",
        ["relativization", "natural_proofs", "algebrization"],
    )
    assert report.passed is True


def test_proof_graph_rejects_state_jump():
    graph = ProofGraph()
    graph.add_claim(ProofClaim("c1", "riemann", "candidate lemma"))
    with pytest.raises(ValueError):
        graph.promote("c1", ProofState.LEMMA_PROVEN)


def test_full_gate_requires_real_evidence_and_two_verifiers():
    graph = ProofGraph()
    graph.add_claim(ProofClaim("c1", "riemann", "candidate lemma"))

    graph.add_evidence("c1", EvidenceRecord("numerical", "local", "finite sanity checks"))
    graph.promote("c1", ProofState.NUMERICALLY_SUPPORTED)

    graph.add_evidence("c1", EvidenceRecord("symbolic", "cas", "symbolic identity checked"))
    graph.promote("c1", ProofState.SYMBOLICALLY_VERIFIED)

    graph.add_evidence("c1", EvidenceRecord("proof", "manuscript", "complete lemma proof"))
    graph.promote("c1", ProofState.LEMMA_PROVEN)

    graph.add_evidence("c1", EvidenceRecord("formal", "proof-assistant", "kernel accepted"))
    graph.promote("c1", ProofState.FORMALLY_VERIFIED)

    graph.add_verifier("c1", "reviewer-a")
    with pytest.raises(ValueError):
        graph.promote("c1", ProofState.INDEPENDENTLY_VERIFIED)

    graph.add_verifier("c1", "reviewer-b")
    graph.promote("c1", ProofState.INDEPENDENTLY_VERIFIED)

    graph.add_evidence("c1", EvidenceRecord("adversarial_review", "review-board", "no blocking defect"))
    graph.promote("c1", ProofState.PUBLISHABLE)
    assert graph.claims["c1"].state is ProofState.PUBLISHABLE


def test_provider_registry_is_opt_in():
    registry = ProviderRegistry()
    assert registry.names() == []

    provider = CallableProvider("test-model", lambda prompt: prompt, lambda prompt: "review:" + prompt)
    registry.register(provider)
    assert registry.ensemble_review("lemma") == {"test-model": "review:lemma"}


def test_candidate_score_penalizes_contradiction():
    clean = MultiDimensionalEngine.score_candidate(
        consistency=1,
        novelty=0.5,
        coverage=0.7,
        formalizability=0.9,
        barrier_survival=1,
        contradiction=0,
    )
    contradicted = MultiDimensionalEngine.score_candidate(
        consistency=1,
        novelty=0.5,
        coverage=0.7,
        formalizability=0.9,
        barrier_survival=1,
        contradiction=1,
    )
    assert clean > contradicted
