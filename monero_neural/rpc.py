from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class MoneroRPCError(RuntimeError):
    pass


class MoneroRPCClient:
    """Minimal read/query Monero JSON-RPC client.

    This client intentionally contains no transfer method and never accepts or
    stores a private spend key.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = float(timeout)

    @classmethod
    def daemon_from_env(cls) -> "MoneroRPCClient":
        return cls(
            os.getenv("MONERO_DAEMON_RPC", "http://127.0.0.1:38081/json_rpc"),
            username=os.getenv("MONERO_DAEMON_RPC_USER") or None,
            password=os.getenv("MONERO_DAEMON_RPC_PASSWORD") or None,
        )

    @classmethod
    def wallet_from_env(cls) -> "MoneroRPCClient":
        return cls(
            os.getenv("MONERO_WALLET_RPC", "http://127.0.0.1:38088/json_rpc"),
            username=os.getenv("MONERO_WALLET_RPC_USER") or None,
            password=os.getenv("MONERO_WALLET_RPC_PASSWORD") or None,
        )

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.username is not None:
            token = base64.b64encode(
                (self.username + ":" + (self.password or "")).encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = "Basic " + token
        return headers

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body = {
            "jsonrpc": "2.0",
            "id": "gpt-doug-xmr-neural",
            "method": method,
            "params": params or {},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise MoneroRPCError("Monero RPC request failed: %s" % exc) from exc
        if payload.get("error"):
            raise MoneroRPCError("Monero RPC error: %s" % payload["error"])
        result = payload.get("result")
        if not isinstance(result, dict):
            raise MoneroRPCError("Monero RPC returned no result object")
        return result

    def daemon_info(self) -> Dict[str, Any]:
        return self.call("get_info")

    def wallet_version(self) -> Dict[str, Any]:
        return self.call("get_version")

    def wallet_balance(self, *, account_index: int = 0) -> Dict[str, Any]:
        return self.call("get_balance", {"account_index": int(account_index)})

    def wallet_transfers(
        self,
        *,
        account_index: int = 0,
        incoming: bool = True,
        outgoing: bool = True,
        pending: bool = True,
        failed: bool = True,
        pool: bool = True,
    ) -> Dict[str, Any]:
        return self.call(
            "get_transfers",
            {
                "account_index": int(account_index),
                "in": bool(incoming),
                "out": bool(outgoing),
                "pending": bool(pending),
                "failed": bool(failed),
                "pool": bool(pool),
            },
        )
