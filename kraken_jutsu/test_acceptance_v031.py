from __future__ import annotations

import json
import subprocess
from pathlib import Path

from kraken_jutsu.live import LiveRuntime, TrustState, install_usb


class FakeKEV:
    def fetch(self):
        return {
            "catalogVersion": "test",
            "dateReleased": "2099-01-01T00:00:00Z",
            "_kraken_source_url": "fixture://cisa-kev",
            "vulnerabilities": [
                {
                    "cveID": "CVE-2099-0001",
                    "vendorProject": "fixture",
                    "product": "fixture",
                    "vulnerabilityName": "fixture",
                }
            ],
        }


def _write_friend(inbox: Path) -> None:
    package = inbox / "gpt-recovery-friend"
    package.mkdir(parents=True)
    (package / "agent.json").write_text(
        json.dumps(
            {
                "name": "gpt-recovery-friend",
                "version": "1.0",
                "capabilities": ["diagnose", "recover", "repair", "verify"],
                "test_score": 0.99,
                "provenance_score": 0.98,
                "integrity_score": 0.99,
            }
        ),
        encoding="utf-8",
    )
    (package / "agent.py").write_text("NAME = 'friend'\n", encoding="utf-8")


def test_gate_a_friend_reaches_blackhouse(tmp_path: Path):
    runtime = LiveRuntime(tmp_path / "state")
    _write_friend(runtime.friends.inbox)

    result = runtime.discover_appoint_promote()
    assert len(result) == 1
    assert result[0]["promotion"]["promoted"] is True
    assert result[0]["appointment"]["role"] == "CPR"

    agents = runtime.store.list_objects("AgentCandidate")
    assert len(agents) == 1
    assert agents[0]["data"]["trust_state"] == TrustState.BLACKHOUSE.value
    assert Path(agents[0]["data"]["source_path"]).exists()


def test_gate_b_live_ontology_ingest_contract(tmp_path: Path):
    runtime = LiveRuntime(tmp_path / "state")
    count = runtime.ingest_kev(FakeKEV())
    assert count == 1
    assert runtime.store.get_object("CVE-2099-0001")["object_type"] == "Vulnerability"
    assert runtime.store.get_object("source:cisa-kev")["object_type"] == "DataSource"


def test_both_gates_are_required_for_ready(tmp_path: Path):
    runtime = LiveRuntime(tmp_path / "state")
    assert runtime.readiness()["kraken_ready"] is False

    runtime.ingest_kev(FakeKEV())
    assert runtime.readiness()["gate_b_live_ontology"] is True
    assert runtime.readiness()["kraken_ready"] is False

    _write_friend(runtime.friends.inbox)
    runtime.discover_appoint_promote()
    readiness = runtime.readiness()
    assert readiness["gate_a_usb_blackhouse"] is True
    assert readiness["gate_b_live_ontology"] is True
    assert readiness["kraken_ready"] is True
    assert len(readiness["va3lm"]["lanes"]) == 7


def test_usb_launcher_executes_status(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    mount = tmp_path / "USB"
    mount.mkdir()
    layout = install_usb(repo_root, mount)
    launcher = layout.runtime / "kraken-jutsu"

    completed = subprocess.run(
        [str(launcher), "status"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["readiness"]["va3lm"]["lanes"] == [
        "Inventory",
        "Identity",
        "Segmentation",
        "Detection",
        "Containment",
        "Recovery",
        "Verification",
    ]
