"""Stripe Checkout integration for paid agent-chain tasks.

Uses raw HTTP calls (urllib) against Stripe's REST API rather than the
`stripe` pip package, consistent with the rest of this codebase
(llm_backend.py, twilio_webhook.py, youtube_comment.py all do the same) —
no extra dependency for a handful of well-documented endpoints.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_API_BASE = "https://api.stripe.com/v1"

TASK_PRICE_CENTS = 100  # $1.00 flat per agent-chain task


def enabled():
    return bool(STRIPE_SECRET_KEY)


def _post(path, params):
    body = urllib.parse.urlencode(params, doseq=True).encode()
    req = urllib.request.Request(
        f"{STRIPE_API_BASE}/{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    req.add_header("Authorization", "Basic " + _basic_auth())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        detail = err.read().decode()
        raise RuntimeError(f"Stripe API error ({err.code}): {detail}") from err


def _basic_auth():
    import base64
    return base64.b64encode(f"{STRIPE_SECRET_KEY}:".encode()).decode()


def create_checkout_session(task_id, task_description, success_url, cancel_url):
    """Creates a Stripe Checkout Session for one $1 agent-chain task run.
    Returns the session dict (session['url'] is where to send the buyer)."""
    if not enabled():
        raise RuntimeError("Stripe not configured (STRIPE_SECRET_KEY unset)")
    params = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        # This account has Managed Payments on by default, which requires a
        # product tax_code we don't have configured — disable it for this
        # simple flat-fee session rather than set up tax codes for a $1 item.
        "managed_payments[enabled]": "false",
        "line_items[0][quantity]": 1,
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": TASK_PRICE_CENTS,
        "line_items[0][price_data][product_data][name]": "GPT Doug agent task",
        "line_items[0][price_data][product_data][description]": task_description[:200],
        "metadata[task_id]": task_id,
    }
    return _post("checkout/sessions", params)


def verify_webhook_signature(payload_bytes, sig_header, tolerance_s=300):
    """Verifies a Stripe webhook per their documented scheme:
    header is 't=<timestamp>,v1=<hex hmac>'; signed payload is
    '<timestamp>.<raw body>' HMAC-SHA256'd with the webhook secret.
    Returns the parsed event dict, or raises ValueError if invalid."""
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        raise ValueError("malformed Stripe-Signature header")

    if abs(time.time() - int(timestamp)) > tolerance_s:
        raise ValueError("webhook timestamp outside tolerance (possible replay)")

    signed_payload = f"{timestamp}.".encode() + payload_bytes
    expected = hmac.new(STRIPE_WEBHOOK_SECRET.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("signature mismatch")

    return json.loads(payload_bytes)
