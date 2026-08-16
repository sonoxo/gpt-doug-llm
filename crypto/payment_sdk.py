"""
Crypto Payment SDK for GPT Doug — accept BTC, ETH, USDC payments.
Open, self-custody, no gatekeeper. Legal: interacts with public blockchain protocols.

Usage:
  from crypto.payment_sdk import CryptoPayment

  payment = CryptoPayment()
  address = payment.generate_address("btc")
  result = payment.check_payment("btc", address, 0.001)
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import hmac
import base64
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PaymentRequest:
    payment_id: str
    crypto: str  # btc, eth, usdc
    address: str
    amount: float
    fiat_amount: float
    fiat_currency: str
    status: str  # pending, paid, expired, confirmed
    created_at: str
    expires_at: str

class CryptoPayment:
    """Accept crypto payments for GPT Doug SaaS. No licenses needed —
    you're accepting cryptocurrency directly to your own wallet."""

    SUPPORTED = {"btc", "eth", "usdc", "sol", "ada"}

    # Price feeds (free APIs, no key required)
    PRICE_FEEDS = {
        "btc": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        "eth": "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
        "usdc": "https://api.coingecko.com/api/v3/simple/price?ids=usd-coin&vs_currencies=usd",
        "sol": "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
        "ada": "https://api.coingecko.com/api/v3/simple/price?ids=cardano&vs_currencies=usd",
    }

    def __init__(self, wallet_dir: str | Path | None = None):
        self.wallet_dir = Path(wallet_dir or Path.home() / ".gpt-doug" / "crypto")
        self.wallet_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.payments_file = self.wallet_dir / "payments.json"
        self._payments = self._load_payments()

    def _load_payments(self) -> list:
        if self.payments_file.exists():
            return json.loads(self.payments_file.read_text())
        return []

    def _save_payments(self):
        self.payments_file.write_text(json.dumps(self._payments, indent=2))
        self.payments_file.chmod(0o600)

    def get_price(self, crypto: str) -> float:
        """Get current USD price from CoinGecko (free, no API key)."""
        crypto = crypto.lower()
        if crypto not in self.PRICE_FEEDS:
            raise ValueError(f"unsupported: {crypto}")
        try:
            req = urllib.request.Request(self.PRICE_FEEDS[crypto], headers={"User-Agent": "GPT-Doug/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                coin_id = {"btc": "bitcoin", "eth": "ethereum", "usdc": "usd-coin", "sol": "solana", "ada": "cardano"}[crypto]
                return data[coin_id]["usd"]
        except Exception:
            return 0.0

    def generate_address(self, crypto: str) -> dict:
        """Generate a receiving address. For production, use a real wallet library.
        This generates a deterministic placeholder — replace with real key generation."""
        crypto = crypto.lower()
        if crypto not in self.SUPPORTED:
            raise ValueError(f"unsupported: {crypto}. Supported: {self.SUPPORTED}")
        # Generate a unique receiving address (placeholder — integrate real wallet SDK)
        seed = os.urandom(32)
        if crypto == "btc":
            addr = "bc1" + hashlib.sha256(seed).hexdigest()[:39]
        elif crypto in ("eth", "usdc"):
            addr = "0x" + hashlib.sha256(seed).hexdigest()[:40]
        elif crypto == "sol":
            addr = hashlib.sha256(seed).hexdigest()[:44]
        else:
            addr = hashlib.sha256(seed).hexdigest()[:58]
        return {"crypto": crypto, "address": addr, "note": "Replace with real wallet SDK for production"}

    def create_payment(self, fiat_amount: float, fiat_currency: str = "usd", crypto: str = "btc") -> PaymentRequest:
        """Create a payment request. Customer pays in crypto, you receive directly."""
        import uuid
        from datetime import datetime, timezone, timedelta
        crypto = crypto.lower()
        price = self.get_price(crypto)
        if price == 0:
            raise RuntimeError(f"cannot get price for {crypto}")
        crypto_amount = fiat_amount / price
        addr = self.generate_address(crypto)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=1)
        payment = PaymentRequest(
            payment_id=str(uuid.uuid4()),
            crypto=crypto, address=addr["address"],
            amount=crypto_amount, fiat_amount=fiat_amount, fiat_currency=fiat_currency,
            status="pending", created_at=now.isoformat(), expires_at=expires.isoformat(),
        )
        self._payments.append({
            "payment_id": payment.payment_id, "crypto": payment.crypto,
            "address": payment.address, "amount": payment.amount,
            "fiat_amount": payment.fiat_amount, "status": payment.status,
            "created_at": payment.created_at, "expires_at": payment.expires_at,
        })
        self._save_payments()
        return payment

    def check_payment(self, crypto: str, address: str, expected_amount: float) -> dict:
        """Check if payment received. For production, query blockchain explorer API."""
        return {
            "crypto": crypto, "address": address,
            "expected": expected_amount, "received": 0.0,
            "confirmed": False, "status": "pending",
            "note": "Integrate with blockchain API (BlockCypher, Etherscan, etc.) for live checking",
        }

    def list_payments(self) -> list:
        return self._payments

    def webhook_handler(self, event: dict) -> dict:
        """Handle incoming payment confirmation webhook from blockchain explorer."""
        payment_id = event.get("payment_id", "")
        for p in self._payments:
            if p["payment_id"] == payment_id:
                p["status"] = "paid"
                self._save_payments()
                return {"status": "confirmed", "payment_id": payment_id, "amount": p["amount"]}
        return {"status": "not_found", "payment_id": payment_id}
