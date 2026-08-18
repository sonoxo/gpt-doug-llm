"""Core ontology validation and game engine for The Resilience Matrix.

The simulator is intentionally defensive and abstract. It models governance,
resilience, safety, quantum readiness, and compliance decisions without
operational attack instructions.
"""
from __future__ import annotations
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
LIKELIHOOD = ['Rare', 'Unlikely', 'Possible', 'Likely', 'Almost Certain']
IMPACT = ['Minor', 'Moderate', 'Major', 'Severe', 'Critical']
CONFIDENCE = ['Low', 'Medium', 'High']
EFFECTIVENESS = ['Ineffective', 'Limited', 'Moderate', 'Strong']
MATURITY = ['Initial', 'Repeatable', 'Defined', 'Managed']
OVERALL_RISK = ['Low', 'Guarded', 'Elevated', 'High', 'Extreme']
READINESS = ['Fragile', 'Developing', 'Prepared', 'Resilient']
BUDGET = ['Depleted', 'Constrained', 'Guarded', 'Adequate', 'Strong']
TRUST = ['Eroding', 'Cautious', 'Stable', 'High']
COMPLIANCE = ['At Risk', 'Watch', 'Managed', 'Strong']
EVIDENCE_QUALITY = ['Weak', 'Partial', 'Adequate', 'Robust']
ENTITY_SECTIONS = ('assets', 'threats', 'dependencies', 'controls', 'stakeholders', 'risks', 'evidence')

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
        self.indexes = {section: {item['id']: item for item in self.data.get(section, [])} for section in ENTITY_SECTIONS}

    @classmethod
    def from_files(cls, ontology_path: Path, scenario_path: Path) -> 'Ontology':
        with ontology_path.open('r', encoding='utf-8') as handle:
            ontology_data = json.load(handle)
        with scenario_path.open('r', encoding='utf-8') as handle:
            scenario_data = json.load(handle)
        return cls(ontology_data, scenario_data)

    def validate(self) -> None:
        for section in ENTITY_SECTIONS:
            if section not in self.data or not isinstance(self.data[section], list):
                raise ValidationError(f'ontology section {section!r} must be a list')
        all_ids: Dict[str, str] = {}
        for section in ENTITY_SECTIONS:
            for item in self.data[section]:
                _require(item, ['id'], section)
                item_id = item['id']
                if item_id in all_ids:
                    raise ValidationError(f'duplicate id {item_id!r} in {section}; already used in {all_ids[item_id]}')
                all_ids[item_id] = section
        ids = {section: {item['id'] for item in self.data[section]} for section in ENTITY_SECTIONS}
        for asset in self.data['assets']:
            _require(asset, ['id', 'name', 'function', 'criticality', 'data_longevity', 'owner'], f"asset {asset.get('id', '?')}")
            _check_enum(asset['criticality'], IMPACT, f"asset {asset['id']} criticality")
            if asset['owner'] not in ids['stakeholders']:
                raise ValidationError(f"asset {asset['id']} owner {asset['owner']} does not exist")
        for threat in self.data['threats']:
            _require(threat, ['id', 'name', 'category', 'affected_assets', 'likelihood', 'impact', 'rationale'], f"threat {threat.get('id', '?')}")
            _check_enum(threat['likelihood'], LIKELIHOOD, f"threat {threat['id']} likelihood")
            _check_enum(threat['impact'], IMPACT, f"threat {threat['id']} impact")
            for asset_id in threat['affected_assets']:
                if asset_id not in ids['assets']:
                    raise ValidationError(f"threat {threat['id']} references unknown asset {asset_id}")
        for dependency in self.data['dependencies']:
            _require(dependency, ['id', 'provider', 'consumer', 'type', 'substitutability', 'failure_mode'], f"dependency {dependency.get('id', '?')}")
            for field_name in ('provider', 'consumer'):
                if dependency[field_name] not in ids['assets']:
                    raise ValidationError(f"dependency {dependency['id']} {field_name} references unknown asset {dependency[field_name]}")
        for control in self.data['controls']:
            _require(control, ['id', 'name', 'control_type', 'mitigated_threats', 'protected_assets', 'effectiveness', 'maturity', 'evidence'], f"control {control.get('id', '?')}")
            _check_enum(control['effectiveness'], EFFECTIVENESS, f"control {control['id']} effectiveness")
            _check_enum(control['maturity'], MATURITY, f"control {control['id']} maturity")
            for threat_id in control['mitigated_threats']:
                if threat_id not in ids['threats']:
                    raise ValidationError(f"control {control['id']} references unknown threat {threat_id}")
            for asset_id in control['protected_assets']:
                if asset_id not in ids['assets']:
                    raise ValidationError(f"control {control['id']} references unknown asset {asset_id}")
            for evidence_id in control['evidence']:
                if evidence_id not in ids['evidence']:
                    raise ValidationError(f"control {control['id']} references unknown evidence {evidence_id}")
        for stakeholder in self.data['stakeholders']:
            _require(stakeholder, ['id', 'name', 'role', 'authority', 'responsibilities'], f"stakeholder {stakeholder.get('id', '?')}")
        for risk in self.data['risks']:
            _require(risk, ['id', 'threat', 'asset', 'dependency_path', 'controls', 'owner', 'confidence', 'rationale'], f"risk {risk.get('id', '?')}")
            if risk['threat'] not in ids['threats']:
                raise ValidationError(f"risk {risk['id']} references unknown threat {risk['threat']}")
            if risk['asset'] not in ids['assets']:
                raise ValidationError(f"risk {risk['id']} references unknown asset {risk['asset']}")
            if risk['owner'] not in ids['stakeholders']:
                raise ValidationError(f"risk {risk['id']} references unknown owner {risk['owner']}")
            _check_enum(risk['confidence'], CONFIDENCE, f"risk {risk['id']} confidence")
            for dep_id in risk['dependency_path']:
                if dep_id not in ids['dependencies']:
                    raise ValidationError(f"risk {risk['id']} references unknown dependency {dep_id}")
            for control_id in risk['controls']:
                if control_id not in ids['controls']:
                    raise ValidationError(f"risk {risk['id']} references unknown control {control_id}")
        for evidence in self.data['evidence']:
            _require(evidence, ['id', 'source', 'date', 'confidence', 'provenance', 'supports'], f"evidence {evidence.get('id', '?')}")
            _check_enum(evidence['confidence'], CONFIDENCE, f"evidence {evidence['id']} confidence")
            support = evidence['supports']
            _require(support, ['type', 'id'], f"evidence {evidence['id']} supports")
            target_section = {'control': 'controls', 'risk': 'risks'}.get(support['type'])
            if not target_section:
                raise ValidationError(f"evidence {evidence['id']} supports type must be control or risk")
            if support['id'] not in ids[target_section]:
                raise ValidationError(f"evidence {evidence['id']} references unknown {support['type']} {support['id']}")
        self._validate_relationships(ids)
        self._validate_scenarios(ids)

    def _validate_relationships(self, ids: Dict[str, set]) -> None:
        relationships = self.data.get('relationships', [])
        if not isinstance(relationships, list):
            raise ValidationError('relationships must be a list')
        valid = {'OWNS': ('stakeholders', 'assets'), 'DEPENDS_ON': ('assets', 'dependencies'), 'THREATENS': ('threats', 'assets'), 'PROPAGATES_FAILURE_TO': ('dependencies', 'assets'), 'PROTECTS': ('controls', 'assets'), 'MITIGATES': ('controls', 'threats'), 'OPERATES': ('stakeholders', 'controls'), 'ACCEPTS_OR_ESCALATES': ('stakeholders', 'risks'), 'SUPPORTS': ('evidence', None)}
        all_ids = set().union(*ids.values())
        for rel in relationships:
            _require(rel, ['subject', 'predicate', 'object'], 'relationship')
            predicate = rel['predicate']
            if predicate not in valid:
                raise ValidationError(f'unsupported relationship predicate {predicate}')
            subject_section, object_section = valid[predicate]
            if rel['subject'] not in ids[subject_section]:
                raise ValidationError(f"relationship {predicate} has invalid subject {rel['subject']} for {subject_section}")
            if object_section:
                if rel['object'] not in ids[object_section]:
                    raise ValidationError(f"relationship {predicate} has invalid object {rel['object']} for {object_section}")
            elif rel['object'] not in all_ids:
                raise ValidationError(f"relationship {predicate} references unknown object {rel['object']}")

    def _validate_scenarios(self, ids: Dict[str, set]) -> None:
        scenarios = self.scenarios.get('scenarios')
        if not isinstance(scenarios, list) or len(scenarios) < 8:
            raise ValidationError('scenarios.json must contain at least 8 scenarios')
        seen = set()
        for scenario in scenarios:
            _require(scenario, ['id', 'title', 'threat_id', 'risk_id', 'brief', 'facts', 'assumptions', 'choices'], f"scenario {scenario.get('id', '?')}")
            if scenario['id'] in seen:
                raise ValidationError(f"duplicate scenario id {scenario['id']}")
            seen.add(scenario['id'])
            if scenario['threat_id'] not in ids['threats']:
                raise ValidationError(f"scenario {scenario['id']} unknown threat {scenario['threat_id']}")
            if scenario['risk_id'] not in ids['risks']:
                raise ValidationError(f"scenario {scenario['id']} unknown risk {scenario['risk_id']}")
            if not 3 <= len(scenario['choices']) <= 5:
                raise ValidationError(f"scenario {scenario['id']} must offer 3-5 choices")
            choice_ids = set()
            for choice in scenario['choices']:
                _require(choice, ['id', 'label', 'description', 'effects', 'why'], f"scenario {scenario['id']} choice")
                if choice['id'] in choice_ids:
                    raise ValidationError(f"scenario {scenario['id']} duplicate choice {choice['id']}")
                choice_ids.add(choice['id'])
                effects = choice['effects']
                if 'control_id' in effects and effects['control_id'] not in ids['controls']:
                    raise ValidationError(f"scenario {scenario['id']} choice {choice['id']} unknown control {effects['control_id']}")

    def get(self, entity_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        for section, index in self.indexes.items():
            if entity_id in index:
                return (section, index[entity_id])
        return None

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
    SAVE_VERSION = 1
    MAX_TURNS = 8

    def __init__(self, ontology: Ontology, seed: int=7) -> None:
        self.ontology = ontology
        self.seed = seed
        self.rng = random.Random(seed)
        scenario_ids = [scenario['id'] for scenario in ontology.scenarios['scenarios']]
        self.rng.shuffle(scenario_ids)
        self.scenario_order = scenario_ids[:self.MAX_TURNS]
        self.turn = 0
        self.finished = False
        self.tracks = {'readiness': 1, 'budget': 3, 'trust': 2, 'compliance': 1, 'evidence_quality': 1}
        self.risks: Dict[str, RiskState] = {}
        for risk in ontology.data['risks']:
            threat = ontology.indexes['threats'][risk['threat']]
            self.risks[risk['id']] = RiskState(risk_id=risk['id'], likelihood=threat['likelihood'], impact=threat['impact'], confidence=risk['confidence'])
        self.control_effectiveness = {control['id']: control['effectiveness'] for control in ontology.data['controls']}
        self.control_maturity = {control['id']: control['maturity'] for control in ontology.data['controls']}
        self.history: List[Dict[str, Any]] = []

    @classmethod
    def default(cls, seed: int=7) -> 'GameEngine':
        base = Path(__file__).resolve().parent / 'data'
        ontology = Ontology.from_files(base / 'ontology.json', base / 'scenarios.json')
        return cls(ontology, seed=seed)

    def current_scenario(self) -> Optional[Dict[str, Any]]:
        if self.finished or self.turn >= self.MAX_TURNS:
            return None
        scenario_id = self.scenario_order[self.turn]
        return next((item for item in self.ontology.scenarios['scenarios'] if item['id'] == scenario_id))

    def track_labels(self) -> Dict[str, str]:
        return {'readiness': READINESS[self.tracks['readiness']], 'budget': BUDGET[self.tracks['budget']], 'trust': TRUST[self.tracks['trust']], 'compliance': COMPLIANCE[self.tracks['compliance']], 'evidence_quality': EVIDENCE_QUALITY[self.tracks['evidence_quality']]}

    def readiness_level(self) -> str:
        return READINESS[self.tracks['readiness']]

    def _risk_explanation(self, risk_id: str) -> Dict[str, str]:
        risk_def = self.ontology.indexes['risks'][risk_id]
        threat = self.ontology.indexes['threats'][risk_def['threat']]
        asset = self.ontology.indexes['assets'][risk_def['asset']]
        state = self.risks[risk_id]
        controls = [self.ontology.indexes['controls'][cid]['name'] for cid in risk_def['controls']]
        dependency_text = 'none identified' if not risk_def['dependency_path'] else ', '.join(risk_def['dependency_path'])
        control_text = ', '.join(controls) if controls else 'no mapped controls'
        return {'likelihood': f"{state.likelihood}: {threat['rationale']['likelihood']} Current decisions may move this ordinal rating up or down; no probability is implied.", 'impact': f"{state.impact}: {threat['rationale']['impact']} The asset is rated {asset['criticality']} criticality and the dependency path is {dependency_text}.", 'confidence': f"{state.confidence}: {risk_def['rationale']['confidence']} Evidence quality and assurance decisions can change this confidence label.", 'overall': f'{state.overall()}: derived from the ordinal combination of {state.likelihood} likelihood and {state.impact} impact, considering mapped defensive controls ({control_text}). It is a qualitative priority band, not a numeric risk score.'}

    def risk_view(self, risk_id: str) -> Dict[str, Any]:
        if risk_id not in self.risks:
            raise KeyError(risk_id)
        risk_def = self.ontology.indexes['risks'][risk_id]
        state = self.risks[risk_id]
        return {'id': risk_id, 'threat': risk_def['threat'], 'asset': risk_def['asset'], 'dependency_path': list(risk_def['dependency_path']), 'controls': list(risk_def['controls']), 'owner': risk_def['owner'], 'likelihood': state.likelihood, 'impact': state.impact, 'confidence': state.confidence, 'overall': state.overall(), 'explanations': self._risk_explanation(risk_id)}

    def all_risks(self) -> List[Dict[str, Any]]:
        return [self.risk_view(risk['id']) for risk in self.ontology.data['risks']]

    def decide(self, choice_token: str) -> Dict[str, Any]:
        scenario = self.current_scenario()
        if scenario is None:
            raise RuntimeError('the simulation has already ended')
        choice = self._resolve_choice(scenario, choice_token)
        before_tracks = self.track_labels()
        risk_id = scenario['risk_id']
        before_risk = self.risk_view(risk_id)
        effects = choice['effects']
        self._apply_track_effects(effects.get('tracks', {}))
        state = self.risks[risk_id]
        if effects.get('likelihood_delta'):
            state.likelihood = _step_label(LIKELIHOOD, state.likelihood, int(effects['likelihood_delta']))
        if effects.get('impact_delta'):
            state.impact = _step_label(IMPACT, state.impact, int(effects['impact_delta']))
        if effects.get('confidence_delta'):
            state.confidence = _step_label(CONFIDENCE, state.confidence, int(effects['confidence_delta']))
        control_change = None
        control_id = effects.get('control_id')
        if control_id:
            old_effectiveness = self.control_effectiveness[control_id]
            old_maturity = self.control_maturity[control_id]
            eff_delta = int(effects.get('effectiveness_delta', 0))
            mat_delta = int(effects.get('maturity_delta', 0))
            self.control_effectiveness[control_id] = _step_label(EFFECTIVENESS, old_effectiveness, eff_delta)
            self.control_maturity[control_id] = _step_label(MATURITY, old_maturity, mat_delta)
            control_change = {'id': control_id, 'effectiveness': [old_effectiveness, self.control_effectiveness[control_id]], 'maturity': [old_maturity, self.control_maturity[control_id]]}
        after_tracks = self.track_labels()
        after_risk = self.risk_view(risk_id)
        record = {'turn': self.turn + 1, 'scenario_id': scenario['id'], 'choice_id': choice['id'], 'choice': choice['label'], 'why': choice['why'], 'before_tracks': before_tracks, 'after_tracks': after_tracks, 'before_risk': before_risk, 'after_risk': after_risk, 'control_change': control_change}
        self.history.append(record)
        self.turn += 1
        if self.turn >= self.MAX_TURNS:
            self.finished = True
        return record

    def _resolve_choice(self, scenario: Dict[str, Any], token: str) -> Dict[str, Any]:
        token = token.strip()
        choices = scenario['choices']
        if token.isdigit():
            index = int(token) - 1
            if 0 <= index < len(choices):
                return choices[index]
        for choice in choices:
            if choice['id'].lower() == token.lower():
                return choice
        raise ValueError(f'unknown choice {token!r}; use a displayed number or choice id')

    def _apply_track_effects(self, track_effects: Mapping[str, Any]) -> None:
        labels = {'readiness': READINESS, 'budget': BUDGET, 'trust': TRUST, 'compliance': COMPLIANCE, 'evidence_quality': EVIDENCE_QUALITY}
        for name, delta in track_effects.items():
            if name not in self.tracks:
                continue
            self.tracks[name] = _clamp(self.tracks[name] + int(delta), 0, len(labels[name]) - 1)

    def dependency_map(self) -> str:
        lines = ['FACT — ASCII DEPENDENCY GRAPH']
        for dep in self.ontology.data['dependencies']:
            provider = self.ontology.indexes['assets'][dep['provider']]
            consumer = self.ontology.indexes['assets'][dep['consumer']]
            lines.append(f"[{provider['id']}] {provider['name']} --{dep['id']}:{dep['type']}--> [{consumer['id']}] {consumer['name']}")
            lines.append(f"    failure: {dep['failure_mode']} | substitutability: {dep['substitutability']}")
        return '\n'.join(lines)

    def objectives(self) -> Dict[str, List[str]]:
        return {'immediate': ['Keep severe risks visible and owned.', 'Preserve decision-quality evidence during each event.'], 'near_term': ['Improve redundancy, control maturity, and assurance coverage.', 'Reduce cryptographic and supplier concentration risk without exhausting capacity.'], 'long_term': ['Reach a resilient readiness posture with durable governance.', 'Maintain auditable evidence and a credible migration path for long-lived data.']}

    def executive_assessment(self) -> Dict[str, Any]:
        risk_counts = {label: 0 for label in OVERALL_RISK}
        for risk in self.risks.values():
            risk_counts[risk.overall()] += 1
        labels = self.track_labels()
        recommendations = []
        if labels['readiness'] != 'Resilient':
            recommendations.append('Prioritize the weakest resilience controls and dependency alternatives.')
        if labels['evidence_quality'] in ('Weak', 'Partial'):
            recommendations.append('Raise evidence quality through documented assurance tests and reviews.')
        if labels['compliance'] in ('At Risk', 'Watch'):
            recommendations.append('Close governance and audit gaps with owned, time-bounded remediation.')
        if any((label in risk_counts and risk_counts[label] for label in ('High', 'Extreme'))):
            recommendations.append('Escalate remaining High or Extreme risks to their accountable owners.')
        if not recommendations:
            recommendations.append('Sustain current controls, test assumptions, and refresh evidence periodically.')
        return {'turns_completed': self.turn, 'tracks': labels, 'risk_distribution': risk_counts, 'recommendations': recommendations}

    def save(self, path: Path) -> Path:
        payload = {'version': self.SAVE_VERSION, 'seed': self.seed, 'turn': self.turn, 'finished': self.finished, 'scenario_order': self.scenario_order, 'tracks': self.tracks, 'risks': {rid: {'likelihood': state.likelihood, 'impact': state.impact, 'confidence': state.confidence} for rid, state in self.risks.items()}, 'control_effectiveness': self.control_effectiveness, 'control_maturity': self.control_maturity, 'history': self.history}
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write('\n')
        return path

    def load(self, path: Path) -> None:
        with Path(path).open('r', encoding='utf-8') as handle:
            payload = json.load(handle)
        if payload.get('version') != self.SAVE_VERSION:
            raise ValidationError(f"unsupported save version {payload.get('version')!r}")
        scenario_ids = {item['id'] for item in self.ontology.scenarios['scenarios']}
        if len(payload.get('scenario_order', [])) != self.MAX_TURNS:
            raise ValidationError('save file has invalid scenario order')
        if not set(payload['scenario_order']).issubset(scenario_ids):
            raise ValidationError('save file references unknown scenarios')
        risk_ids = set(self.risks)
        if set(payload.get('risks', {})) != risk_ids:
            raise ValidationError('save file risk set does not match ontology')
        self.seed = int(payload['seed'])
        self.rng = random.Random(self.seed)
        self.turn = int(payload['turn'])
        self.finished = bool(payload['finished'])
        self.scenario_order = list(payload['scenario_order'])
        self.tracks = {key: int(value) for key, value in payload['tracks'].items()}
        for rid, values in payload['risks'].items():
            _check_enum(values['likelihood'], LIKELIHOOD, f'save risk {rid} likelihood')
            _check_enum(values['impact'], IMPACT, f'save risk {rid} impact')
            _check_enum(values['confidence'], CONFIDENCE, f'save risk {rid} confidence')
            self.risks[rid] = RiskState(rid, values['likelihood'], values['impact'], values['confidence'])
        self.control_effectiveness = dict(payload['control_effectiveness'])
        self.control_maturity = dict(payload['control_maturity'])
        self.history = list(payload['history'])

def load_default_ontology() -> Ontology:
    base = Path(__file__).resolve().parent / 'data'
    return Ontology.from_files(base / 'ontology.json', base / 'scenarios.json')
