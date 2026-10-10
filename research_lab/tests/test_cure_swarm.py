"""Offline evidence-safety and metadata-normalization checks."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_lab import cure_swarm as c

ROOT = Path(__file__).resolve().parents[2]


def trial_api():
    return {"studies": [{"protocolSection": {
        "identificationModule":{"nctId":"NCT12345678", "briefTitle":"Example trial title"},
        "statusModule":{"overallStatus":"RECRUITING", "hasResults":False,
                        "lastUpdatePostDateStruct":{"date":"2026-09-30"}},
        "designModule":{"studyType":"INTERVENTIONAL", "phases":["PHASE2"],
                        "designInfo":{"allocation":"RANDOMIZED"}}}}]}


def paper_api():
    return {"resultList":{"result":[{"source":"MED", "id":"98765432",
        "title":"Example publication title", "pubType":"journal article",
        "isRetracted":"N", "firstPublicationDate":"2026-01-20"}]}}


class CureSwarmTests(unittest.TestCase):
    def test_offline_demo_never_certifies_a_cure(self):
        report=c.analyze(c.sample_snapshot())
        self.assertTrue(report['synthetic_demo'])
        self.assertEqual(report['status'],'EVIDENCE_CATALOG_REQUIRES_HUMAN_REVIEW')
        self.assertFalse(report['agents'][3]['clinical_benefit_validated'])
        self.assertEqual(report['agents'][3]['treatment_use'],'PROHIBITED')
        self.assertEqual(report['agents'][4]['agent_runtimes_started'],0)

    def test_all_five_roles_execute(self):
        report=c.analyze(c.sample_snapshot())
        self.assertEqual([a['role'] for a in report['agents']], [
            'GPT-Doug','GPT-Pineal','GPT-Doug-Chaos','GPT-Doug-Shaggoth','GPT-Doug-Redpanda'])
        self.assertEqual(report['counts'],{'studies':2,'publications':1,'total':3})
        self.assertEqual(len(report['research_questions']),3)

    def test_report_exact_replay(self):
        self.assertTrue(c.verify(c.analyze(c.sample_snapshot())))

    def test_hash_tampering_rejected(self):
        report=c.analyze(c.sample_snapshot())
        report['report_sha256']='0'*64
        self.assertFalse(c.verify(report))

    def test_evidence_tampering_rejected(self):
        report=c.analyze(c.sample_snapshot())
        report['evidence'][0]['review_flags']=[]
        self.assertFalse(c.verify(report))

    def test_fabricated_medical_claim_rejected(self):
        data=c.sample_snapshot()
        data['records'][0]['proven_cure']=True
        with self.assertRaises(ValueError): c.analyze(data)

    def test_secret_fields_rejected(self):
        data=c.sample_snapshot()
        data['records'][0]['api_key']='secret'
        with self.assertRaises(ValueError): c.analyze(data)

    def test_injected_patient_info_rejected(self):
        data=c.sample_snapshot()
        data['patient_name']='PRIVATE'
        with self.assertRaises(ValueError): c.analyze(data)

    def test_invalid_query_syntax_fails(self):
        for query in ['a', 'abc@provider.com', 'name@example.com','glioblastoma; DROP TABLE',
                      'x'*80, 123, 'three\nwords', 'ftp://test']:
            with self.subTest(query=query),self.assertRaises(ValueError):
                c.valid_query(query)

    def test_valid_topics(self):
        self.assertEqual(c.valid_query('  non small cell lung cancer  '),'non small cell lung cancer')
        self.assertEqual(c.valid_query('HER2-positive breast cancer'),'HER2-positive breast cancer')

    def test_too_many_records_rejected(self):
        data=c.sample_snapshot()
        data['records']=[{**data['records'][0], 'id':f'SIM-TRIAL-{i}'} for i in range(22)]
        with self.assertRaises(ValueError):c.analyze(data)

    def test_duplicate_id_rejected(self):
        data=c.sample_snapshot()
        data['records'].append(copy.deepcopy(data['records'][0]))
        with self.assertRaises(ValueError):c.analyze(data)

    def test_source_urls_are_canonical(self):
        data=c.sample_snapshot()
        data['records'][0]['url']='https://example.com'
        with self.assertRaises(ValueError):c.analyze(data)

    def test_source_spoofing_rejected(self):
        data=c.sample_snapshot()
        data['records'][0]['source']='ClinicalTrials.gov'
        with self.assertRaises(ValueError):c.analyze(data)

    def test_randomized_flag_rejects_nonboolean(self):
        data=c.sample_snapshot()
        data['records'][0]['randomized']='yes'
        with self.assertRaises(ValueError):c.analyze(data)

    def test_bad_pub_retraction_rejected(self):
        data=c.sample_snapshot()
        data['records'][2]['retracted']='uncertain'
        with self.assertRaises(ValueError):c.analyze(data)

    def test_preprint_not_accepted_as_clinical_proof(self):
        report=c.analyze(c.sample_snapshot())
        publication=next(x for x in report['evidence'] if x['kind']=='paper')
        self.assertIn('PREPRINT_NOT_CLINICALLY_VERIFIED',publication['review_flags'])

    def test_early_phase_flags(self):
        report=c.analyze(c.sample_snapshot())
        early=next(x for x in report['evidence'] if x['id']=='SIM-TRIAL-1')
        self.assertIn('EARLY_PHASE',early['review_flags'])
        self.assertIn('RESULTS_NOT_CONFIRMED',early['review_flags'])

    def test_retracted_publication_flag(self):
        data=c.sample_snapshot()
        data['records'][2]['retracted']=True
        report=c.analyze(data)
        publication=next(x for x in report['evidence'] if x['kind']=='paper')
        self.assertIn('RETRACTION_SIGNAL_REVIEW',publication['review_flags'])

    def test_terminated_trial_flag(self):
        data=c.sample_snapshot()
        data['records'][0]['status']='TERMINATED'
        report=c.analyze(data)
        early=next(x for x in report['evidence'] if x['id']=='SIM-TRIAL-1')
        self.assertIn('STATUS_REQUIRES_REVIEW',early['review_flags'])

    def test_empty_snapshot_allowed_but_not_efficacy(self):
        data=c.sample_snapshot()
        data['records']=[]
        report=c.analyze(data)
        self.assertEqual(report['counts']['total'],0)
        self.assertTrue(c.verify(report))
        self.assertTrue(report['agents'][3]['approval']=='REQUIRED')

    def test_order_independent_and_deterministic(self):
        data=c.sample_snapshot()
        a=c.analyze(data)
        data['records'].reverse()
        b=c.analyze(data)
        self.assertEqual(a,b)

    def test_trial_parser(self):
        out=c._trial_records(trial_api(),5)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['id'],'NCT12345678')
        self.assertFalse(out[0]['results_posted'])
        self.assertTrue(out[0]['randomized'])
        self.assertEqual(out[0]['updated'],'2026-09-30')

    def test_europepmc_parser(self):
        out=c._paper_records(paper_api(),3)
        self.assertEqual(out[0]['id'],'MED:98765432')
        self.assertFalse(out[0]['retracted'])
        self.assertEqual(out[0]['publication_type'],'journal article')

    def test_invalid_provider_shape_fails_closed(self):
        with self.assertRaises(ValueError):c._trial_records({},5)
        with self.assertRaises(ValueError):c._paper_records({},5)

    def test_live_fetch_uses_fixed_endpoints_only(self):
        links=[]
        def stub(url):
            links.append(url)
            if url.startswith(c.API_TRIALS+'?'):return trial_api()
            if url.startswith(c.API_PAPERS+'?'):return paper_api()
            raise AssertionError('unknown endpoint')
        data=c.fetch_public_snapshot('glioblastoma',2,stub)
        self.assertEqual(len(links),2)
        self.assertEqual(data['origin'],'public_api')
        self.assertEqual(c.analyze(data)['counts']['total'],2)
        self.assertEqual(data['records'][0]['source'],'Europe PMC')
        self.assertTrue(c.verify(c.analyze(data)))

    def test_live_source_outage_is_not_a_fake_empty_result(self):
        with self.assertRaises(ValueError):
            c.fetch_public_snapshot('glioblastoma',2,lambda _: {})

    def test_bad_online_batch_limits_rejected(self):
        for x in [0,11,True,'3']:
            with self.subTest(x=x),self.assertRaises(ValueError):
                c.fetch_public_snapshot('glioblastoma',x,lambda _: {})

    def test_default_demo_no_network(self):
        with patch.object(c,'_fetch_json',side_effect=AssertionError('network call')):
            report=c.analyze(c.sample_snapshot())
        self.assertEqual(report['origin'],'synthetic')

    def test_retraction_unknown_not_false(self):
        self.assertIsNone(c._retraction(None))
        self.assertIsNone(c._retraction('unknown'))

    def test_compare_is_audit_not_missing_claim(self):
        a=c.sample_snapshot()
        b=copy.deepcopy(a)
        b['records'][0]['status']='COMPLETED'
        b['records'].pop(1)
        out=c.compare_snapshots(a,b)
        self.assertEqual(out['changed_records'],[['trial','SIM-TRIAL-1']])
        self.assertEqual(out['not_in_new_bounded_page'],[['trial','SIM-TRIAL-2']])
        self.assertIn('does not mean',out['caveat'])

    def test_compare_rejects_mismatched_topic(self):
        a=c.sample_snapshot()
        b=copy.deepcopy(a)
        b['query']='lung cancer'
        with self.assertRaises(ValueError):c.compare_snapshots(a,b)

    def test_oversized_local_file_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/'too_big.json'
            file.write_text('x'*(c.MAX_INPUT_BYTES+1))
            with self.assertRaises(ValueError):c.load_json(file)

    def test_cli_offline_roundtrip_and_reject_tamper(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            input_file=root/'snapshot.json'
            report_file=root/'report.json'
            input_file.write_text(json.dumps(c.sample_snapshot()))
            run=subprocess.run([sys.executable,'-m','research_lab.cure_swarm','analyze',str(input_file)],
                cwd=str(ROOT),capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stderr)
            report_file.write_text(run.stdout)
            check=subprocess.run([sys.executable,'-m','research_lab.cure_swarm','verify',str(report_file)],
                cwd=str(ROOT),capture_output=True,text=True,timeout=15)
            self.assertEqual(check.returncode,0,check.stderr)
            report=json.loads(run.stdout)
            report['status']='CURE_PROVEN'
            report_file.write_text(json.dumps(report))
            check=subprocess.run([sys.executable,'-m','research_lab.cure_swarm','verify',str(report_file)],
                cwd=str(ROOT),capture_output=True,text=True,timeout=15)
            self.assertEqual(check.returncode,1)

    def test_cli_compare(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'demo.json'
            path.write_text(json.dumps(c.sample_snapshot()))
            cmd=[sys.executable,'-m','research_lab.cure_swarm','compare',str(path),str(path)]
            run=subprocess.run(cmd,cwd=str(ROOT),capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(run.stdout)['new_records'],[])


if __name__ == '__main__':
    unittest.main()
