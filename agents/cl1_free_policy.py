"""CL1 zero-billing boundary for the GPT-DOUG inference runtime.

This deliberately rejects metered/cloud inference regardless of credentials,
provider selection, legacy PAID_MODE flags, or model-routing order.
It does not claim that operating your own computer or network is costless.
"""

from __future__ import annotations

from urllib.parse import urlsplit

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
CLOUD_PROVIDERS = frozenset({"openai", "claude", "anthropic", "gemini"})


def is_local_inference_url(url: str) -> bool:
    """Allow only loopback HTTP(S) inference endpoints; never arbitrary hosts."""
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme in {"http", "https"}
            and parsed.hostname is not None
            and parsed.hostname.lower() in LOCAL_HOSTS
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


def provider_is_cloud(name: str) -> bool:
    return name.strip().lower() in CLOUD_PROVIDERS


def free_policy_status() -> dict[str, object]:
    return {
        "profile": "CL1_FREE_ONLY",
        "paid_inference_allowed": False,
        "cloud_inference_allowed": False,
        "local_inference_allowed": True,
        "billing_credentials_required": False,
    }
