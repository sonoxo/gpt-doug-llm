"""Terminal interface for The Resilience Matrix."""
from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .effects import TerminalFX
from .engine import GameEngine, Ontology, ValidationError

BANNER = r'''
+======================================================================+
|                       THE RESILIENCE MATRIX                          |
|     Defensive governance, cyber resilience & readiness simulation   |
+======================================================================+
'''.strip()


def _heading(label: str, title: str) -> None:
    print(f"\n{label} — {title}")
    print("-" * min(78, len(label) + len(title) + 3))


def _pairs(items: Dict[str, Any]) -> None:
    for key, value in items.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")


def print_event(engine: GameEngine, fx: Optional[TerminalFX] = None) -> None:
    scenario = engine.current_scenario()
    if not scenario:
        print_executive_assessment(engine, fx)
        return
    if fx:
        fx.turn(engine.turn + 1, engine.MAX_TURNS, scenario["title"])
    _heading("SCENARIO", f"Turn {engine.turn + 1}/{engine.MAX_TURNS}: {scenario['title']}")
    print(f"  {scenario['brief']}")
    _heading("FACT", "Known conditions")
    for item in scenario["facts"]:
        print(f"  - {item}")
    _heading("ASSUMPTION", "Planning assumptions")
    for item in scenario["assumptions"]:
        print(f"  - {item}")
    risk = engine.risk_view(scenario["risk_id"])
    _heading("FACT", f"Current risk {risk['id']}")
    for key in ("likelihood", "impact", "confidence", "overall"):
        print(f"  {key.title()}: {risk['explanations'][key]}")
    _heading("RECOMMENDATION", "Defensive choices")
    for index, choice in enumerate(scenario["choices"], 1):
        print(f"  {index}. [{choice['id']}] {choice['label']}")
        print(f"     {choice['description']}")
    print("\n  Use: decide <number-or-choice-id>")


def print_mission(engine: GameEngine, fx: Optional[TerminalFX] = None) -> None:
    if fx:
        fx.boot()
    print(BANNER)
    _heading("SCENARIO", "Mission briefing")
    print("  You are the resilience council for the fictional Meridian Civic Cooperative.\n"
          "  Preserve essential services, governance credibility, safety, compliance, and\n"
          "  long-lived information through eight abstract disruption events.")
    _heading("FACT", "Current posture")
    _pairs(engine.track_labels())
    for horizon, goals in engine.objectives().items():
        _heading("RECOMMENDATION", f"{horizon.replace('_', ' ').title()} objectives")
        for goal in goals:
            print(f"  - {goal}")
    print_event(engine, fx)


def print_risks(engine: GameEngine, risk_id: Optional[str] = None) -> None:
    _heading("FACT", "Risk register")
    risks = [engine.risk_view(risk_id)] if risk_id else engine.all_risks()
    for risk in risks:
        print(f"[{risk['id']}] threat={risk['threat']} asset={risk['asset']} owner={risk['owner']}")
        print(f"  {risk['likelihood']} likelihood | {risk['impact']} impact | {risk['confidence']} confidence | {risk['overall']} overall")
        print(f"  Why: {risk['explanations']['overall']}")


def print_status(engine: GameEngine) -> None:
    _heading("FACT", "Simulation status")
    status = engine.status()
    print(f"  Turn: {status['turn']}/{status['max_turns']} | Finished: {status['finished']}")
    print(f"  Next scenario: {status['next_scenario'] or 'none'}")
    _pairs(status["tracks"])


def print_history(engine: GameEngine) -> None:
    _heading("FACT", "Decision history")
    if not engine.history:
        print("  No decisions recorded yet.")
        return
    for record in engine.history:
        print(f"  Turn {record['turn']}: {record['scenario_id']} -> {record['choice_id']} ({record['choice']})")
        print(f"    Why: {record['why']}")


def print_controls(engine: GameEngine, control_id: Optional[str] = None) -> None:
    _heading("FACT", "Controls")
    controls = engine.ontology.data["controls"]
    if control_id:
        controls = [c for c in controls if c["id"] == control_id]
    if not controls:
        print(f"  Unknown control id: {control_id}")
        return
    for control in controls:
        cid = control["id"]
        print(f"[{cid}] {control['name']} ({control['control_type']})")
        print(f"  Effectiveness: {engine.control_effectiveness[cid]} | Maturity: {engine.control_maturity[cid]}")
        print(f"  Protects: {', '.join(control['protected_assets'])}")
        print(f"  Mitigates: {', '.join(control['mitigated_threats'])}")
        print(f"  Evidence: {', '.join(control['evidence']) or 'none'}")


def print_stakeholders(engine: GameEngine, stakeholder_id: Optional[str] = None) -> None:
    _heading("FACT", "Stakeholders")
    items = engine.ontology.data["stakeholders"]
    if stakeholder_id:
        items = [s for s in items if s["id"] == stakeholder_id]
    if not items:
        print(f"  Unknown stakeholder id: {stakeholder_id}")
        return
    for item in items:
        print(f"[{item['id']}] {item['name']} — {item['role']}")
        print(f"  Authority: {item['authority']}")
        print(f"  Responsibilities: {', '.join(item['responsibilities'])}")


def print_evidence(engine: GameEngine, evidence_id: Optional[str] = None) -> None:
    _heading("FACT", "Evidence register")
    items = engine.ontology.data["evidence"]
    if evidence_id:
        items = [e for e in items if e["id"] == evidence_id]
    if not items:
        print(f"  Unknown evidence id: {evidence_id}")
        return
    for item in items:
        target = item["supports"]
        print(f"[{item['id']}] {item['source']} ({item['date']})")
        print(f"  Confidence: {item['confidence']} | Provenance: {item['provenance']}")
        print(f"  Supports: {target['type']} {target['id']}")


def inspect_entity(engine: GameEngine, entity_id: str) -> None:
    found = engine.ontology.get(entity_id)
    if not found:
        print(f"Unknown entity id: {entity_id}")
        return
    section, item = found
    _heading("FACT", f"Inspect {entity_id} ({section})")
    print(json.dumps(item, indent=2, sort_keys=True))
    if section == "risks":
        print_risks(engine, entity_id)


def print_decision(record: Dict[str, Any]) -> None:
    _heading("FACT", "Decision applied")
    print(f"  Choice: {record['choice']} [{record['choice_id']}]")
    _heading("RECOMMENDATION", "Why the system changed")
    print(f"  {record['why']}")
    for key, before in record["before_tracks"].items():
        after = record["after_tracks"][key]
        if before != after:
            print(f"  - {key.replace('_', ' ').title()}: {before} -> {after}")
    for key in ("likelihood", "impact", "confidence", "overall"):
        before = record["before_risk"][key]
        after = record["after_risk"][key]
        if before != after:
            print(f"  - Risk {key}: {before} -> {after}")
    if record["control_change"]:
        change = record["control_change"]
        print(f"  - Control {change['id']} effectiveness: {change['effectiveness'][0]} -> {change['effectiveness'][1]}")
        print(f"  - Control {change['id']} maturity: {change['maturity'][0]} -> {change['maturity'][1]}")


def print_executive_assessment(engine: GameEngine, fx: Optional[TerminalFX] = None) -> None:
    if fx:
        fx.finale()
    assessment = engine.executive_assessment()
    _heading("FACT", "Executive assessment")
    print(f"  Turns completed: {assessment['turns_completed']}/{engine.MAX_TURNS}")
    _pairs(assessment["tracks"])
    print("  Priority risks:")
    for risk in assessment.get("priority_risks", []):
        print(f"    - {risk['id']}: {risk['overall']} ({risk['likelihood']} / {risk['impact']}) owner={risk['owner']}")
    _heading("RECOMMENDATION", "Mitigation roadmap")
    for item in assessment["recommendations"]:
        print(f"  - {item}")


def print_effects(fx: TerminalFX) -> None:
    _heading("FACT", "Terminal effects")
    settings = fx.settings()
    print(f"  Supported: {settings['supported']}")
    print(f"  Enabled: {settings['enabled']}")
    print(f"  3D mode: {settings['three_d']}")
    print(f"  Scene seconds: {settings['scene_seconds']}")
    print(f"  FPS: {settings['fps']}")
    print(f"  Color: {settings['color']}")
    print("  Commands: effects demo | effects on | effects off | effects seconds <n> | effects fps <6-60>")


def handle_effects_command(fx: TerminalFX, args: list[str]) -> None:
    if not args or args[0].lower() == "status":
        print_effects(fx)
        return
    action = args[0].lower()
    if action == "demo":
        seconds = float(args[1]) if len(args) > 1 else None
        fx.showcase(seconds=seconds)
        return
    if action == "on":
        enabled = fx.set_enabled(True)
        print(f"Terminal effects {'enabled' if enabled else 'unavailable on this terminal'}.")
        return
    if action == "off":
        fx.set_enabled(False)
        print("Terminal effects disabled.")
        return
    if action == "seconds":
        if len(args) != 2:
            raise ValueError("usage: effects seconds <number>")
        seconds = fx.set_scene_seconds(float(args[1]))
        print(f"3D scene duration set to {seconds:g} seconds.")
        return
    if action == "fps":
        if len(args) != 2:
            raise ValueError("usage: effects fps <6-60>")
        fps = fx.set_fps(int(args[1]))
        print(f"3D frame rate set to {fps} FPS.")
        return
    raise ValueError("usage: effects [status|demo [seconds]|on|off|seconds <n>|fps <6-60>]")


def print_help() -> None:
    print("""
Commands:
  status                      Show turn and current readiness tracks.
  history                     Show decisions already taken.
  map                         Render the ASCII dependency graph.
  inspect <id>                Inspect any ontology entity by ID.
  risks [risk-id]             Show qualitative risk ratings and explanations.
  controls [control-id]       Show control state and evidence links.
  stakeholders [id]           Show stakeholder authority and responsibilities.
  evidence [evidence-id]      Show evidence confidence and provenance.
  decide <number|choice-id>   Apply one defensive decision for the current turn.
  effects                     Show terminal animation settings.
  effects demo [seconds]      Replay the pseudo-3D effects showcase.
  effects on|off              Enable or disable effects during play.
  effects seconds <n>         Change 3D scene duration without restarting.
  effects fps <6-60>          Change pseudo-3D frame rate.
  save <path>                 Save the current simulation to JSON.
  load <path>                 Load a saved simulation.
  help                        Show this command reference.
  quit                        Exit the simulation.
""".strip())


def execute_command(engine: GameEngine, line: str, fx: Optional[TerminalFX] = None) -> bool:
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        print(f"Command parse error: {exc}")
        return True
    if not parts:
        return True
    command, args = parts[0].lower(), parts[1:]
    try:
        if command == "help": print_help()
        elif command == "status": print_status(engine)
        elif command == "history": print_history(engine)
        elif command == "map": print(engine.dependency_map())
        elif command == "inspect": inspect_entity(engine, args[0]) if args else print("Usage: inspect <id>")
        elif command == "risks": print_risks(engine, args[0] if args else None)
        elif command == "controls": print_controls(engine, args[0] if args else None)
        elif command == "stakeholders": print_stakeholders(engine, args[0] if args else None)
        elif command == "evidence": print_evidence(engine, args[0] if args else None)
        elif command == "effects":
            if fx is None:
                print("Terminal effects controller is unavailable.")
            else:
                handle_effects_command(fx, args)
        elif command == "decide":
            if not args:
                print("Usage: decide <number-or-choice-id>")
            else:
                record = engine.decide(args[0])
                if fx:
                    fx.decision()
                print_decision(record)
                print_executive_assessment(engine, fx) if engine.finished else print_event(engine, fx)
        elif command == "save":
            if not args:
                print("Usage: save <path>")
            else:
                path = engine.save(Path(args[0]))
                if fx:
                    fx.io("Writing simulation state", "SAVED")
                print(f"Saved simulation: {path}")
        elif command == "load":
            if not args:
                print("Usage: load <path>")
            else:
                if fx:
                    fx.io("Reading simulation state", "LOADED")
                engine.load(Path(args[0]))
                print(f"Loaded simulation: {args[0]}")
                print_executive_assessment(engine, fx) if engine.finished else print_event(engine, fx)
        elif command in ("quit", "exit"):
            return False
        else:
            print(f"Unknown command: {command}. Use 'help'.")
    except (KeyError, ValueError, RuntimeError, OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Command error: {exc}")
    return True


def run_demo(engine: GameEngine, fx: Optional[TerminalFX] = None) -> None:
    print_mission(engine, fx)
    print("\nresilience> status")
    print_status(engine)
    print("\nresilience> map")
    print(engine.dependency_map())
    print("\nresilience> decide 1")
    record = engine.decide("1")
    if fx:
        fx.decision()
    print_decision(record)
    if not engine.finished:
        print_event(engine, fx)
    print("\nSAMPLE — Demo stopped after one decision; interactive play continues to eight turns.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="The Resilience Matrix defensive risk-simulation RPG")
    parser.add_argument("--seed", type=int, default=7, help="deterministic scenario seed (default: 7)")
    parser.add_argument("--demo", action="store_true", help="run a one-decision sample game and exit")
    parser.add_argument("--ontology", type=Path, help="custom ontology JSON file")
    parser.add_argument("--scenarios", type=Path, help="custom scenarios JSON file")
    parser.add_argument("--validate-only", action="store_true", help="validate JSON model files and exit")
    parser.add_argument("--no-animations", action="store_true", help="disable terminal animations")
    parser.add_argument("--3d-seconds", dest="three_d_seconds", type=float, default=3.0,
                        help="seconds per pseudo-3D scene (default: 3.0)")
    parser.add_argument("--3d-fps", dest="three_d_fps", type=int, default=24,
                        help="pseudo-3D frame rate, 6-60 (default: 24)")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if bool(args.ontology) != bool(args.scenarios):
        print("Unable to start: --ontology and --scenarios must be provided together")
        return 2
    if args.three_d_seconds <= 0:
        print("Unable to start: --3d-seconds must be greater than zero")
        return 2
    if not 6 <= args.three_d_fps <= 60:
        print("Unable to start: --3d-fps must be between 6 and 60")
        return 2
    try:
        ontology = Ontology.from_files(args.ontology, args.scenarios) if args.ontology else None
        engine = GameEngine(ontology, args.seed) if ontology else GameEngine.default(args.seed)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Unable to start: {exc}")
        return 2
    if args.validate_only:
        print("VALID — ontology and scenarios passed reference and schema validation.")
        return 0

    fx = TerminalFX(
        enabled=not args.no_animations,
        scene_seconds=args.three_d_seconds,
        fps=args.three_d_fps,
    )
    if args.demo:
        run_demo(engine, fx)
        return 0

    print_mission(engine, fx)
    while not engine.finished:
        try:
            line = input("\nresilience> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not execute_command(engine, line, fx):
            return 0
    print("\nSimulation complete. Final assessment shown above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
