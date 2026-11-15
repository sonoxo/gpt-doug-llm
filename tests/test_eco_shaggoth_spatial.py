"""Offline validation of the real ECO-SHAGGOTH spatial terminal."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "eco_shaggoth_cl1.py"

spec = importlib.util.spec_from_file_location("eco_shaggoth_cl1", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class SpatialTests(unittest.TestCase):
    def test_nodes_are_unique_and_every_edge_references_known_nodes(self):
        self.assertGreaterEqual(len(mod.NODES), 15)
        self.assertEqual(len(mod.NODES), len(mod.BY_ID))
        self.assertTrue(all(n.layer in mod.LAYERS[1:] for n in mod.NODES))
        for source, target, relationship in mod.EDGES:
            self.assertIn(source, mod.BY_ID)
            self.assertIn(target, mod.BY_ID)
            self.assertTrue(relationship)

    def test_versioned_json_topology_is_read_only(self):
        graph = mod.topology()
        self.assertFalse(graph["bank_accounts_connected"])
        self.assertFalse(graph["bank_transactions_enabled"])
        self.assertFalse(graph["vault_unlocked"])
        self.assertFalse(graph["external_calls"])
        self.assertEqual(len(graph["nodes"]), len(mod.NODES))
        self.assertTrue(all(len(n["xyz"]) == 3 for n in graph["nodes"]))
        self.assertNotIn("password", json.dumps(graph).lower())

    def test_camera_rotates_and_zooms_without_invalid_coordinates(self):
        position = (2.2, -0.3, 0.7)
        a = mod.rotate_project(position, 0, 0, 1, 100, 30)
        b = mod.rotate_project(position, 0.8, 0.4, 1, 100, 30)
        zoomed = mod.rotate_project(position, 0, 0, 2, 100, 30)
        self.assertNotEqual(a[:2], b[:2])
        self.assertGreater(abs(zoomed[0] - 50), abs(a[0] - 50))
        self.assertTrue(all(isinstance(c, int) for c in zoomed[:2]))

    def test_frame_contains_organic_core_nodes_and_edges(self):
        view = mod.View()
        canvas = mod.Canvas(110, 38)
        coords = mod.draw_world(canvas, view)
        rendered = "\n".join("".join(c for c, _ in row) for row in canvas.cells)
        self.assertIn("SHAGGOTH", rendered)
        self.assertIn("KRAKEN", rendered)
        self.assertIn("OLLAMA", rendered)
        self.assertIn("◉", rendered)
        self.assertIn("·", rendered)
        self.assertIn("cl1", coords)
        view.yaw += 1
        rotated = mod.draw_world(mod.Canvas(110, 38), view)
        self.assertNotEqual(coords["glass"], rotated["glass"])

    def test_layer_filters_only_relevant_nodes(self):
        view = mod.View(layer="FINANCE")
        ids = [n.id for n in mod.visible_nodes(view)]
        self.assertIn("bank", ids)
        self.assertIn("vault", ids)
        self.assertNotIn("ollama", ids)

    def test_select_and_search_are_interactive_without_network(self):
        view = mod.View()
        first = view.selected
        mod._step_selection(view, 1)
        self.assertNotEqual(first, view.selected)
        self.assertEqual(mod._find_node("glass onion"), "glass")
        self.assertEqual(mod._find_node("ollama"), "ollama")
        self.assertIsNone(mod._find_node("not-a-node"))
        mod._handle_key(view, ord("+"), None)
        self.assertGreater(view.zoom, 1.0)
        mod._handle_key(view, ord("n"), None)
        self.assertNotEqual(view.layer, "ALL")
        mod._handle_key(view, ord("f"), None)
        self.assertEqual(view.layer, "ALL")
        self.assertEqual(view.zoom, 1.0)
        mod._handle_key(view, ord("q"), None)
        self.assertFalse(view.running)

    def test_offline_snapshot_performs_no_socket_calls(self):
        with patch.object(mod.socket, "create_connection", side_effect=AssertionError("network")):
            view = mod.health_snapshot(offline=True)
            text = mod.snapshot_text(100, 28, offline=True)
        self.assertEqual(view["ollama"], "UNTESTED")
        self.assertEqual(view["bank"], "DENY")
        self.assertEqual(view["vault"], "SEALED")
        self.assertIn("SPATIAL ECOSYSTEM", text)
        self.assertIn("SHAGGOTH", text)
        self.assertIn("TCP reachable only", text)

    def test_port_scans_are_loopback_only(self):
        called = []

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, *unused):
                return None

        def fake(address, timeout):
            called.append((address, timeout))
            return FakeConnection()

        with patch.object(mod.socket, "create_connection", side_effect=fake):
            self.assertEqual(mod.probe_local(11434), "LISTENING")
            self.assertEqual(mod.probe_local(0), "UNKNOWN")
            self.assertEqual(mod.probe_local(65536), "UNKNOWN")
        self.assertEqual(called, [(("127.0.0.1", 11434), 0.1)])

    def test_cli_snapshot_and_json_work_without_tty_or_extra_packages(self):
        for args in (["--json"], ["--snapshot", "--offline"]):
            result = subprocess.run(
                [sys.executable, str(SOURCE), *args],
                capture_output=True, text=True, timeout=10, check=True,
            )
            self.assertTrue(result.stdout.strip())
            if "--json" in args:
                self.assertEqual(json.loads(result.stdout)["schema"], "eco-shaggoth/cl1-spatial-v1")
            else:
                self.assertIn("SHAGGOTH", result.stdout)


if __name__ == "__main__":
    unittest.main()
