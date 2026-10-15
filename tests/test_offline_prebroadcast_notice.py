"""Stage 084 read-only notice text contract (no external action)."""
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_broadcast_schedule import parse_reference
from ai_broadcaster.offline_prebroadcast_notice import make_prebroadcast_notice


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.config = deepcopy(DEFAULTS)
        self.when = parse_reference('2026-10-14 19:30')

    def make(self, **kwargs):
        return make_prebroadcast_notice(self.config, self.when, **kwargs)

    def test_basic_kst_notice(self):
        d = self.make()
        self.assertIn('2026-10-14 19:30 KST', d.text)
        self.assertIn('아이스팅', d.text)
        self.assertIn('미선택', d.text)

    def test_not_ai_or_published(self):
        d = self.make()
        self.assertFalse(d.ai_generated)
        self.assertFalse(d.published)
        self.assertFalse(d.scheduled)
        self.assertTrue(d.review_only)
        self.assertIn('규칙 기반', d.describe())

    def test_selected_platform_order(self):
        self.config['platforms'] = ['twitch', 'youtube', 'chzzk']
        self.assertIn('트위치, 유튜브, 치지직', self.make().text)

    def test_all_content_modes(self):
        for content in ('undecided', 'chat', 'game', 'both'):
            with self.subTest(content=content):
                self.config['content'] = content
                self.assertIn('방송 내용:', self.make().text)

    def test_custom_persona(self):
        self.config['persona_mode'] = 'custom'
        self.config['persona']['name'] = '테스트 캐릭터'
        self.assertIn('테스트 캐릭터', self.make().text)

    def test_default_persona_ignores_unsaved_custom(self):
        self.config['persona']['name'] = '숨겨 둔 초안'
        self.assertNotIn('숨겨 둔 초안', self.make().text)

    def test_topic_optional(self):
        self.assertNotIn('오늘의 주제:', self.make().text)

    def test_topic_explicit(self):
        self.assertIn('게임 이어하기', self.make(topic='게임 이어하기').text)

    def test_no_fake_url(self):
        d = self.make()
        self.assertIn('미설정', d.text)
        self.assertNotIn('https://', d.text)

    def test_newline_rejected(self):
        with self.assertRaises(ValueError):
            self.make(topic='one\ntwo')

    def test_control_character_rejected(self):
        with self.assertRaises(ValueError):
            self.make(topic='hi\x00')

    def test_overlong_topic_rejected(self):
        with self.assertRaises(ValueError):
            self.make(topic='가' * 101)

    def test_type_invalid_topic_rejected(self):
        with self.assertRaises(ValueError):
            self.make(topic=None)

    def test_mass_mentions_rejected(self):
        for text in ('@everyone 지금', 'hello @HERE'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.make(topic=text)

    def test_external_urls_rejected(self):
        for text in ('https://example.org', 'www.example.org'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.make(topic=text)

    def test_wrong_timezone_rejected(self):
        with self.assertRaises(ValueError):
            make_prebroadcast_notice(self.config, datetime.now(timezone.utc))

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            make_prebroadcast_notice(self.config, datetime(2026, 10, 14, 19, 30))

    def test_bool_flags_block_broadcast_permission(self):
        for key in ('streaming_enabled', 'scheduled_execution', 'external_publish_enabled'):
            with self.subTest(key=key):
                settings = deepcopy(self.config)
                settings[key] = True
                with self.assertRaises(ValueError):
                    make_prebroadcast_notice(settings, self.when)

    def test_immutable_output(self):
        with self.assertRaises(FrozenInstanceError):
            self.make().published = True

    def test_no_settings_mutation(self):
        before = deepcopy(self.config)
        self.make(topic='초안')
        self.assertEqual(self.config, before)

    def test_no_connect_or_process(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.make()

    def test_repeat_is_deterministic(self):
        self.assertEqual(self.make(topic='수다'), self.make(topic='수다'))

    def test_no_external_publish_stub(self):
        import ai_broadcaster.offline_prebroadcast_notice as m
        self.assertFalse(hasattr(m, 'send_notice'))
        self.assertFalse(hasattr(m, 'publish'))


if __name__ == '__main__':
    unittest.main()
