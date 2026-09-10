#!/usr/bin/env python3
"""Governed Palantir Maven configuration and readiness checks.

This adapter does not create Palantir access or credentials. It consumes the
Maven repository URL and short-lived/publisher credentials generated inside an
authorized Foundry Artifact Repository, validates the local configuration, and
can emit a Maven settings.xml fragment without persisting secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape


class PalantirMavenError(RuntimeError):
    pass


@dataclass(frozen=True)
class PalantirMavenConfig:
    repository_url: str
    repository_id: str = "palantir-foundry"
    username: str = ""
    token: str = ""
    allowed_host: str = ""
    timeout: float = 10.0

    @classmethod
    def from_environment(cls) -> "PalantirMavenConfig":
        url = os.getenv("PALANTIR_MAVEN_REPOSITORY_URL", "").strip()
        repo_id = os.getenv("PALANTIR_MAVEN_REPOSITORY_ID", "palantir-foundry").strip()
        username = os.getenv("PALANTIR_MAVEN_USERNAME", "").strip()
        token = os.getenv("PALANTIR_MAVEN_TOKEN", "").strip()
        allowed_host = os.getenv("PALANTIR_MAVEN_ALLOWED_HOST", "").strip().lower()
        try:
            timeout = max(1.0, float(os.getenv("PALANTIR_MAVEN_TIMEOUT_SECONDS", "10")))
        except ValueError as exc:
            raise PalantirMavenError("PALANTIR_MAVEN_TIMEOUT_SECONDS must be numeric") from exc
        return cls(url, repo_id, username, token, allowed_host, timeout)

    def validate(self, *, require_credentials: bool = False) -> dict[str, Any]:
        if not self.repository_url:
            raise PalantirMavenError("PALANTIR_MAVEN_REPOSITORY_URL is not configured")
        parsed = urllib.parse.urlparse(self.repository_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise PalantirMavenError("Palantir Maven repository URL must use HTTPS")
        if parsed.username or parsed.password or parsed.fragment:
            raise PalantirMavenError("Repository URL must not embed credentials or a fragment")
        if self.allowed_host and parsed.hostname.lower() != self.allowed_host:
            raise PalantirMavenError("Repository URL host does not match PALANTIR_MAVEN_ALLOWED_HOST")
        if not self.repository_id:
            raise PalantirMavenError("PALANTIR_MAVEN_REPOSITORY_ID must not be empty")
        if require_credentials and not self.token:
            raise PalantirMavenError("PALANTIR_MAVEN_TOKEN is required for authenticated publishing")
        return {
            "configured": True,
            "repository_id": self.repository_id,
            "host": parsed.hostname.lower(),
            "https": True,
            "credentials_present": bool(self.token),
            "username_present": bool(self.username),
        }

    def settings_xml(self) -> str:
        self.validate(require_credentials=True)
        server_id = escape(self.repository_id)
        user = escape(self.username)
        token = escape(self.token)
        return (
            "<settings>\n"
            "  <servers>\n"
            "    <server>\n"
            f"      <id>{server_id}</id>\n"
            f"      <username>{user}</username>\n"
            f"      <password>{token}</password>\n"
            "    </server>\n"
            "  </servers>\n"
            "</settings>\n"
        )

    def probe(self) -> dict[str, Any]:
        status = self.validate(require_credentials=False)
        headers = {"Accept": "*/*", "User-Agent": "gpt-doug-palantir-maven/1"}
        if self.token:
            import base64
            raw = f"{self.username}:{self.token}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
        request = urllib.request.Request(self.repository_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                code = int(getattr(response, "status", 0))
                status.update({"reachable": 200 <= code < 500, "http_status": code})
        except Exception as exc:
            status.update({"reachable": False, "error": type(exc).__name__})
        return status


def main() -> int:
    parser = argparse.ArgumentParser(prog="palantir-maven")
    parser.add_argument("command", choices=("status", "probe", "settings"), nargs="?", default="status")
    args = parser.parse_args()
    try:
        config = PalantirMavenConfig.from_environment()
        if args.command == "status":
            payload = config.validate(require_credentials=False)
            print(json.dumps(payload, indent=2, sort_keys=True))
        elif args.command == "probe":
            payload = config.probe()
            print(json.dumps(payload, indent=2, sort_keys=True))
            if not payload.get("reachable"):
                return 1
        else:
            print(config.settings_xml(), end="")
        return 0
    except PalantirMavenError as exc:
        print(json.dumps({"configured": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
