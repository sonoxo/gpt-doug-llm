"""CL1 free-only process environment guard.

Legacy PAID_MODE=true is ignored. Drop recognized billed-provider credentials
from the current process without printing, copying, or retaining their values.
This is defense in depth; agents.llm_backend also blocks cloud transports.
"""

from __future__ import annotations

import os
import sys

_PAID_KEYS_TO_BLOCK = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "QWEN_API_KEY",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_ACCOUNT_SID",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "RESEND_API_KEY",
    "AI_GATEWAY_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
)

_BLOCKED_KEY_NAMES: list[str] = []

for _key in _PAID_KEYS_TO_BLOCK:
    if _key in os.environ:
        os.environ.pop(_key, None)
        _BLOCKED_KEY_NAMES.append(_key)
        print(f"CL1 FREE ONLY: disabled billed-service credential {_key}", file=sys.stderr)

os.environ["PAID_MODE"] = "false"
os.environ["GPT_DOUG_FREE_ONLY"] = "true"


def is_free_mode() -> bool:
    return True


def get_blocked_keys() -> list[str]:
    return list(_BLOCKED_KEY_NAMES)


def enable_paid_mode() -> None:
    """Do not allow paid mode through the CL1 process."""
    raise RuntimeError("CL1 free-only policy does not permit paid mode")
