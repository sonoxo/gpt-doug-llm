from __future__ import annotations

import uuid
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

from .ledger import HashChainLedger, hash_value, utc_now


def _clean_id(value: str, field: str) -> str:
    cleaned = " ".join(str(value).split()).strip()
    if not cleaned:
        raise ValueError("%s must not be empty" % field)
    return cleaned


def _validate_hash(value: str, field: str) -> str:
    cleaned = _clean_id(value, field).lower()
    if len(cleaned) != 64 or any(ch not in "0123456789abcdef" for ch in cleaned):
        raise ValueError("%s must be a 64-character SHA-256 hex digest" % field)
    return cleaned


class MoneroNeuralChain:
    """Evidence/provenance layer between neural workers and Monero settlement.

    Neural work remains off-chain. The local ledger stores hashes and compact
    metadata. This class never signs or broadcasts a payment.
    """

    def __init__(self, state_dir: str | Path, hive: Optional[Any] = None) -> None:
        self.state_dir = Path(state_dir).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = HashChainLedger(self.state_dir / "neural-chain.jsonl")
        self.hive = hive

    @staticmethod
    def digest(value: Any) -> str:
        return hash_value(value)

    def _job_record(self, job_id: str) -> Dict[str, Any]:
        rows = [
            row
            for row in self.ledger.rows(event="NEURAL_JOB_CREATED")
            if row.get("payload", {}).get("job_id") == job_id
        ]
        if not rows:
            raise KeyError("unknown job: %s" % job_id)
        return rows[-1]

    def _receipt_record(self, receipt_id: str) -> Dict[str, Any]:
        rows = [
            row
            for row in self.ledger.rows(event="NEURAL_RECEIPT")
            if row.get("payload", {}).get("receipt_id") == receipt_id
        ]
        if not rows:
            raise KeyError("unknown receipt: %s" % receipt_id)
        return rows[-1]

    def create_job(
        self,
        input_payload: Any,
        *,
        model_hash: str,
        ontology_hash: str,
        purpose: str,
        builders: Optional[Iterable[str]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        model_hash = _validate_hash(model_hash, "model_hash")
        ontology_hash = _validate_hash(ontology_hash, "ontology_hash")
        purpose = _clean_id(purpose, "purpose")
        request_key = request_id.strip() if request_id else None

        if request_key:
            for row in self.ledger.rows(event="NEURAL_JOB_CREATED"):
                payload = row.get("payload", {})
                if payload.get("request_id") == request_key:
                    return dict(payload, created=False)

        swarm: Optional[Dict[str, Any]] = None
        if self.hive is not None:
            swarm = self.hive.summon_swarm(
                purpose,
                builders=builders,
                source="monero-neural",
                request_id=request_key,
            )

        job_id = "xmrjob-" + uuid.uuid4().hex
        payload: Dict[str, Any] = {
            "job_id": job_id,
            "request_id": request_key,
            "purpose": purpose,
            "input_hash": self.digest(input_payload),
            "model_hash": model_hash,
            "ontology_hash": ontology_hash,
            "created_at": utc_now(),
            "raw_input_persisted": False,
            "settlement_network": "monero",
            "settlement_mode": "external_signer_only",
        }
        if swarm is not None:
            payload.update(
                {
                    "hive_id": swarm.get("hive_id"),
                    "swarm_id": swarm.get("swarm_id"),
                    "reward_event_id": swarm.get("reward_event_id"),
                }
            )
        self.ledger.append("NEURAL_JOB_CREATED", payload)
        return dict(payload, created=True)

    def record_result(
        self,
        job_id: str,
        *,
        worker_id: str,
        output_payload: Any,
        confidence: float,
        role: str = "worker",
        evidence_hashes: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        self._job_record(job_id)
        worker_id = _clean_id(worker_id, "worker_id")
        role = _clean_id(role, "role").lower()
        if role not in {"worker", "critic", "verifier"}:
            raise ValueError("role must be worker, critic, or verifier")
        confidence = float(confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("confidence must be between 0 and 1")
        hashes: List[str] = []
        for item in evidence_hashes or []:
            hashes.append(_validate_hash(item, "evidence_hash"))
        result_id = "result-" + uuid.uuid4().hex
        payload = {
            "result_id": result_id,
            "job_id": job_id,
            "worker_id": worker_id,
            "role": role,
            "output_hash": self.digest(output_payload),
            "confidence": confidence,
            "evidence_hashes": hashes,
            "created_at": utc_now(),
            "raw_output_persisted": False,
        }
        self.ledger.append("NEURAL_RESULT_RECORDED", payload)
        return payload

    def results(self, job_id: str) -> List[Dict[str, Any]]:
        self._job_record(job_id)
        return [
            row["payload"]
            for row in self.ledger.rows(event="NEURAL_RESULT_RECORDED")
            if row.get("payload", {}).get("job_id") == job_id
        ]

    def reconcile(
        self,
        job_id: str,
        *,
        final_output: Any,
        minimum_workers: int = 1,
        require_critic: bool = True,
        require_verifier: bool = True,
    ) -> Dict[str, Any]:
        job = self._job_record(job_id)["payload"]
        results = self.results(job_id)
        workers = [r for r in results if r["role"] == "worker"]
        critics = [r for r in results if r["role"] == "critic"]
        verifiers = [r for r in results if r["role"] == "verifier"]
        missing: List[str] = []
        if len(workers) < int(minimum_workers):
            missing.append("worker_quorum")
        if require_critic and not critics:
            missing.append("critic")
        if require_verifier and not verifiers:
            missing.append("verifier")
        if missing:
            return {
                "status": "NEEDS_EVIDENCE",
                "job_id": job_id,
                "missing": missing,
                "worker_count": len(workers),
                "critic_count": len(critics),
                "verifier_count": len(verifiers),
            }

        confidences = [float(r["confidence"]) for r in results]
        final_confidence = mean(confidences) if confidences else 0.0
        receipt_id = "receipt-" + uuid.uuid4().hex
        payload = {
            "receipt_id": receipt_id,
            "job_id": job_id,
            "model_hash": job["model_hash"],
            "ontology_hash": job["ontology_hash"],
            "input_hash": job["input_hash"],
            "output_hash": self.digest(final_output),
            "worker_ids": sorted({r["worker_id"] for r in workers}),
            "critic_ids": sorted({r["worker_id"] for r in critics}),
            "verifier_ids": sorted({r["worker_id"] for r in verifiers}),
            "result_ids": [r["result_id"] for r in results],
            "confidence": round(final_confidence, 6),
            "verification": "PASSED",
            "created_at": utc_now(),
            "raw_output_persisted": False,
            "pre_receipt_ledger_head": self.ledger.head_hash(),
            "hive_id": job.get("hive_id"),
            "swarm_id": job.get("swarm_id"),
            "reward_event_id": job.get("reward_event_id"),
        }
        self.ledger.append("NEURAL_RECEIPT", payload)
        return payload

    def propose_settlement(
        self,
        receipt_id: str,
        *,
        amount_piconero: int,
        destination_subaddress: str,
        note: str = "",
    ) -> Dict[str, Any]:
        receipt = self._receipt_record(receipt_id)["payload"]
        if receipt.get("verification") != "PASSED":
            raise ValueError("only verified neural receipts can be proposed for settlement")
        amount = int(amount_piconero)
        if amount <= 0:
            raise ValueError("amount_piconero must be positive")
        destination = _clean_id(destination_subaddress, "destination_subaddress")
        proposal_id = "xmrpay-" + uuid.uuid4().hex
        payload = {
            "proposal_id": proposal_id,
            "receipt_id": receipt_id,
            "job_id": receipt["job_id"],
            "network": "monero",
            "amount_piconero": amount,
            "destination_subaddress": destination,
            "note": str(note)[:500],
            "status": "AWAITING_HUMAN_AUTHORIZATION",
            "automatic_transfer_performed": False,
            "created_at": utc_now(),
        }
        self.ledger.append("XMR_SETTLEMENT_PROPOSED", payload)
        return payload

    def authorize_settlement(
        self, proposal_id: str, *, authorized_by: str
    ) -> Dict[str, Any]:
        matches = [
            row
            for row in self.ledger.rows(event="XMR_SETTLEMENT_PROPOSED")
            if row.get("payload", {}).get("proposal_id") == proposal_id
        ]
        if not matches:
            raise KeyError("unknown settlement proposal: %s" % proposal_id)
        proposal = matches[-1]["payload"]
        authorized_by = _clean_id(authorized_by, "authorized_by")
        payload = {
            "proposal_id": proposal_id,
            "receipt_id": proposal["receipt_id"],
            "authorized_by": authorized_by,
            "authorized_at": utc_now(),
            "status": "AUTHORIZED_FOR_EXTERNAL_SIGNER",
            "automatic_transfer_performed": False,
        }
        self.ledger.append("XMR_SETTLEMENT_AUTHORIZED", payload)
        return payload

    def attach_settlement_tx(
        self,
        proposal_id: str,
        *,
        txid: str,
        confirmations: int = 0,
    ) -> Dict[str, Any]:
        auth = [
            row
            for row in self.ledger.rows(event="XMR_SETTLEMENT_AUTHORIZED")
            if row.get("payload", {}).get("proposal_id") == proposal_id
        ]
        if not auth:
            raise PermissionError(
                "settlement must be authorized before attaching a transaction"
            )
        txid = _validate_hash(txid, "txid")
        payload = {
            "proposal_id": proposal_id,
            "txid": txid,
            "confirmations": max(0, int(confirmations)),
            "status": "SETTLEMENT_REFERENCE_ATTACHED",
            "broadcast_performed_by_this_layer": False,
            "recorded_at": utc_now(),
        }
        self.ledger.append("XMR_SETTLEMENT_TX_ATTACHED", payload)
        return payload

    def status(self) -> Dict[str, Any]:
        integrity = self.ledger.verify()
        rows = self.ledger.rows()
        return {
            "schema": "xunia/monero-neural-status-v1",
            "mode": "OFFCHAIN_NEURAL_PROVENANCE_ONCHAIN_SETTLEMENT_REFERENCE",
            "ledger_valid": bool(integrity.get("valid")),
            "ledger_head": integrity.get("head_hash"),
            "record_count": len(rows),
            "job_count": len(
                [r for r in rows if r.get("event") == "NEURAL_JOB_CREATED"]
            ),
            "receipt_count": len(
                [r for r in rows if r.get("event") == "NEURAL_RECEIPT"]
            ),
            "settlement_proposal_count": len(
                [r for r in rows if r.get("event") == "XMR_SETTLEMENT_PROPOSED"]
            ),
            "spend_key_loaded": False,
            "automatic_transfer_enabled": False,
        }
