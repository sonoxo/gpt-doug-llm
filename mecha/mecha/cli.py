"""Offline MECHA research demonstrator; no hardware or remote actions."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .fixtures import _read_confined_json,load_fixture
from .robotics import simulate_rover
from .snapshot import build_snapshot
from .quantum import simulate_quantum
from .render.terminal import render_frames


def _parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(prog='mecha',description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='report honest offline simulator status')
    for action in ('demo','watch'):
        p=sub.add_parser(action,help='read-only synthetic inspection rover '+action)
        p.add_argument('--fixture',required=True,type=Path)
        p.add_argument('--input-root',required=True,type=Path)
        p.add_argument('--steps',type=int,default=3)
        if action=='watch':
            p.add_argument('--frames',type=int,default=3)
            p.add_argument('--no-color',action='store_true')
    q=sub.add_parser('quantum',help='bounded classical simulation, not quantum hardware')
    q.add_argument('file',type=Path)
    q.add_argument('--input-root',required=True,type=Path)
    q.add_argument('--budget-units',type=int,default=200)
    return parser


def _evaluate(argv: list[str] | None=None) -> Any:
    args=_parser().parse_args(argv)
    if args.command=='doctor':
        return {'system':'GPT-DOUG-MECHA','implementation':'SIMULATED_OFFLINE_V1',
                'authority':'RESEARCH_ONLY','source_kind':'SYNTHETIC',
                'connected_robot':False,'real_world_actuation':False,
                'quantum_hardware_used':False,'biological_hardware_connected':False,
                'host_adapters':'ADAPTER_UNAVAILABLE','external_calls':0}
    if args.command=='quantum':
        return simulate_quantum(_read_confined_json(args.file,input_root=args.input_root),
                                budget_units=args.budget_units)
    fixture=load_fixture(args.fixture,input_root=args.input_root)
    simulation=simulate_rover(fixture,steps=args.steps)
    snapshot=build_snapshot(fixture,simulation)
    if args.command=='demo':
        return {'simulation':simulation,'snapshot':snapshot}
    return render_frames(snapshot,frames=args.frames,color=False)


def main(argv: list[str] | None=None) -> int:
    try:
        value=_evaluate(argv)
        if isinstance(value,list):
            for index,frame in enumerate(value):
                print('=== FRAME {} ==='.format(index+1))
                print(frame)
        else:
            print(json.dumps(value,sort_keys=True,allow_nan=False))
        return 0
    except (ValueError,OSError,TypeError) as exc:
        print(json.dumps({'error':str(exc),'authority':'RESEARCH_ONLY',
                          'external_calls':0},sort_keys=True),file=sys.stderr)
        return 2


if __name__=='__main__':
    sys.exit(main())
