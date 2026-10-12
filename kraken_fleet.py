"""Operator-owned, offline evidence of GPT-Doug/ZYRA emergency-stop coverage.

Never scans networks, starts/stops other machines, or rearms AI. A receipt
reports what the cooperating local Python stop gate observed at that instant.
A signature and a fresh receipt do not prove host integrity or external control.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ai_killswitch import status as local_stop_status

SCHEMA = 1
ALG = "HMAC-SHA256"
NODE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}\Z")
FLEET_ID = NODE_ID
CONFIRMED_REASONS = frozenset(("operator_stop_latched", "host_enforced_stop"))
REPORT_FIELDS = frozenset(("schema_version", "fleet_id", "campaign_id", "node_id", "reported_at", "state", "stop_reason", "algorithm"))
MAX_NODES = 256
CLOCK_SKEW_SECONDS = 60


class FleetError(ValueError):
    """Invalid or unsafe operator input. No remote actions are performed."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise FleetError("expected UTC timestamp with Z suffix")
    try:
        instant = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise FleetError("invalid UTC timestamp") from error
    if instant.utcoffset() != timedelta(0):
        raise FleetError("timestamp must be UTC")
    return instant


def identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not NODE_ID.fullmatch(value):
        raise FleetError(f"invalid {name}: use 1-64 letters, digits, dot, underscore, hyphen")
    return value


def _json_file(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise FleetError(f"missing or unsafe JSON file: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FleetError(f"unreadable or invalid JSON file: {path}") from error
    if not isinstance(document, dict):
        raise FleetError(f"expected JSON object: {path}")
    return document


def load_inventory(path: Path) -> dict[str, Any]:
    value = _json_file(path)
    if value.get("schema_version") != SCHEMA or set(value) != {"schema_version", "fleet_id", "nodes"}:
        raise FleetError("inventory must contain schema_version, fleet_id and nodes")
    identifier(value["fleet_id"], "fleet_id")
    nodes = value["nodes"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise FleetError("inventory must explicitly identify 1-256 controlled nodes")
    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {"id", "label"}:
            raise FleetError("each node requires only id and label")
        node_id = identifier(node["id"], "node_id")
        if node_id in seen:
            raise FleetError("duplicate node identifier")
        seen.add(node_id)
        if not isinstance(node["label"], str) or not 1 <= len(node["label"]) <= 120:
            raise FleetError("node label must be 1-120 characters")
    return value


def load_campaign(path: Path, *, now: datetime | None = None) -> dict[str, Any]:
    value = _json_file(path)
    if value.get("schema_version") != SCHEMA or set(value) != {"schema_version", "fleet_id", "campaign_id", "created_at"}:
        raise FleetError("invalid emergency-stop campaign format")
    identifier(value["fleet_id"], "fleet_id")
    campaign = value["campaign_id"]
    if not isinstance(campaign, str) or not re.fullmatch(r"[0-9a-f]{32}", campaign):
        raise FleetError("invalid campaign identifier")
    created = parse_time(value["created_at"])
    if created > (now or utc_now()) + timedelta(seconds=CLOCK_SKEW_SECONDS):
        raise FleetError("campaign time is in the future")
    return value


def _write_private_new(path: Path, content: bytes) -> None:
    """Refuse overwriting existing operator files; never follow a final symlink."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(path), flags, 0o600)
    except OSError as error:
        raise FleetError(f"unable to create private file: {path}") from error
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def create_node_key(path: Path) -> None:
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise FleetError("key directory must already exist and be operator-owned")
    _write_private_new(path, secrets.token_bytes(32))


def read_node_key(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(path), flags)
    except OSError as error:
        raise FleetError(f"node key is missing or inaccessible: {path}") from error
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != 32:
            raise FleetError("node key must be a 32-byte regular file")
        if os.name == "posix":
            if info.st_uid != os.getuid() or (stat.S_IMODE(info.st_mode) & 0o077):
                raise FleetError("node key must be owned by caller and mode 0600")
        return stream.read()


def create_campaign(inventory: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "fleet_id": inventory["fleet_id"],
        "campaign_id": secrets.token_hex(16),
        "created_at": iso(now or utc_now()),
    }


def _canonical(report: dict[str, Any]) -> bytes:
    return json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sign_report(report: dict[str, Any], key: bytes) -> dict[str, Any]:
    if set(report) != REPORT_FIELDS:
        raise FleetError("invalid receipt fields")
    if len(key) != 32:
        raise FleetError("node key must be 32 bytes")
    return {**report, "signature": hmac.new(key, _canonical(report), hashlib.sha256).hexdigest()}


def make_receipt(
    inventory: dict[str, Any], campaign: dict[str, Any], node_id: str, key: bytes,
    *, now: datetime | None = None, stop_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identifier(node_id, "node_id")
    if campaign["fleet_id"] != inventory["fleet_id"]:
        raise FleetError("fleet identifier mismatch")
    if node_id not in {node["id"] for node in inventory["nodes"]}:
        raise FleetError("node is not registered in the operator inventory")
    state = local_stop_status() if stop_state is None else stop_state
    if not state.get("stopped") or state.get("reason") not in CONFIRMED_REASONS:
        raise FleetError("cannot acknowledge STOP: local operator latch is not confirmed")
    stamp = now or utc_now()
    if stamp < parse_time(campaign["created_at"]) - timedelta(seconds=CLOCK_SKEW_SECONDS):
        raise FleetError("receipt time predates campaign")
    report = {
        "schema_version": SCHEMA, "fleet_id": inventory["fleet_id"],
        "campaign_id": campaign["campaign_id"], "node_id": node_id,
        "reported_at": iso(stamp), "state": "stopped", "stop_reason": state["reason"],
        "algorithm": ALG,
    }
    return sign_report(report, key)


def verify_receipt(
    receipt: dict[str, Any], inventory: dict[str, Any], campaign: dict[str, Any],
    node_id: str, key: bytes, *, now: datetime | None = None, max_age: int = 300,
) -> str:
    """Verify evidence only, never assert the remote host is truly controlled."""
    if not isinstance(receipt, dict) or set(receipt) != REPORT_FIELDS | {"signature"}:
        return "invalid_receipt"
    signature = receipt.get("signature")
    if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
        return "invalid_signature"
    signed = {name: receipt[name] for name in REPORT_FIELDS}
    if not hmac.compare_digest(hmac.new(key, _canonical(signed), hashlib.sha256).hexdigest(), signature):
        return "invalid_signature"
    if (receipt.get("schema_version") != SCHEMA or receipt.get("algorithm") != ALG
            or receipt.get("fleet_id") != inventory["fleet_id"]
            or receipt.get("campaign_id") != campaign["campaign_id"]
            or receipt.get("node_id") != node_id):
        return "wrong_campaign_or_node"
    if receipt.get("state") != "stopped" or receipt.get("stop_reason") not in CONFIRMED_REASONS:
        return "not_confirmed_stopped"
    try:
        at = parse_time(receipt["reported_at"])
        created_at = parse_time(campaign["created_at"])
    except FleetError:
        return "invalid_timestamp"
    current = now or utc_now()
    if at < created_at - timedelta(seconds=CLOCK_SKEW_SECONDS):
        return "predates_campaign"
    if at > current + timedelta(seconds=CLOCK_SKEW_SECONDS):
        return "future_receipt"
    if (current - at).total_seconds() > max_age:
        return "stale_receipt"
    return "confirmed_stopped_receipt"


def audit_fleet(
    inventory: dict[str, Any], campaign: dict[str, Any], receipt_dir: Path, key_dir: Path,
    *, now: datetime | None = None, max_age: int = 300,
) -> dict[str, Any]:
    if not 1 <= max_age <= 3600:
        raise FleetError("maximum age must be 1-3600 seconds")
    if inventory["fleet_id"] != campaign["fleet_id"]:
        raise FleetError("inventory and campaign belong to different fleets")
    if not receipt_dir.is_dir() or receipt_dir.is_symlink():
        raise FleetError("receipt directory does not exist or is unsafe")
    if not key_dir.is_dir() or key_dir.is_symlink():
        raise FleetError("verification key directory does not exist or is unsafe")
    nodes: list[dict[str, str]] = []
    known = {node["id"] for node in inventory["nodes"]}
    for node in inventory["nodes"]:
        node_id = node["id"]
        rp = receipt_dir / (node_id + ".json")
        kp = key_dir / (node_id + ".key")
        if not rp.exists() and not rp.is_symlink():
            outcome = "missing_receipt"
        else:
            try:
                received = _json_file(rp)
                key = read_node_key(kp)
                outcome = verify_receipt(received, inventory, campaign, node_id, key, now=now, max_age=max_age)
            except FleetError:
                outcome = "invalid_or_unverifiable_receipt"
        nodes.append({"id": node_id, "label": node["label"], "result": outcome})
    extras = sorted(p.name for p in receipt_dir.glob("*.json") if p.stem not in known)
    confirmed = sum(node["result"] == "confirmed_stopped_receipt" for node in nodes)
    return {
        "schema_version": SCHEMA,
        "fleet_id": inventory["fleet_id"], "campaign_id": campaign["campaign_id"],
        "reported_at": iso(now or utc_now()),
        "expected_nodes": len(nodes), "confirmed_receipts": confirmed,
        "coverage_complete": confirmed == len(nodes) and not extras,
        "nodes": nodes, "unregistered_receipts": extras,
        "interpretation": "signed recent reports, not proof of physical or external AI shutdown",
    }


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """Refresh one explicit node receipt atomically; reject symlink destinations."""
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        raise FleetError("receipt output directory must exist and not be a symlink")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise FleetError("unsafe receipt output path")
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=parent, prefix=".kraken-ack-", delete=False) as stream:
            temp_name = stream.name
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline, human-operated STOP THE KRAKEN fleet evidence")
    commands = parser.add_subparsers(dest="action", required=True)
    keygen = commands.add_parser("keygen", help="Create one local private 32-byte node key")
    keygen.add_argument("--output", type=Path, required=True)
    campaign_cmd = commands.add_parser("campaign", help="Create a new audit identifier; DOES NOT STOP AI")
    campaign_cmd.add_argument("--inventory", type=Path, required=True)
    campaign_cmd.add_argument("--output", type=Path, required=True)
    ack = commands.add_parser("ack", help="Sign one local stopped-state receipt (no network)")
    ack.add_argument("--inventory", type=Path, required=True)
    ack.add_argument("--campaign", type=Path, required=True)
    ack.add_argument("--node", required=True)
    ack.add_argument("--key", type=Path, required=True)
    ack.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify", help="Verify all expected receipts; fail closed for missing/stale")
    verify.add_argument("--inventory", type=Path, required=True)
    verify.add_argument("--campaign", type=Path, required=True)
    verify.add_argument("--receipts", type=Path, required=True)
    verify.add_argument("--keys", type=Path, required=True)
    verify.add_argument("--max-age", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        if args.action == "keygen":
            create_node_key(args.output)
            print(json.dumps({"key_created": str(args.output), "private": True}))
            return 0
        inventory = load_inventory(args.inventory)
        if args.action == "campaign":
            doc = create_campaign(inventory)
            _write_private_new(args.output, (json.dumps(doc, sort_keys=True, indent=2) + "\n").encode())
            print(json.dumps({"campaign_id": doc["campaign_id"], "output": str(args.output), "ai_stopped": False}))
            return 0
        campaign = load_campaign(args.campaign)
        if args.action == "ack":
            receipt = make_receipt(inventory, campaign, args.node, read_node_key(args.key))
            _write_receipt(args.output, receipt)
            print(json.dumps({"node_id": args.node, "receipt_written": str(args.output), "local_stop_confirmed": True}))
            return 0
        report = audit_fleet(inventory, campaign, args.receipts, args.keys, max_age=args.max_age)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["coverage_complete"] else 3
    except FleetError as error:
        print(json.dumps({"error": str(error), "coverage_complete": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
