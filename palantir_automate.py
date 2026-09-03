"""Palantir Automate effect bridge.

Public Automate documentation exposes Actions, AIP Logic functions, Foundry
functions, and notifications as effects. This module implements the external
execution contract for the two effects Wakeup3lm can safely invoke through the
public Foundry API: Ontology Actions and published Logic/Function queries.

Creation/scheduling of Automate resources remains an in-platform operation
unless the operator supplies another supported API surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from palantir_aip import PalantirAIPClient
from palantir_foundry import FoundryClient


EffectType = Literal["ontology-action", "aip-logic"]


@dataclass(frozen=True)
class AutomateEffect:
    effect_type: EffectType
    ontology: str
    api_name: str
    parameters: dict[str, Any]
    version: Optional[str] = None


class PalantirAutomateBridge:
    """Execute Automate-compatible effects through governed public APIs."""

    def __init__(self, foundry: FoundryClient) -> None:
        self.foundry = foundry
        self.aip = PalantirAIPClient(foundry)

    def execute_effect(self, effect: AutomateEffect) -> dict[str, Any]:
        if effect.effect_type == "ontology-action":
            return self.foundry.apply_action(
                effect.ontology,
                effect.api_name,
                effect.parameters,
            )
        if effect.effect_type == "aip-logic":
            return self.aip.execute_logic(
                effect.ontology,
                effect.api_name,
                effect.parameters,
                version=effect.version,
            )
        raise ValueError(f"Unsupported Automate effect type: {effect.effect_type}")

    def manifest(self, effect: AutomateEffect) -> dict[str, Any]:
        """Machine-readable intent for configuring the matching in-platform automation."""
        return {
            "version": 1,
            "effect": {
                "type": effect.effect_type,
                "ontology": effect.ontology,
                "apiName": effect.api_name,
                "parameters": effect.parameters,
                "version": effect.version,
            },
            "operator_note": (
                "Configure the trigger/condition in Palantir Automate, then use this "
                "effect target. Wakeup3lm does not invent an undocumented Automate CRUD API."
            ),
        }
