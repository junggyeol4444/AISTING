"""Original stage 062: manual mock ingress, no real-time network activity."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector
from ai_broadcaster.offline_chat_receiver import (
    OfflineChatReceiveBuffer, MAX_RECEIVED, MockReceivedChat,
)


def connected(*codes):
    session = OfflinePlatformChatConnector(list(codes))
    session.connect()
    return session


class MockReceiveTests(unittest.TestCase):
    def setUp(self):
        self.receiver = OfflineChatReceiveBuffer()

    def test_default_is_detached_and_empty(self):
        state = self.receiver.snapshot()
        self.assertFalse(state.attached)
        self.assertEqual(state.buffered, ())
        self.assertTrue(state.mock_only)

    def test_no_inject_before_manual_attach(self):
        with self.assertRaises(ValueError):
            self.receiver.inject('chzzk', 'a', 'b')

    def test_cannot_attach_unconnected_contract(self):
        with self.assertRaises(ValueError):
            self.receiver.attach(OfflinePlatformChatConnector(['chzzk']))

    def test_cannot_attach_invalid_connector(self):
        for bad in (None, 'chzzk', [], object()):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.receiver.attach(bad)

    def test_attach_connected_contract(self):
        self.assertTrue(self.receiver.attach(connected('youtube')).attached)

    def test_one_event_fields_and_ordinal(self):
        self.receiver.attach(connected('chzzk'))
        event = self.receiver.inject('chzzk', ' A ', ' Hi ')
        self.assertEqual(event, MockReceivedChat(1, 'chzzk', 'A', 'Hi'))

    def test_three_platforms(self):
        self.receiver.attach(connected('twitch', 'chzzk', 'youtube'))
        for name in ('twitch', 'chzzk', 'youtube'):
            self.receiver.inject(name, 'a', 'x')
        self.assertEqual([x.platform for x in self.receiver.snapshot().buffered],
                         ['twitch', 'chzzk', 'youtube'])

    def test_unselected_platform_refused(self):
        self.receiver.attach(connected('youtube'))
        with self.assertRaises(ValueError):
            self.receiver.inject('chzzk', 'a', 'b')
        self.assertEqual(self.receiver.snapshot().accepted_count, 0)

    def test_unknown_platform_refused(self):
        self.receiver.attach(connected('youtube'))
        with self.assertRaises(ValueError):
            self.receiver.inject('fake', 'a', 'b')

    def test_invalid_platform_types(self):
        self.receiver.attach(connected('youtube'))
        for bad in (None, 5, True, ['youtube']):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.receiver.inject(bad, 'a', 'b')

    def test_invalid_sender_types(self):
        self.receiver.attach(connected('youtube'))
        for bad in (None, 5, True, [], ''):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.receiver.inject('youtube', bad, 'b')

    def test_invalid_text_types(self):
        self.receiver.attach(connected('youtube'))
        for bad in (None, 5, True, [], ''):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.receiver.inject('youtube', 'a', bad)

    def test_sender_and_text_length_limits(self):
        self.receiver.attach(connected('youtube'))
        self.receiver.inject('youtube', 'a'*100, 'b'*4000)
        for sender, text in (('a'*101, 'ok'), ('ok', 'b'*4001), ('  ', 'ok'), ('ok', '\n ')):
            with self.subTest(sender=sender[:5]), self.assertRaises(ValueError):
                self.receiver.inject('youtube', sender, text)

    def test_duplicate_chat_not_filtered(self):
        self.receiver.attach(connected('youtube'))
        self.receiver.inject('youtube', 'a', 'same')
        self.receiver.inject('youtube', 'a', 'same')
        self.assertEqual(self.receiver.snapshot().accepted_count, 2)

    def test_disconnect_blocks_further_injection_preserves_buffer(self):
        session = connected('youtube')
        self.receiver.attach(session)
        self.receiver.inject('youtube', 'a', 'before')
        session.disconnect()
        self.assertFalse(self.receiver.snapshot().attached)
        with self.assertRaises(ValueError):
            self.receiver.inject('youtube', 'a', 'after')
        self.assertEqual(self.receiver.snapshot().buffered[0].text, 'before')

    def test_detach_preserves_buffer(self):
        self.receiver.attach(connected('youtube'))
        self.receiver.inject('youtube', 'a', 'b')
        self.receiver.detach()
        self.assertEqual(self.receiver.snapshot().accepted_count, 1)

    def test_rebind_after_manual_reconnect_preserves_prior_events(self):
        self.receiver.attach(connected('youtube'))
        self.receiver.inject('youtube', 'a', 'old')
        self.receiver.detach()
        self.receiver.attach(connected('chzzk'))
        self.receiver.inject('chzzk', 'b', 'new')
        self.assertEqual([x.ordinal for x in self.receiver.snapshot().buffered], [1, 2])

    def test_buffer_limit_no_silent_loss(self):
        self.receiver.attach(connected('youtube'))
        for i in range(MAX_RECEIVED):
            self.receiver.inject('youtube', 'a', str(i))
        before = self.receiver.snapshot()
        with self.assertRaisesRegex(ValueError, '삭제하지'):
            self.receiver.inject('youtube', 'a', 'overflow')
        self.assertEqual(self.receiver.snapshot(), before)

    def test_snapshots_and_events_immutable(self):
        self.receiver.attach(connected('youtube'))
        old = self.receiver.snapshot()
        event = self.receiver.inject('youtube', 'a', 'b')
        self.assertEqual(old.accepted_count, 0)
        with self.assertRaises(Exception):
            event.text = 'modified'

    def test_manual_accept_does_not_call_network_disk_db_or_sleep(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('builtins.open', side_effect=AssertionError('disk')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('time.sleep', side_effect=AssertionError('sleep')):
            self.receiver.attach(connected('chzzk'))
            self.receiver.inject('chzzk', 'a', 'b')
            self.receiver.detach()

    def test_disclaimer_and_no_fake_real_time(self):
        report = self.receiver.snapshot().describe()
        self.assertIn('실제 플랫폼에서 받은 메시지: 0건', report)
        self.assertIn('자동 실시간 수신: 없음', report)

    def test_no_platform_io_code(self):
        source = (Path(__file__).resolve().parents[1] / 'src/ai_broadcaster/offline_chat_receiver.py').read_text(encoding='utf8')
        for forbidden in ('import requests', 'import socket', 'import websocket', 'urllib.request', 'subprocess.Popen', 'time.sleep', 'sqlite3.connect'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main()
