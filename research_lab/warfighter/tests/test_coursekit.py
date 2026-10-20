"""Fail-closed Warfighter CourseKit security and behavior checks."""
import copy
import io
import json
import socket
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch
from research_lab.warfighter.coursekit import (
    command, fingerprint, grade, load_local_json, main, sources,
    validate_pack, validate_responses,
)

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'examples' / 'synthetic_coursekit_v1.json'
ANSWERS = ROOT / 'examples' / 'synthetic_responses_demo.json'


class TestCourseKit(unittest.TestCase):
    def setUp(self):
        self.pack = json.loads(PACK.read_text(encoding='utf-8'))
        self.answers = json.loads(ANSWERS.read_text(encoding='utf-8'))

    def test_valid_pack_golden_and_stable_digest(self):
        result = validate_pack(self.pack)
        self.assertEqual(len(result['items']), 10)
        self.assertEqual(fingerprint(result), fingerprint(dict(reversed(list(result.items())))))
        self.assertEqual(len(fingerprint(result)), 64)

    def test_reject_non_synthetic_or_extra_fields(self):
        for change in [dict(synthetic=False), dict(classification='PUBLIC'),
                       dict(classification='CUI'), dict(source_kind='DRIVE'),
                       dict(authority='OPERATIONAL'), dict(url='https://example.com')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_pack(dict(self.pack, **change))

    def test_reject_malicious_questions(self):
        bad = [dict(id='../../other'), dict(id='q001', domain='targeting'),
               dict(correct_choice=True), dict(correct_choice=6),
               dict(choices=['Yes', 'yes']), dict(prompt=''),
               dict(rationale='line\ncontrol')]
        for change in bad:
            course = copy.deepcopy(self.pack)
            course['items'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_pack(course)

    def test_reject_duplicate_question_and_short_pack(self):
        dup = copy.deepcopy(self.pack)
        dup['items'][1]['id'] = dup['items'][0]['id']
        with self.assertRaises(ValueError):
            validate_pack(dup)
        short = copy.deepcopy(self.pack)
        short['items'] = short['items'][:4]
        with self.assertRaises(ValueError):
            validate_pack(short)

    def test_grading_is_deterministic_and_not_operational(self):
        result = grade(self.pack, self.answers)
        self.assertEqual(result['correct'], 9)
        self.assertEqual(result['score_pct'], 90)
        self.assertEqual(result['answered'], 10)
        self.assertEqual(result['feedback'][2]['result'], 'REVIEW')
        self.assertFalse(result['operational_ready'])
        self.assertFalse(result['human_reviewed'])
        self.assertEqual(result['external_calls'], 0)
        self.assertEqual(result, grade(self.pack, self.answers))

    def test_unanswered_included_in_denominator(self):
        answers = dict(self.answers, responses={'q001': 1})
        result = grade(self.pack, answers)
        self.assertEqual(result['answered'], 1)
        self.assertEqual(result['score_pct'], 10)
        self.assertEqual(result['feedback'][1]['result'], 'UNANSWERED')

    def test_reject_wrong_course_unknown_answers_and_boolean(self):
        invalid = [dict(course_id='wr:course:other'),
                   dict(responses={'nope': 0}),
                   dict(responses={'q001': True}),
                   dict(responses={'q001': -1}),
                   dict(responses={'q001': 999}),
                   dict(responses=[]),
                   dict(role='admin')]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_responses(dict(self.answers, **change), self.pack)

    def test_local_file_caps_duplicate_json_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            good = root / 'pack.json'
            good.write_text(json.dumps(self.pack), encoding='utf-8')
            self.assertEqual(load_local_json(good, allowed_root=root), self.pack)
            invalid = {'dup.json': '{"a":1,"a":2}',
                       'nan.json': '{"a": NaN}',
                       'large.json': ' ' * 65537,
                       'bad.json': '{garbage'}
            for name, content in invalid.items():
                p = root / name
                p.write_text(content, encoding='utf-8')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    load_local_json(p, allowed_root=root)
            outside = root.parent / 'not-in-root.json'
            with self.assertRaises(ValueError):
                load_local_json(outside, allowed_root=root)
            link = root / 'link.json'
            try:
                link.symlink_to(good)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ValueError):
                    load_local_json(link, allowed_root=root)

    def test_source_slots_do_not_publish_cloud_links(self):
        result = sources()
        self.assertEqual(result['remote_folders_imported'], 0)
        self.assertEqual(result['source_slots'], 2)
        self.assertFalse(result['auto_drive_access'])
        self.assertNotIn('drive.google.com', json.dumps(result))

    def test_module_cli_and_no_network(self):
        stdout = io.StringIO()
        with patch.object(socket, 'socket', side_effect=AssertionError('network prohibited')):
            with redirect_stdout(stdout):
                result = main(['grade', '--pack', str(PACK), '--input-root', str(ROOT / 'examples'),
                               '--responses', str(ANSWERS)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())['score_pct'], 90)

    def test_cli_fails_closed(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(['grade', '--pack', str(PACK), '--input-root', str(ROOT / 'examples')])
        self.assertEqual(code, 2)
        self.assertIn('requires --responses', stderr.getvalue())

    def test_real_file_pack_validation(self):
        report = command('validate', pack=PACK, input_root=ROOT / 'examples')
        self.assertEqual(report['status'], 'VALID_SYNTHETIC_COURSE')
        self.assertEqual(report['question_count'], 10)


if __name__ == '__main__':
    unittest.main()
