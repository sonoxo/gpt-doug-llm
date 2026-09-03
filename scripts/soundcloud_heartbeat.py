#!/usr/bin/env python3
"""SoundCloud creator-session heartbeat for GPT-DOUG-LLM.

This monitor deliberately separates consumer playback reachability from creator
surfaces. Public probes never use private browser cookies. If
SOUNDCLOUD_ACCESS_TOKEN is configured as a GitHub Actions secret, /me is also
checked. The token is never printed.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

TIMEOUT_SECONDS = 20
USER_AGENT = "gpt-doug-llm-soundcloud-heartbeat/1.1"
CREATOR_FAILURE_HINTS = {
    "unauthenticated-session-page",
    "soundcloud-error-page",
}


def classify_body(body: str) -> str:
    text = body.lower()
    if "you are not logged in" in text or "sign in to upload" in text:
        return "unauthenticated-session-page"
    if (
        "sorry! something went wrong" in text
        or "thanks for your patience. try again" in text
        or "something went wrong" in text
    ):
        return "soundcloud-error-page"
    if "javascript is disabled" in text:
        return "javascript-shell"
    return "normal-or-unclassified"


def request(url: str, *, token: str | None = None) -> dict:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    }
    if token:
        headers["Authorization"] = f"OAuth {token}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(131072).decode("utf-8", errors="replace")
            status = int(response.status)
            return {
                "status": status,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "final_url": response.geturl(),
                "reachable": status < 500,
                "body_hint": classify_body(body),
            }
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(131072).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        status = int(exc.code)
        return {
            "status": status,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "final_url": exc.geturl(),
            "reachable": status < 500,
            "body_hint": classify_body(body),
        }
    except Exception as exc:
        return {
            "status": None,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "final_url": url,
            "reachable": False,
            "error": f"{type(exc).__name__}: {exc}",
            "body_hint": "unavailable",
        }


def main() -> int:
    token = os.getenv("SOUNDCLOUD_ACCESS_TOKEN", "").strip()
    report = {
        "service": "soundcloud",
        "observer": "gpt-doug-llm-max-heartbeat",
        "ontology": "foundry/ontology/soundcloud-creator-session-ontology.json",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "probes": {},
    }

    public_targets = {
        "consumer_web": "https://soundcloud.com/",
        "artist_studio": "https://soundcloud.com/artists",
        "upload_surface": "https://soundcloud.com/upload",
        "auth_surface": "https://secure.soundcloud.com/",
        "developers": "https://developers.soundcloud.com/",
    }

    hard_failure = False
    creator_degraded = False

    for name, url in public_targets.items():
        result = request(url)
        report["probes"][name] = result
        if not result.get("reachable", False):
            hard_failure = True
        if name in {"artist_studio", "upload_surface"} and result.get("body_hint") in CREATOR_FAILURE_HINTS:
            creator_degraded = True

    if token:
        auth_result = request("https://api.soundcloud.com/me", token=token)
        auth_result["configured"] = True
        auth_result["valid"] = auth_result.get("status") == 200
        report["probes"]["account_api_auth"] = auth_result
        if not auth_result["valid"]:
            creator_degraded = True
    else:
        report["probes"]["account_api_auth"] = {
            "configured": False,
            "valid": None,
            "note": "Optional account-scoped check. Do not store browser cookies, passwords, or OTPs in GitHub.",
        }

    consumer_ok = report["probes"]["consumer_web"].get("reachable", False)
    if consumer_ok and creator_degraded:
        report["incident_classification"] = "CREATOR_AUTH_SPLIT_BRAIN"
        report["suspected_layer"] = "creator identity/session propagation or creator entitlement"
        hard_failure = True
    elif creator_degraded:
        report["incident_classification"] = "CREATOR_SURFACE_DEGRADED"
        hard_failure = True
    elif hard_failure:
        report["incident_classification"] = "SOUNDCLOUD_SURFACE_OUTAGE"
    else:
        report["incident_classification"] = "NO_DETECTED_PUBLIC_CREATOR_FAILURE"

    report["healthy"] = not hard_failure
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
