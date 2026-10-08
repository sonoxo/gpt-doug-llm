import unittest

from shaggoth_swarm.visual import build_visual_data, render_visual_dashboard


class VisualDataLayerTests(unittest.TestCase):
    def test_visual_payload_contains_all_atomic_layers(self):
        payload = build_visual_data()
        self.assertEqual(payload["atomic"]["layer_count"], 8)
        self.assertEqual(len(payload["atomic"]["layers"]), 8)
        self.assertTrue(payload["atomic"]["valid"])

    def test_visual_payload_contains_runtime_and_capability_metrics(self):
        payload = build_visual_data()
        self.assertEqual(payload["runtime"]["agent_capacity"], 100)
        self.assertGreaterEqual(payload["capabilities"]["total"], payload["capabilities"]["enabled"])
        self.assertEqual(set(payload["capabilities"]["by_risk"]), {"low", "medium", "high"})

    def test_every_layer_has_visual_metrics(self):
        payload = build_visual_data()
        for layer in payload["atomic"]["layers"]:
            self.assertTrue(layer["metrics"], layer["name"])

    def test_dashboard_is_self_contained_and_points_to_visual_data(self):
        html = render_visual_dashboard()
        self.assertIn("SHAGGOTH // VISUAL DATA LAYERS", html)
        self.assertIn('fetch("/visual/data"', html)
        self.assertNotIn("https://", html)
        self.assertNotIn("<script src=", html)


if __name__ == "__main__":
    unittest.main()
