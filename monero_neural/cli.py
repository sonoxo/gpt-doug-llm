from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
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


def _probe_rpc(client: MoneroRPCClient, method: str) -> Dict[str, Any]:
    try:
        if method == "daemon":
            result = client.daemon_info()
            return {
                "reachable": True,
                "height": result.get("height"),
                "network": (
                    "stagenet"
                    if result.get("stagenet")
                    else "testnet"
                    if result.get("testnet")
                    else "mainnet"
                ),
            }
        result = client.wallet_balance(account_index=0)
        return {
            "reachable": True,
            "balance": result.get("balance"),
            "unlocked_balance": result.get("unlocked_balance"),
        }
    except MoneroRPCError as exc:
        return {"reachable": False, "error": str(exc)}


def doctor_payload(*, check_rpc: bool = True) -> Dict[str, Any]:
    chain = MoneroNeuralChain(_state_dir())
    ledger = chain.ledger.verify()
    isolated = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    launcher = shutil.which("gpt-doug-xmr-neural")
    daemon_rpc = MoneroRPCClient.daemon_from_env()
    wallet_rpc = MoneroRPCClient.wallet_from_env()

    daemon: Dict[str, Any] = {
        "endpoint": daemon_rpc.endpoint,
        "binary": shutil.which("monerod"),
        "reachable": None,
    }
    wallet: Dict[str, Any] = {
        "endpoint": wallet_rpc.endpoint,
        "binary": shutil.which("monero-wallet-rpc"),
        "reachable": None,
    }
    if check_rpc:
        daemon.update(_probe_rpc(daemon_rpc, "daemon"))
        wallet.update(_probe_rpc(wallet_rpc, "wallet"))

    local_ready = bool(isolated and ledger.get("valid"))
    rpc_ready = daemon.get("reachable") is True and wallet.get("reachable") is True
    if not local_ready:
        status = "LOCAL_INSTALL_INCOMPLETE"
    elif not check_rpc:
        status = "READY_LOCAL"
    elif rpc_ready:
        status = "READY_END_TO_END"
    else:
        status = "READY_LOCAL_RPC_OFFLINE"

    return {
        "schema": "xunia/monero-neural-doctor-v1",
        "status": status,
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "isolated_environment": isolated,
            "prefix": sys.prefix,
        },
        "launcher": launcher,
        "state_dir": str(chain.state_dir),
        "ledger": ledger,
        "monero": {"daemon": daemon, "wallet": wallet},
        "security": {
            "spend_key_loaded": False,
            "automatic_transfer_enabled": False,
            "settlement_signer": "external_only",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpt-doug-xmr-neural")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show local neural-ledger status")
    sub.add_parser("verify-ledger", help="verify the local hash chain")
    doctor = sub.add_parser("doctor", help="verify install, ledger, and Monero RPC wiring")
    doctor.add_argument(
        "--skip-rpc",
        action="store_true",
        help="verify the local install without contacting Monero RPC endpoints",
    )
    doctor.add_argument(
        "--strict-rpc",
        action="store_true",
        help="return a non-zero status unless both daemon and wallet RPC are reachable",
    )
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
    if args.command == "doctor":
        payload = doctor_payload(check_rpc=not args.skip_rpc)
        _print(payload)
        if payload["status"] == "LOCAL_INSTALL_INCOMPLETE":
            return 2
        if args.strict_rpc and payload["status"] != "READY_END_TO_END":
            return 3
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
