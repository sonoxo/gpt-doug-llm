"""Local resolver for XUNI/Xbox GDK documentation.

The resolver never bypasses Microsoft authorization. It indexes approved Microsoft Learn
URLs and marks topics that require licensed/authorized access so developers know which
items must be opened on an approved GDK workstation/account.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REGISTRY = Path(__file__).parent / "knowledge" / "xbox_gdk_sources.json"


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def search_sources(query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return []
    registry = load_registry()
    ranked: list[tuple[int, dict[str, Any]]] = []
    for source in registry["sources"]:
        haystack = " ".join([source["id"], source["title"], *source.get("topics", [])]).lower()
        score = sum(1 for token in q.split() if token in haystack)
        if score:
            ranked.append((score, source))
    return [source for _, source in sorted(ranked, key=lambda item: (-item[0], item[1]["title"]))]


def resolve(query: str) -> dict[str, Any]:
    matches = search_sources(query)
    return {
        "query": query,
        "authority": "Microsoft Learn",
        "matches": matches,
        "licensedAccessRequired": [
            item for item in matches if item.get("access") == "authorization-may-be-required"
        ],
        "policy": {
            "publicOnly": True,
            "authorizationBypass": False,
            "restrictedDocsRemainOnLicensedWorkstation": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve Xbox GDK documentation for XUNI")
    parser.add_argument("query", nargs="+", help="Topic to resolve, e.g. XTaskQueue or packaging")
    args = parser.parse_args()
    print(json.dumps(resolve(" ".join(args.query)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
