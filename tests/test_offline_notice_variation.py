"""Original 088 deterministic operator-selected notice variation unit contracts."""
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_schedule import parse_reference
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_prebroadcast_notice import make_prebroadcast_notice
from ai_broadcaster.offline_notice_variation import (
    NoticeVariationOptions, make_notice_variation,
)


class NoticeVariationTests(unittest.TestCase):
    def setUp(self):
        self.settings = deepcopy(DEFAULTS)
        self.when = parse_reference('2026-10-14 19:30')
        self.base = make_prebroadcast_notice(self.settings, self.when, '게임')

    def create(self, **options):
        return make_notice_variation(self.base, self.settings, NoticeVariationOptions(**options))

    def test_default_review_only(self):
        result = self.create()
        self.assertTrue(result.review_only)
        self.assertFalse(result.published or result.scheduled or result.ai_generated)
        self.assertIn('규칙 기반', result.describe())

    def test_preserves_base_draft(self):
        before = self.base
        self.create(style='활기', variant_number=2)
        self.assertEqual(self.base, before)

    def test_all_styles_have_distinct_openings(self):
        texts = [self.create(style=style).text for style in ('친근', '차분', '활기')]
        self.assertEqual(len(set(texts)), 3)

    def test_all_variant_numbers_distinct(self):
        texts = [self.create(variant_number=n).text for n in (1, 2, 3)]
        self.assertEqual(len(set(texts)), 3)

    def test_repeatable_for_same_settings(self):
        self.assertEqual(self.create().text, self.create().text)

    def test_length_modes(self):
        short = self.create(length='짧게').text
        basic = self.create(length='기본').text
        long = self.create(length='자세히').text
        self.assertLess(len(short), len(basic))
        self.assertLess(len(basic), len(long))

    def test_long_mode_persona_style(self):
        self.settings['persona_mode'] = 'custom'
        self.settings['persona']['style'] = '차분한 말투'
        self.base = make_prebroadcast_notice(self.settings, self.when, '게임')
        self.assertIn('차분한 말투', self.create(length='자세히').text)

    def test_default_persona_ignores_custom_draft(self):
        self.settings['persona']['style'] = '숨겨둔 캐릭터 말투'
        self.assertNotIn('숨겨둔', self.create(length='자세히').text)

    def test_emoji_explicit_only(self):
        self.assertNotIn('✨', self.create().text)
        self.assertIn('✨', self.create(emoji=True).text)

    def test_empty_context_allowed(self):
        self.assertNotIn('오늘의 맥락', self.create().text)

    def test_context_included(self):
        self.assertIn('어제 하던 게임', self.create(context='어제 하던 게임').text)

    def test_blank_topic(self):
        self.base = make_prebroadcast_notice(self.settings, self.when)
        self.assertNotIn('오늘의 주제:', self.create().text)

    def test_lead_time_disabled(self):
        self.assertIsNone(self.create().suggested_notice_time)

    def test_lead_time_ten_minutes(self):
        self.assertEqual(self.create(lead_minutes=10).suggested_notice_time, '2026-10-14 19:20 KST')

    def test_lead_time_date_boundary(self):
        self.when = parse_reference('2026-10-14 00:10')
        self.base = make_prebroadcast_notice(self.settings, self.when)
        self.assertEqual(self.create(lead_minutes=40).suggested_notice_time, '2026-10-13 23:30 KST')

    def test_time_is_never_scheduled(self):
        self.assertFalse(self.create(lead_minutes=20).scheduled)
        self.assertIn('예약 아님', self.create(lead_minutes=20).text)

    def test_invalid_styles_and_lengths(self):
        for kw in ({'style': '미등록'}, {'length': '기타'}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.create(**kw)

    def test_invalid_variant_type_and_range(self):
        for n in (0, 4, True, 1.0, '1'):
            with self.subTest(n=n), self.assertRaises(ValueError):
                self.create(variant_number=n)

    def test_invalid_emoji_type(self):
        with self.assertRaises(ValueError):
            self.create(emoji='yes')

    def test_invalid_lead(self):
        for minutes in (-1, 1, 9, 41, True, 10.5):
            with self.subTest(minutes=minutes), self.assertRaises(ValueError):
                self.create(lead_minutes=minutes)

    def test_rejects_control_url_mass_mentions(self):
        for value in ('두 줄\n입력', '@everyone', '@here', 'https://example.com', 'www.example.com', 'x'*101):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.create(context=value)

    def test_settings_mutation_rejected(self):
        self.settings['content'] = 'game'
        with self.assertRaisesRegex(ValueError, '변경'):
            self.create()

    def test_tampered_base_rejected(self):
        bad = replace(self.base, text=self.base.text+'추가')
        with self.assertRaises(ValueError):
            make_notice_variation(bad, self.settings, NoticeVariationOptions())

    def test_fake_published_base_rejected(self):
        with self.assertRaises(ValueError):
            make_notice_variation(replace(self.base, published=True), self.settings, NoticeVariationOptions())

    def test_unsafe_settings_blocked(self):
        self.settings['external_publish_enabled'] = True
        with self.assertRaises(ValueError):
            self.create()

    def test_long_mode_unsafe_persona_rejected(self):
        self.settings['persona_mode'] = 'custom'
        self.settings['persona']['style'] = '@everyone'
        self.base = make_prebroadcast_notice(self.settings, self.when)
        with self.assertRaises(ValueError):
            self.create(length='자세히')

    def test_preview_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.create().published = True

    def test_no_io_or_external_process(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('file')):
            self.assertIn('KST', self.create().text)


if __name__ == '__main__':
    unittest.main()
