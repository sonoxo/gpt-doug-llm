"""Terminal commands that expose the GPT-DOUG <-> Palantir platform bridge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Optional

from federal_compliance import FederalComplianceProfile
from palantir_aip import PalantirAIPClient
from palantir_bridge import DougPalantirBridge
from palantir_foundry import FoundryError
from palantir_stack import PalantirStack
from palantir_tenant_probe import PalantirTenantProbe


@dataclass
class PalantirCommandResult:
    handled: bool
    output: str = ""
    grounded_prompt: str = ""


def _dump(value) -> str:
    return json.dumps(value, indent=2, default=str)


def handle_palantir_command(
    prompt: str,
    bridge: Optional[DougPalantirBridge],
    approve_write: Optional[Callable[[str], bool]] = None,
) -> PalantirCommandResult:
    if not prompt.startswith("/palantir"):
        return PalantirCommandResult(handled=False)

    raw = prompt[len("/palantir") :].strip()

    if raw in {"stack", "platform"}:
        return PalantirCommandResult(
            True,
            _dump(PalantirStack(bridge.foundry if bridge else None).status()),
        )
    if raw in {"compliance", "federal", "rmf"}:
        return PalantirCommandResult(
            True,
            _dump(FederalComplianceProfile(bridge.foundry if bridge else None).status()),
        )
    if raw in {"probe", "readiness", "verify"}:
        return PalantirCommandResult(True, _dump(PalantirTenantProbe().probe()))
    if raw in {"probe-model", "verify-aip-model"}:
        return PalantirCommandResult(True, _dump(PalantirTenantProbe().probe(execute_aip_model=True)))

    if bridge is None:
        return PalantirCommandResult(
            handled=True,
            output=(
                "PALANTIR // NOT CONFIGURED // set FOUNDRY_BASE_URL and authorized credentials // "
                "use /palantir stack, /palantir compliance, or /palantir probe to inspect readiness"
            ),
        )

    if not raw or raw == "status":
        status = bridge.status()
        status["platform"] = PalantirStack(bridge.foundry).status()
        return PalantirCommandResult(True, _dump(status))

    aip = PalantirAIPClient(bridge.foundry)

    try:
        if raw == "ontologies":
            return PalantirCommandResult(True, _dump(bridge.foundry.list_ontologies()))

        if raw.startswith("query-types "):
            ontology = raw.split(maxsplit=1)[1].strip()
            return PalantirCommandResult(True, _dump(aip.list_query_types(ontology)))

        if raw.startswith("aip-logic "):
            parts = raw.split(maxsplit=3)
            if len(parts) != 4:
                raise FoundryError("usage: /palantir aip-logic <ontology> <query_api_name> <parameters_json>")
            parameters = json.loads(parts[3])
            if not isinstance(parameters, dict):
                raise FoundryError("AIP Logic parameters must be a JSON object")
            return PalantirCommandResult(
                True,
                _dump(aip.execute_logic(parts[1], parts[2], parameters)),
            )

        if raw.startswith("aip-chat "):
            parts = raw.split(maxsplit=2)
            if len(parts) != 3:
                raise FoundryError("usage: /palantir aip-chat <model_rid> <prompt>")
            return PalantirCommandResult(
                True,
                _dump(
                    aip.openai_chat_completions(
                        model=parts[1],
                        messages=[{"role": "user", "content": parts[2]}],
                    )
                ),
            )

        if raw.startswith("object-types "):
            ontology = raw.split(maxsplit=1)[1].strip()
            return PalantirCommandResult(True, _dump(bridge.foundry.list_object_types(ontology)))

        if raw.startswith("objects "):
            parts = raw.split()
            if len(parts) not in {3, 4}:
                raise FoundryError("usage: /palantir objects <ontology> <object_type> [limit]")
            limit = int(parts[3]) if len(parts) == 4 else 25
            return PalantirCommandResult(
                True,
                _dump(bridge.foundry.list_objects(parts[1], parts[2], page_size=limit)),
            )

        if raw.startswith("get "):
            parts = raw.split(maxsplit=3)
            if len(parts) != 4:
                raise FoundryError("usage: /palantir get <ontology> <object_type> <primary_key>")
            return PalantirCommandResult(
                True,
                _dump(bridge.foundry.get_object(parts[1], parts[2], parts[3])),
            )

        if raw.startswith("search "):
            parts = raw.split(maxsplit=3)
            if len(parts) != 4:
                raise FoundryError("usage: /palantir search <ontology> <object_type> <json_body>")
            search_body = json.loads(parts[3])
            if not isinstance(search_body, dict):
                raise FoundryError("search body must be a JSON object")
            return PalantirCommandResult(
                True,
                _dump(bridge.foundry.search_objects(parts[1], parts[2], search_body)),
            )

        if raw.startswith("ask "):
            parts = raw.split(maxsplit=3)
            if len(parts) != 4:
                raise FoundryError("usage: /palantir ask <ontology> <object_type> <question>")
            grounded = bridge.ground_prompt(parts[3], parts[1], parts[2])
            return PalantirCommandResult(handled=True, grounded_prompt=grounded)

        if raw.startswith("action "):
            parts = raw.split(maxsplit=3)
            if len(parts) != 4:
                raise FoundryError("usage: /palantir action <ontology> <action> <parameters_json>")
            parameters = json.loads(parts[3])
            if not isinstance(parameters, dict):
                raise FoundryError("action parameters must be a JSON object")
            approved = approve_write("Apply this Palantir Foundry action?") if approve_write else False
            if not approved:
                return PalantirCommandResult(True, "PALANTIR // ACTION CANCELLED")
            return PalantirCommandResult(
                True,
                _dump(bridge.foundry.apply_action(parts[1], parts[2], parameters)),
            )

        raise FoundryError(
            "commands: status | stack | platform | compliance | federal | rmf | probe | probe-model | ontologies | query-types | aip-logic | aip-chat | object-types | objects | get | search | ask | action"
        )
    except (FoundryError, ValueError) as error:
        return PalantirCommandResult(True, f"PALANTIR ERROR // {error}")
