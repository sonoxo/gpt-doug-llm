"""Ontology provenance and model coverage checks."""
import json
import tempfile
import unittest
from pathlib import Path

from universal_watchdog.core import Watchtower


class OntologyTests(unittest.TestCase):
    def test_graph_contains_only_registered_models(self):
        with tempfile.TemporaryDirectory() as d:
            engine = Watchtower(Path(d) / 'watchtower.db', b'A' * 32,
                                external_stop_checker=lambda: {'stopped': False})
            graph = engine.ontology()
            self.assertEqual(graph['nodes'][0]['id'], 'xunia-watchtower')
            self.assertEqual(len(graph['edges']), 0)
            engine.register({'model_id':'sample','provider':'other-ai','agent_id':'sample-agent'})
            graph = engine.ontology()
            self.assertEqual(len(graph['nodes']), 2)
            self.assertEqual(graph['nodes'][1]['status'], 'registered_not_necessarily_online')
            self.assertEqual(graph['edges'][0]['relationship'], 'requires_approval_before_action')
            engine.store.close()

    def test_static_ontology_matches_declared_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root/'docs/watchtower/ontology.json').read_text())
        self.assertEqual(data['schema'], 'xunia.watchtower.ontology.v1')
        self.assertTrue(all(node['status'] != 'live_remote_control' for node in data['nodes']))
        for name in ('index.html','app.js','style.css','demo.json','ontology.json'):
            self.assertEqual((root/'docs/watchtower'/name).read_bytes(),(root/'universal_watchdog/static'/name).read_bytes())

if __name__ == '__main__':
    unittest.main()
