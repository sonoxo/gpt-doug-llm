import json
import sys

from gpt_brain.cli import build_parser, main


def test_parser_exposes_warhawk_status():
    args = build_parser().parse_args(
        ["warhawk", "status", "--repo", ".", "--workers", "4"]
    )
    assert args.command == "warhawk"
    assert args.warhawk_command == "status"
    assert args.workers == 4


def test_warhawk_status_cli_requires_no_model(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["gpt-doug", "warhawk", "status"])
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["codename"] == "US-01-GoDsWarHawk"
    assert payload["mode"] == "DEFENSIVE_SOFTWARE_SWARM"
