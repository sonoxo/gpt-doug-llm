import copy
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from research_lab.warfighter.baseline import run_baseline
from research_lab.warfighter.artifact import build_run, source_hash
from research_lab.warfighter.verify import verify_run

DEMO=json.loads((Path(__file__).resolve().parents[1]/'examples/synthetic_training_defense.json').read_text())
NOW='2026-10-12T16:00:00+00:00'


def new_run():
    return build_run(run_id='wr:run:demo-1',scenario=DEMO,engine='baseline',
                     output=run_baseline(DEMO),code_sha256=source_hash('baseline'),
                     generated_at=NOW)

class TestEvidence(unittest.TestCase):
    def test_baseline_replays_and_hashes(self):
        r=new_run()
        self.assertEqual(len(r['run_sha256']),64)
        self.assertEqual(r['model']['implementation_sha256'],source_hash('baseline'))
        self.assertEqual(r['authority'],'RESEARCH_ONLY')
        self.assertEqual(r['publication']['status'],'QUARANTINED')
        self.assertEqual(verify_run(r)['status'],'VERIFIED_FOR_MODEL')
        self.assertEqual(r['output']['metrics']['patch_compliance_pct']['hypothetical'],79)

    def test_tampered_outputs_hashes_review_fields_fail(self):
        base=new_run()
        changes=[lambda x:x['output']['metrics']['patch_compliance_pct'].update(hypothetical=99),
                 lambda x:x['input'].update(seed=2),
                 lambda x:x['model'].update(implementation_sha256='0'*64),
                 lambda x:x['verification'].update(status='VERIFIED_FOR_MODEL'),
                 lambda x:x['publication'].update(status='PUBLISHED_RESEARCH_ONLY'),
                 lambda x:x.update(run_sha256='1'*64)]
        for mutate in changes:
            clone=copy.deepcopy(base)
            mutate(clone)
            with self.subTest(mutate=mutate):
                self.assertEqual(verify_run(clone)['status'],'FAILED')

    def test_fail_invalid_timestamp_or_code_hash(self):
        for timestamp in ('2026-13-35','2026-10-12T10:00:00',None):
            with self.subTest(timestamp=timestamp),self.assertRaises(ValueError):
                build_run(run_id='wr:run:r2',scenario=DEMO,engine='baseline',
                          output=run_baseline(DEMO),code_sha256=source_hash('baseline'),
                          generated_at=timestamp)
        with self.assertRaises(ValueError):
            build_run(run_id='wr:run:r2',scenario=DEMO,engine='baseline',output=run_baseline(DEMO),
                      code_sha256='0'*64,generated_at=NOW)

    def test_rehashed_output_cannot_change_undeclared_model_assumptions(self):
        from research_lab.warfighter.fixtures import digest
        from research_lab.warfighter.artifact import run_digest
        r=new_run()
        altered=run_baseline(DEMO,what_if_delta=10)
        r['output']=altered
        r['output_sha256']=digest(altered)
        r['run_sha256']=run_digest(r)
        self.assertEqual(verify_run(r)['status'],'FAILED')

    def test_model_cannot_be_authoritative_by_rehashing(self):
        clone=new_run()
        clone['authority']='OPERATIONAL'
        self.assertEqual(verify_run(clone)['status'],'FAILED')
