#!/usr/bin/env python3
"""Generate machine-readable Zyra security-review evidence."""

import json
import os
import base64
from pathlib import Path

from secret_store import SecretStore
from zyra import Zyra


def main() -> int:
    account = os.getenv("GPT_DOUG_VERIFIED_BUSINESS_EMAIL", "").strip()
    if not account:
        raise SystemExit("security review requires GPT_DOUG_VERIFIED_BUSINESS_EMAIL")
    raw_key = SecretStore.get("audit_hmac", account)
    key = base64.b64decode(raw_key, validate=True)
    watchdog = Zyra(Path.home() / ".gpt-doug" / "zyra-audit.jsonl", audit_key=key)
    report = watchdog.review_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    healthy = report["audit_hmac_enabled"] and report["audit_owner_only"] and report["sink_failures"] == 0
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
