from __future__ import annotations

import argparse
import json
import os

from .capabilities import CAPABILITY_CATALOG, PROFILES
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

    caps = sub.add_parser("capabilities", help="show supported capabilities and active profile")
    caps.add_argument("--json", action="store_true", help="emit JSON")

    sub.add_parser("status", help="show configured service and swarm capacity")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = SwarmConfig()
    policy = CapabilityPolicy.from_env()

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
