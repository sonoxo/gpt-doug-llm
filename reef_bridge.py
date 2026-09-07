"""Reef continual-learning bridge for GPT-DOUG-LLM.

This module connects GPT-DOUG's ontology-centered agent stack to a running
Reef service without forcing Reef's Python >=3.10 runtime requirement onto
GPT-DOUG's Python >=3.9 core.

Upstream project: https://github.com/Human-Agent-Society/reef
Upstream license: Apache-2.0

The adapter follows Reef's public HTTP contract documented by the upstream
project: provider-compatible inference endpoints return an
``x-reef-agent-record-id`` receipt, and ``/reef/report`` attaches feedback to
one or more receipts.

No Reef source code is vendored here.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REEF_UPSTREAM_REPOSITORY = "https://github.com/Human-Agent-Society/reef"
REEF_UPSTREAM_LICENSE = "Apache-2.0"
REEF_LIFECYCLE = ("serve", "observe", "grow", "commit")

REEF_ONTOLOGY = {
    "integration_id": "reef-continual-learning",
    "upstream": {
        "repository": REEF_UPSTREAM_REPOSITORY,
        "license": REEF_UPSTREAM_LICENSE,
    },
    "lifecycle": list(REEF_LIFECYCLE),
    "object_types": {
        "AgentInteraction": {
            "description": "An inference interaction recorded by Reef.",
            "key": "receipt_id",
        },
        "FeedbackReport": {
            "description": "A score and/or structured feedback attached to an interaction.",
            "key": "report_id",
        },
        "LearningCandidate": {
            "description": "A candidate harness or model update produced from eligible records.",
            "key": "candidate_id",
        },
        "ArtifactVersion": {
            "description": "A versioned artifact accepted by the configured Reef selection policy.",
            "key": "version_id",
        },
    },
    "link_types": {
        "evaluates": {"from": "FeedbackReport", "to": "AgentInteraction"},
        "derived_from": {"from": "LearningCandidate", "to": "AgentInteraction"},
        "commits": {"from": "ArtifactVersion", "to": "LearningCandidate"},
    },
    "action_types": {
        "ReefInfer": {"stage": "serve", "endpoint": "/v1/chat/completions"},
        "ReefReportFeedback": {"stage": "observe", "endpoint": "/reef/report"},
    },
    "gpt_doug_mapping": {
        "Task": "AgentInteraction",
        "Result": "FeedbackReport",
        "KnowledgeEntry": "ArtifactVersion",
    },
}


class ReefBridgeError(RuntimeError):
    """Raised when the configured Reef service cannot satisfy a bridge request."""


@dataclass(frozen=True)
class ReefConfig:
    """Connection settings for a Reef deployment."""

    base_url: str = "http://127.0.0.1:8901"
    token: str = ""
    scenario: str = "gpt-doug"
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "ReefConfig":
        """Build a config from REEF_* environment variables."""
        timeout_raw = os.getenv("REEF_TIMEOUT", "60")
        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise ReefBridgeError("REEF_TIMEOUT must be numeric") from exc
        if timeout <= 0:
            raise ReefBridgeError("REEF_TIMEOUT must be greater than zero")

        return cls(
            base_url=os.getenv("REEF_BASE_URL", "http://127.0.0.1:8901").rstrip("/"),
            token=os.getenv("REEF_TOKEN", ""),
            scenario=os.getenv("REEF_SCENARIO", "gpt-doug"),
            timeout=timeout,
        )


class ReefBridge:
    """Small HTTP adapter for Reef inference + feedback reporting."""

    def __init__(self, config: Optional[ReefConfig] = None) -> None:
        self.config = config or ReefConfig.from_env()

    @staticmethod
    def ontology_registration() -> Dict[str, Any]:
        """Return an isolated copy of the Reef ontology registration."""
        return json.loads(json.dumps(REEF_ONTOLOGY))

    def _headers(self, extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-reef-scenario": self.config.scenario,
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.config.base_url}/{path.lstrip('/')}"
        body = None if payload is None else json.dumps(dict(payload)).encode("utf-8")
        request = Request(url, data=body, headers=self._headers(), method=method.upper())

        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read().decode("utf-8")
                response_body = json.loads(raw) if raw else None
                return {
                    "status": response.status,
                    "headers": {key.lower(): value for key, value in response.headers.items()},
                    "body": response_body,
                }
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ReefBridgeError(f"Reef HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise ReefBridgeError(f"Reef connection failed: {exc.reason}") from exc

    def health(self) -> Dict[str, Any]:
        """Check the configured Reef deployment's health endpoint."""
        return self._request("GET", "/healthz")

    def chat_completion(
        self,
        *,
        model: str,
        messages: Iterable[Mapping[str, Any]],
        **parameters: Any,
    ) -> Dict[str, Any]:
        """Run a chat completion through Reef and preserve its interaction receipt."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [dict(message) for message in messages],
        }
        payload.update(parameters)
        response = self._request("POST", "/v1/chat/completions", payload)
        receipt = response["headers"].get("x-reef-agent-record-id")
        if not receipt:
            raise ReefBridgeError("Reef response did not include x-reef-agent-record-id")
        return {
            "receipt_id": receipt,
            "scenario": self.config.scenario,
            "response": response["body"],
            "http_status": response["status"],
        }

    def report(
        self,
        *,
        references: Iterable[str],
        score: Optional[float] = None,
        feedback: Any = None,
    ) -> Dict[str, Any]:
        """Attach feedback to one or more recorded Reef interaction receipts."""
        refs = [reference for reference in references if reference]
        if not refs:
            raise ReefBridgeError("At least one Reef receipt reference is required")
        if score is None and feedback is None:
            raise ReefBridgeError("A score and/or feedback value is required")

        payload: Dict[str, Any] = {"references": refs}
        if score is not None:
            payload["score"] = float(score)
        if feedback is not None:
            payload["feedback"] = feedback
        return self._request("POST", "/reef/report", payload)

    def feedback_for_completion(
        self,
        completion: Mapping[str, Any],
        *,
        score: Optional[float] = None,
        feedback: Any = None,
    ) -> Dict[str, Any]:
        """Convenience action: report feedback using a completion's saved receipt."""
        receipt = str(completion.get("receipt_id", ""))
        return self.report(references=[receipt], score=score, feedback=feedback)

    def status(self) -> Dict[str, Any]:
        """Return bridge configuration without exposing authentication material."""
        return {
            "integration": "reef-continual-learning",
            "base_url": self.config.base_url,
            "scenario": self.config.scenario,
            "authenticated": bool(self.config.token),
            "lifecycle": list(REEF_LIFECYCLE),
            "upstream": REEF_UPSTREAM_REPOSITORY,
            "license": REEF_UPSTREAM_LICENSE,
        }
