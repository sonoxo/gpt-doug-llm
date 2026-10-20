#!/usr/bin/env python3
"""Network smoke verification for official XUNIA Glass Onion sources and Pages.

No secret, personal record, actual account password, or .onion URL is queried.
Writes an explicit JSON PASS/FAIL report with HTTP observations.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CISA = "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"
HIBP = "https://api.pwnedpasswords.com/range/5BAA6"  # SHA-1 prefix for public dummy string "password"
OPENPGP = "https://unpkg.com/openpgp@5.11.3/dist/openpgp.min.js"
SITE = "https://xunia.org/darkweb/"


def fetch(url, timeout=18, limit=2_000_000):
    req = Request(url, headers={"User-Agent": "XUNIA-GlassOnion-Verification/1.0", "Cache-Control": "no-cache"})
    with urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError("HTTP " + str(response.status))
        content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError("Response exceeded verification size limit")
        return content


def main(argv=None):
    args_parser = argparse.ArgumentParser(description=__doc__)
    args_parser.add_argument("--mode", choices=["sources", "site"], required=True)
    args_parser.add_argument("--retries", type=int, default=1)
    args_parser.add_argument("--interval", type=int, default=10)
    args_parser.add_argument("--output", default="glass-onion-network-evidence.json")
    args = args_parser.parse_args(argv)
    checks = [
        ("CISA KEV public JSON", CISA, "cisa"),
        ("HIBP Pwned Passwords public range", HIBP, "hibp"),
        ("Pinned OpenPGP.js distribution", OPENPGP, "pgp")
    ] if args.mode == "sources" else [
        ("XUNIA /darkweb/ document", SITE, "html"),
        ("XUNIA JavaScript controller", SITE + "app.mjs", "js"),
        ("XUNIA catalog module", SITE + "core.mjs", "catalog"),
        ("XUNIA stylesheet", SITE + "styles.css", "css")
    ]
    results = []
    for name, url, kind in checks:
        observation = {"name": name, "url": url, "status": "FAIL", "detail": ""}
        for attempt in range(max(1, min(args.retries, 40))):
            try:
                response = fetch(url)
                if kind == "cisa":
                    data = json.loads(response)
                    count = len(data["vulnerabilities"])
                    if count < 100:
                        raise ValueError("Suspiciously small public KEV catalog")
                    detail = f"{count} vulnerabilities; version {data.get('catalogVersion','unreported')}"
                elif kind == "hibp":
                    if b"1E4C9B93F3F0682250B6CF8331B7EE68FD8:" not in response.upper():
                        raise ValueError("Dummy SHA-1 suffix not found in returned k-anonymity range")
                    detail = "Dummy test-only SHA-1 suffix present; raw password not transmitted"
                elif kind == "pgp":
                    if len(response) < 25_000:
                        raise ValueError("OpenPGP distribution unexpectedly small")
                    detail = f"Obtained pinned distribution, {len(response)} bytes"
                elif kind == "html":
                    if b"XUNIA // GLASS ONION" not in response or b"data-engine=\"pgp\"" not in response:
                        raise ValueError("Live HTML does not contain Glass Onion workbench")
                    detail = f"Published HTML verified, {len(response)} bytes"
                elif kind == "js":
                    if b"parseTelegramArchive" not in response or b"hibpCount" not in response:
                        raise ValueError("Live JavaScript is missing hardened features")
                    detail = f"Published JavaScript verified, {len(response)} bytes"
                elif kind == "catalog":
                    if b"parseTelegramArchive" not in response or b"Have I Been Pwned" not in response:
                        raise ValueError("Live research catalog mismatch")
                    detail = f"Published catalog verified, {len(response)} bytes"
                else:
                    if b".tool-card" not in response:
                        raise ValueError("Expected XUNIA stylesheet rules not found")
                    detail = f"Published stylesheet verified, {len(response)} bytes"
                observation.update({"status": "PASS", "detail": detail, "attempt":attempt+1})
                break
            except (ValueError, KeyError, json.JSONDecodeError, HTTPError, URLError, TimeoutError, OSError) as exc:
                observation["detail"] = str(exc)
                observation["attempt"] = attempt+1
                if attempt+1 < args.retries:
                    time.sleep(max(1, min(args.interval, 30)))
        results.append(observation)
        print(f"{observation['status']}: {name}: {observation['detail']}", flush=True)
    report = {
        "schema": "xunia.glass-onion.verification.v1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "checks": results,
        "result": "PASS" if all(r["status"] == "PASS" for r in results) else "BLOCKED",
    }
    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
    print(f"FINAL={report['result']}", flush=True)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
