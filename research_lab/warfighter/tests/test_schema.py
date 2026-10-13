import copy
import hashlib
import json
import unittest
from pathlib import Path

from research_lab.warfighter.schema import load_schema, validate_record, validate_graph


def record(kind, ident):
    payload = {
        'id': 'wr:' + kind.lower() + ':' + ident,
        'schema_version': '1.0.0', 'type': kind,
        'source_kind': 'SYNTHETIC', 'classification': 'SYNTHETIC',
        'synthetic': True, 'created_at': '2026-10-12T17:00:00+00:00',
        'provenance': 'synthetic-fixture', 'source_refs': ['fixture:demo'],
        'evidence_status': 'COMPUTED_UNVERIFIED',
        'confidence_scope': 'mathematical-toy-model',
        'record_sha256': '0' * 64,
    }
    return payload


class TestSchema(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()

    def test_public_contract_and_type_count(self):
        self.assertEqual(self.schema['ontology_id'], 'WARFIGHTER_RESEARCH_V1')
        self.assertEqual(self.schema['authority'], 'RESEARCH_ONLY')
        self.assertEqual(len(self.schema['object_types']), 21)
        self.assertEqual(len(self.schema['edge_types']), 16)
        self.assertIn('ResearchScenario', self.schema['object_types'])

    def test_record_with_required_kind_fields(self):
        item = record('MathCertificate', 'c1')
        item.update(run_ref='wr:simulationrun:r1', certificate_kind='exact',
                    verification_method='replay', check_status='VERIFIED_FOR_MODEL')
        self.assertEqual(validate_record(item, self.schema)['type'], 'MathCertificate')

    def test_provenance_and_classification_fail_closed(self):
        item = record('MathCertificate', 'c1')
        item.update(run_ref='wr:simulationrun:r1', certificate_kind='exact',
                    verification_method='replay', check_status='VERIFIED_FOR_MODEL')
        for edit in [{'synthetic': False, 'classification': 'PUBLIC'},
                     {'classification': 'CUI'}, {'password': 'unsafe'},
                     {'created_at': '2026-12-99'}, {'record_sha256': 'not-hex'},
                     {'source_refs': []}]:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                validate_record(dict(item, **edit), self.schema)

    def test_edge_types_and_no_dangling_ids(self):
        a = record('ResearchEvidence', 'e1')
        a.update(run_ref='wr:simulationrun:r1', certificate_refs=['wr:mathcertificate:c1'],
                 claim_text='Toy-model equality held', scope_of_claim='toy-only',
                 limitations='not operational')
        b = record('MathCertificate', 'c1')
        b.update(run_ref='wr:simulationrun:r1', certificate_kind='exact',
                 verification_method='replay', check_status='VERIFIED_FOR_MODEL')
        edge = {'from': a['id'], 'predicate': 'SUPPORTED_BY', 'to': b['id']}
        validate_graph([a, b], [edge], self.schema)
        with self.assertRaises(ValueError):
            validate_graph([a, b], [dict(edge, to='wr:unknown:missing')], self.schema)
        with self.assertRaises(ValueError):
            validate_graph([a, b], [dict(edge, predicate='AUTHORIZED_BY')], self.schema)
        with self.assertRaises(ValueError):
            validate_graph([a, a], [], self.schema)
        with self.assertRaises(ValueError):
            validate_graph([b] * 101, [], self.schema)
        with self.assertRaises(ValueError):
            validate_graph([a, b], [edge] * 501, self.schema)
