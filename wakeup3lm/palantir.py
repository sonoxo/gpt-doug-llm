"""Wakeup3lm ↔ Palantir AIP bridge.

This is the external Palantir execution layer for the IDE LLM. Wakeup3lm keeps
its local ontology/audit trail while invoking authorized AIP model or Logic
resources through the hardened Palantir clients.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable
from uuid import uuid4

from palantir_aip import AIPTestCase, PalantirAIPClient
from palantir_automate import AutomateEffect, PalantirAutomateBridge
from palantir_foundry import FoundryClient

from .runtime import Wakeup3LM


class Wakeup3LMPalantirBridge:
    def __init__(self, wakeup: Wakeup3LM, foundry: FoundryClient) -> None:
        self.wakeup = wakeup
        self.foundry = foundry
        self.aip = PalantirAIPClient(foundry)
        self.automate = PalantirAutomateBridge(foundry)

    def _record(self, operation: str, request: dict[str, Any], result: Any = None, error: str = "") -> str:
        run_id = uuid4().hex
        status = "FAILED" if error else "PASSED"
        self.wakeup.ontology.upsert(
            "AgentRun",
            run_id,
            platform="palantir",
            operation=operation,
            request=request,
            result=result,
            error=error,
            status=status,
        )
        self.wakeup.ontology.link("Model", "wakeup3lm", "EXECUTED_EXTERNAL_RUN", "AgentRun", run_id)
        return run_id

    def invoke_model(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        request = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            response = self.aip.openai_chat_completions(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as error:
            self._record("aip-model", request, error=str(error))
            raise
        self._record("aip-model", request, result=response)
        return response

    def invoke_logic(
        self,
        *,
        ontology: str,
        query_api_name: str,
        parameters: dict[str, Any],
        version: str | None = None,
    ) -> dict[str, Any]:
        request = {
            "ontology": ontology,
            "query_api_name": query_api_name,
            "parameters": parameters,
            "version": version,
        }
        try:
            response = self.aip.execute_logic(
                ontology,
                query_api_name,
                parameters,
                version=version,
            )
        except Exception as error:
            self._record("aip-logic", request, error=str(error))
            raise
        self._record("aip-logic", request, result=response)
        return response

    def run_eval_suite(
        self,
        *,
        ontology: str,
        query_api_name: str,
        cases: Iterable[AIPTestCase],
        version: str | None = None,
    ) -> dict[str, Any]:
        cases = list(cases)
        report = self.aip.run_eval_suite(
            ontology,
            query_api_name,
            cases,
            version=version,
        )
        payload = {
            "target": report.target,
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "success": report.success,
            "results": [asdict(item) for item in report.results],
        }
        self._record(
            "aip-evals",
            {"ontology": ontology, "query_api_name": query_api_name, "case_count": len(cases)},
            result=payload,
        )
        return payload

    def execute_automate_effect(self, effect: AutomateEffect) -> dict[str, Any]:
        request = asdict(effect)
        try:
            response = self.automate.execute_effect(effect)
        except Exception as error:
            self._record("automate-effect", request, error=str(error))
            raise
        self._record("automate-effect", request, result=response)
        return response
