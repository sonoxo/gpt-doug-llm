#!/usr/bin/env python3
"""Sonoxo revenue billing: local invoices and manually verified Cash App receipts.

This module does not access Cash App, initiate transfers, or verify deposits.
A payer must authorize their own payment. Receipts require operator verification.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote

CASH_TAG = "$Sonoxo"
CASH_APP_URL = "https://cash.app/$Sonoxo"
DEFAULT_DB = Path(os.environ.get("SONOXO_BILLING_DB", "workers/live/sonoxo-billing.sqlite3"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def amount_to_cents(raw: str) -> int:
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    if not number.is_finite() or number <= 0 or number.as_tuple().exponent < -2:
        raise ValueError("Amount must be positive dollars with at most two decimal places")
    cents = int(number * 100)
    if cents > 100_000_000:
        raise ValueError("Amount exceeds configured limit")
    return cents


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS invoices (
        invoice_id TEXT PRIMARY KEY,
        client TEXT NOT NULL,
        description TEXT NOT NULL,
        amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','void')),
        payment_tag TEXT NOT NULL,
        created_at TEXT NOT NULL,
        paid_at TEXT,
        verified_reference TEXT UNIQUE
    )""")
    db.commit()
    return db


def issue(db: sqlite3.Connection, client: str, description: str, amount: str) -> dict:
    client, description = client.strip(), description.strip()
    if not client or not description or len(client) > 200 or len(description) > 1000:
        raise ValueError("Client and description are required and length-limited")
    invoice_id = "SX-" + uuid.uuid4().hex[:12].upper()
    cents = amount_to_cents(amount)
    db.execute("INSERT INTO invoices (invoice_id, client, description, amount_cents, payment_tag, created_at) VALUES (?,?,?,?,?,?)",
               (invoice_id, client, description, cents, CASH_TAG, utc_now()))
    db.commit()
    return invoice(db, invoice_id)


def invoice(db: sqlite3.Connection, invoice_id: str) -> dict:
    row = db.execute("SELECT * FROM invoices WHERE invoice_id=?", (invoice_id,)).fetchone()
    if row is None:
        raise ValueError("Invoice not found")
    data = dict(row)
    data["amount_usd"] = format(Decimal(data.pop("amount_cents")) / 100, ".2f")
    data["payment_url"] = CASH_APP_URL
    data["payment_instructions"] = (
        f"Pay {CASH_TAG} via Cash App for invoice {invoice_id}. "
        "Confirm the recipient in Cash App before authorizing payment. "
        "Include the invoice ID in the note if available. "
        "Payment remains pending until independently verified by the seller."
    )
    return data


def verify_receipt(db: sqlite3.Connection, invoice_id: str, reference: str, confirmed: bool) -> dict:
    if not confirmed:
        raise ValueError("Explicit manual verification flag required")
    reference = reference.strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{6,128}", reference):
        raise ValueError("Reference must be a verified transaction identifier (6-128 safe characters)")
    current = invoice(db, invoice_id)
    if current["status"] != "pending":
        raise ValueError("Only pending invoices can be marked paid")
    try:
        db.execute("UPDATE invoices SET status='paid', paid_at=?, verified_reference=? WHERE invoice_id=? AND status='pending'",
                   (utc_now(), reference, invoice_id))
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("Receipt reference already used") from exc
    return invoice(db, invoice_id)


def report(db: sqlite3.Connection) -> dict:
    rows = db.execute("SELECT status, COUNT(*) AS count, COALESCE(SUM(amount_cents),0) AS cents FROM invoices GROUP BY status").fetchall()
    return {row["status"]: {"invoices": row["count"], "amount_usd": format(Decimal(row["cents"])/100, ".2f")} for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Invoice and track manually verified payments to $Sonoxo.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    commands = parser.add_subparsers(dest="action", required=True)
    new = commands.add_parser("issue")
    new.add_argument("--client", required=True)
    new.add_argument("--description", required=True)
    new.add_argument("--amount", required=True, help="USD e.g. 499.00")
    show = commands.add_parser("show")
    show.add_argument("invoice_id")
    paid = commands.add_parser("verify-paid")
    paid.add_argument("invoice_id")
    paid.add_argument("--reference", required=True, help="Independently checked transaction reference")
    paid.add_argument("--confirmed-in-cashapp", action="store_true")
    commands.add_parser("report")
    args = parser.parse_args()
    try:
        with connect(args.db) as db:
            if args.action == "issue":
                result = issue(db, args.client, args.description, args.amount)
            elif args.action == "show":
                result = invoice(db, args.invoice_id)
            elif args.action == "verify-paid":
                result = verify_receipt(db, args.invoice_id, args.reference, args.confirmed_in_cashapp)
            else:
                result = report(db)
        print(json.dumps(result, indent=2))
        return 0
    except ValueError as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
