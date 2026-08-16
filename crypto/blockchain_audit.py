"""
✓ 7/10 Crypto Audit Chain — put Zyra's HMAC audit log on-chain
Uses Bitcoin OP_RETURN or Ethereum contract to anchor audit hashes.
Free: only broadcasts a hash (80 bytes) — no data stored on-chain.
"""
from __future__ import annotations
import hashlib, json, os, sys, time
from pathlib import Path
_PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT))

class BlockchainAuditChain:
    """Anchor Zyra audit log hashes to blockchain for tamper-evident forensics.
    
    How it works:
    1. Read the local HMAC audit log (zyra-audit.jsonl)
    2. Compute a Merkle root of all events
    3. Anchor the root hash on-chain via OP_RETURN (BTC) or contract (ETH)
    4. Anyone can verify the audit log wasn't tampered with by checking the chain
    
    This only stores an 80-byte hash on-chain — not conversation content.
    """
    def __init__(self, audit_path: str | Path | None = None):
        self.audit_path = Path(audit_path or Path.home() / ".gpt-doug" / "zyra-audit.jsonl")

    def compute_merkle_root(self) -> dict:
        """Compute Merkle root of all audit events."""
        if not self.audit_path.exists():
            return {"merkle_root": "0"*64, "event_count": 0, "note": "no audit log"}
        events = []
        for line in self.audit_path.read_text().splitlines():
            if line.strip():
                events.append(hashlib.sha256(line.encode()).hexdigest())
        if not events:
            return {"merkle_root": "0"*64, "event_count": 0}
        # Build Merkle tree
        while len(events) > 1:
            if len(events) % 2: events.append(events[-1])
            events = [hashlib.sha256((events[i]+events[i+1]).encode()).hexdigest() for i in range(0, len(events), 2)]
        return {"merkle_root": events[0], "event_count": sum(1 for _ in self.audit_path.read_text().splitlines() if _.strip())}

    def create_anchor(self, network: str = "btc") -> dict:
        """Create a blockchain anchor transaction (for manual broadcast)."""
        merkle = self.compute_merkle_root()
        anchor = {
            "network": network,
            "merkle_root": merkle["merkle_root"],
            "event_count": merkle["event_count"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": "OP_RETURN" if network == "btc" else "contract_storage",
            "op_return_hex": bytes("ZYRA3:" + merkle["merkle_root"][:32], "utf-8").hex() if network == "btc" else "",
            "note": "Broadcast this OP_RETURN to anchor the audit log on-chain. Verification: recompute Merkle root and compare.",
        }
        return anchor

    def verify_anchor(self, claimed_root: str) -> dict:
        """Verify that a claimed on-chain root matches current audit log."""
        actual = self.compute_merkle_root()
        match = actual["merkle_root"] == claimed_root
        return {"verified": match, "actual_root": actual["merkle_root"], "claimed_root": claimed_root,
                "event_count": actual["event_count"], "status": "VERIFIED" if match else "MISMATCH"}

if __name__ == "__main__":
    chain = BlockchainAuditChain()
    anchor = chain.create_anchor("btc")
    print(json.dumps(anchor, indent=2))
    verification = chain.verify_anchor(anchor["merkle_root"])
    print(json.dumps(verification, indent=2))
