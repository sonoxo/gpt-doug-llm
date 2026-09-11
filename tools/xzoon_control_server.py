#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = pathlib.Path.home() / ".config/gpt-doug"


def read_json(path):
    return json.loads(
        pathlib.Path(path).read_text()
    )


def validate_graph(path):
    graph = read_json(path)

    nodes = graph.get("nodes", [])
    links = graph.get("links", [])

    ids = [
        n.get("id")
        for n in nodes
    ]

    if None in ids:
        raise ValueError(
            "node without id"
        )

    if len(ids) != len(set(ids)):
        raise ValueError(
            "duplicate node ids"
        )

    idset = set(ids)
    dangling = []

    for edge in links:
        if len(edge) != 3:
            dangling.append(edge)
            continue

        if (
            edge[0] not in idset
            or edge[1] not in idset
        ):
            dangling.append(edge)

    if dangling:
        raise ValueError(
            f"{len(dangling)} dangling or malformed links"
        )

    return {
        "ok": True,
        "nodes": len(nodes),
        "links": len(links),
        "verified": sum(
            1
            for n in nodes
            if n.get("status") == "verified"
        ),
    }


def validate_https_host(host):
    """Return a safe HTTPS network location for operator config."""

    candidate = str(host).strip()

    if (
        not candidate
        or "://" in candidate
        or any(
            character in candidate
            for character in "/?#@\\"
        )
        or any(
            character.isspace()
            for character in candidate
        )
    ):
        raise ValueError(
            "invalid Foundry host"
        )

    parsed = urllib.parse.urlsplit(
        "https://" + candidate
    )

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(
            "invalid Foundry port"
        ) from exc

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or port not in (None, 443)
    ):
        raise ValueError(
            "Foundry endpoint must be HTTPS"
        )

    return parsed.netloc


class Handler(SimpleHTTPRequestHandler):
    server_version = "xZOON-Control/1.0"

    def api_json(
        self,
        code,
        payload,
    ):
        body = json.dumps(
            payload,
            indent=2,
        ).encode()

        self.send_response(code)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def body_json(self):
        size = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        if size > 1024 * 128:
            raise ValueError(
                "request too large"
            )

        data = self.rfile.read(size)

        if not data:
            return {}

        return json.loads(data)

    def do_GET(self):
        path = urllib.parse.urlparse(
            self.path
        ).path

        if path == "/xzoon-api/health":
            self.api_json(
                200,
                {
                    "ok": True,
                    "mode": "governed-local-control",
                    "aipConfigured": all([
                        os.getenv("FOUNDRY_HOST"),
                        os.getenv("FOUNDRY_TOKEN"),
                        os.getenv(
                            "XZOON_FOUNDRY_ONTOLOGY"
                        ),
                        os.getenv(
                            "XZOON_AIP_QUERY_API_NAME"
                        ),
                    ]),
                    "remoteActionsEnabled": False,
                },
            )
            return

        super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(
            self.path
        ).path

        try:
            body = self.body_json()

            if path == "/xzoon-api/action":
                self.handle_action(body)
                return

            if path == "/xzoon-api/aip-query":
                self.handle_aip(body)
                return

            self.api_json(
                404,
                {
                    "ok": False,
                    "error": "unknown endpoint",
                },
            )

        except Exception as exc:
            self.api_json(
                500,
                {
                    "ok": False,
                    "error": str(exc),
                },
            )

    def graph_path(self):
        return (
            pathlib.Path(
                self.server.site
            )
            / "maven-ontology"
            / "ontology.json"
        )

    def handle_action(self, body):
        if body.get("approved") is not True:
            self.api_json(
                403,
                {
                    "ok": False,
                    "error": "human approval required",
                },
            )
            return

        action = body.get("action")
        node_id = body.get("nodeId")

        if action == "validate_graph":
            result = validate_graph(
                self.graph_path()
            )

            self.api_json(
                200,
                result,
            )
            return

        if action == "reverify_object":
            graph = read_json(
                self.graph_path()
            )

            node = next(
                (
                    n
                    for n in graph.get(
                        "nodes",
                        [],
                    )
                    if n.get("id")
                    == node_id
                ),
                None,
            )

            if not node:
                raise ValueError(
                    "object not found"
                )

            edges = [
                e
                for e in graph.get(
                    "links",
                    [],
                )
                if (
                    e[0] == node_id
                    or e[1] == node_id
                )
            ]

            self.api_json(
                200,
                {
                    "ok": True,
                    "nodeId": node_id,
                    "status": node.get(
                        "status"
                    ),
                    "confidence": node.get(
                        "confidence"
                    ),
                    "provenancePresent": bool(
                        node.get(
                            "provenance"
                        )
                    ),
                    "relationships": len(
                        edges
                    ),
                    "note": (
                        "Local graph/provenance re-check only; "
                        "no remote system was mutated."
                    ),
                },
            )
            return

        if action == "sync_verified_maven_proof":
            script = (
                ROOT
                / "scripts"
                / "xzoon-sync-from-maven-proof"
            )

            if not script.exists():
                raise ValueError(
                    "Maven proof sync script missing"
                )

            p = subprocess.run(
                [str(script)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=60,
            )

            if p.returncode != 0:
                raise RuntimeError(
                    p.stderr[-3000:]
                    or p.stdout[-3000:]
                )

            src = (
                ROOT
                / "docs"
                / "maven-ontology"
                / "ontology.json"
            )

            dst = self.graph_path()

            shutil.copy2(
                src,
                dst,
            )

            self.api_json(
                200,
                {
                    "ok": True,
                    "stdout": p.stdout[-3000:],
                    "note": (
                        "Latest already-verified Maven proof "
                        "was projected into the local graph."
                    ),
                },
            )
            return

        if action == "repo_checks":
            checks = []

            for command in (
                ["git", "diff", "--check"],
                ["git", "status", "--short"],
            ):
                p = subprocess.run(
                    command,
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    timeout=60,
                )

                checks.append({
                    "command": " ".join(
                        command
                    ),
                    "returncode": p.returncode,
                    "stdout": p.stdout[-4000:],
                    "stderr": p.stderr[-4000:],
                })

            self.api_json(
                200,
                {
                    "ok": all(
                        x["returncode"] == 0
                        for x in checks
                    ),
                    "checks": checks,
                },
            )
            return

        if action == "queue_agent_task":
            task = str(
                body.get(
                    "task",
                    "",
                )
            ).strip()

            if not task:
                raise ValueError(
                    "task required"
                )

            if len(task) > 1000:
                raise ValueError(
                    "task too long"
                )

            queue = (
                STATE
                / "xzoon-action-queue"
            )

            queue.mkdir(
                parents=True,
                exist_ok=True,
            )

            item = {
                "schema": (
                    "xunia.xzoon."
                    "governed-action-request.v1"
                ),
                "id": str(
                    uuid.uuid4()
                ),
                "createdAt": dt.datetime.now(
                    dt.timezone.utc
                ).isoformat(),
                "nodeId": node_id,
                "task": task,
                "approvedByHuman": True,
                "executed": False,
            }

            output = (
                queue
                / (
                    item["createdAt"]
                    .replace(":", "-")
                    + "-"
                    + item["id"]
                    + ".json"
                )
            )

            output.write_text(
                json.dumps(
                    item,
                    indent=2,
                ) + "\n"
            )

            output.chmod(0o600)

            self.api_json(
                200,
                {
                    "ok": True,
                    "queued": True,
                    "executed": False,
                    "requestId": item["id"],
                    "note": (
                        "Task queued for governed review; "
                        "no autonomous execution occurred."
                    ),
                },
            )
            return

        self.api_json(
            400,
            {
                "ok": False,
                "error": "action not allowlisted",
            },
        )

    def handle_aip(self, body):
        query = str(
            body.get(
                "query",
                "",
            )
        ).strip()

        if not query:
            raise ValueError(
                "query required"
            )

        host = os.getenv(
            "FOUNDRY_HOST",
            "",
        ).strip()

        token = os.getenv(
            "FOUNDRY_TOKEN",
            "",
        ).strip()

        ontology = os.getenv(
            "XZOON_FOUNDRY_ONTOLOGY",
            "",
        ).strip()

        query_api = os.getenv(
            "XZOON_AIP_QUERY_API_NAME",
            "",
        ).strip()

        param = os.getenv(
            "XZOON_AIP_QUERY_PARAM",
            "query",
        ).strip()

        branch = os.getenv(
            "XZOON_FOUNDRY_BRANCH",
            "",
        ).strip()

        scenario = os.getenv(
            "XZOON_SCENARIO_RID",
            "",
        ).strip()

        if not all([
            host,
            token,
            ontology,
            query_api,
        ]):
            self.api_json(
                409,
                {
                    "ok": False,
                    "configured": False,
                    "error": (
                        "AIP/Foundry Query is not configured. "
                        "Set FOUNDRY_HOST, FOUNDRY_TOKEN, "
                        "XZOON_FOUNDRY_ONTOLOGY and "
                        "XZOON_AIP_QUERY_API_NAME."
                    ),
                },
            )
            return

        params = {}

        if branch:
            params["branch"] = branch

        if scenario:
            params["scenarioRid"] = (
                scenario
            )

        suffix = (
            "?"
            + urllib.parse.urlencode(
                params
            )
            if params
            else ""
        )

        safe_host = validate_https_host(
            host
        )

        url = (
            "https://"
            + safe_host
            + "/api/v2/ontologies/"
            + urllib.parse.quote(
                ontology,
                safe="",
            )
            + "/queries/"
            + urllib.parse.quote(
                query_api,
                safe="",
            )
            + "/execute"
            + suffix
        )

        payload = json.dumps({
            "parameters": {
                param: query
            }
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": (
                    "Bearer "
                    + token
                ),
                "Content-Type": (
                    "application/json"
                ),
                "Accept": (
                    "application/json"
                ),
                "User-Agent": (
                    "xzoon-aip-query/1"
                ),
            },
        )

        try:
            # B310 is intentionally suppressed only after
            # validate_https_host() guarantees an HTTPS origin.
            with urllib.request.urlopen(  # nosec B310
                req,
                timeout=60,
            ) as response:
                result = json.load(
                    response
                )

        except urllib.error.HTTPError as exc:
            detail = exc.read(
                3000
            ).decode(
                "utf-8",
                errors="replace",
            )

            self.api_json(
                exc.code,
                {
                    "ok": False,
                    "configured": True,
                    "error": detail,
                },
            )
            return

        self.api_json(
            200,
            {
                "ok": True,
                "configured": True,
                "queryApiName": query_api,
                "value": result.get(
                    "value"
                ),
            },
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--site",
        required=True,
    )

    parser.add_argument(
        "--port",
        required=True,
        type=int,
    )

    args = parser.parse_args()

    site = pathlib.Path(
        args.site
    ).resolve()

    def handler(*args, **kwargs):
        return Handler(
            *args,
            directory=str(site),
            **kwargs,
        )

    server = ThreadingHTTPServer(
        (
            "127.0.0.1",
            args.port,
        ),
        handler,
    )

    server.site = str(site)

    print(
        "xZOON CONTROL SERVER",
        f"http://127.0.0.1:{args.port}",
        flush=True,
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
