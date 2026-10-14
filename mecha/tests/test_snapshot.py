import copy
import json
import unittest

from mecha.snapshot import build_snapshot
from mecha.robotics import simulate_rover
from mecha.contracts import digest
from test_contracts import FIXTURE


class TestSnapshot(unittest.TestCase):
    def setUp(self):
        self.state=simulate_rover(FIXTURE)

    def test_six_channels_and_source_sha(self):
        s=build_snapshot(FIXTURE,self.state)
        self.assertEqual(s['schema_version'],'1.0.0')
        self.assertEqual(s['type'],'MechaSnapshot')
        self.assertEqual(s['system'],'GPT-DOUG-MECHA')
        self.assertEqual(s['source_sha256'],digest(FIXTURE))
        self.assertEqual(s['source_kind'],'SYNTHETIC')
        self.assertEqual(s['authority'],'RESEARCH_ONLY')
        self.assertEqual(set(s['channels']),{'x','y','z','time','memory','compute'})
        self.assertEqual(s['channels']['time']['simulated_step'],3)
        self.assertEqual(s['channels']['memory'],'SOURCE_LABELS_ONLY')
        self.assertEqual(s['channels']['compute'],'ABSTRACT_SIMULATION_OPERATIONS')
        self.assertEqual(s['channels']['x'],0.75)
        self.assertFalse(s['real_world_actuation'])
        self.assertFalse(s['quantum_hardware_used'])
        self.assertFalse(s['biological_hardware_connected'])

    def test_public_json_omits_untrusted_private_host_state(self):
        extra=copy.deepcopy(self.state)
        extra.update({'operator':'Agent10','home_path':'/Users/special/Downloads',
                      'token':'secret-password','private_notes':'sensitive'})
        text=json.dumps(build_snapshot(FIXTURE,extra))
        for secret in ('Agent10','/Users/','secret-password','sensitive','operator','token'):
            self.assertNotIn(secret,text)

    def test_refuses_untruthful_robot_actuation_or_status(self):
        bad=dict(self.state,REAL_WORLD_ACTUATION=True)
        with self.assertRaises(ValueError):build_snapshot(FIXTURE,bad)
        bad=dict(self.state,simulation_status='CONNECTED_REAL_ROVER')
        with self.assertRaises(ValueError):build_snapshot(FIXTURE,bad)

    def test_snapshot_rejects_state_from_different_source_fixture(self):
        different=copy.deepcopy(FIXTURE)
        different['robot']['pose']=[10.0,0.0,0.0]
        run=simulate_rover(different)
        with self.assertRaisesRegex(ValueError,'mismatch|fixture|source'):
            build_snapshot(FIXTURE,run)

    def test_snapshot_rejects_valid_but_tampered_state_metrics(self):
        altered=copy.deepcopy(self.state)
        altered['simulated_pose']=[0.5,0.0,0.0]
        with self.assertRaises(ValueError):build_snapshot(FIXTURE,altered)
        altered=copy.deepcopy(self.state)
        altered['simulation_status']='SIMULATED_OBSTACLE_HALT'
        with self.assertRaises(ValueError):build_snapshot(FIXTURE,altered)

    def test_snapshot_uses_requested_step_count_when_verifying(self):
        short=simulate_rover(FIXTURE,steps=1)
        snap=build_snapshot(FIXTURE,short)
        self.assertEqual(snap['channels']['time']['simulated_step'],1)
        self.assertEqual(short['requested_steps'],1)
        self.assertEqual(short['source_sha256'],digest(FIXTURE))

    def test_determinism_and_immutability(self):
        state=copy.deepcopy(self.state)
        a=build_snapshot(FIXTURE,state)
        self.assertEqual(a,build_snapshot(dict(reversed(list(FIXTURE.items()))),state))
        self.assertEqual(state,self.state)
        self.assertLess(len(json.dumps(a)),1024*1024)


if __name__=='__main__':unittest.main()
