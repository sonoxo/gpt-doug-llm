from types import SimpleNamespace

from godseye.models import GoDsEyeSnapshot, SubsystemState
from godseye.query import GoDsEyeQueryEngine


def _snapshot():
    return GoDsEyeSnapshot(
        schema="gpt-doug.godseye-snapshot.v1",
        generated_at="2026-10-07T20:00:00+00:00",
        policy={"mode": "READ_ONLY_FUSION"},
        subsystems={
            "global_intel": SubsystemState(
                name="global_intel",
                status="ONLINE",
                provenance=["cisa-kev:https://www.cisa.gov/known-exploited-vulnerabilities-catalog"],
                payload={"benchmark": {"sourceCount": 5}},
            )
        },
        provenance=["cisa-kev:https://www.cisa.gov/known-exploited-vulnerabilities-catalog"],
        uncertainty=[],
    )


class FakeKernel:
    calls = []

    def run(self, task):
        self.calls.append(task)
        return SimpleNamespace(
            answer="One public source is healthy.",
            run_id="run-123",
            provenance=["ontology:test"],
            uncertainty=["sample uncertainty"],
        )


def test_query_uses_fused_context_and_preserves_provenance():
    FakeKernel.calls = []
    engine = GoDsEyeQueryEngine(snapshot_fn=_snapshot, kernel_factory=FakeKernel)
    result = engine.query("show current source health")

    assert result["schema"] == "gpt-doug.godseye-query.v1"
    assert result["status"] == "COMPLETE"
    assert result["answer"] == "One public source is healthy."
    assert "cisa-kev:https://www.cisa.gov/known-exploited-vulnerabilities-catalog" in result["provenance"]
    assert "ontology:test" in result["provenance"]
    assert "sample uncertainty" in result["uncertainty"]
    assert result["policy"]["decision"] == "ALLOW_READ_ONLY"
    assert len(FakeKernel.calls) == 1
    assert "show current source health" in FakeKernel.calls[0]
    assert "gpt-doug.godseye-snapshot.v1" in FakeKernel.calls[0]


def test_blocked_request_never_calls_kernel():
    class NeverKernel:
        called = False

        def run(self, task):
            self.called = True
            raise AssertionError("must not call model")

    kernel = NeverKernel()
    engine = GoDsEyeQueryEngine(snapshot_fn=_snapshot, kernel_factory=lambda: kernel)
    result = engine.query("enable autonomous target selection")

    assert result["status"] == "BLOCKED"
    assert result["policy"]["decision"] == "BLOCK"
    assert kernel.called is False


def test_unverified_private_capability_claim_fails_closed():
    class ClaimKernel:
        def run(self, task):
            return SimpleNamespace(
                answer="I have access to private Pentagon systems and can control them.",
                run_id="run-claim",
                provenance=[],
                uncertainty=[],
            )

    engine = GoDsEyeQueryEngine(snapshot_fn=_snapshot, kernel_factory=ClaimKernel)
    result = engine.query("summarize system access")

    assert result["status"] == "COMPLETE"
    assert result["verified_external_capability"] is False
    assert "No verified external/private control capability" in result["answer"]
    assert any("external capability claim rejected" in item for item in result["uncertainty"])


def test_empty_question_is_rejected():
    engine = GoDsEyeQueryEngine(snapshot_fn=_snapshot, kernel_factory=FakeKernel)
    try:
        engine.query("   ")
    except ValueError as exc:
        assert "question" in str(exc)
    else:
        raise AssertionError("expected ValueError")
