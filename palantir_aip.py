"""Live Palantir AIP adapter for authorized Foundry enrollments.

Uses public Foundry/AIP REST surfaces:
- provider-compatible LLM proxy endpoints
- Ontology Query execution for published Logic/Function queries
- query metadata for readiness checks

No credentials are stored here; all authority comes from the configured
FoundryClient and the permissions on the supplied token/service principal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional
import urllib.parse

from palantir_foundry import FoundryClient, FoundryError


@dataclass(frozen=True)
class AIPTestCase:
    name: str
    parameters: dict[str, Any]
    expected: Any = None


@dataclass
class AIPEvalResult:
    name: str
    passed: bool
    actual: Any = None
    expected: Any = None
    error: str = ""


@dataclass
class AIPEvalReport:
    target: str
    total: int
    passed: int
    failed: int
    results: list[AIPEvalResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed == 0


class PalantirAIPClient:
    """AIP execution client layered on the hardened Foundry transport."""

    def __init__(self, foundry: FoundryClient) -> None:
        self.foundry = foundry

    def openai_chat_completions(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"model": model, "messages": messages}
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if extra:
            body.update(extra)
        return self.foundry.request(
            "POST",
            "/api/v2/llm/proxy/openai/v1/chat/completions",
            body=body,
        )

    def openai_responses(
        self,
        *,
        model: str,
        input: Any,
        instructions: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"model": model, "input": input}
        if instructions:
            body["instructions"] = instructions
        if extra:
            body.update(extra)
        return self.foundry.request(
            "POST",
            "/api/v2/llm/proxy/openai/v1/responses",
            body=body,
        )

    def anthropic_messages(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if extra:
            body.update(extra)
        return self.foundry.request(
            "POST",
            "/api/v2/llm/proxy/anthropic/v1/messages",
            body=body,
        )

    def list_query_types(
        self,
        ontology: str,
        *,
        page_size: int = 100,
        page_token: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> dict[str, Any]:
        ontology_q = urllib.parse.quote(ontology, safe="")
        return self.foundry.request(
            "GET",
            f"/api/v2/ontologies/{ontology_q}/queryTypes",
            query={
                "pageSize": max(1, min(page_size, 1000)),
                "pageToken": page_token,
                "branch": branch,
            },
        )

    def get_query_type(
        self,
        ontology: str,
        query_api_name: str,
        *,
        version: Optional[str] = None,
    ) -> dict[str, Any]:
        ontology_q = urllib.parse.quote(ontology, safe="")
        query_q = urllib.parse.quote(query_api_name, safe="")
        return self.foundry.request(
            "GET",
            f"/api/v2/ontologies/{ontology_q}/queryTypes/{query_q}",
            query={"version": version},
        )

    def execute_logic(
        self,
        ontology: str,
        query_api_name: str,
        parameters: dict[str, Any],
        *,
        version: Optional[str] = None,
        branch: Optional[str] = None,
        scenario_rid: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a published AIP Logic/Function query through Ontology Query API."""
        ontology_q = urllib.parse.quote(ontology, safe="")
        query_q = urllib.parse.quote(query_api_name, safe="")
        return self.foundry.request(
            "POST",
            f"/api/v2/ontologies/{ontology_q}/queries/{query_q}/execute",
            body={"parameters": parameters},
            query={
                "version": version,
                "branch": branch,
                "scenarioRid": scenario_rid,
            },
        )

    def run_eval_suite(
        self,
        ontology: str,
        query_api_name: str,
        cases: Iterable[AIPTestCase],
        *,
        evaluator: Optional[Callable[[Any, Any], bool]] = None,
        version: Optional[str] = None,
    ) -> AIPEvalReport:
        """Run a deterministic regression suite against a published AIP Logic target.

        This is the external CI companion to Palantir AIP Evals: the target is a
        real published Logic/Function query and every case executes through the
        Foundry API. It does not claim to create resources inside the AIP Evals UI.
        """
        evaluate = evaluator or (lambda actual, expected: actual == expected)
        results: list[AIPEvalResult] = []
        for case in cases:
            try:
                response = self.execute_logic(
                    ontology,
                    query_api_name,
                    case.parameters,
                    version=version,
                )
                actual = response.get("value")
                passed = True if case.expected is None else bool(evaluate(actual, case.expected))
                results.append(
                    AIPEvalResult(
                        name=case.name,
                        passed=passed,
                        actual=actual,
                        expected=case.expected,
                    )
                )
            except FoundryError as error:
                results.append(
                    AIPEvalResult(
                        name=case.name,
                        passed=False,
                        expected=case.expected,
                        error=str(error),
                    )
                )
        passed_count = sum(1 for item in results if item.passed)
        return AIPEvalReport(
            target=f"{ontology}:{query_api_name}",
            total=len(results),
            passed=passed_count,
            failed=len(results) - passed_count,
            results=results,
        )
