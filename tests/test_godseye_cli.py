import json
import sys

from gpt_brain.cli import build_parser, main


def test_parser_exposes_godseye_commands():
    args = build_parser().parse_args(["godseye", "query", "show", "health"])
    assert args.command == "godseye"
    assert args.godseye_command == "query"
    assert args.question == ["show", "health"]


def test_parser_exposes_planetary_commands():
    args = build_parser().parse_args(["planetary", "plan", "compare", "layers"])
    assert args.command == "planetary"
    assert args.planetary_command == "plan"
    assert args.mission == ["compare", "layers"]


def test_godseye_status_cli(monkeypatch, capsys):
    import godseye.fusion as fusion

    class Snapshot:
        def to_dict(self):
            return {"schema": "gpt-doug.godseye-snapshot.v1", "subsystems": {}}

    monkeypatch.setattr(fusion, "collect_snapshot", lambda: Snapshot())
    monkeypatch.setattr(sys, "argv", ["gpt-doug", "godseye", "status"])
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "gpt-doug.godseye-snapshot.v1"


def test_planetary_plan_cli(monkeypatch, capsys):
    import godseye.planetary as planetary

    monkeypatch.setattr(
        planetary,
        "planetary_plan",
        lambda mission: {"schema": "gpt-doug.planetary-plan.v1", "mission": mission},
    )
    monkeypatch.setattr(sys, "argv", ["gpt-doug", "planetary", "plan", "compare", "layers"])
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mission"] == "compare layers"
