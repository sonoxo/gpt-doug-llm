from __future__ import annotations

from typing import Any


def palantir_verification_status(*, execute_aip_model: bool = False) -> dict[str, Any]:
    """Expose Palantir readiness without confusing code-complete with tenant-verified."""

    try:
        from palantir_tenant_probe import PalantirTenantProbe
    except ImportError:
        return {
            "implementationState": "CODE_COMPLETE",
            "verificationState": "PROBE_UNAVAILABLE_IN_STANDALONE_RUNTIME",
            "liveTenantVerified": False,
            "configuredComponents": 0,
            "verifiedComponents": 0,
            "items": [],
        }

    result = PalantirTenantProbe().probe(execute_aip_model=execute_aip_model)
    items = result.get("items", [])
    configured = [item for item in items if item.get("configured")]
    verified = [item for item in configured if item.get("live_verified")]

    if not configured:
        verification_state = "LIVE_TENANT_UNVERIFIED"
    elif len(verified) == len(configured):
        verification_state = "LIVE_TENANT_VERIFIED"
    else:
        verification_state = "CONFIGURED_BUT_NOT_FULLY_VERIFIED"

    return {
        "implementationState": "CODE_COMPLETE",
        "verificationState": verification_state,
        "liveTenantVerified": bool(configured) and len(verified) == len(configured),
        "configuredComponents": len(configured),
        "verifiedComponents": len(verified),
        "allCodeImplemented": bool(result.get("all_code_implemented")),
        "items": items,
    }
