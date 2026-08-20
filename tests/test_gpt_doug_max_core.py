from doug_core.core_profile import can_mark_verified, get_core_profile
from doug_core.runtime import DougRuntime


def test_core_identity_and_truth_contract():
    profile = get_core_profile()

    assert profile.name == "GPT-DOUG-MAX"
    assert profile.signal_word == "EUREKA"
    assert profile.capability_state_model == (
        "PLANNED",
        "IMPLEMENTED",
        "TESTED",
        "VERIFIED",
    )
    assert "UNKNOWN" in profile.truth_labels
    assert profile.max_same_failure_retries == 3
    assert profile.local_first is True
    assert profile.human_authority_required is True
    assert profile.proof_required_for_verified is True


def test_non_weaponized_uav_domain_is_available():
    profile = get_core_profile()

    assert "non-weaponized UAV readiness" in profile.safe_domains
    assert "synthetic-data training" in profile.safe_domains
    assert "human-governed decision support" in profile.safe_domains


def test_operational_weapon_domains_are_not_core_capabilities():
    profile = get_core_profile()

    blocked = set(profile.prohibited_operational_domains)
    assert "real-world target designation" in blocked
    assert "fire-control computation" in blocked
    assert "weapon release" in blocked
    assert "autonomous lethal execution" in blocked
    assert "weaponized UAV payload control" in blocked


def test_verified_truth_gate_requires_all_evidence():
    assert can_mark_verified(
        implemented=True,
        tested=True,
        exit_zero=True,
        observed=True,
        proof_persisted=True,
    ) is True

    assert can_mark_verified(
        implemented=True,
        tested=True,
        exit_zero=True,
        observed=False,
        proof_persisted=True,
    ) is False

    assert can_mark_verified(
        implemented=True,
        tested=True,
        exit_zero=True,
        observed=True,
        proof_persisted=False,
    ) is False


def test_runtime_exposes_core_profile():
    runtime = DougRuntime()
    result = runtime.offline_response("Inspect this project")

    assert result.metadata["core_profile"] == "GPT-DOUG-MAX"
    assert result.metadata["core_version"] == "2026.08-core.1"
    assert "UNKNOWN" in result.metadata["truth_labels"]
    assert result.metadata["max_same_failure_retries"] == 3
