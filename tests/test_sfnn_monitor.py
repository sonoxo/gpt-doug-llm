import pytest

from doug_core.sfnn_monitor import (
    IDENTITY_ANCHOR,
    StringFieldSelfMonitor,
    identity_invariant_proxy,
    phi_sft_proxy,
)


def test_phi_proxy_is_bounded():
    score = phi_sft_proxy("build a secure streaming agent", "secure streaming agent plan")
    assert 0.0 <= score <= 1.0


def test_identity_anchor_is_stable():
    assert identity_invariant_proxy(IDENTITY_ANCHOR) == pytest.approx(1.0)


def test_monitor_accepts_nontrivial_audited_state():
    monitor = StringFieldSelfMonitor()
    report = monitor.observe(
        "inspect this repository",
        "I inspected the repository and produced a verified plan",
        audit_passed=True,
    )
    assert report.brst_physical is True
    assert report.introspective_stable is True


def test_monitor_rejects_exact_echo():
    monitor = StringFieldSelfMonitor()
    report = monitor.observe("same", "same", audit_passed=True)
    assert report.brst_nontrivial is False
    assert report.introspective_stable is False


def test_monitor_rejects_failed_audit():
    monitor = StringFieldSelfMonitor()
    report = monitor.observe("input", "different output", audit_passed=False)
    assert report.brst_closed is False
    assert report.introspective_stable is False


def test_cycles_are_hard_capped_at_1000():
    monitor = StringFieldSelfMonitor()
    with pytest.raises(ValueError):
        monitor.observe("input", "output", cycles=1001)
