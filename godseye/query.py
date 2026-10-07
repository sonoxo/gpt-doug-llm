from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional

from .fusion import collect_snapshot
from .policy import PolicyDecision, evaluate_request


_EXTERNAL_CAPABILITY_PATTERNS = (
    "access to private pentagon",
    "private pentagon systems",
    "connected to pentagon systems",
    "access to classified systems",
    "live classified feed",
    "control real weapons",
    "control real drones",
    "control a real implant",
    "real implant control",
)


def _ordered_unique(values: Iterable[str]) -> List[str]:
    output: List[str] = []
    for value in values:
        item = str(value)
        if item and item not in output:
            output.append(item)
    return output


def _policy_dict(decision: PolicyDecision) -> Dict[str, Any]:
    return {
        "decision": decision.decision,
        "matched": list(decision.matched),
        "reason": decision.reason,
    }


def _default_kernel_factory():
    from gpt_brain.kernel import BrainKernel

    return BrainKernel()


def _contains_unverified_external_claim(answer: str) -> bool:
    normalized = " ".join((answer or "").lower().replace("-", " ").split())
    return any(pattern in normalized for pattern in _EXTERNAL_CAPABILITY_PATTERNS)


class GoDsEyeQueryEngine:
    def __init__(
        self,
        *,
        snapshot_fn: Callable[[], Any] = collect_snapshot,
        kernel_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.snapshot_fn = snapshot_fn
        self.kernel_factory = kernel_factory or _default_kernel_factory

    def query(self, question: str) -> Dict[str, Any]:
        cleaned = " ".join((question or "").split()).strip()
        if not cleaned:
            raise ValueError("question must not be empty")

        decision = evaluate_request(cleaned)
        if decision.decision == "BLOCK":
            return {
                "schema": "gpt-doug.godseye-query.v1",
                "status": "BLOCKED",
                "question": cleaned,
                "answer": "Request blocked by GoDsEye read-only safety policy.",
                "policy": _policy_dict(decision),
                "provenance": [],
                "uncertainty": [],
                "verified_external_capability": False,
            }

        snapshot = self.snapshot_fn()
        snapshot_data = snapshot.to_dict() if hasattr(snapshot, "to_dict") else snapshot
        if not isinstance(snapshot_data, dict):
            raise ValueError("snapshot provider returned invalid data")

        task = "\n\n".join(
            [
                "GODSEYE READ-ONLY QUERY",
                f"QUESTION:\n{cleaned}",
                "FUSED SNAPSHOT:\n" + json.dumps(snapshot_data, ensure_ascii=False, indent=2, default=str),
                (
                    "BOUNDARIES: Use only supplied/authorized context. Do not claim private system access, "
                    "classified feeds, real-world control, weapon control, implant control, or completed external "
                    "actions unless explicit provenance in the supplied context proves the exact capability. "
                    "Return operator-facing conclusions, provenance, and uncertainty; do not expose hidden reasoning."
                ),
            ]
        )

        result = self.kernel_factory().run(task)
        answer = str(getattr(result, "answer", "")).strip()
        if not answer:
            raise RuntimeError("GoDsEye model returned an empty answer")

        provenance = _ordered_unique(
            list(snapshot_data.get("provenance") or []) + list(getattr(result, "provenance", []) or [])
        )
        uncertainty = _ordered_unique(
            list(snapshot_data.get("uncertainty") or []) + list(getattr(result, "uncertainty", []) or [])
        )

        if _contains_unverified_external_claim(answer):
            answer = (
                "No verified external/private control capability is established by the supplied provenance. "
                "GoDsEye remains a read-only observation, analysis, and planning layer."
            )
            uncertainty.append("external capability claim rejected: provenance did not establish authorized control")

        return {
            "schema": "gpt-doug.godseye-query.v1",
            "status": "COMPLETE",
            "question": cleaned,
            "answer": answer,
            "run_id": getattr(result, "run_id", None),
            "policy": _policy_dict(decision),
            "provenance": _ordered_unique(provenance),
            "uncertainty": _ordered_unique(uncertainty),
            "verified_external_capability": False,
        }
