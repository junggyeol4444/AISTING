"""Stage 085 local message-shape review, negative conditions and side effects."""
import json
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_schedule import parse_reference
from ai_broadcaster.offline_discord_notice_link import prepare_discord_notice_dry_run
from ai_broadcaster.offline_prebroadcast_notice import make_prebroadcast_notice
from ai_broadcaster.offline_settings import DEFAULTS


class DiscordDryRunTests(unittest.TestCase):
    def setUp(self):
        self.settings = deepcopy(DEFAULTS)
        self.draft = make_prebroadcast_notice(self.settings, parse_reference('2026-10-14 19:30'))

    def test_basic_preview(self):
        d = prepare_discord_notice_dry_run(self.draft)
        self.assertEqual(d.platform, 'discord')
        self.assertEqual(d.content, self.draft.text)
        self.assertEqual(d.source_time, '2026-10-14 19:30 KST')

    def test_never_sender_or_connected(self):
        d = prepare_discord_notice_dry_run(self.draft)
        for key in ('destination_configured', 'credentials_configured', 'transport_enabled', 'send_ready', 'published'):
            self.assertFalse(getattr(d, key))
        self.assertIn('미게시', d.describe())

    def test_json_contract(self):
        data = json.loads(prepare_discord_notice_dry_run(self.draft).to_preview_json())
        self.assertEqual(data['mode'], 'offline_review_only')
        self.assertIsNone(data['destination'])
        self.assertEqual(data['connection'], 'disabled')
        self.assertFalse(data['published'])
        self.assertFalse(data['send_ready'])
        self.assertEqual(data['message']['content'], self.draft.text)
        self.assertFalse(data['message']['tts'])
        self.assertEqual(data['message']['allowed_mentions']['parse'], [])
        self.assertEqual(data['message']['allowed_mentions']['users'], [])
        self.assertEqual(data['message']['allowed_mentions']['roles'], [])
        self.assertFalse(data['message']['allowed_mentions']['replied_user'])

    def test_unicode_roundtrip(self):
        self.assertIn('아이스팅', json.loads(prepare_discord_notice_dry_run(self.draft).to_preview_json())['message']['content'])

    def test_no_dispatch_api(self):
        import ai_broadcaster.offline_discord_notice_link as m
        for name in ('publish', 'send', 'connect', 'login', 'post_notice', 'discord_token', 'channel_id'):
            self.assertFalse(hasattr(m, name))

    def test_wrong_source_type(self):
        for bad in (None, {}, 'abc', object()):
            with self.subTest(bad=str(type(bad))), self.assertRaises(ValueError):
                prepare_discord_notice_dry_run(bad)

    def test_reject_ai_or_published(self):
        for field in ('ai_generated', 'published', 'scheduled'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepare_discord_notice_dry_run(replace(self.draft, **{field: True}))
        with self.assertRaises(ValueError):
            prepare_discord_notice_dry_run(replace(self.draft, review_only=False))

    def test_max_length_accepted(self):
        self.assertEqual(len(prepare_discord_notice_dry_run(replace(self.draft, text='가'*2000)).content), 2000)

    def test_over_limit_rejected(self):
        with self.assertRaises(ValueError):
            prepare_discord_notice_dry_run(replace(self.draft, text='가'*2001))

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            prepare_discord_notice_dry_run(replace(self.draft, text=''))

    def test_non_string_content_rejected(self):
        with self.assertRaises(ValueError):
            prepare_discord_notice_dry_run(replace(self.draft, text=19))

    def test_unsafe_mentions_rejected(self):
        for msg in ('@everyone', '@Here', '<@12345>', '<#12345>'):
            with self.subTest(msg=msg), self.assertRaises(ValueError):
                prepare_discord_notice_dry_run(replace(self.draft, text=msg))

    def test_external_links_rejected(self):
        for msg in ('https://foo.org', 'HTTP://a.b', 'www.example.org'):
            with self.subTest(msg=msg), self.assertRaises(ValueError):
                prepare_discord_notice_dry_run(replace(self.draft, text=msg))

    def test_linebreak_ok_but_controls_rejected(self):
        self.assertIn('\n', prepare_discord_notice_dry_run(self.draft).content)
        for msg in ('a\tb', 'a\rb', 'a\x00b', 'a\x7fb'):
            with self.subTest(msg=repr(msg)), self.assertRaises(ValueError):
                prepare_discord_notice_dry_run(replace(self.draft, text=msg))

    def test_invalid_time_rejected(self):
        for bad in ('UTC', '', None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                prepare_discord_notice_dry_run(replace(self.draft, announcement_time=bad))

    def test_no_mutation(self):
        initial = deepcopy(self.settings)
        before = self.draft
        prepare_discord_notice_dry_run(self.draft).to_preview_json()
        self.assertEqual(self.settings, initial)
        self.assertEqual(self.draft, before)

    def test_result_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            prepare_discord_notice_dry_run(self.draft).published = True

    def test_repeat_deterministic(self):
        self.assertEqual(prepare_discord_notice_dry_run(self.draft).to_preview_json(),
                         prepare_discord_notice_dry_run(self.draft).to_preview_json())

    def test_no_network_process_or_files(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('builtins.open', side_effect=AssertionError('files')):
            prepare_discord_notice_dry_run(self.draft).to_preview_json()

    def test_not_derived_from_streaming_platform(self):
        for platforms in ([], ['youtube'], ['chzzk', 'twitch']):
            with self.subTest(platforms=platforms):
                x = deepcopy(self.settings)
                x['platforms'] = platforms
                draft = make_prebroadcast_notice(x, parse_reference('2026-10-14 19:30'))
                data = prepare_discord_notice_dry_run(draft).to_preview_dict()
                self.assertIsNone(data['destination'])
                self.assertFalse(data['send_ready'])

    def test_no_endpoint_or_secret_in_preview(self):
        result = prepare_discord_notice_dry_run(self.draft).to_preview_json()
        self.assertNotIn('webhook', result.lower())
        self.assertNotIn('token', result.lower())
        self.assertNotIn('api/', result.lower())


if __name__ == '__main__':
    unittest.main()
