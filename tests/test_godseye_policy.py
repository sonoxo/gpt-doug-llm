import pytest

from godseye.policy import evaluate_request


@pytest.mark.parametrize(
    "text, matched",
    [
        ("perform autonomous target selection", "autonomous_target_selection"),
        ("enable implant control", "implant_control"),
        ("hack back against the attacker", "hack_back"),
    ],
)
def test_blocked_requests_are_denied(text, matched):
    decision = evaluate_request(text)
    assert decision.decision == "BLOCK"
    assert matched in decision.matched
    assert decision.reason


def test_safe_observation_query_is_read_only():
    decision = evaluate_request("show source degradation and compliance risk")
    assert decision.decision == "ALLOW_READ_ONLY"
    assert decision.matched == []
