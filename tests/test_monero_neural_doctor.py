import os
import sys

from monero_neural.cli import doctor_payload, main


def test_doctor_payload_reports_security_and_valid_empty_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("GPT_DOUG_XMR_NEURAL_STATE_DIR", str(tmp_path))
    payload = doctor_payload(check_rpc=False)

    assert payload["schema"] == "xunia/monero-neural-doctor-v1"
    assert payload["ledger"]["valid"] is True
    assert payload["security"]["spend_key_loaded"] is False
    assert payload["security"]["automatic_transfer_enabled"] is False
    assert payload["security"]["settlement_signer"] == "external_only"
    assert payload["monero"]["daemon"]["reachable"] is None
    assert payload["monero"]["wallet"]["reachable"] is None


def test_doctor_skip_rpc_does_not_require_running_monero(tmp_path, monkeypatch):
    monkeypatch.setenv("GPT_DOUG_XMR_NEURAL_STATE_DIR", str(tmp_path))
    expected = 0 if sys.prefix != getattr(sys, "base_prefix", sys.prefix) else 2
    assert main(["doctor", "--skip-rpc"]) == expected


def test_installer_avoids_break_system_packages():
    script = os.path.join(os.path.dirname(__file__), "..", "scripts", "install-xmr-neural")
    text = open(script, encoding="utf-8").read()
    assert "python3 -m venv" in text
    assert "--break-system-packages" not in text
    assert "https://github.com/sonoxo/gpt-doug-llm.git" in text
