"""Original 087: Naver Cafe official API preflight is OFFLINE ONLY."""
import json
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_schedule import parse_reference
from ai_broadcaster.offline_naver_cafe_review import review_naver_cafe_official_link
from ai_broadcaster.offline_prebroadcast_notice import make_prebroadcast_notice
from ai_broadcaster.offline_settings import DEFAULTS


class OfflineNaverCafeReviewTests(unittest.TestCase):
    def setUp(self):
        self.settings = deepcopy(DEFAULTS)
        self.draft = make_prebroadcast_notice(self.settings, parse_reference('2026-10-14 19:30'))

    def review(self, draft=None):
        return review_naver_cafe_official_link(self.draft if draft is None else draft)

    def test_preview_fields(self):
        result = self.review()
        self.assertIn('방송 시작 예정 안내', result.title)
        self.assertEqual(result.body, self.draft.text)
        self.assertEqual(result.source_time, self.draft.announcement_time)

    def test_json_is_not_api_request(self):
        d = json.loads(self.review().to_report_json())
        self.assertEqual(d['mode'], 'offline_feasibility_review_only')
        self.assertEqual(d['provider'], 'naver_cafe')
        self.assertIsNone(d['cafe_target'])
        self.assertIsNone(d['credentials'])
        self.assertFalse(d['api_payload_ready'])
        self.assertFalse(d['published'])
        self.assertFalse(d['network_enabled'])
        self.assertFalse(d['browser_automation_enabled'])
        self.assertEqual(d['operator_approval'], 'pending')

    def test_api_support_unverified(self):
        d = self.review().to_report_dict()
        for key in ('official_api_capability', 'current_terms_and_scope', 'cafe_write_permission'):
            self.assertEqual(d[key], 'unverified')

    def test_review_checklist(self):
        d = self.review().to_report_dict()
        self.assertEqual(len(d['operator_checklist']), 4)
        self.assertIn('별도 Windows', d['operator_checklist'][-1])

    def test_report_is_described_as_unpublished(self):
        self.assertIn('게시 없음', self.review().describe())

    def test_bad_source_type(self):
        for item in (None, {}, object(), '안내'):
            with self.subTest(item=type(item)), self.assertRaises(ValueError):
                review_naver_cafe_official_link(item)

    def test_unapproved_or_posted_draft_rejected(self):
        for name, value in (('review_only', False), ('ai_generated', True),
                            ('published', True), ('scheduled', True)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.review(replace(self.draft, **{name: value}))

    def test_invalid_content_types(self):
        for value in ('', 123, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.review(replace(self.draft, text=value))

    def test_local_body_length_limit(self):
        with self.assertRaises(ValueError):
            self.review(replace(self.draft, text='가' * 5001))

    def test_invalid_character_name(self):
        for name in ('', '가'*201, 'name\nheader'):
            with self.subTest(name=repr(name)), self.assertRaises(ValueError):
                self.review(replace(self.draft, persona_name=name))

    def test_title_local_bound(self):
        with self.assertRaises(ValueError):
            self.review(replace(self.draft, persona_name='가'*90))

    def test_block_unsafe_links(self):
        for fragment in ('https://example.net', 'HTTP://foo', 'www.hello.com'):
            with self.subTest(fragment=fragment), self.assertRaises(ValueError):
                self.review(replace(self.draft, text=self.draft.text + fragment))

    def test_block_mass_mentions(self):
        for fragment in ('@everyone', '@HERE', '<@1234>', '<#9876>'):
            with self.subTest(fragment=fragment), self.assertRaises(ValueError):
                self.review(replace(self.draft, text=self.draft.text + fragment))

    def test_block_controls(self):
        for character in ('\x00', '\x7f', '\r', '\t'):
            with self.subTest(character=repr(character)), self.assertRaises(ValueError):
                self.review(replace(self.draft, text=self.draft.text + character))

    def test_allow_linebreaks(self):
        self.assertIn('\n', self.review().body)

    def test_bad_time(self):
        for time in ('', None, '2026-10-14 UTC'):
            with self.subTest(time=time), self.assertRaises(ValueError):
                self.review(replace(self.draft, announcement_time=time))

    def test_time_mismatch(self):
        with self.assertRaises(ValueError):
            self.review(replace(self.draft, announcement_time='2026-10-15 19:30 KST'))

    def test_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.review().published = True

    def test_no_mutation_of_input(self):
        settings = deepcopy(self.settings)
        draft = self.draft
        self.review().to_report_json()
        self.assertEqual(self.settings, settings)
        self.assertEqual(self.draft, draft)

    def test_deterministic(self):
        self.assertEqual(self.review().to_report_json(), self.review().to_report_json())

    def test_no_network_or_process_file_usage(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('disk')):
            self.review().to_report_json()

    def test_no_remote_compatibility_claim(self):
        import ai_broadcaster.offline_naver_cafe_review as m
        for attr in ('publish', 'send', 'connect', 'login', 'oauth', 'write_article', 'open_browser'):
            self.assertFalse(hasattr(m, attr))
        self.assertNotIn('api_endpoint', self.review().to_report_json().lower())

    def test_streaming_platform_not_cafe_target(self):
        for platforms in ([], ['youtube'], ['chzzk', 'twitch']):
            with self.subTest(platforms=platforms):
                conf = deepcopy(self.settings)
                conf['platforms'] = platforms
                draft = make_prebroadcast_notice(conf, parse_reference('2026-10-14 19:30'))
                self.assertIsNone(self.review(draft).to_report_dict()['cafe_target'])


if __name__ == '__main__':
    unittest.main()
