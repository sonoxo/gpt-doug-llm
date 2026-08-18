"""Runtime engine for The Resilience Matrix."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .model import (
    BUDGET, COMPLIANCE, CONFIDENCE, EFFECTIVENESS, EVIDENCE_QUALITY, IMPACT,
    LIKELIHOOD, MATURITY, OVERALL_RISK, READINESS, TRACK_LABELS, TRUST,
    Ontology, ValidationError, _check_enum, _clamp, _require, _step_label,
    load_default_ontology,
)

@dataclass
class RiskState:
    risk_id: str
    likelihood: str
    impact: str
    confidence: str

    def overall(self) -> str:
        li = LIKELIHOOD.index(self.likelihood)
        ii = IMPACT.index(self.impact)
        band = max(li, ii)
        if li >= 3 and ii >= 3:
            band = min(4, band + 1)
        elif li <= 1 and ii <= 1:
            band = 0
        return OVERALL_RISK[band]

class GameEngine:
    SAVE_VERSION = 2
    MAX_TURNS = 8

    def __init__(self, ontology: Ontology, seed: int = 7) -> None:
        self.ontology = ontology
        self.seed = seed
        self.rng = random.Random(seed)
        ids = [s["id"] for s in ontology.scenarios["scenarios"]]
        self.rng.shuffle(ids)
        self.scenario_order = ids[:self.MAX_TURNS]
        self.turn = 0
        self.finished = False
        self.tracks = {"readiness": 1, "budget": 3, "trust": 2, "compliance": 1, "evidence_quality": 1}
        self.risks: Dict[str, RiskState] = {}
        for risk in ontology.data["risks"]:
            threat = ontology.indexes["threats"][risk["threat"]]
            self.risks[risk["id"]] = RiskState(risk["id"], threat["likelihood"], threat["impact"], risk["confidence"])
        self.control_effectiveness = {c["id"]: c["effectiveness"] for c in ontology.data["controls"]}
        self.control_maturity = {c["id"]: c["maturity"] for c in ontology.data["controls"]}
        self.history: List[Dict[str, Any]] = []

    @classmethod
    def default(cls, seed: int = 7) -> "GameEngine":
        return cls(load_default_ontology(), seed)

    def current_scenario(self) -> Optional[Dict[str, Any]]:
        if self.finished or self.turn >= self.MAX_TURNS:
            return None
        sid = self.scenario_order[self.turn]
        return next(s for s in self.ontology.scenarios["scenarios"] if s["id"] == sid)

    def track_labels(self) -> Dict[str, str]:
        return {name: labels[self.tracks[name]] for name, labels in TRACK_LABELS.items()}

    def readiness_level(self) -> str:
        return READINESS[self.tracks["readiness"]]

    def status(self) -> Dict[str, Any]:
        scenario = self.current_scenario()
        return {
            "turn": self.turn,
            "max_turns": self.MAX_TURNS,
            "finished": self.finished,
            "next_scenario": scenario["id"] if scenario else None,
            "tracks": self.track_labels(),
        }

    def _risk_explanation(self, risk_id: str) -> Dict[str, str]:
        rd = self.ontology.indexes["risks"][risk_id]
        threat = self.ontology.indexes["threats"][rd["threat"]]
        asset = self.ontology.indexes["assets"][rd["asset"]]
        state = self.risks[risk_id]
        controls = [self.ontology.indexes["controls"][cid]["name"] for cid in rd["controls"]]
        deps = "none identified" if not rd["dependency_path"] else ", ".join(rd["dependency_path"])
        return {
            "likelihood": f"{state.likelihood}: {threat['rationale']['likelihood']} Current decisions may move this ordinal rating; no probability is implied.",
            "impact": f"{state.impact}: {threat['rationale']['impact']} Asset criticality is {asset['criticality']}; dependency path: {deps}.",
            "confidence": f"{state.confidence}: {rd['rationale']['confidence']} Evidence and assurance decisions may change this label.",
            "overall": f"{state.overall()}: qualitative priority derived from ordinal likelihood and impact with mapped controls ({', '.join(controls) or 'none'}); not a numeric score.",
        }

    def risk_view(self, risk_id: str) -> Dict[str, Any]:
        if risk_id not in self.risks:
            raise KeyError(risk_id)
        rd = self.ontology.indexes["risks"][risk_id]
        state = self.risks[risk_id]
        return {
            "id": risk_id, "threat": rd["threat"], "asset": rd["asset"],
            "dependency_path": list(rd["dependency_path"]), "controls": list(rd["controls"]),
            "owner": rd["owner"], "likelihood": state.likelihood, "impact": state.impact,
            "confidence": state.confidence, "overall": state.overall(),
            "explanations": self._risk_explanation(risk_id),
        }

    def all_risks(self) -> List[Dict[str, Any]]:
        return [self.risk_view(r["id"]) for r in self.ontology.data["risks"]]

    def _resolve_choice(self, scenario: Dict[str, Any], token: str) -> Dict[str, Any]:
        token = token.strip()
        choices = scenario["choices"]
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        for choice in choices:
            if choice["id"].lower() == token.lower():
                return choice
        raise ValueError(f"unknown choice {token!r}; use a displayed number or choice id")

    def _apply_track_effects(self, effects: Mapping[str, Any]) -> None:
        for name, delta in effects.items():
            if name not in TRACK_LABELS:
                continue
            self.tracks[name] = _clamp(self.tracks[name] + int(delta), 0, len(TRACK_LABELS[name]) - 1)

    def decide(self, choice_token: str) -> Dict[str, Any]:
        scenario = self.current_scenario()
        if scenario is None:
            raise RuntimeError("the simulation has already ended")
        choice = self._resolve_choice(scenario, choice_token)
        before_tracks = self.track_labels()
        risk_id = scenario["risk_id"]
        before_risk = self.risk_view(risk_id)
        effects = choice["effects"]
        self._apply_track_effects(effects.get("tracks", {}))
        state = self.risks[risk_id]
        for key, labels, attr in (
            ("likelihood_delta", LIKELIHOOD, "likelihood"),
            ("impact_delta", IMPACT, "impact"),
            ("confidence_delta", CONFIDENCE, "confidence"),
        ):
            if key in effects:
                setattr(state, attr, _step_label(labels, getattr(state, attr), int(effects[key])))
        control_change = None
        control_id = effects.get("control_id")
        if control_id:
            old_eff = self.control_effectiveness[control_id]
            old_mat = self.control_maturity[control_id]
            self.control_effectiveness[control_id] = _step_label(EFFECTIVENESS, old_eff, int(effects.get("effectiveness_delta", 0)))
            self.control_maturity[control_id] = _step_label(MATURITY, old_mat, int(effects.get("maturity_delta", 0)))
            control_change = {
                "id": control_id,
                "effectiveness": [old_eff, self.control_effectiveness[control_id]],
                "maturity": [old_mat, self.control_maturity[control_id]],
            }
        record = {
            "turn": self.turn + 1, "scenario_id": scenario["id"], "choice_id": choice["id"],
            "choice": choice["label"], "why": choice["why"], "before_tracks": before_tracks,
            "after_tracks": self.track_labels(), "before_risk": before_risk,
            "after_risk": self.risk_view(risk_id), "control_change": control_change,
        }
        self.history.append(record)
        self.turn += 1
        self.finished = self.turn >= self.MAX_TURNS
        return record

    def dependency_map(self) -> str:
        lines = ["FACT — ASCII DEPENDENCY GRAPH"]
        for dep in self.ontology.data["dependencies"]:
            p = self.ontology.indexes["assets"][dep["provider"]]
            c = self.ontology.indexes["assets"][dep["consumer"]]
            lines.append(f"[{p['id']}] {p['name']} --{dep['id']}:{dep['type']}--> [{c['id']}] {c['name']}")
            lines.append(f"    failure: {dep['failure_mode']} | substitutability: {dep['substitutability']}")
        return "\n".join(lines)

    def objectives(self) -> Dict[str, List[str]]:
        return {
            "immediate": ["Keep severe risks visible and owned.", "Preserve decision-quality evidence during each event."],
            "near_term": ["Improve redundancy, control maturity, and assurance coverage.", "Reduce cryptographic and supplier concentration risk without exhausting capacity."],
            "long_term": ["Reach a resilient readiness posture with durable governance.", "Maintain auditable evidence and a credible migration path for long-lived data."],
        }

    def executive_assessment(self) -> Dict[str, Any]:
        counts = {label: 0 for label in OVERALL_RISK}
        for risk in self.risks.values():
            counts[risk.overall()] += 1
        labels = self.track_labels()
        recs: List[str] = []
        if labels["readiness"] != "Resilient":
            recs.append("Prioritize the weakest resilience controls and dependency alternatives.")
        if labels["evidence_quality"] in ("Weak", "Partial"):
            recs.append("Raise evidence quality through documented assurance tests and reviews.")
        if labels["compliance"] in ("At Risk", "Watch"):
            recs.append("Close governance and audit gaps with owned, time-bounded remediation.")
        if counts["High"] or counts["Extreme"]:
            recs.append("Escalate remaining High or Extreme risks to their accountable owners.")
        if not recs:
            recs.append("Sustain current controls, test assumptions, and refresh evidence periodically.")
        priority = sorted(self.all_risks(), key=lambda r: (OVERALL_RISK.index(r["overall"]), IMPACT.index(r["impact"]), LIKELIHOOD.index(r["likelihood"])), reverse=True)[:3]
        return {
            "turns_completed": self.turn, "tracks": labels, "risk_distribution": counts,
            "priority_risks": [{k: r[k] for k in ("id", "overall", "likelihood", "impact", "owner")} for r in priority],
            "recommendations": recs,
        }

    def save(self, path: Path) -> Path:
        payload = {
            "version": self.SAVE_VERSION, "ontology_fingerprint": self.ontology.fingerprint(),
            "seed": self.seed, "turn": self.turn, "finished": self.finished,
            "scenario_order": self.scenario_order, "tracks": self.tracks,
            "risks": {rid: {"likelihood": s.likelihood, "impact": s.impact, "confidence": s.confidence} for rid, s in self.risks.items()},
            "control_effectiveness": self.control_effectiveness, "control_maturity": self.control_maturity,
            "history": self.history,
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        tmp.replace(path)
        return path

    def _validate_save_payload(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        version = payload.get("version")
        if version not in (1, self.SAVE_VERSION):
            raise ValidationError(f"unsupported save version {version!r}")
        if version == self.SAVE_VERSION and payload.get("ontology_fingerprint") != self.ontology.fingerprint():
            raise ValidationError("save file was created for a different ontology or scenario set")
        required = {"seed", "turn", "finished", "scenario_order", "tracks", "risks", "control_effectiveness", "control_maturity", "history"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValidationError(f"save file missing required fields: {', '.join(missing)}")
        try:
            seed, turn = int(payload["seed"]), int(payload["turn"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("save seed and turn must be integers") from exc
        if not 0 <= turn <= self.MAX_TURNS:
            raise ValidationError(f"save turn must be between 0 and {self.MAX_TURNS}")
        if type(payload["finished"]) is not bool or payload["finished"] != (turn >= self.MAX_TURNS):
            raise ValidationError("save finished flag is inconsistent with turn count")
        order = payload["scenario_order"]
        valid_scenarios = {s["id"] for s in self.ontology.scenarios["scenarios"]}
        if not isinstance(order, list) or len(order) != self.MAX_TURNS or len(set(order)) != self.MAX_TURNS or not set(order).issubset(valid_scenarios):
            raise ValidationError("save file has invalid scenario order")
        tracks = payload["tracks"]
        if not isinstance(tracks, dict) or set(tracks) != set(TRACK_LABELS):
            raise ValidationError("save file track set does not match the simulation")
        checked_tracks = {}
        for name, labels in TRACK_LABELS.items():
            value = tracks[name]
            if type(value) is not int or not 0 <= value < len(labels):
                raise ValidationError(f"save track {name} is outside its ordinal range")
            checked_tracks[name] = value
        risks = payload["risks"]
        if not isinstance(risks, dict) or set(risks) != set(self.risks):
            raise ValidationError("save file risk set does not match ontology")
        checked_risks = {}
        for rid, values in risks.items():
            _require(values, ["likelihood", "impact", "confidence"], f"save risk {rid}")
            _check_enum(values["likelihood"], LIKELIHOOD, f"save risk {rid} likelihood")
            _check_enum(values["impact"], IMPACT, f"save risk {rid} impact")
            _check_enum(values["confidence"], CONFIDENCE, f"save risk {rid} confidence")
            checked_risks[rid] = RiskState(rid, values["likelihood"], values["impact"], values["confidence"])
        control_ids = set(self.control_effectiveness)
        ce, cm = payload["control_effectiveness"], payload["control_maturity"]
        if not isinstance(ce, dict) or set(ce) != control_ids or not isinstance(cm, dict) or set(cm) != control_ids:
            raise ValidationError("save control sets do not match ontology")
        for cid in control_ids:
            _check_enum(ce[cid], EFFECTIVENESS, f"save control {cid} effectiveness")
            _check_enum(cm[cid], MATURITY, f"save control {cid} maturity")
        history = payload["history"]
        if not isinstance(history, list) or len(history) != turn:
            raise ValidationError("save history length must match completed turns")
        scenario_index = {s["id"]: s for s in self.ontology.scenarios["scenarios"]}
        for expected, record in enumerate(history, 1):
            _require(record, ["turn", "scenario_id", "choice_id"], f"save history turn {expected}")
            if record["turn"] != expected or record["scenario_id"] != order[expected - 1]:
                raise ValidationError("save history sequence is invalid")
            valid_choices = {c["id"] for c in scenario_index[record["scenario_id"]]["choices"]}
            if record["choice_id"] not in valid_choices:
                raise ValidationError("save history references an unknown choice")
        return {"seed": seed, "turn": turn, "finished": payload["finished"], "scenario_order": list(order), "tracks": checked_tracks, "risks": checked_risks, "control_effectiveness": dict(ce), "control_maturity": dict(cm), "history": list(history)}

    def load(self, path: Path) -> None:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValidationError("save file root must be a JSON object")
        valid = self._validate_save_payload(payload)
        self.seed = valid["seed"]
        self.rng = random.Random(self.seed)
        self.turn = valid["turn"]
        self.finished = valid["finished"]
        self.scenario_order = valid["scenario_order"]
        self.tracks = valid["tracks"]
        self.risks = valid["risks"]
        self.control_effectiveness = valid["control_effectiveness"]
        self.control_maturity = valid["control_maturity"]
        self.history = valid["history"]

__all__ = ["GameEngine", "Ontology", "ValidationError", "load_default_ontology"]
