"""CL1 free-only legacy Stripe interface.

Legacy endpoints stay import-compatible, but checkout creation and payment
webhook acceptance are unconditionally disabled. No Stripe HTTP client exists.
This does not modify or cancel pre-existing Stripe subscriptions or records.
"""

from __future__ import annotations

# Retained only for compatibility with legacy callers and fixtures.
STRIPE_SECRET_KEY = ""
STRIPE_WEBHOOK_SECRET = ""
TASK_PRICE_CENTS = 100


def enabled() -> bool:
    return False


def create_checkout_session(task_id, task_description, success_url, cancel_url):
    raise RuntimeError("CL1 free-only policy disables Stripe checkout")


def verify_webhook_signature(payload_bytes, sig_header, tolerance_s=300):
    raise ValueError("CL1 free-only policy rejects Stripe payment webhooks")
