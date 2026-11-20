"""Local COSMOS launcher regression tests: occupied ports must not crash the app."""
from __future__ import annotations

import errno
import importlib.util
import socket
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "xunia_cosmos_serve.py"
SPEC = importlib.util.spec_from_file_location("xunia_cosmos_serve", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
serve = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(serve)


class CosmosLocalServerTests(unittest.TestCase):
    def test_busy_port_moves_to_next_available_without_killing_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
            blocker.bind(("127.0.0.1", 0))
            blocker.listen(1)
            busy = blocker.getsockname()[1]
            if busy > 65531:
                self.skipTest("No room above the ephemeral port for a fallback test")
            server, chosen = serve.open_server(
                busy,
                auto_fallback=True,
                attempts=4,
            )
            try:
                self.assertGreater(chosen, busy)
                self.assertLessEqual(chosen, busy + 3)
                self.assertEqual(server.server_address[0], "127.0.0.1")
                self.assertEqual(blocker.getsockname()[1], busy)
            finally:
                server.server_close()

    def test_explicit_busy_port_fails_cleanly(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
            blocker.bind(("127.0.0.1", 0))
            blocker.listen(1)
            busy = blocker.getsockname()[1]
            with self.assertRaises(OSError) as captured:
                serve.open_server(busy, auto_fallback=False)
            self.assertEqual(captured.exception.errno, errno.EADDRINUSE)

    def test_local_server_serves_xenology_and_planets(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        server, port = serve.open_server(port)
        worker = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.1},
            daemon=True,
        )
        worker.start()
        try:
            for relative, marker in [
                ("/cosmos/xenology/", b'id="creatureCanvas"'),
                ("/cosmos/planets/", b'id="orrery"'),
                ("/cosmos/", b'id="space"'),
                ("/favicon.svg", b'<svg'),
                ("/cosmos/catalogs/nasa.json", b'"data_mode": "not-imported"'),
                ("/cosmos/catalogs/gaia.json", b'"data_mode": "not-imported"'),
                ("/molecules/", b'id="moleculeCanvas"'),
                ("/molecules/catalogs/seed.json", b'"molecules": ['),
                ("/molecules/catalogs/pubchem.json", b'"status": "not-imported"'),
            ]:
                with self.subTest(relative=relative):
                    with urlopen(f"http://127.0.0.1:{port}{relative}", timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(marker, response.read())
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
