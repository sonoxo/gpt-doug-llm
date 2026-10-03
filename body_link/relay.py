from __future__ import annotations

import queue
import threading
from typing import Any

from .client import BodyLinkClient


class BodyStateRelay:
    """Latest-state-only non-blocking relay from GPT-Doug to the remote body."""

    def __init__(self, client: BodyLinkClient) -> None:
        self.client = client
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self.last_error: str | None = None
        self.last_ack: dict[str, Any] | None = None
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="gpt-doug-body-state-relay",
        )
        self._thread.start()

    def publish(self, body_state: dict[str, Any]) -> None:
        if self._stop.is_set():
            return
        try:
            self._queue.put_nowait(body_state)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(body_state)
            except queue.Full:
                pass

    def close(self) -> None:
        self._stop.set()

    def status(self) -> dict[str, Any]:
        return {
            "running": self._thread.is_alive() and not self._stop.is_set(),
            "last_error": self.last_error,
            "last_ack": self.last_ack,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                body_state = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                self.last_ack = self.client.push_state(body_state)
                self.last_error = None
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
