import json
from pathlib import Path
import tempfile
import unittest

from va3lm.mission_ledger import MissionLedger
from va3lm.rvia import MissionEnvelope, RVIARouter
from va3lm.training_sources import ROOT, SOURCE_ID, load_training_source


class PriorityIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = MissionLedger(Path(self.tmp.name) / 'missions.db')
        self.router = RVIARouter(self.ledger)

    def mission(self, target='ZYRA', **kwargs):
        return MissionEnvelope(requestedBy='test', intent='Inspect status', target=target, **kwargs)

    def test_registered_source_produces_plan_and_durable_receipt(self):
        source = load_training_source()
        self.assertEqual(source['sourceId'], SOURCE_ID)
        result = self.router.route(self.mission(SOURCE_ID, classification='public'))
        self.assertEqual(result['status'], 'PLANNED')
        self.assertTrue(all(step['status'] == 'PLANNED' for step in result['mission']['result']['steps']))
        receipt = result['mission']['evidence'][-1]
        self.assertFalse(receipt['executionVerified'])
        self.assertEqual(self.ledger.get(receipt['missionId'])['envelope']['evidence'][-1], receipt)
        self.assertIn(SOURCE_ID, self.router.manifest()['targets'])

    def test_contract_acceptance_never_claims_remote_completion(self):
        for target in ('ZYRA', 'XUNIA', 'NXYZ', 'ZYRA_CLOUD'):
            result = self.router.route(self.mission(target))
            self.assertEqual(result['status'], 'ACCEPTED')
            self.assertFalse(result['mission']['evidence'][-1]['executionVerified'])

    def test_rejected_content_is_not_retained(self):
        mission = self.mission(SOURCE_ID, classification='classified', metadata={'content':'DO_NOT_RETAIN'})
        result = self.router.route(mission)
        self.assertEqual(result['status'], 'REJECTED')
        self.assertNotIn('DO_NOT_RETAIN', json.dumps(self.ledger.get(mission.missionId)))

    def test_adapter_exception_is_audited_failure(self):
        def fail(mission):
            raise RuntimeError('private diagnostic')
        self.router.register_handler('ZYRA', fail)
        result = self.router.route(self.mission())
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotIn('private diagnostic', json.dumps(result))
        self.assertEqual(self.ledger.timeline(result['mission']['missionId'])[-1]['eventType'], 'MISSION_FINALIZED')

    def test_source_vocabulary_maps_to_kernel(self):
        source = load_training_source()
        kernel = json.loads((ROOT / 'the-black-house/kernel/kernel.manifest.json').read_text())
        self.assertLessEqual(set(source['ontology']['objectTypeMap'].values()), set(kernel['objectTypes']))
        self.assertLessEqual(set(source['ontology']['relationshipMap'].values()), set(kernel['relationshipTypes']))

    def test_unknown_source_capability_fails_closed(self):
        result = self.router.route(self.mission(SOURCE_ID, classification='public', requiredCapabilities=['execution']))
        self.assertEqual(result['status'], 'REJECTED')


if __name__ == '__main__':
    unittest.main()
