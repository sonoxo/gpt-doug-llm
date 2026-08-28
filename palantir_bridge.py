"""GPT-DOUG-LLM bridge to an authorized Palantir Foundry instance."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, List, Optional

from doug_core.runtime import DougRuntime
from palantir_foundry import FoundryClient, FoundryConfigurationError, FoundryError


@dataclass
class DougPalantirBridge:
    foundry: FoundryClient
    doug: DougRuntime

    @classmethod
    def from_environment(cls) -> Optional["DougPalantirBridge"]:
        client = FoundryClient.from_environment()
        if client is None:
            return None
        return cls(foundry=client, doug=DougRuntime())

    def status(self) -> dict[str, Any]:
        return {
            "bridge": "gpt-doug-llm -> palantir-foundry",
            "foundry": self.foundry.status(),
        }

    def ontology_context(
        self,
        ontology: str,
        object_type: str,
        *,
        page_size: int = 25,
    ) -> dict[str, Any]:
        payload = self.foundry.list_objects(ontology, object_type, page_size=page_size)
        values = payload.get("data")
        if values is None:
            values = payload.get("values")
        if values is None:
            values = payload.get("objects")
        if not isinstance(values, list):
            values = []
        return {
            "source": "palantir-foundry",
            "ontology": ontology,
            "object_type": object_type,
            "objects": values,
            "next_page_token": payload.get("nextPageToken"),
        }

    def ground_prompt(
        self,
        prompt: str,
        ontology: str,
        object_type: str,
        *,
        page_size: int = 25,
    ) -> str:
        context = self.ontology_context(ontology, object_type, page_size=page_size)
        return (
            "Use the following authorized Palantir Foundry data as grounding context. "
            "Do not invent fields that are not present.\n\n"
            f"FOUNDRY_CONTEXT={json.dumps(context, separators=(',', ':'), default=str)}\n\n"
            f"USER_REQUEST={prompt}"
        )

    def doug_analysis(
        self,
        prompt: str,
        ontology: str,
        object_type: str,
        *,
        page_size: int = 25,
    ) -> dict[str, Any]:
        grounded = self.ground_prompt(prompt, ontology, object_type, page_size=page_size)
        result = self.doug.analyze(grounded)
        return {
            "grounded": True,
            "ontology": ontology,
            "object_type": object_type,
            "analysis": result,
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPT-DOUG to Palantir Foundry bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("ontologies")

    object_types = sub.add_parser("object-types")
    object_types.add_argument("ontology")

    objects = sub.add_parser("objects")
    objects.add_argument("ontology")
    objects.add_argument("object_type")
    objects.add_argument("--limit", type=int, default=25)

    get_object = sub.add_parser("get")
    get_object.add_argument("ontology")
    get_object.add_argument("object_type")
    get_object.add_argument("primary_key")

    analyze = sub.add_parser("analyze")
    analyze.add_argument("ontology")
    analyze.add_argument("object_type")
    analyze.add_argument("prompt")
    analyze.add_argument("--limit", type=int, default=25)

    action = sub.add_parser("action")
    action.add_argument("ontology")
    action.add_argument("action")
    action.add_argument("parameters_json")
    action.add_argument("--approve", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        bridge = DougPalantirBridge.from_environment()
        if bridge is None:
            raise FoundryConfigurationError("Palantir Foundry is not configured")

        if args.command == "status":
            payload = bridge.status()
        elif args.command == "ontologies":
            payload = bridge.foundry.list_ontologies()
        elif args.command == "object-types":
            payload = bridge.foundry.list_object_types(args.ontology)
        elif args.command == "objects":
            payload = bridge.foundry.list_objects(args.ontology, args.object_type, page_size=args.limit)
        elif args.command == "get":
            payload = bridge.foundry.get_object(args.ontology, args.object_type, args.primary_key)
        elif args.command == "analyze":
            payload = bridge.doug_analysis(
                args.prompt,
                args.ontology,
                args.object_type,
                page_size=args.limit,
            )
        elif args.command == "action":
            if not args.approve:
                raise FoundryError("Foundry actions require --approve in addition to FOUNDRY_ENABLE_WRITES=true")
            parameters = json.loads(args.parameters_json)
            if not isinstance(parameters, dict):
                raise FoundryError("Action parameters must be a JSON object")
            payload = bridge.foundry.apply_action(args.ontology, args.action, parameters)
        else:
            raise FoundryError("Unknown command")

        print(json.dumps(payload, indent=2, default=str))
        return 0
    except (FoundryError, ValueError) as error:
        print(f"PALANTIR ERROR // {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
