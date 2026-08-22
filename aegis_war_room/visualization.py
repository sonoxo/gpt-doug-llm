from __future__ import annotations

from typing import Any, Dict

from .models import DecisionRequest, DecisionResult


def build_dashboard_payload(request: DecisionRequest, result: DecisionResult) -> Dict[str, Any]:
    """Return a visualization-ready payload without inventing operational data."""
    option_lookup = {option.option_id: option for option in request.options}
    ranked = []
    for item in result.ranked_options:
        option = option_lookup[item.option_id]
        ranked.append(
            {
                "optionId": item.option_id,
                "title": option.title,
                "score": item.score,
                "confidence": item.confidence,
                "evidenceIds": list(item.evidence_ids),
                "rationale": list(item.rationale),
            }
        )

    return {
        "requestId": request.request_id,
        "missionId": request.mission_id,
        "category": request.category.value,
        "status": result.status,
        "riskLevel": result.risk_level.value,
        "recommendedOptionId": result.recommended_option_id,
        "requiresHumanApproval": result.requires_human_approval,
        "rankedOptions": ranked,
        "limitations": list(result.limitations),
        "provenance": dict(result.provenance),
        "visualizationSafety": {
            "targetingData": "not_supported",
            "weaponControl": "not_supported",
            "offensiveCyber": "not_supported",
            "unknownDataPolicy": "display_unknown_not_green",
        },
    }
