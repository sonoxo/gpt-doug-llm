from __future__ import annotations

import asyncio
from collections.abc import Iterable

from fastapi import WebSocket


class EventHub:
    """In-process fan-out for public/synthetic event notifications.

    Durable history lives in Postgres. This hub is intentionally only the
    low-latency delivery plane; reconnecting clients recover from the REST
    event history endpoint.
    """

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            clients = list(self._clients)
        if not clients:
            return

        async def send(client: WebSocket) -> WebSocket | None:
            try:
                await client.send_json(payload)
                return None
            except Exception:
                return client

        failed = [item for item in await asyncio.gather(*(send(c) for c in clients)) if item]
        if failed:
            async with self._lock:
                for client in failed:
                    self._clients.discard(client)

    async def broadcast_many(self, payloads: Iterable[dict]) -> None:
        for payload in payloads:
            await self.broadcast(payload)

    @property
    def connection_count(self) -> int:
        return len(self._clients)


event_hub = EventHub()
