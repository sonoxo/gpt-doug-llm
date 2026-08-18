"""Ontology schema, ordinal vocabularies, and reference validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

LIKELIHOOD = ["Rare", "Unlikely", "Possible", "Likely", "Almost Certain"]
IMPACT = ["Minor", "Moderate", "Major", "Severe", "Critical"]
CONFIDENCE = ["Low", "Medium", "High"]
EFFECTIVENESS = ["Ineffective", "Limited", "Moderate", "Strong"]
MATURITY = ["Initial", "Repeatable", "Defined", "Managed"]
OVERALL_RISK = ["Low", "Guarded", "Elevated", "High", "Extreme"]

READINESS = ["Fragile", "Developing", "Prepared", "Resilient"]
BUDGET = ["Depleted", "Constrained", "Guarded", "Adequate", "Strong"]
TRUST = ["Eroding", "Cautious", "Stable", "High"]
COMPLIANCE = ["At Risk", "Watch", "Managed", "Strong"]
EVIDENCE_QUALITY = ["Weak", "Partial", "Adequate", "Robust"]

TRACK_LABELS = {
    "readiness": READINESS,
    "budget": BUDGET,
    "trust": TRUST,
    "compliance": COMPLIANCE,
    "evidence_quality": EVIDENCE_QUALITY,
}

ENTITY_SECTIONS = ("assets", "threats", "dependencies", "controls", "stakeholders", "risks", "evidence")


class ValidationError(ValueError):
    """Raised when ontology or scenario references are invalid."""


def _require(mapping: Mapping[str, Any], fields: Iterable[str], context: str) -> None:
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise ValidationError(f"{context} missing required fields: {', '.join(missing)}")


def _check_enum(value: str, allowed: Sequence[str], context: str) -> None:
    if value not in allowed:
        raise ValidationError(f"{context} must be one of {', '.join(allowed)}; got {value!r}")


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _step_label(labels: Sequence[str], current: str, delta: int) -> str:
    index = labels.index(current)
    return labels[_clamp(index + delta, 0, len(labels) - 1)]


@dataclass
class Ontology:
    data: Dict[str, Any]
    scenarios: Dict[str, Any]
    indexes: Dict[str, Dict[str, Dict[str, Any]]] = field(init=False)

    def __post_init__(self) -> None:
        self.validate()
        self.indexes = {
            section: {item["id"]: item for item in self.data.get(section, [])}
            for section in ENTITY_SECTIONS
        }

    @classmethod
    def from_files(cls, ontology_path: Path, scenario_path: Path) -> "Ontology":
        with ontology_path.open("r", encoding="utf-8") as handle:
            ontology_data = json.load(handle)
        with scenario_path.open("r", encoding="utf-8") as handle:
            scenario_data = json.load(handle)
        return cls(ontology_data, scenario_data)

    def fingerprint(self) -> str:
        """Return a deterministic fingerprint for save-file compatibility checks."""
        canonical = json.dumps(
            {"ontology": self.data, "scenarios": self.scenarios},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def validate(self) -> None:
        for section in ENTITY_SECTIONS:
            if section not in self.data or not isinstance(self.data[section], list):
                raise ValidationError(f"ontology section {section!r} must be a list")

        all_ids: Dict[str, str] = {}
        for section in ENTITY_SECTIONS:
            for item in self.data[section]:
                _require(item, ["id"], section)
                item_id = item["id"]
                if item_id in all_ids:
                    raise ValidationError(
                        f"duplicate id {item_id!r} in {section}; already used in {all_ids[item_id]}"
                    )
                all_ids[item_id] = section

        ids = {
            section: {item["id"] for item in self.data[section]}
            for section in ENTITY_SECTIONS
        }

        for asset in self.data["assets"]:
            _require(
                asset,
                ["id", "name", "function", "criticality", "data_longevity", "owner"],
                f"asset {asset.get('id', '?')}",
            )
            _check_enum(asset["criticality"], IMPACT, f"asset {asset['id']} criticality")
            if asset["owner"] not in ids["stakeholders"]:
                raise ValidationError(f"asset {asset['id']} owner {asset['owner']} does not exist")

        for threat in self.data["threats"]:
            _require(
                threat,
                ["id", "name", "category", "affected_assets", "likelihood", "impact", "rationale"],
                f"threat {threat.get('id', '?')}",
            )
            _check_enum(threat["likelihood"], LIKELIHOOD, f"threat {threat['id']} likelihood")
            _check_enum(threat["impact"], IMPACT, f"threat {threat['id']} impact")
            for asset_id in threat["affected_assets"]:
                if asset_id not in ids["assets"]:
                    raise ValidationError(f"threat {threat['id']} references unknown asset {asset_id}")

        for dependency in self.data["dependencies"]:
            _require(
                dependency,
                ["id", "provider", "consumer", "type", "substitutability", "failure_mode"],
                f"dependency {dependency.get('id', '?')}",
            )
            for field_name in ("provider", "consumer"):
                if dependency[field_name] not in ids["assets"]:
                    raise ValidationError(
                        f"dependency {dependency['id']} {field_name} references unknown asset "
                        f"{dependency[field_name]}"
                    )

        for control in self.data["controls"]:
            _require(
                control,
                [
                    "id",
                    "name",
                    "control_type",
                    "mitigated_threats",
                    "protected_assets",
                    "effectiveness",
                    "maturity",
                    "evidence",
                ],
                f"control {control.get('id', '?')}",
            )
            _check_enum(control["effectiveness"], EFFECTIVENESS, f"control {control['id']} effectiveness")
            _check_enum(control["maturity"], MATURITY, f"control {control['id']} maturity")
            for threat_id in control["mitigated_threats"]:
                if threat_id not in ids["threats"]:
                    raise ValidationError(f"control {control['id']} references unknown threat {threat_id}")
            for asset_id in control["protected_assets"]:
                if asset_id not in ids["assets"]:
                    raise ValidationError(f"control {control['id']} references unknown asset {asset_id}")
            for evidence_id in control["evidence"]:
                if evidence_id not in ids["evidence"]:
                    raise ValidationError(f"control {control['id']} references unknown evidence {evidence_id}")

        for stakeholder in self.data["stakeholders"]:
            _require(
                stakeholder,
                ["id", "name", "role", "authority", "responsibilities"],
                f"stakeholder {stakeholder.get('id', '?')}",
            )

        for risk in self.data["risks"]:
            _require(
                risk,
                ["id", "threat", "asset", "dependency_path", "controls", "owner", "confidence", "rationale"],
                f"risk {risk.get('id', '?')}",
            )
            if risk["threat"] not in ids["threats"]:
                raise ValidationError(f"risk {risk['id']} references unknown threat {risk['threat']}")
            if risk["asset"] not in ids["assets"]:
                raise ValidationError(f"risk {risk['id']} references unknown asset {risk['asset']}")
            if risk["owner"] not in ids["stakeholders"]:
                raise ValidationError(f"risk {risk['id']} references unknown owner {risk['owner']}")
            _check_enum(risk["confidence"], CONFIDENCE, f"risk {risk['id']} confidence")
            for dep_id in risk["dependency_path"]:
                if dep_id not in ids["dependencies"]:
                    raise ValidationError(f"risk {risk['id']} references unknown dependency {dep_id}")
            for control_id in risk["controls"]:
                if control_id not in ids["controls"]:
                    raise ValidationError(f"risk {risk['id']} references unknown control {control_id}")

        for evidence in self.data["evidence"]:
            _require(
                evidence,
                ["id", "source", "date", "confidence", "provenance", "supports"],
                f"evidence {evidence.get('id', '?')}",
            )
            _check_enum(evidence["confidence"], CONFIDENCE, f"evidence {evidence['id']} confidence")
            support = evidence["supports"]
            _require(support, ["type", "id"], f"evidence {evidence['id']} supports")
            target_section = {"control": "controls", "risk": "risks"}.get(support["type"])
            if not target_section:
                raise ValidationError(f"evidence {evidence['id']} supports type must be control or risk")
            if support["id"] not in ids[target_section]:
                raise ValidationError(
                    f"evidence {evidence['id']} references unknown {support['type']} {support['id']}"
                )

        self._validate_relationships(ids)
        self._validate_scenarios(ids)

    def _validate_relationships(self, ids: Dict[str, set]) -> None:
        relationships = self.data.get("relationships", [])
        if not isinstance(relationships, list):
            raise ValidationError("relationships must be a list")
        valid = {
            "OWNS": ("stakeholders", "assets"),
            "DEPENDS_ON": ("assets", "dependencies"),
            "THREATENS": ("threats", "assets"),
            "PROPAGATES_FAILURE_TO": ("dependencies", "assets"),
            "PROTECTS": ("controls", "assets"),
            "MITIGATES": ("controls", "threats"),
            "OPERATES": ("stakeholders", "controls"),
            "ACCEPTS_OR_ESCALATES": ("stakeholders", "risks"),
            "SUPPORTS": ("evidence", None),
        }
        all_ids = set().union(*ids.values())
        for rel in relationships:
            _require(rel, ["subject", "predicate", "object"], "relationship")
            predicate = rel["predicate"]
            if predicate not in valid:
                raise ValidationError(f"unsupported relationship predicate {predicate}")
            subject_section, object_section = valid[predicate]
            if rel["subject"] not in ids[subject_section]:
                raise ValidationError(
                    f"relationship {predicate} has invalid subject {rel['subject']} for {subject_section}"
                )
            if object_section:
                if rel["object"] not in ids[object_section]:
                    raise ValidationError(
                        f"relationship {predicate} has invalid object {rel['object']} for {object_section}"
                    )
            elif rel["object"] not in all_ids:
                raise ValidationError(f"relationship {predicate} references unknown object {rel['object']}")

    def _validate_scenarios(self, ids: Dict[str, set]) -> None:
        scenarios = self.scenarios.get("scenarios")
        if not isinstance(scenarios, list) or len(scenarios) < 8:
            raise ValidationError("scenarios.json must contain at least 8 scenarios")

        risk_index = {item["id"]: item for item in self.data["risks"]}
        valid_effect_keys = {
            "likelihood_delta",
            "impact_delta",
            "confidence_delta",
            "tracks",
            "control_id",
            "effectiveness_delta",
            "maturity_delta",
        }
        seen = set()
        for scenario in scenarios:
            _require(
                scenario,
                ["id", "title", "threat_id", "risk_id", "brief", "facts", "assumptions", "choices"],
                f"scenario {scenario.get('id', '?')}",
            )
            scenario_id = scenario["id"]
            if scenario_id in seen:
                raise ValidationError(f"duplicate scenario id {scenario_id}")
            seen.add(scenario_id)
            if scenario["threat_id"] not in ids["threats"]:
                raise ValidationError(f"scenario {scenario_id} unknown threat {scenario['threat_id']}")
            if scenario["risk_id"] not in ids["risks"]:
                raise ValidationError(f"scenario {scenario_id} unknown risk {scenario['risk_id']}")

            risk = risk_index[scenario["risk_id"]]
            if risk["threat"] != scenario["threat_id"]:
                raise ValidationError(
                    f"scenario {scenario_id} threat {scenario['threat_id']} does not match "
                    f"risk {scenario['risk_id']} threat {risk['threat']}"
                )
            for field_name in ("facts", "assumptions"):
                values = scenario[field_name]
                if not isinstance(values, list) or not values or not all(
                    isinstance(item, str) and item.strip() for item in values
                ):
                    raise ValidationError(f"scenario {scenario_id} {field_name} must be non-empty text items")
            if not isinstance(scenario["choices"], list) or not 3 <= len(scenario["choices"]) <= 5:
                raise ValidationError(f"scenario {scenario_id} must offer 3-5 choices")

            choice_ids = set()
            for choice in scenario["choices"]:
                _require(
                    choice,
                    ["id", "label", "description", "effects", "why"],
                    f"scenario {scenario_id} choice",
                )
                if choice["id"] in choice_ids:
                    raise ValidationError(f"scenario {scenario_id} duplicate choice {choice['id']}")
                choice_ids.add(choice["id"])
                if not all(
                    isinstance(choice[field_name], str) and choice[field_name].strip()
                    for field_name in ("id", "label", "description", "why")
                ):
                    raise ValidationError(f"scenario {scenario_id} choices require non-empty text fields")

                effects = choice["effects"]
                if not isinstance(effects, dict):
                    raise ValidationError(f"scenario {scenario_id} choice {choice['id']} effects must be an object")
                unknown_effects = set(effects) - valid_effect_keys
                if unknown_effects:
                    raise ValidationError(
                        f"scenario {scenario_id} choice {choice['id']} has unknown effects: "
                        f"{', '.join(sorted(unknown_effects))}"
                    )
                for delta_name in (
                    "likelihood_delta",
                    "impact_delta",
                    "confidence_delta",
                    "effectiveness_delta",
                    "maturity_delta",
                ):
                    if delta_name in effects and type(effects[delta_name]) is not int:
                        raise ValidationError(
                            f"scenario {scenario_id} choice {choice['id']} {delta_name} must be an integer"
                        )
                track_effects = effects.get("tracks", {})
                if not isinstance(track_effects, dict):
                    raise ValidationError(
                        f"scenario {scenario_id} choice {choice['id']} tracks must be an object"
                    )
                for track_name, delta in track_effects.items():
                    if track_name not in TRACK_LABELS:
                        raise ValidationError(
                            f"scenario {scenario_id} choice {choice['id']} unknown track {track_name}"
                        )
                    if type(delta) is not int:
                        raise ValidationError(
                            f"scenario {scenario_id} choice {choice['id']} track {track_name} delta must be an integer"
                        )

                control_id = effects.get("control_id")
                if control_id is not None:
                    if control_id not in ids["controls"]:
                        raise ValidationError(
                            f"scenario {scenario_id} choice {choice['id']} unknown control {control_id}"
                        )
                    if control_id not in risk["controls"]:
                        raise ValidationError(
                            f"scenario {scenario_id} choice {choice['id']} control {control_id} is not mapped "
                            f"to risk {scenario['risk_id']}"
                        )
                elif "effectiveness_delta" in effects or "maturity_delta" in effects:
                    raise ValidationError(
                        f"scenario {scenario_id} choice {choice['id']} control deltas require control_id"
                    )

    def get(self, entity_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        for section, index in self.indexes.items():
            if entity_id in index:
                return section, index[entity_id]
        return None


def load_default_ontology() -> Ontology:
    base = Path(__file__).resolve().parent / "data"
    return Ontology.from_files(base / "ontology.json", base / "scenarios.json")
