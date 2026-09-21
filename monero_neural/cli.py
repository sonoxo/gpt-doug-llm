from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from .core import MoneroNeuralChain
from .rpc import MoneroRPCClient, MoneroRPCError


def _state_dir() -> Path:
    return Path(
        os.getenv("GPT_DOUG_XMR_NEURAL_STATE_DIR", "~/.gpt-doug/monero-neural")
    ).expanduser()


def _print(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpt-doug-xmr-neural")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show local neural-ledger status")
    sub.add_parser("verify-ledger", help="verify the local hash chain")
    sub.add_parser("daemon-info", help="query configured Monero daemon RPC")
    balance = sub.add_parser(
        "wallet-balance", help="query configured wallet RPC balance"
    )
    balance.add_argument("--account-index", type=int, default=0)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    chain = MoneroNeuralChain(_state_dir())
    if args.command == "status":
        _print(chain.status())
        return 0
    if args.command == "verify-ledger":
        _print(chain.ledger.verify())
        return 0
    try:
        if args.command == "daemon-info":
            _print(MoneroRPCClient.daemon_from_env().daemon_info())
            return 0
        if args.command == "wallet-balance":
            _print(
                MoneroRPCClient.wallet_from_env().wallet_balance(
                    account_index=args.account_index
                )
            )
            return 0
    except MoneroRPCError as exc:
        _print({"status": "RPC_ERROR", "error": str(exc)})
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
