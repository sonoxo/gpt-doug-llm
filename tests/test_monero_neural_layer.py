import hashlib
import json

import pytest

from monero_neural import HashChainLedger, MoneroNeuralChain


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DummyHive:
    def summon_swarm(
        self, job, *, builders=None, source="gpt-doug", request_id=None
    ):
        return {
            "hive_id": "hive-test",
            "swarm_id": "swarm-test",
            "reward_event_id": "reward-test",
            "job": job,
            "source": source,
        }


def test_hash_chain_detects_tampering(tmp_path):
    ledger = HashChainLedger(tmp_path / "ledger.jsonl")
    ledger.append("ONE", {"value": 1})
    ledger.append("TWO", {"value": 2})
    assert ledger.verify()["valid"] is True

    rows = ledger.path.read_text().splitlines()
    payload = json.loads(rows[0])
    payload["payload"]["value"] = 999
    rows[0] = json.dumps(payload)
    ledger.path.write_text("\n".join(rows) + "\n")

    result = ledger.verify()
    assert result["valid"] is False
    assert result["reason"] == "record_hash_mismatch"


def test_job_persists_hashes_not_raw_input_and_links_hive(tmp_path):
    chain = MoneroNeuralChain(tmp_path, hive=DummyHive())
    raw = {"prompt": "private raw neural input", "feature": [1, 2, 3]}
    job = chain.create_job(
        raw,
        model_hash=digest("model"),
        ontology_hash=digest("ontology"),
        purpose="build neural receipt",
        request_id="job-1",
    )

    assert job["raw_input_persisted"] is False
    assert job["input_hash"] == chain.digest(raw)
    assert job["swarm_id"] == "swarm-test"
    assert "private raw neural input" not in chain.ledger.path.read_text()


def test_request_id_is_idempotent(tmp_path):
    chain = MoneroNeuralChain(tmp_path)
    kwargs = {
        "model_hash": digest("model"),
        "ontology_hash": digest("ontology"),
        "purpose": "same job",
        "request_id": "same-request",
    }
    first = chain.create_job({"x": 1}, **kwargs)
    second = chain.create_job({"x": 2}, **kwargs)

    assert first["job_id"] == second["job_id"]
    assert first["created"] is True
    assert second["created"] is False
    assert chain.status()["job_count"] == 1


def test_reconciliation_requires_worker_critic_and_verifier(tmp_path):
    chain = MoneroNeuralChain(tmp_path)
    job = chain.create_job(
        "input",
        model_hash=digest("model"),
        ontology_hash=digest("ontology"),
        purpose="reconcile",
    )
    chain.record_result(
        job["job_id"],
        worker_id="worker-a",
        output_payload="candidate",
        confidence=0.8,
    )
    result = chain.reconcile(job["job_id"], final_output="final")
    assert result["status"] == "NEEDS_EVIDENCE"
    assert "critic" in result["missing"]
    assert "verifier" in result["missing"]


def test_verified_receipt_and_external_signer_settlement_flow(tmp_path):
    chain = MoneroNeuralChain(tmp_path)
    job = chain.create_job(
        "input",
        model_hash=digest("model"),
        ontology_hash=digest("ontology"),
        purpose="settlement test",
    )
    chain.record_result(
        job["job_id"], worker_id="worker-a", output_payload="a", confidence=0.8
    )
    chain.record_result(
        job["job_id"],
        worker_id="chaos-a",
        output_payload="challenge",
        confidence=0.6,
        role="critic",
    )
    chain.record_result(
        job["job_id"],
        worker_id="verify-a",
        output_payload="verified",
        confidence=1.0,
        role="verifier",
    )
    receipt = chain.reconcile(job["job_id"], final_output={"answer": 42})

    assert receipt["verification"] == "PASSED"
    assert receipt["confidence"] == pytest.approx(0.8)
    assert receipt["critic_ids"] == ["chaos-a"]
    assert receipt["verifier_ids"] == ["verify-a"]

    proposal = chain.propose_settlement(
        receipt["receipt_id"],
        amount_piconero=123456,
        destination_subaddress="8ExampleSubaddress",
    )
    assert proposal["automatic_transfer_performed"] is False
    assert proposal["status"] == "AWAITING_HUMAN_AUTHORIZATION"

    with pytest.raises(PermissionError):
        chain.attach_settlement_tx(
            proposal["proposal_id"], txid=digest("tx")
        )

    auth = chain.authorize_settlement(
        proposal["proposal_id"], authorized_by="operator"
    )
    assert auth["status"] == "AUTHORIZED_FOR_EXTERNAL_SIGNER"
    assert auth["automatic_transfer_performed"] is False

    attached = chain.attach_settlement_tx(
        proposal["proposal_id"], txid=digest("tx"), confirmations=4
    )
    assert attached["broadcast_performed_by_this_layer"] is False
    assert attached["confirmations"] == 4
    assert chain.status()["spend_key_loaded"] is False
    assert chain.status()["automatic_transfer_enabled"] is False
