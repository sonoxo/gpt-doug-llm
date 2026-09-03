from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_REPOSITORIES = [
    "sonoxo/gpt-doug-llm",
    "sonoxo/xuniadao",
    "sonoxo/zyra",
    "sonoxo/aip-community-registry-zyra",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_json(url: str, token: str = "", timeout: float = 5.0) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "black-house-telemetry/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("GitHub telemetry response was not a JSON object")
    return payload


def _repository_payloads(
    base: str,
    auth: str,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        return (
            _request_json(base, auth, timeout),
            _request_json(f"{base}/actions/runs?per_page=1", auth, timeout),
        )
    except HTTPError as exc:
        if auth and exc.code in {401, 403, 404}:
            return (
                _request_json(base, "", timeout),
                _request_json(f"{base}/actions/runs?per_page=1", "", timeout),
            )
        raise


def _workflow_state(run: dict[str, Any] | None) -> str:
    if run is None:
        return "AMBER"
    status = str(run.get("status") or "").lower()
    conclusion = str(run.get("conclusion") or "").lower()
    if status != "completed":
        return "AMBER"
    if conclusion == "success":
        return "GREEN"
    if conclusion in {"failure", "timed_out", "cancelled", "action_required"}:
        return "RED"
    return "AMBER"


def probe_repository(
    repository: str,
    *,
    token: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    auth = token if token is not None else os.getenv("GITHUB_TOKEN", "")
    base = f"https://api.github.com/repos/{repository}"
    try:
        repo, runs = _repository_payloads(base, auth, timeout)
        workflow_runs = runs.get("workflow_runs", [])
        latest = workflow_runs[0] if workflow_runs else None
        return {
            "repository": repository,
            "reachable": True,
            "state": _workflow_state(latest),
            "defaultBranch": repo.get("default_branch"),
            "pushedAt": repo.get("pushed_at"),
            "archived": bool(repo.get("archived")),
            "visibility": repo.get("visibility") or ("private" if repo.get("private") else "public"),
            "latestWorkflow": (
                {
                    "name": latest.get("name"),
                    "status": latest.get("status"),
                    "conclusion": latest.get("conclusion"),
                    "runNumber": latest.get("run_number"),
                    "headSha": latest.get("head_sha"),
                    "updatedAt": latest.get("updated_at"),
                }
                if latest
                else None
            ),
        }
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        return {
            "repository": repository,
            "reachable": False,
            "state": "RED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def collect_fleet(
    repositories: list[str] | None = None,
    *,
    token: str | None = None,
    live: bool = True,
) -> dict[str, Any]:
    repos = repositories or DEFAULT_REPOSITORIES
    if not live:
        items = [
            {
                "repository": repository,
                "reachable": None,
                "state": "DECLARED",
                "mode": "LIVE_PROBE_DISABLED",
            }
            for repository in repos
        ]
        return {
            "provider": "github",
            "generatedAt": _utc_now(),
            "live": False,
            "overall": "DECLARED",
            "repositories": items,
        }

    items = [probe_repository(repository, token=token) for repository in repos]
    states = {item["state"] for item in items}
    overall = "RED" if "RED" in states else "AMBER" if "AMBER" in states else "GREEN"
    return {
        "provider": "github",
        "generatedAt": _utc_now(),
        "live": True,
        "overall": overall,
        "counts": {
            "repositories": len(items),
            "green": sum(item["state"] == "GREEN" for item in items),
            "amber": sum(item["state"] == "AMBER" for item in items),
            "red": sum(item["state"] == "RED" for item in items),
        },
        "repositories": items,
    }
