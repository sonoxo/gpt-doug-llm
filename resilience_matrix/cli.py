"""Terminal interface for The Resilience Matrix."""
from __future__ import annotations
import argparse
import json
import shlex
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from .engine import GameEngine, ValidationError
BANNER = '\n+======================================================================+\n|                       THE RESILIENCE MATRIX                          |\n|     Defensive governance, cyber resilience & readiness simulation   |\n+======================================================================+\n'.strip('\n')

def _print_heading(label: str, title: str) -> None:
    print(f'\n{label} — {title}')
    print('-' * min(78, len(label) + len(title) + 3))

def _print_pairs(items: Dict[str, Any], indent: str='  ') -> None:
    for key, value in items.items():
        print(f"{indent}{key.replace('_', ' ').title()}: {value}")

def _print_objectives(engine: GameEngine) -> None:
    objectives = engine.objectives()
    for horizon, goals in objectives.items():
        _print_heading('RECOMMENDATION', f"{horizon.replace('_', ' ').title()} objectives")
        for goal in goals:
            print(f'  - {goal}')

def print_mission(engine: GameEngine) -> None:
    print(BANNER)
    _print_heading('SCENARIO', 'Mission briefing')
    print('  You are the resilience council for the fictional Meridian Civic Cooperative.\n  Preserve essential services, governance credibility, safety, compliance, and\n  long-lived information through eight abstract disruption events.')
    _print_heading('FACT', 'Current posture')
    _print_pairs(engine.track_labels())
    print(f'  Readiness level: {engine.readiness_level()}')
    _print_objectives(engine)
    print_event(engine)

def print_event(engine: GameEngine) -> None:
    scenario = engine.current_scenario()
    if not scenario:
        print_executive_assessment(engine)
        return
    _print_heading('SCENARIO', f"Turn {engine.turn + 1}/{engine.MAX_TURNS}: {scenario['title']}")
    print(f"  {scenario['brief']}")
    _print_heading('FACT', 'Known conditions')
    for item in scenario['facts']:
        print(f'  - {item}')
    _print_heading('ASSUMPTION', 'Planning assumptions')
    for item in scenario['assumptions']:
        print(f'  - {item}')
    risk = engine.risk_view(scenario['risk_id'])
    _print_heading('FACT', f"Current risk {risk['id']}")
    print(f"  Likelihood: {risk['explanations']['likelihood']}")
    print(f"  Impact: {risk['explanations']['impact']}")
    print(f"  Confidence: {risk['explanations']['confidence']}")
    print(f"  Overall: {risk['explanations']['overall']}")
    _print_heading('RECOMMENDATION', 'Defensive choices')
    for index, choice in enumerate(scenario['choices'], start=1):
        print(f"  {index}. [{choice['id']}] {choice['label']}")
        print(f"     {choice['description']}")
    print('\n  Use: decide <number-or-choice-id>')

def _print_risk(risk: Dict[str, Any]) -> None:
    print(f"[{risk['id']}] threat={risk['threat']} asset={risk['asset']} owner={risk['owner']}")
    print(f"  Likelihood: {risk['likelihood']} | Impact: {risk['impact']} | Confidence: {risk['confidence']}")
    print(f"  Overall: {risk['overall']}")
    print(f"  Why likelihood: {risk['explanations']['likelihood']}")
    print(f"  Why impact: {risk['explanations']['impact']}")
    print(f"  Why confidence: {risk['explanations']['confidence']}")
    print(f"  Why overall: {risk['explanations']['overall']}")

def print_risks(engine: GameEngine, risk_id: Optional[str]=None) -> None:
    _print_heading('FACT', 'Risk register')
    if risk_id:
        try:
            _print_risk(engine.risk_view(risk_id))
        except KeyError:
            print(f'  Unknown risk id: {risk_id}')
        return
    for risk in engine.all_risks():
        _print_risk(risk)

def print_controls(engine: GameEngine, control_id: Optional[str]=None) -> None:
    _print_heading('FACT', 'Controls')
    controls = engine.ontology.data['controls']
    if control_id:
        controls = [item for item in controls if item['id'] == control_id]
    if not controls:
        print(f'  Unknown control id: {control_id}')
        return
    for control in controls:
        print(f"[{control['id']}] {control['name']} ({control['control_type']})")
        print(f"  Effectiveness: {engine.control_effectiveness[control['id']]} | Maturity: {engine.control_maturity[control['id']]}")
        print(f"  Protects: {', '.join(control['protected_assets'])}")
        print(f"  Mitigates: {', '.join(control['mitigated_threats'])}")
        print(f"  Evidence: {', '.join(control['evidence']) or 'none'}")

def print_stakeholders(engine: GameEngine, stakeholder_id: Optional[str]=None) -> None:
    _print_heading('FACT', 'Stakeholders')
    items = engine.ontology.data['stakeholders']
    if stakeholder_id:
        items = [item for item in items if item['id'] == stakeholder_id]
    if not items:
        print(f'  Unknown stakeholder id: {stakeholder_id}')
        return
    for item in items:
        print(f"[{item['id']}] {item['name']} — {item['role']}")
        print(f"  Authority: {item['authority']}")
        print(f"  Responsibilities: {', '.join(item['responsibilities'])}")

def print_evidence(engine: GameEngine, evidence_id: Optional[str]=None) -> None:
    _print_heading('FACT', 'Evidence register')
    items = engine.ontology.data['evidence']
    if evidence_id:
        items = [item for item in items if item['id'] == evidence_id]
    if not items:
        print(f'  Unknown evidence id: {evidence_id}')
        return
    for item in items:
        target = item['supports']
        print(f"[{item['id']}] {item['source']} ({item['date']})")
        print(f"  Confidence: {item['confidence']} | Provenance: {item['provenance']}")
        print(f"  Supports: {target['type']} {target['id']}")

def inspect_entity(engine: GameEngine, entity_id: str) -> None:
    found = engine.ontology.get(entity_id)
    if found:
        section, item = found
        _print_heading('FACT', f'Inspect {entity_id} ({section})')
        print(json.dumps(item, indent=2, sort_keys=True))
        if section == 'risks':
            _print_heading('FACT', 'Current dynamic rating')
            _print_risk(engine.risk_view(entity_id))
        return
    print(f'Unknown entity id: {entity_id}')

def print_decision_result(record: Dict[str, Any]) -> None:
    _print_heading('FACT', 'Decision applied')
    print(f"  Choice: {record['choice']} [{record['choice_id']}]")
    _print_heading('RECOMMENDATION', 'Why the system changed')
    print(f"  {record['why']}")
    before = record['before_tracks']
    after = record['after_tracks']
    for key in before:
        if before[key] != after[key]:
            print(f"  - {key.replace('_', ' ').title()}: {before[key]} -> {after[key]}")
    br = record['before_risk']
    ar = record['after_risk']
    for key in ('likelihood', 'impact', 'confidence', 'overall'):
        if br[key] != ar[key]:
            print(f'  - Risk {key}: {br[key]} -> {ar[key]}')
    if record['control_change']:
        change = record['control_change']
        print(f"  - Control {change['id']} effectiveness: {change['effectiveness'][0]} -> {change['effectiveness'][1]}")
        print(f"  - Control {change['id']} maturity: {change['maturity'][0]} -> {change['maturity'][1]}")

def print_executive_assessment(engine: GameEngine) -> None:
    assessment = engine.executive_assessment()
    _print_heading('FACT', 'Executive assessment')
    print(f"  Turns completed: {assessment['turns_completed']}/{engine.MAX_TURNS}")
    _print_pairs(assessment['tracks'])
    print('  Risk distribution:')
    for label, count in assessment['risk_distribution'].items():
        print(f'    {label}: {count}')
    _print_heading('RECOMMENDATION', 'Mitigation roadmap')
    for recommendation in assessment['recommendations']:
        print(f'  - {recommendation}')
    _print_heading('RECOMMENDATION', 'Horizon roadmap')
    objectives = engine.objectives()
    for horizon, goals in objectives.items():
        print(f"  {horizon.replace('_', ' ').title()}:")
        for goal in goals:
            print(f'    - {goal}')

def print_help() -> None:
    print('\nCommands:\n  map                         Render the ASCII dependency graph.\n  inspect <id>                Inspect any ontology entity by ID.\n  risks [risk-id]             Show qualitative risk ratings and explanations.\n  controls [control-id]       Show control state and evidence links.\n  stakeholders [id]           Show stakeholder authority and responsibilities.\n  evidence [evidence-id]      Show evidence confidence and provenance.\n  decide <number|choice-id>   Apply one defensive decision for the current turn.\n  save <path>                 Save the current simulation to JSON.\n  load <path>                 Load a saved simulation.\n  help                        Show this command reference.\n  quit                        Exit the simulation.\n'.strip())

def execute_command(engine: GameEngine, line: str) -> bool:
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        print(f'Command parse error: {exc}')
        return True
    if not parts:
        return True
    command = parts[0].lower()
    args = parts[1:]
    if command == 'help':
        print_help()
    elif command == 'map':
        print(engine.dependency_map())
    elif command == 'inspect':
        if not args:
            print('Usage: inspect <id>')
        else:
            inspect_entity(engine, args[0])
    elif command == 'risks':
        print_risks(engine, args[0] if args else None)
    elif command == 'controls':
        print_controls(engine, args[0] if args else None)
    elif command == 'stakeholders':
        print_stakeholders(engine, args[0] if args else None)
    elif command == 'evidence':
        print_evidence(engine, args[0] if args else None)
    elif command == 'decide':
        if not args:
            print('Usage: decide <number-or-choice-id>')
        else:
            try:
                record = engine.decide(args[0])
                print_decision_result(record)
                if engine.finished:
                    print_executive_assessment(engine)
                else:
                    print_event(engine)
            except (ValueError, RuntimeError) as exc:
                print(f'Decision error: {exc}')
    elif command == 'save':
        if not args:
            print('Usage: save <path>')
        else:
            path = engine.save(Path(args[0]))
            print(f'Saved simulation: {path}')
    elif command == 'load':
        if not args:
            print('Usage: load <path>')
        else:
            try:
                engine.load(Path(args[0]))
                print(f'Loaded simulation: {args[0]}')
                if engine.finished:
                    print_executive_assessment(engine)
                else:
                    print_event(engine)
            except (OSError, json.JSONDecodeError, ValidationError) as exc:
                print(f'Load error: {exc}')
    elif command in ('quit', 'exit'):
        return False
    else:
        print(f"Unknown command: {command}. Use 'help'.")
    return True

def run_demo(engine: GameEngine) -> None:
    """Run a short deterministic, non-interactive sample without consuming all turns."""
    print_mission(engine)
    print('\nresilience> map')
    print(engine.dependency_map())
    print('\nresilience> decide 1')
    record = engine.decide('1')
    print_decision_result(record)
    if not engine.finished:
        print_event(engine)
    print('\nSAMPLE — Demo stopped after one decision; interactive play continues to eight turns.')

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='The Resilience Matrix defensive risk-simulation RPG')
    parser.add_argument('--seed', type=int, default=7, help='deterministic scenario seed (default: 7)')
    parser.add_argument('--demo', action='store_true', help='run a one-decision sample game and exit')
    return parser

def main(argv: Optional[Iterable[str]]=None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        engine = GameEngine.default(seed=args.seed)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f'Unable to start: {exc}')
        return 2
    if args.demo:
        run_demo(engine)
        return 0
    print_mission(engine)
    while True:
        try:
            line = input('\nresilience> ')
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not execute_command(engine, line):
            break
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
