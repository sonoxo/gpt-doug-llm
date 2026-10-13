import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from research_lab.warfighter.fixtures import canonical_json, digest, validate_scenario, load_scenario

ROOT=Path(__file__).resolve().parents[1]

class TestFixtures(unittest.TestCase):
    def setUp(self):
        self.demo=json.loads((ROOT/'examples/synthetic_training_defense.json').read_text())

    def test_golden_input_and_digest(self):
        self.assertEqual(self.demo['fixture']['training_readiness_pct'],68)
        self.assertEqual(self.demo['fixture']['patch_compliance_pct'],74)
        self.assertEqual(self.demo['fixture']['sensor_health_pct'],91)
        self.assertEqual(validate_scenario(self.demo)['seed'],0)
        self.assertEqual(digest(self.demo),digest(dict(reversed(list(self.demo.items())))))

    def test_reject_untrusted_source_and_invalid_metrics(self):
        for changes in [ {'synthetic':False,'classification':'PUBLIC'},
                         {'classification':'CUI'}, {'password':'oops'},
                         {'fixture':{'targeting':12}},
                         {'fixture':{'patch_compliance_pct':True}},
                         {'fixture':{'patch_compliance_pct':101}},
                         {'fixture':{'patch_compliance_pct':math.inf}},
                         {'seed':True}, {'seed':-1} ]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                validate_scenario(dict(self.demo,**changes))

    def test_reject_invalid_json_and_symlinks_and_large_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            good=root/'fixture.json'
            good.write_text(json.dumps(self.demo))
            self.assertEqual(load_scenario(good,allowed_root=root)['seed'],0)
            (root/'big.json').write_text(' '*(65537))
            (root/'notjson.json').write_text('{ no }')
            (root/'unicode.json').write_bytes(b'\xff\xfe')
            for path in (root/'big.json',root/'notjson.json',root/'unicode.json'):
                with self.subTest(path=path),self.assertRaises(ValueError):
                    load_scenario(path,allowed_root=root)
            (root/'link.json').symlink_to(good)
            with self.assertRaises(ValueError):
                load_scenario(root/'link.json',allowed_root=root)
            with self.assertRaises(ValueError):
                load_scenario(root/'../outside.json',allowed_root=root)

class TestCanonical(unittest.TestCase):
    def test_reject_nan(self):
        with self.assertRaises(ValueError):
            canonical_json({'v':float('nan')})
