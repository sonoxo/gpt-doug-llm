from web.xunia_server import build_self_monitor_event


def test_monitor_event_is_emitted_before_completion_marker():
    event = build_self_monitor_event(
        "build a secure streaming agent",
        "I built and verified the streaming agent",
        audit_passed=True,
    )

    assert event["type"] == "self_monitor"
    assert event["done"] is False
    report = event["self_monitor"]
    assert report["brst_physical"] is True
    assert report["introspective_stable"] is True
    assert report["interpretation"] == "operational_proxy_not_consciousness_claim"


def test_monitor_event_reflects_failed_output_audit():
    event = build_self_monitor_event(
        "input",
        "different output",
        audit_passed=False,
    )

    assert event["self_monitor"]["brst_closed"] is False
    assert event["self_monitor"]["introspective_stable"] is False
