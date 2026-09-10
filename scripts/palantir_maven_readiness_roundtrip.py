#!/usr/bin/env python3
"""Publish and retrieve a harmless Maven readiness artifact.

This verifier exercises only the configured Palantir Foundry Maven artifact
repository. It creates a tiny inert JAR containing metadata text, publishes the
POM + JAR under a unique version, downloads both back, and verifies SHA-256
identity. It executes no code from the artifact and never prints credentials.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Any

GROUP_ID = "com.xunia"
ARTIFACT_ID = "defense-readiness-test"


def fail(message: str, *, code: int = 2) -> int:
    print(json.dumps({"ok": False, "error": message}, indent=2), file=sys.stderr)
    return code


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_jar(version: str) -> bytes:
    payload = {
        "artifact": f"{GROUP_ID}:{ARTIFACT_ID}:{version}",
        "purpose": "harmless Palantir Maven readiness verification",
        "executable": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as jar:
        jar.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nCreated-By: GPT-DOUG readiness verifier\n\n")
        jar.writestr("readiness.json", json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out.getvalue()


def build_pom(version: str) -> bytes:
    xml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project xmlns=\"http://maven.apache.org/POM/4.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd\">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{GROUP_ID}</groupId>
  <artifactId>{ARTIFACT_ID}</artifactId>
  <version>{version}</version>
  <packaging>jar</packaging>
  <name>XUNIA Defense Readiness Test</name>
  <description>Inert artifact used only to verify Palantir Maven publish/retrieve integrity.</description>
</project>
"""
    return xml.encode("utf-8")


def auth_header(username: str, token: str) -> str:
    raw = f"{username}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def request(url: str, *, method: str, auth: str, body: bytes | None = None, content_type: str = "application/octet-stream") -> tuple[int, bytes]:
    headers = {
        "Authorization": auth,
        "Accept": "*/*",
        "User-Agent": "gpt-doug-palantir-maven-readiness/1",
    }
    if body is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(512).decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {method} {urllib.parse.urlparse(url).path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error for {method} {urllib.parse.urlparse(url).path}: {exc.reason}") from exc


def main() -> int:
    base_url = os.getenv("PALANTIR_MAVEN_REPOSITORY_URL", "").strip().rstrip("/")
    token = os.getenv("PALANTIR_MAVEN_TOKEN", "").strip()
    username = os.getenv("PALANTIR_MAVEN_USERNAME", "")
    allowed_host = os.getenv("PALANTIR_MAVEN_ALLOWED_HOST", "").strip().lower()

    if not base_url:
        return fail("PALANTIR_MAVEN_REPOSITORY_URL is not set")
    if not token:
        return fail("PALANTIR_MAVEN_TOKEN is not set")

    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return fail("repository URL must be HTTPS")
    if allowed_host and parsed.hostname.lower() != allowed_host:
        return fail("repository host does not match PALANTIR_MAVEN_ALLOWED_HOST")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    version = os.getenv("PALANTIR_MAVEN_READINESS_VERSION", f"0.1.0-readiness-{stamp}").strip()
    group_path = GROUP_ID.replace(".", "/")
    prefix = f"{base_url}/{group_path}/{ARTIFACT_ID}/{version}"
    jar_name = f"{ARTIFACT_ID}-{version}.jar"
    pom_name = f"{ARTIFACT_ID}-{version}.pom"
    jar_url = f"{prefix}/{jar_name}"
    pom_url = f"{prefix}/{pom_name}"

    jar = build_jar(version)
    pom = build_pom(version)
    auth = auth_header(username, token)

    try:
        pom_put, _ = request(pom_url, method="PUT", auth=auth, body=pom, content_type="application/xml")
        jar_put, _ = request(jar_url, method="PUT", auth=auth, body=jar, content_type="application/java-archive")
        pom_get, pom_back = request(pom_url, method="GET", auth=auth)
        jar_get, jar_back = request(jar_url, method="GET", auth=auth)
    except RuntimeError as exc:
        return fail(str(exc), code=1)

    jar_sha = sha256(jar)
    pom_sha = sha256(pom)
    jar_match = jar_back == jar and sha256(jar_back) == jar_sha
    pom_match = pom_back == pom and sha256(pom_back) == pom_sha
    ok = all((200 <= pom_put < 300, 200 <= jar_put < 300, 200 <= pom_get < 300, 200 <= jar_get < 300, jar_match, pom_match))

    result: dict[str, Any] = {
        "schema": "xunia.palantir-maven-readiness.v1",
        "ok": ok,
        "coordinates": f"{GROUP_ID}:{ARTIFACT_ID}:{version}",
        "host": parsed.hostname.lower(),
        "publish": {"pom_status": pom_put, "jar_status": jar_put},
        "retrieve": {"pom_status": pom_get, "jar_status": jar_get},
        "integrity": {
            "pom_sha256": pom_sha,
            "jar_sha256": jar_sha,
            "pom_match": pom_match,
            "jar_match": jar_match,
        },
        "artifact_executed": False,
        "credentials_printed": False,
        "defense_ready": ok,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
