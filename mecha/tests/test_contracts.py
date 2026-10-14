import copy
import json
import tempfile
import unittest
from pathlib import Path

from mecha.contracts import validate_fixture, digest
from mecha.fixtures import load_fixture


FIXTURE = {
    'schema_version': '1.0.0', 'type': 'MechaExercise',
    'source_kind': 'SYNTHETIC', 'authority': 'RESEARCH_ONLY',
    'mode': 'OFFLINE_ROBOTICS_DEMO', 'synthetic': True, 'seed': 0,
    'robot': {'id':'rover-1', 'class':'INDUSTRIAL_INSPECTION_ROVER',
              'pose':[0.0, 0.0, 0.0], 'health_pct':91, 'power_budget_units':100},
    'environment': {'terrain':'SYNTHETIC_FLAT', 'obstacles':[]},
    'assumptions':['Invented and non-operational exercise only'],
}


class TestContract(unittest.TestCase):
    def test_valid_schema_and_canonical_digest(self):
        expected = validate_fixture(FIXTURE)
        self.assertEqual(expected, FIXTURE)
        self.assertEqual(len(digest(FIXTURE)), 64)
        self.assertEqual(digest(FIXTURE), digest(dict(reversed(list(FIXTURE.items())))))

    def test_unknown_and_privileged_fields_rejected(self):
        for bad in ('operator', 'credential', 'motor_command', 'gps_route',
                    'target_coordinates', 'endpoint', 'write_capability', 'classification'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_fixture(dict(FIXTURE, **{bad:'Agent10'}))

    def test_non_synthetic_and_secret_rejected(self):
        for field,value in [('source_kind','LIVE'),('authority','OPERATIONAL'),
                            ('synthetic',False),('mode','REAL_ROBOT'),('type','RobotCommand')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_fixture(dict(FIXTURE, **{field:value}))

    def test_robot_boundary_and_types_rejected(self):
        for key,value in [('health_pct', True),('health_pct',101),
                          ('pose',[float('nan'),0,0]),('pose',[1000,0,0]),
                          ('pose',[0,0]),('power_budget_units',0),
                          ('class','ARMED_DRONE'),('motor_command',10)]:
            bad=copy.deepcopy(FIXTURE);bad['robot'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                validate_fixture(bad)

    def test_obstacles_and_assumptions_bounded(self):
        for obstacles in ([[0,0,0]]*51, [[float('inf'),0,0]], [[0,0]], ['x']):
            bad=copy.deepcopy(FIXTURE);bad['environment']['obstacles']=obstacles
            with self.subTest(obstacles=repr(obstacles)[:30]),self.assertRaises(ValueError):
                validate_fixture(bad)
        bad=dict(FIXTURE,assumptions=['\x1b[0m'])
        with self.assertRaises(ValueError):validate_fixture(bad)

    def test_local_loader_rejects_symlink_escape_and_oversize(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); allowed=root/'allowed';allowed.mkdir()
            valid=allowed/'fixture.json';valid.write_text(json.dumps(FIXTURE))
            self.assertEqual(load_fixture(valid,input_root=allowed),FIXTURE)
            other=root/'other.json';other.write_text(json.dumps(FIXTURE))
            (allowed/'link.json').symlink_to(other)
            with self.assertRaises(ValueError):load_fixture(allowed/'link.json',input_root=allowed)
            with self.assertRaises(ValueError):load_fixture(other,input_root=allowed)
            too_big=allowed/'huge.json';too_big.write_text(' '*65537)
            with self.assertRaises(ValueError):load_fixture(too_big,input_root=allowed)
            (allowed/'nested').symlink_to(root,target_is_directory=True)
            with self.assertRaises(ValueError):load_fixture(allowed/'nested'/'other.json',input_root=allowed)


if __name__=='__main__':unittest.main()
