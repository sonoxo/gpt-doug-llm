import json

from gpt_chaos import GPTChaos
from uap_matrix import UAPMatrixSharedSpace
from universal_hive import UniversalHiveRuntime


def test_doug_and_chaos_share_one_blackboard(tmp_path):
    doug = UAPMatrixSharedSpace(
        state_dir=tmp_path,
        hive_id="hive-test",
        ontology_hash="ontology-test",
    )
    chaos = UAPMatrixSharedSpace(
        state_dir=tmp_path,
        hive_id="hive-test",
        ontology_hash="ontology-test",
    )

    event = doug.publish(
        "GPT_DOUG",
        "OBSERVATION",
        "shared signal",
        evidence={"source": "test"},
    )
    snapshot = chaos.snapshot()

    assert snapshot["agents"]["GPT_DOUG"]["status"] == "PEER"
    assert snapshot["agents"]["GPT_CHAOS"]["status"] == "PEER"
    assert snapshot["blackboard"]["OBSERVATION"][0]["event_id"] == event["event_id"]
    assert snapshot["blackboard"]["OBSERVATION"][0]["content"] == "shared signal"


def test_quorum_requires_both_peers(tmp_path):
    matrix = UAPMatrixSharedSpace(state_dir=tmp_path)
    decision = matrix.propose("GPT_DOUG", "promote verified result")

    pending = matrix.vote("GPT_DOUG", decision["decision_id"], "SUPPORT")
    assert pending["state"] == "PENDING_PEER"

    reached = matrix.vote("GPT_CHAOS", decision["decision_id"], "SUPPORT")
    assert reached["state"] == "QUORUM_REACHED"


def test_dissent_is_preserved_and_blocks_quorum(tmp_path):
    matrix = UAPMatrixSharedSpace(state_dir=tmp_path)
    decision = matrix.propose("GPT_DOUG", "candidate action")

    matrix.vote("GPT_DOUG", decision["decision_id"], "SUPPORT")
    contested = matrix.vote(
        "GPT_CHAOS",
        decision["decision_id"],
        "DISSENT",
        evidence={"reason": "missing evidence"},
    )
    snapshot = matrix.snapshot()

    assert contested["state"] == "CONTESTED"
    assert len(snapshot["blackboard"]["DISSENT"]) == 1
    assert snapshot["blackboard"]["DISSENT"][0]["agent"] == "GPT_CHAOS"
    assert snapshot["blackboard"]["DISSENT"][0]["evidence"]["reason"] == "missing evidence"


def test_checkpoint_and_rollback_only_mutate_local_shared_state(tmp_path):
    matrix = UAPMatrixSharedSpace(state_dir=tmp_path)
    matrix.publish("GPT_DOUG", "OBSERVATION", "before")
    checkpoint = matrix.checkpoint("known-good")
    matrix.publish("GPT_CHAOS", "FAULT", "after-checkpoint")

    assert matrix.status()["blackboard_counts"]["FAULT"] == 1

    result = matrix.rollback(
        checkpoint["checkpoint_id"],
        authorized_by="human-operator",
    )

    assert result["rolled_back"] is True
    assert result["external_actions_performed"] is False
    assert matrix.status()["blackboard_counts"]["FAULT"] == 0


def test_event_log_is_append_only_evidence(tmp_path):
    matrix = UAPMatrixSharedSpace(state_dir=tmp_path)
    matrix.publish("GPT_DOUG", "EVIDENCE", {"hash": "abc"})
    matrix.publish("GPT_CHAOS", "HYPOTHESIS", "challenge")

    rows = [
        json.loads(line)
        for line in matrix.events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) == 2
    assert rows[0]["agent"] == "GPT_DOUG"
    assert rows[1]["agent"] == "GPT_CHAOS"


def test_gpt_chaos_attaches_to_universal_hive_matrix(tmp_path):
    hive = UniversalHiveRuntime(state_dir=tmp_path / "hive")
    chaos = GPTChaos(hive=hive)

    chaos.matrix_publish("HYPOTHESIS", "peer challenge")
    matrix = UAPMatrixSharedSpace(
        state_dir=hive.state_dir / "uap-matrix",
        hive_id=hive.hive_id,
        ontology_hash=hive.ontology_hash,
    )

    assert matrix.status()["blackboard_counts"]["HYPOTHESIS"] == 1
    assert chaos.status()["uap_matrix"]["peer_symmetry"] is True
