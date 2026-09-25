from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .protocol import canonical_json, normalize_runtime_url, sign, verify
from .state import runtime_body_state, sanitize_body_state


class BodyLinkError(RuntimeError):
    pass


class BodyLinkClient:
    WORKSPACE_URL = "https://replit.com/@24kmediaproduct/GPT-Doug-AI-Hub"

    def __init__(
        self,
        base_url: str,
        secret: str,
        *,
        state_dir: str | Path | None = None,
        controller_id: str = "GPT_DOUG",
        hive_id: str | None = None,
        ontology_hash: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = normalize_runtime_url(base_url)
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("GPT_DOUG_BODY_LINK_KEY must be at least 32 bytes")
        self._secret = secret
        self.controller_id = controller_id
        self.hive_id = hive_id
        self.ontology_hash = ontology_hash
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 30.0))
        root = Path(state_dir or (Path.home() / ".gpt-doug" / "body-link")).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        self.state_path = root / "state.json"

    @classmethod
    def optional_from_env(
        cls,
        *,
        state_dir: str | Path | None = None,
        hive_id: str | None = None,
        ontology_hash: str | None = None,
    ) -> "BodyLinkClient | None":
        url = os.getenv("GPT_DOUG_BODY_URL", "").strip()
        key = os.getenv("GPT_DOUG_BODY_LINK_KEY", "")
        if not url and not key:
            return None
        if not url or not key:
            raise ValueError("GPT_DOUG_BODY_URL and GPT_DOUG_BODY_LINK_KEY must be configured together")
        return cls(
            url,
            key,
            state_dir=state_dir,
            hive_id=hive_id,
            ontology_hash=ontology_hash,
        )

    def _state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def _write_state(self, payload: dict[str, Any]) -> None:
        safe = {
            "protocol": payload.get("protocol"),
            "linked": bool(payload.get("linked")),
            "controller_id": payload.get("controller_id"),
            "body_node_id": payload.get("body_node_id"),
            "body_url": self.base_url,
            "workspace_url": self.WORKSPACE_URL,
            "hive_id": self.hive_id,
            "ontology_hash": self.ontology_hash,
            "last_handshake_at": payload.get("last_handshake_at"),
            "last_heartbeat_at": payload.get("last_heartbeat_at"),
            "capabilities": payload.get("capabilities", []),
        }
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.state_path)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = canonical_json(payload)
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = sign(
            self._secret,
            method="POST",
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
        )
        request = Request(
            self.base_url + path,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-GPTDoug-Protocol": "gptdoug-body-link-v1",
                "X-GPTDoug-Timestamp": timestamp,
                "X-GPTDoug-Nonce": nonce,
                "X-GPTDoug-Signature": signature,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read()
                response_timestamp = response.headers.get("X-GPTDoug-Timestamp", "")
                response_nonce = response.headers.get("X-GPTDoug-Nonce", "")
                response_signature = response.headers.get("X-GPTDoug-Signature", "")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise BodyLinkError(f"body node HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise BodyLinkError(f"body node unreachable: {exc.reason}") from exc

        if not verify(
            self._secret,
            method="RESPONSE",
            path=path,
            timestamp=response_timestamp,
            nonce=response_nonce,
            body=response_body,
            signature=response_signature,
        ):
            raise BodyLinkError("body node response signature verification failed")

        try:
            data = json.loads(response_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise BodyLinkError("body node returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise BodyLinkError("body node returned an invalid payload")
        return data

    def link(self) -> dict[str, Any]:
        challenge = secrets.token_urlsafe(24)
        payload = {
            "controller_id": self.controller_id,
            "controller_role": "GPT_DOUG",
            "simulation_layer": "GPT_CHAOS",
            "hive_id": self.hive_id,
            "ontology_hash": self.ontology_hash,
            "challenge": challenge,
            "workspace_url": self.WORKSPACE_URL,
        }
        data = self._post("/v1/handshake", payload)
        if data.get("challenge") != challenge:
            raise BodyLinkError("body node challenge mismatch")
        if data.get("linked") is not True:
            raise BodyLinkError("body node did not acknowledge the link")
        data["last_handshake_at"] = int(time.time())
        self._write_state(data)
        return data

    def ping(self) -> dict[str, Any]:
        state = self._state()
        payload = {
            "controller_id": self.controller_id,
            "hive_id": self.hive_id,
            "ontology_hash": self.ontology_hash,
            "known_body_node_id": state.get("body_node_id"),
        }
        data = self._post("/v1/heartbeat", payload)
        data["last_heartbeat_at"] = int(time.time())
        data.setdefault("linked", True)
        data.setdefault("controller_id", self.controller_id)
        self._write_state({**state, **data})
        return data

    def push_state(self, body_state: dict[str, Any]) -> dict[str, Any]:
        sanitized = sanitize_body_state(body_state)
        payload = {
            "controller_id": self.controller_id,
            "hive_id": self.hive_id,
            "ontology_hash": self.ontology_hash,
            "body_state": sanitized,
        }
        data = self._post("/v1/state", payload)
        if data.get("accepted") is not True:
            raise BodyLinkError("body node did not accept state update")
        return data

    def push_runtime_state(self, state: str, detail: str = "") -> dict[str, Any]:
        return self.push_state(runtime_body_state(state, detail))

    def status(self) -> dict[str, Any]:
        state = self._state()
        return {
            "configured": True,
            "body_url": self.base_url,
            "workspace_url": self.WORKSPACE_URL,
            "protocol": "gptdoug-body-link-v1",
            "linked": bool(state.get("linked")),
            "body_node_id": state.get("body_node_id"),
            "last_handshake_at": state.get("last_handshake_at"),
            "last_heartbeat_at": state.get("last_heartbeat_at"),
            "capabilities": state.get("capabilities", []),
            "remote_shell": False,
            "state_push": True,
            "state_stream": True,
            "secrets_persisted": False,
        }
