"""Offline behavioral and security checks for bounded public YouTube retrieval."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_lab import youtube_short_ingest as mod


class URLSafety(unittest.TestCase):
    def test_shorts(self):
        self.assertEqual(mod.parse_video_id('https://www.youtube.com/shorts/eNIFAcuEFVU?feature=share'), mod.VIDEO_ID)

    def test_watch(self):
        self.assertEqual(mod.parse_video_id('https://youtube.com/watch?v=eNIFAcuEFVU'), mod.VIDEO_ID)

    def test_youtu_be(self):
        self.assertEqual(mod.parse_video_id('https://youtu.be/eNIFAcuEFVU'), mod.VIDEO_ID)

    def test_embed(self):
        self.assertEqual(mod.parse_video_id('https://www.youtube.com/embed/eNIFAcuEFVU'), mod.VIDEO_ID)

    def test_reject_non_public_host(self):
        values = [
            'https://youtube.com.evil.test/watch?v=eNIFAcuEFVU',
            'http://www.youtube.com/watch?v=eNIFAcuEFVU',
            'https://www.youtube.com:444/watch?v=eNIFAcuEFVU',
            'https://user@www.youtube.com/watch?v=eNIFAcuEFVU',
            'https://127.0.0.1/watch?v=eNIFAcuEFVU',
            'https://www.youtube.com/watch?v=eNIFAcuEFVU&v=AAAAAAAAAAA',
            'https://www.youtube.com/channel/eNIFAcuEFVU',
            'https://youtu.be/eNIFAcuEFVU/path',
            'https://youtube.com/watch?v=eNIFAcuEFVU%2F',
        ]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                mod.parse_video_id(value)

    def test_bounded_id(self):
        self.assertEqual(len(mod.parse_video_id(mod.DEFAULT_VIDEO)), 11)
        with self.assertRaises(ValueError):
            mod.parse_video_id(mod.DEFAULT_VIDEO + 'x'*500)

    def test_caption_url_allowlist(self):
        self.assertTrue(mod.allowed_resource_url('https://www.youtube.com/api/timedtext?foo=1'))
        self.assertTrue(mod.allowed_resource_url('https://r1.googlevideo.com/videoplayback'))
        self.assertTrue(mod.allowed_resource_url('https://i.ytimg.com/vi/eNIFAcuEFVU/hqdefault.jpg'))
        for value in ('http://www.youtube.com/api/timedtext',
                      'https://evil.youtube.com.evil.net/videoplayback',
                      'https://localhost/private',
                      'https://169.254.169.254/latest/meta-data',
                      'https://user@www.youtube.com/api/timedtext'):
            self.assertFalse(mod.allowed_resource_url(value))

    def test_oembed_allowlist(self):
        self.assertFalse(mod.allowed_resource_url('https://www.youtube.com/api/timedtext',oembed=False) is False)
        self.assertFalse(mod.allowed_resource_url('https://noembed.com/embed',oembed=True))


class EvidenceParsing(unittest.TestCase):
    def test_json3_captions(self):
        data=json.dumps({'events':[{'segs':[{'utf8':'Hello '},{'utf8':'world'}]},{'segs':[{'utf8':'code shown'}]}]}).encode()
        self.assertEqual(mod.parse_captions(data, 'json3'), 'Hello world\ncode shown')

    def test_malformed_json3_fails_closed(self):
        self.assertEqual(mod.parse_captions(b'not json','json3'), '')

    def test_webvtt_captions(self):
        data=b'WEBVTT\n\n00:00:00.500 --> 00:00:02.000\n<em>Hello</em>\n\n00:00:02.000 --> 00:00:04.000\nworld\n'
        self.assertEqual(mod.parse_captions(data,'vtt'),'Hello\nworld')

    def test_creator_caption_priority(self):
        info={'subtitles':{'en':[{'ext':'vtt','url':'https://www.youtube.com/api/timedtext?a=1'}]},
              'automatic_captions':{'en':[{'ext':'json3','url':'https://www.youtube.com/api/timedtext?a=2'}]}}
        self.assertEqual(mod.select_caption_track(info)[0],'creator')

    def test_reject_untrusted_caption_track(self):
        info={'subtitles':{'en':[{'ext':'vtt','url':'http://evil.local/metadata'}]}}
        self.assertIsNone(mod.select_caption_track(info))

    def test_normalize_strips_provider_data(self):
        info={'title':'Actual short ','description':'x'*7000,'uploader':'channel','duration':14,'cookie':'SECRET','formats':[{'url':'https://example.com/?signed=SECRET'}]}
        output=mod.normalize(info,mod.VIDEO_ID,'yt_dlp_public')
        self.assertNotIn('cookie',output)
        self.assertNotIn('SECRET',json.dumps(output))
        self.assertEqual(output['title'],'Actual short')
        self.assertEqual(len(output['description']),mod.MAX_DESCRIPTION_CHARS)

    def test_frame_skipped_without_duration(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(mod.extract_frames(mod.VIDEO_ID,{},Path(d))['status'],'SKIPPED_DURATION_UNVERIFIED')

    def test_full_capture_with_subtitles_and_digest(self):
        info={'id':mod.VIDEO_ID,'title':'Verified robotics demonstration','uploader':'Demo creator',
              'description':'Explains the prototype','duration':30,
              'automatic_captions':{'en':[{'ext':'json3','url':'https://www.youtube.com/api/timedtext?lang=en'}]}}
        subs=json.dumps({'events':[{'segs':[{'utf8':'Sample walkthrough'}]}]}).encode()
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,'get_yt_dlp_info',return_value=info), \
            patch.object(mod,'read_public',return_value=subs):
            report=mod.inspect(mod.DEFAULT_VIDEO,Path(d))
            self.assertEqual(report['capture_status'],'TRANSCRIPT_CAPTURED')
            self.assertEqual(report['merge_decision'],'REVIEW_REQUIRED__NO_CODE_MERGED')
            self.assertTrue(mod.verify_report(Path(d)/'report.json'))
            self.assertEqual((Path(d)/'transcript.txt').read_text(),'Sample walkthrough')
            self.assertEqual(report['transcript_sha256'],hashlib.sha256(b'Sample walkthrough').hexdigest())

    def test_public_poster_is_validated_and_hashed(self):
        data = b"\xff\xd8\xff" + b"a" * 1024
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,'get_yt_dlp_info', side_effect=RuntimeError('network')), \
            patch.object(mod,'oembed', return_value=mod.normalize({'title':'Demo'},mod.VIDEO_ID,'youtube_oembed')), \
            patch.object(mod,'read_public', return_value=data):
            report=mod.inspect(mod.DEFAULT_VIDEO,Path(d),poster=True)
            self.assertEqual(report['poster']['status'],'CAPTURED')
            self.assertEqual((Path(d)/'poster.jpg').read_bytes(),data)
            self.assertTrue(mod.verify_report(Path(d)/'report.json'))

    def test_rejects_fake_poster(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,'get_yt_dlp_info', side_effect=RuntimeError('network')), \
            patch.object(mod,'oembed', return_value=mod.normalize({'title':'Demo'},mod.VIDEO_ID,'youtube_oembed')), \
            patch.object(mod,'read_public',return_value=b'<html>fake</html>'):
            report=mod.inspect(mod.DEFAULT_VIDEO,Path(d),poster=True)
            self.assertEqual(report['poster']['status'],'UNAVAILABLE')
            self.assertFalse((Path(d)/'poster.jpg').exists())

    def test_metadata_only_fallback(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,'get_yt_dlp_info',side_effect=RuntimeError('blocked')), \
            patch.object(mod,'oembed',return_value=mod.normalize({'title':'Oembed title'},mod.VIDEO_ID,'youtube_oembed')):
            report=mod.inspect(mod.DEFAULT_VIDEO,Path(d))
            self.assertEqual(report['capture_status'],'METADATA_ONLY')
            self.assertIsNone(report['transcript_sha256'])
            self.assertIn('youtube_oembed',report['sources_attempted'])

    def test_total_unavailability_never_invents_content(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,'get_yt_dlp_info',side_effect=RuntimeError('network unavailable')), \
            patch.object(mod,'oembed',side_effect=RuntimeError('network unavailable')):
            report=mod.inspect(mod.DEFAULT_VIDEO,Path(d),frames=True)
            self.assertEqual(report['capture_status'],'UNVERIFIED')
            self.assertEqual(report['metadata']['source'],'unverified_url_only')
            self.assertEqual(report['metadata']['title'],'')
            self.assertEqual(report['frames']['count'],0)

    def test_report_tampering_detected(self):
        with tempfile.TemporaryDirectory() as d, \
            patch.object(mod,'get_yt_dlp_info',side_effect=RuntimeError('offline')), \
            patch.object(mod,'oembed',side_effect=RuntimeError('offline')):
            mod.inspect(mod.DEFAULT_VIDEO,Path(d))
            p=Path(d)/'report.json'
            obj=json.loads(p.read_text())
            obj['merge_decision']='MERGED'
            p.write_text(json.dumps(obj))
            self.assertFalse(mod.verify_report(p))


if __name__=='__main__':
    unittest.main()
