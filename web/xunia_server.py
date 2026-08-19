#!/usr/bin/env python3
"""HTTP/1.1 streaming entrypoint for GPT XUNIA.

Reuses the hardened GPT Doug web handler and forces SSE requests to close
cleanly after the final event so browser ReadableStream consumers receive EOF.
"""

import atexit
import os
import signal
from http.server import ThreadingHTTPServer

from web import server as base


class XuniaHandler(base.Handler):
    def _handle_chat(self, stream):
        if stream:
            self.close_connection = True
        return super()._handle_chat(stream)


def _shutdown(*_args):
    base.runner.stop_all()
    raise SystemExit(0)


if __name__ == "__main__":
    atexit.register(base.runner.stop_all)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server = ThreadingHTTPServer(("127.0.0.1", base.PORT), XuniaHandler)
    print(f"GPT XUNIA streaming at http://localhost:{base.PORT}")
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
