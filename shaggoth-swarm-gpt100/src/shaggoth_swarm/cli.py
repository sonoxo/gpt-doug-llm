from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .atomic import stack_manifest, validate_stack
from .capabilities import CAPABILITY_CATALOG, PROFILES
from .catalogs.open_source_everything import (
    DEFAULT_CACHE as OSE_DEFAULT_CACHE,
    SOURCE_COMMIT as OSE_SOURCE_COMMIT,
    SOURCE_HOST as OSE_SOURCE_HOST,
    SOURCE_LICENSE as OSE_SOURCE_LICENSE,
    SOURCE_MIRROR as OSE_SOURCE_MIRROR,
    SOURCE_REPOSITORY as OSE_SOURCE_REPOSITORY,
    SOURCE_VERSION as OSE_SOURCE_VERSION,
    load_cache as load_ose_cache,
    refresh_cache as refresh_ose_cache,
    search_index as search_ose_index,
)
from .config import SwarmConfig
from .connectors import AuthorizedConnectorMonitor, ConnectorConfig
from .orchestrator import SwarmOrchestrator
from .policy import CapabilityPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shaggoth", description="Shaggoth Swarm GPT-100")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a bounded swarm job")
    run.add_argument("goal", help="goal for the swarm")
    run.add_argument("--fanout", type=int, default=None, help="number of agents to activate")
    run.add_argument("--json", action="store_true", help="emit JSON")

    connect = sub.add_parser("connect", help="monitor explicitly authorized endpoints")
    connect.add_argument("--once", action="store_true", help="poll each endpoint once and exit")

    layers = sub.add_parser("layers", help="show and validate the atomic layer stack")
    layers.add_argument("--json", action="store_true", help="emit JSON")
    layers.add_argument("--validate", action="store_true", help="exit non-zero if the stack is invalid")

    caps = sub.add_parser("capabilities", help="show supported capabilities and active profile")
    caps.add_argument("--json", action="store_true", help="emit JSON")

    catalog = sub.add_parser("catalog", help="query external open-source catalog sources")
    catalog_sub = catalog.add_subparsers(dest="catalog_command", required=True)

    catalog_source = catalog_sub.add_parser("source", help="show Open Source Everything provenance")
    catalog_source.add_argument("--json", action="store_true", help="emit JSON")

    catalog_refresh = catalog_sub.add_parser("refresh", help="refresh the Open Source Everything index")
    catalog_refresh.add_argument("--cache", default=str(OSE_DEFAULT_CACHE), help="cache JSON path")
    catalog_refresh.add_argument("--timeout", type=float, default=30.0, help="request timeout in seconds")

    catalog_search = catalog_sub.add_parser("search", help="search the Open Source Everything index")
    catalog_search.add_argument("query", help="space-separated search terms")
    catalog_search.add_argument("--cache", default=str(OSE_DEFAULT_CACHE), help="cache JSON path")
    catalog_search.add_argument("--limit", type=int, default=20, help="maximum results, 1-100")
    catalog_search.add_argument("--refresh", action="store_true", help="refresh before searching")
    catalog_search.add_argument("--json", action="store_true", help="emit JSON")

    sub.add_parser("status", help="show configured service and swarm capacity")
    return parser


def _catalog_source_payload() -> dict:
    return {
        "source": "Open Source Everything",
        "repository": OSE_SOURCE_REPOSITORY,
        "canonical_host": OSE_SOURCE_HOST,
        "github_mirror": OSE_SOURCE_MIRROR,
        "commit": OSE_SOURCE_COMMIT,
        "version": OSE_SOURCE_VERSION,
        "license": OSE_SOURCE_LICENSE,
    }


def main() -> int:
    args = build_parser().parse_args()
    config = SwarmConfig()
    policy = CapabilityPolicy.from_env()

    if args.command == "layers":
        manifest = stack_manifest()
        if args.json:
            print(json.dumps(manifest, indent=2))
        else:
            print(
                f"atomic-stack v{manifest['version']} "
                f"layers={manifest['layer_count']} valid={manifest['valid']}"
            )
            for layer in manifest["layers"]:
                deps = ",".join(layer["dependencies"]) or "none"
                print(
                    f"L{layer['id']} {layer['name']} "
                    f"deps={deps} - {layer['purpose']}"
                )
            for error in manifest["errors"]:
                print(f"ERROR {error}")
        if args.validate:
            valid, _ = validate_stack()
            return 0 if valid else 1
        return 0

    if args.command == "catalog":
        if args.catalog_command == "source":
            payload = _catalog_source_payload()
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                for key, value in payload.items():
                    print(f"{key}: {value}")
            return 0

        cache = Path(args.cache)
        if args.catalog_command == "refresh":
            index = refresh_ose_cache(cache, timeout=args.timeout)
            print(
                json.dumps(
                    {
                        "cache": str(cache),
                        "entry_count": index["entry_count"],
                        "source": index["source"],
                    },
                    indent=2,
                )
            )
            return 0

        if args.refresh or not cache.exists():
            index = refresh_ose_cache(cache)
        else:
            index = load_ose_cache(cache)
        results = search_ose_index(index, args.query, limit=args.limit)
        if args.json:
            print(json.dumps({"query": args.query, "results": results}, indent=2))
        else:
            print(f"results={len(results)} source={index['source']['repository']}")
            for entry in results:
                section = entry.get("section", "")
                subsection = entry.get("subsection", "")
                category = f"{section} / {subsection}" if subsection else section
                print(f"- {entry['name']} [{category}] {entry['url']}")
        return 0

    if args.command == "capabilities":
        payload = {
            "active_profile": os.getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning"),
            "enabled_count": len(policy.allowed),
            "supported_count": len(CAPABILITY_CATALOG),
            "profiles": {name: sorted(values) for name, values in PROFILES.items()},
            "capabilities": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "risk": spec.risk.value,
                    "requires_scope": spec.requires_scope,
                    "enabled": spec.name in policy.allowed,
                }
                for spec in CAPABILITY_CATALOG
            ],
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"profile={payload['active_profile']} "
                f"enabled={payload['enabled_count']}/{payload['supported_count']}"
            )
            for spec in payload["capabilities"]:
                marker = "ON " if spec["enabled"] else "OFF"
                scope = " scoped" if spec["requires_scope"] else ""
                print(f"{marker} {spec['name']} [{spec['risk']}]{scope} - {spec['description']}")
        return 0

    if args.command == "status":
        connectors = ConnectorConfig.from_env()
        manifest = stack_manifest()
        print(
            json.dumps(
                {
                    "project": "shaggoth-swarm-gpt100",
                    "service": connectors.service_name,
                    "service_version": connectors.service_version,
                    "agent_capacity": config.agent_count,
                    "max_fanout": config.max_fanout,
                    "max_depth": config.max_depth,
                    "adapter": config.adapter,
                    "capability_profile": os.getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning"),
                    "enabled_capability_count": len(policy.allowed),
                    "authorized_endpoint_count": len(connectors.endpoints),
                    "connector_interval_seconds": connectors.interval_seconds,
                    "connector_max_retries": connectors.max_retries,
                    "connector_auth_configured": bool(connectors.bearer_token),
                    "open_source_everything_cache": str(OSE_DEFAULT_CACHE),
                    "atomic_stack_valid": manifest["valid"],
                    "atomic_layer_count": manifest["layer_count"],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "connect":
        monitor = AuthorizedConnectorMonitor(ConnectorConfig.from_env())
        if args.once:
            print(json.dumps(monitor.poll_once(), indent=2))
            return 0
        try:
            monitor.run_forever()
        except KeyboardInterrupt:
            return 0

    orchestrator = SwarmOrchestrator(config=config, policy=policy)
    report = orchestrator.run(args.goal, fanout=args.fanout)
    print(json.dumps(orchestrator.report_as_dict(report), indent=2) if args.json else report.summary)
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
