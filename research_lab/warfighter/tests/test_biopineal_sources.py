"""Evidence-only USPTO/Vendor source segregation for BioPINEAL."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from research_lab.warfighter import biopineal_sources
from research_lab.warfighter.cli import main

SOURCE_FILE = Path(__file__).resolve().parents[3] / 'intel' / 'sources' / 'biopineal-2026-10-12-public-evidence.json'


class TestBioPinealSources(unittest.TestCase):
    def test_two_independent_credible_source_categories(self):
        sources = biopineal_sources.load_sources()
        self.assertEqual(sources['ontology_namespace'], 'GPT_DOUG_BIOPINEAL_RESEARCH_SOURCES_V1')
        self.assertEqual(sources['authority'], 'RESEARCH_ONLY')
        self.assertEqual(len(sources['records']), 2)
        by_topic = {r['topic']:r for r in sources['records']}
        self.assertEqual(set(by_topic), {'bioassimilating_polymers', 'biological_computing'})
        patent = by_topic['bioassimilating_polymers']
        self.assertEqual(patent['document_number'], 'US-20260308339-A1')
        self.assertEqual(patent['record_kind'], 'PUBLISHED_APPLICATION')
        self.assertEqual(patent['patent_grant_verified'], False)
        self.assertEqual(patent['assignee'], 'SMART PLASTIC TECHNOLOGIES, LLC')
        self.assertEqual(patent['source_capture_sha256'], 'fd01488625510df8bb52e0d27eb88e63c99fa0759ea0471b828ec3270ad5bfc9')
        self.assertEqual(patent['relationship_to_biopineal'], 'MATERIALS_SCIENCE_REFERENCE_ONLY')
        self.assertFalse(patent['has_neural_biochip_claims'])
        self.assertFalse(patent['cortical_labs_associated'])
        neuron = by_topic['biological_computing']
        self.assertEqual(neuron['publisher'], 'Cortical Labs')
        self.assertEqual(neuron['source_url'], 'https://www.corticallabs.com/cl1.html')
        self.assertEqual(neuron['record_kind'], 'FIRST_PARTY_VENDOR_REFERENCE')
        self.assertFalse(neuron['connected_to_local_hardware'])
        self.assertFalse(neuron['associated_with_patent'])
        self.assertEqual(neuron['evidence_state'], 'VENDOR_CLAIMS_NOT_INDEPENDENTLY_VALIDATED')

    def test_source_search_does_not_conflate_patent_with_cortical_labs(self):
        result = biopineal_sources.search_sources(query='cortical labs')
        self.assertEqual(len(result['records']), 1)
        self.assertEqual(result['records'][0]['topic'], 'biological_computing')
        self.assertEqual(result['authority'], 'RESEARCH_ONLY')
        patent = biopineal_sources.search_sources(query='20260308339')
        self.assertEqual(len(patent['records']), 1)
        self.assertEqual(patent['records'][0]['topic'], 'bioassimilating_polymers')
        self.assertEqual(len(biopineal_sources.search_sources(topic='bioassimilating_polymers')['records']), 1)
        self.assertEqual(len(biopineal_sources.search_sources(query='nonexistent')['records']), 0)

    def test_registry_is_read_only_and_provenance_hashed(self):
        before = SOURCE_FILE.read_bytes()
        result = biopineal_sources.search_sources()
        self.assertEqual(before, SOURCE_FILE.read_bytes())
        self.assertRegex(result['registry_sha256'], r'\A[0-9a-f]{64}\Z')
        self.assertEqual(result['external_calls'], 0)
        self.assertFalse(result['automated_publication'])
        self.assertFalse(result['hardware_connected'])
        for record in result['records']:
            self.assertRegex(record['record_sha256'], r'\A[0-9a-f]{64}\Z')
            self.assertEqual(record['authority'], 'RESEARCH_ONLY')
            self.assertFalse(record['scientific_claims_verified'])

    def test_tampered_publisher_or_elevated_scope_rejected(self):
        original = json.loads(SOURCE_FILE.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'bad.json'
            for mutation in (
                lambda data: data['records'][0].update(publisher='Cortical Labs'),
                lambda data: data['records'][0].update(cortical_labs_associated=True),
                lambda data: data['records'][0].update(has_neural_biochip_claims=True),
                lambda data: data['records'][0].update(patent_grant_verified=True),
                lambda data: data.update(authority='OPERATIONAL'),
                lambda data: data['records'][1].update(connected_to_local_hardware=True),
                lambda data: data['records'][1].update(associated_with_patent=True),
                lambda data: data['records'][1].update(evidence_state='VERIFIED_LAB_RESULTS'),
                lambda data: data['records'][0].update(secret='do-not-copy'),
            ):
                data = json.loads(json.dumps(original))
                mutation(data)
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.subTest(mutation=mutation):
                    with self.assertRaises(ValueError):
                        biopineal_sources.load_sources(path)

    def test_content_replacement_requires_versioned_source_update(self):
        data = json.loads(SOURCE_FILE.read_text(encoding='utf-8'))
        data['records'][0]['claims'][0] = 'Cortical Labs owns the patent and BioPINEAL has a real wetware interface.'
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'forged.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'pinned|integrity|digest'):
                biopineal_sources.load_sources(path)

    def test_invalid_source_file_size_query_and_symlink_rejected(self):
        with self.assertRaises(ValueError):
            biopineal_sources.search_sources(query='\x1b[31m')
        with self.assertRaises(ValueError):
            biopineal_sources.search_sources(query='x'*129)
        with self.assertRaises(ValueError):
            biopineal_sources.search_sources(topic='targeting')
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'source.json'
            target.write_bytes(b' ' * 70000)
            with self.assertRaises(ValueError):
                biopineal_sources.load_sources(target)
            target.write_bytes(SOURCE_FILE.read_bytes())
            alias = Path(td) / 'alias.json'
            alias.symlink_to(target)
            with self.assertRaises(ValueError):
                biopineal_sources.load_sources(alias)

    def test_cli_biopineal_sources_read_only(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            result = main(['biopineal','sources','--query','20260308339'])
        self.assertEqual(result, 0)
        data = json.loads(stream.getvalue())
        self.assertEqual(len(data['records']), 1)
        self.assertEqual(data['records'][0]['topic'],'bioassimilating_polymers')
        self.assertEqual(data['external_calls'],0)
        self.assertEqual(data['authority'],'RESEARCH_ONLY')


if __name__ == '__main__':
    unittest.main()
