"""CL1-AURA interactive terminal click regressions: offline, no dependencies."""
from __future__ import annotations

import curses
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from cl1_aura_mouse import footer_targets, hit_test, parse_sgr_mouse, try_read_sgr_mouse

spec = importlib.util.spec_from_file_location("aura_eco_shaggoth", SCRIPTS / "eco_shaggoth_cl1.py")
assert spec and spec.loader
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)


class Screen:
    def __init__(self, height=40, width=150, keys=()):
        self.height, self.width = height, width
        self.keys = iter(keys)
        self.timeouts = []

    def getmaxyx(self):
        return (self.height, self.width)

    def timeout(self, number):
        self.timeouts.append(number)

    def getch(self):
        return next(self.keys, -1)


class AuraMouseTests(unittest.TestCase):
    def setUp(self):
        self.screen = Screen()
        self.view = core.View()
        canvas = core.Canvas(150 - 58, 40 - 11)
        self.view.coords = core.draw_world(canvas, self.view)

    def hit(self, x, y):
        return hit_test(
            x, y, width=150, height=40, selected=self.view.selected,
            coords=self.view.coords, edges=core.EDGES,
            visible=core.visible_nodes(self.view), layers=core.LAYERS,
        )

    def test_click_spatial_node_and_label(self):
        x, y = self.view.coords["shaggoth"]
        hit = self.hit(26+x, 5+y)
        self.assertEqual(hit.action, "node")
        self.assertEqual(hit.target, "shaggoth")
        # Long label areas are clickable, not just one glyph.
        self.assertEqual(self.hit(26+x+4, 5+y).target, "shaggoth")

    def test_layer_and_telemetry_click_targets(self):
        self.assertEqual(self.hit(4, 7+4).target, "MUSIC")
        self.assertEqual(self.hit(12, 18).target, "ollama")
        self.assertEqual(self.hit(12, 19).target, "cl1")

    def test_inspector_link_selection(self):
        self.assertEqual(self.hit(121, 25).action, "node")
        self.assertIn(self.hit(121, 25).target, core.BY_ID)

    def test_footer_controls_match_printed_bounds(self):
        for left, right, label, action in footer_targets():
            self.assertEqual(self.hit(left, 37).action, action, label)
            self.assertEqual(right-left, len(label))
        self.assertIsNone(self.hit(0, 0))

    def test_click_actions_change_real_view(self):
        x, y = self.view.coords["kraken"]
        self.assertTrue(core.aura_mouse_event(
            self.view, 26+x, 5+y, curses.BUTTON1_PRESSED, self.screen
        ))
        self.assertEqual(self.view.selected, "kraken")
        self.assertGreater(self.view.aura_events, 0)
        self.assertTrue(core.aura_mouse_event(
            self.view, 5, 11, curses.BUTTON1_PRESSED, self.screen
        ))
        self.assertEqual(self.view.layer, "MUSIC")

    def test_footer_zoom_and_scan(self):
        footer = {action: left for left, right, label, action in footer_targets()}
        zoom = self.view.zoom
        core.aura_mouse_event(self.view, footer["zoom_in"], 37, curses.BUTTON1_PRESSED, self.screen)
        self.assertGreater(self.view.zoom, zoom)
        core.aura_mouse_event(self.view, footer["scan"], 37, curses.BUTTON1_PRESSED, self.screen)
        self.assertTrue(self.view.aura_rescan)

    def test_mouse_wheel_zoom(self):
        zoom = self.view.zoom
        core.aura_mouse_event(self.view, 80, 15, curses.BUTTON4_PRESSED, self.screen)
        self.assertGreater(self.view.zoom, zoom)
        core.aura_mouse_event(self.view, 80, 15, 65, self.screen, sgr=True)
        self.assertLess(self.view.zoom, 1.1)

    def test_raw_mouse_drag_orbits(self):
        yaw = self.view.yaw
        core.aura_mouse_event(self.view, 88, 17, 0, self.screen, sgr=True, pressed=True)
        core.aura_mouse_event(self.view, 98, 22, 32, self.screen, sgr=True, pressed=True)
        self.assertNotEqual(self.view.yaw, yaw)
        core.aura_mouse_event(self.view, 98, 22, 0, self.screen, sgr=True, pressed=False)
        self.assertIsNone(self.view.aura_drag)

    def test_sgr_decoding_and_rejection(self):
        self.assertEqual(parse_sgr_mouse("\x1b[<0;88;21M"), (87, 20, 0, True))
        self.assertEqual(parse_sgr_mouse("\x1b[<0;88;21m"), (87, 20, 0, False))
        self.assertEqual(parse_sgr_mouse("\x1b[<64;100;25M"), (99, 24, 64, True))
        for text in ("\x1b[<0;0;1M", "\x1b[<0;99999;1M",
                     "\x1b[<0;80;30", "evil", "\x1b[<abc;1;1M"):
            self.assertIsNone(parse_sgr_mouse(text))

    def test_sgr_fallback_is_bounded_and_restores_timeout(self):
        screen = Screen(keys=[ord(x) for x in "[<0;88;21M"])
        self.assertEqual(try_read_sgr_mouse(screen), (87, 20, 0, True))
        self.assertEqual(screen.timeouts, [25, 0])

    def test_mouse_restrictions_dont_mutate_system(self):
        with patch.object(core.socket, "create_connection",
                          side_effect=AssertionError("unexpected network")):
            self.view.aura_rescan = False
            core.aura_mouse_event(
                self.view, 4, 7+1, curses.BUTTON1_PRESSED, self.screen
            )
        self.assertEqual(self.view.layer, "CORE")
        self.assertFalse(self.view.aura_rescan)


if __name__ == "__main__":
    unittest.main()
