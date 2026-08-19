#!/usr/bin/env python3
"""HTTP/1.1 streaming entrypoint for GPT XUNIA.

Reuses the hardened GPT Doug web stack while adding an SFNN-inspired
self-monitoring checkpoint to every streamed response. The checkpoint is
emitted before the final SSE ``done`` event and before the connection closes,
so browser-side conversation memory is committed only after monitoring has
completed.

The SFNN metrics are operational engineering telemetry, not a claim or proof
of phenomenal consciousness.
"""

import atexit
import os
import signal
import urllib.error
from http.server import ThreadingHTTPServer

from doug_core.sfnn_monitor import IDENTITY_ANCHOR, StringFieldSelfMonitor
from web import server as base

_MONITOR = StringFieldSelfMonitor()


def build_self_monitor_event(
    external_context: str,
    internal_state: str,
    *,
    audit_passed: bool,
) -> dict:
    """Build the final pre-commit monitor event for one streamed reply."""
    report = _MONITOR.observe(
        external_context,
        internal_state,
        audit_passed=audit_passed,
        current_identity=IDENTITY_ANCHOR,
        cycles=1,
    )
    return {
        "type": "self_monitor",
        "self_monitor": report.as_dict(),
        "done": False,
    }


class XuniaHandler(base.Handler):
    """GPT XUNIA streaming handler with a pre-memory SFNN checkpoint."""

    def _handle_chat(self, stream):
        if not stream:
            return super()._handle_chat(stream)

        # Force a clean EOF after the final monitor + done events. The browser
        # only persists the assistant reply after ReadableStream reaches EOF.
        self.close_connection = True

        payload = self._read_json()
        if payload is None:
            return self._json(400, {"error": "invalid json"})

        messages = payload.get("messages", [])
        model = payload.get("model", base.MODEL)
        last_user = next(
            (
                message.get("content", "")
                for message in reversed(messages)
                if message.get("role") == "user"
            ),
            "",
        )

        input_verdict = base.zyra.inspect(last_user, direction="input")
        if not input_verdict.allowed:
            reason = "; ".join(input_verdict.reasons) or "blocked by policy"
            blocked_message = f"Zyra blocked this request: {reason}"
            output_verdict = base.zyra.inspect(blocked_message, direction="output")

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            self._sse_send(
                {
                    "message": {
                        "role": "assistant",
                        "content": blocked_message,
                    },
                    "done": False,
                }
            )
            self._sse_send(
                build_self_monitor_event(
                    last_user,
                    blocked_message,
                    audit_passed=bool(output_verdict.allowed),
                )
            )
            self._sse_send({"type": "complete", "done": True})
            return

        if not messages or messages[0].get("role") != "system":
            messages = [
                {"role": "system", "content": base.SYSTEM_PROMPT},
                *list(messages),
            ]

        options = {
            **base.DEFAULT_PROVIDER_OPTIONS,
            **payload.get("options", {}),
        }

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        full_reply: list[str] = []
        client_connected = True

        try:
            for upstream_event in base.llm_backend.chat_stream(
                messages,
                model,
                options,
            ):
                token = upstream_event.get("message", {}).get("content", "")
                if token:
                    full_reply.append(token)

                # Hold the upstream done marker until after the SFNN checkpoint.
                # This guarantees clients that honor `done` do not commit early.
                event = dict(upstream_event)
                provider_done = bool(event.get("done"))
                if provider_done:
                    event["done"] = False

                if token or not provider_done or len(event) > 1:
                    self._sse_send(event)

                if provider_done:
                    break

        except (BrokenPipeError, ConnectionResetError):
            client_connected = False
        except urllib.error.URLError as err:
            try:
                self._sse_send(
                    {"error": f"Unable to reach the model backend: {err}"}
                )
            except (BrokenPipeError, ConnectionResetError):
                client_connected = False
        except Exception as err:  # noqa: BLE001
            try:
                self._sse_send({"error": str(err)})
            except (BrokenPipeError, ConnectionResetError):
                client_connected = False
        finally:
            reply = "".join(full_reply)
            output_verdict = base.zyra.inspect(reply, direction="output")

            if client_connected:
                try:
                    self._sse_send(
                        build_self_monitor_event(
                            last_user,
                            reply,
                            audit_passed=bool(output_verdict.allowed),
                        )
                    )
                    self._sse_send({"type": "complete", "done": True})
                except (BrokenPipeError, ConnectionResetError):
                    pass


def _shutdown(*_args):
    base.runner.stop_all()
    raise SystemExit(0)


if __name__ == "__main__":
    atexit.register(base.runner.stop_all)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server = ThreadingHTTPServer(("127.0.0.1", base.PORT), XuniaHandler)
    print(f"GPT XUNIA streaming at http://localhost:{base.PORT}")
    print("SFNN self-monitor checkpoint: enabled before stream commit")
    print(base.auth.startup_message())
    if os.environ.get("GPT_DOUG_ENABLE_WORKER", "false").lower() in {"1", "true", "yes"}:
        base.worker.start()
        print("Autonomous marketplace worker started.")
    else:
        print("Autonomous marketplace worker disabled.")
    try:
        server.serve_forever()
    finally:
        base.runner.stop_all()
