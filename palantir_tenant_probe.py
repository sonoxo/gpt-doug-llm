"""Machine-verifiable Palantir tenant readiness probe.

This probe separates code completeness from live enrollment entitlement. A
component can be fully implemented in the repository while live_verified stays
false until authorized credentials and enrollment resources are configured.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import os
from typing import Any

from palantir_aip import PalantirAIPClient
from palantir_apollo import ApolloClient
from palantir_foundry import FoundryClient, FoundryError, FoundryConfigurationError
from palantir_gotham import PalantirGothamClient


@dataclass
class ProbeItem:
    component: str
    implemented: bool
    configured: bool
    live_verified: bool
    detail: str


class PalantirTenantProbe:
    def probe(self, *, execute_aip_model: bool = False) -> dict[str, Any]:
        items: list[ProbeItem] = []

        foundry = None
        try:
            foundry = FoundryClient.from_environment()
            if foundry is None:
                items.append(ProbeItem("Foundry/Ontology", True, False, False, "FOUNDRY_BASE_URL not configured"))
            else:
                try:
                    payload = foundry.list_ontologies(page_size=1)
                    items.append(ProbeItem("Foundry/Ontology", True, True, True, f"API reachable; keys={sorted(payload.keys())}"))
                except FoundryError as error:
                    items.append(ProbeItem("Foundry/Ontology", True, True, False, str(error)))
        except FoundryConfigurationError as error:
            items.append(ProbeItem("Foundry/Ontology", True, True, False, str(error)))

        if foundry is None:
            items.append(ProbeItem("AIP Logic", True, False, False, "Foundry transport not configured"))
            items.append(ProbeItem("AIP Model Proxy", True, False, False, "Foundry transport not configured"))
        else:
            aip = PalantirAIPClient(foundry)
            ontology = os.getenv("PALANTIR_AIP_ONTOLOGY", "").strip()
            query_name = os.getenv("PALANTIR_AIP_LOGIC_QUERY", "").strip()
            if ontology and query_name:
                try:
                    metadata = aip.get_query_type(ontology, query_name)
                    items.append(ProbeItem("AIP Logic", True, True, True, f"Published query visible: {metadata.get('apiName', query_name)}"))
                except FoundryError as error:
                    items.append(ProbeItem("AIP Logic", True, True, False, str(error)))
            else:
                items.append(ProbeItem("AIP Logic", True, False, False, "Set PALANTIR_AIP_ONTOLOGY and PALANTIR_AIP_LOGIC_QUERY to verify a published Logic target"))

            model = os.getenv("PALANTIR_AIP_MODEL", "").strip()
            if model and execute_aip_model:
                try:
                    aip.openai_responses(model=model, input="Reply with the single word OK.")
                    items.append(ProbeItem("AIP Model Proxy", True, True, True, "AIP provider-compatible model request succeeded"))
                except FoundryError as error:
                    items.append(ProbeItem("AIP Model Proxy", True, True, False, str(error)))
            else:
                detail = "Set PALANTIR_AIP_MODEL and run with explicit model execution to verify entitlement" if not model else "Model configured; execution probe intentionally not run"
                items.append(ProbeItem("AIP Model Proxy", True, bool(model), False, detail))

        try:
            gotham = PalantirGothamClient.from_environment()
            if gotham is None:
                items.append(ProbeItem("Gotham", True, False, False, "GOTHAM_BASE_URL not configured"))
            else:
                try:
                    payload = gotham.openapi()
                    keys = sorted(payload.keys()) if isinstance(payload, dict) else []
                    items.append(
                        ProbeItem(
                            "Gotham",
                            True,
                            True,
                            True,
                            f"Gotham API reachable at {gotham.status()['host']}; OpenAPI keys={keys[:10]}",
                        )
                    )
                except Exception as error:
                    items.append(ProbeItem("Gotham", True, True, False, str(error)))
        except Exception as error:
            items.append(ProbeItem("Gotham", True, True, False, str(error)))

        try:
            apollo = ApolloClient.from_environment()
            if apollo is None:
                items.append(ProbeItem("Apollo", True, False, False, "APOLLO_URL not configured"))
            else:
                status = apollo.status()
                live = False
                detail = f"configured; graphql={status['graphql_configured']}; cli={status['cli_available']}"
                if status["graphql_configured"] and apollo.token:
                    try:
                        apollo.get_current_user()
                        live = True
                        detail = "Apollo GraphQL reachable"
                    except Exception as error:
                        detail = str(error)
                items.append(ProbeItem("Apollo", True, True, live, detail))
        except Exception as error:
            items.append(ProbeItem("Apollo", True, True, False, str(error)))

        return {
            "all_code_implemented": all(item.implemented for item in items),
            "all_configured_components_live": all(
                item.live_verified for item in items if item.configured
            ),
            "items": [asdict(item) for item in items],
        }
