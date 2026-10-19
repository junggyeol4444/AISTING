"""Stage 061 contract rehearsal: no live platform connections."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.platform_chat_connector import OfflinePlatformChatConnector, PLATFORM_CODES


class PlatformChatContractTests(unittest.TestCase):
    def test_all_codes_match_existing_operator_settings(self):
        self.assertEqual(PLATFORM_CODES, ('chzzk', 'youtube', 'twitch'))

    def test_unselected_is_allowed_but_cannot_connect(self):
        session = OfflinePlatformChatConnector([])
        self.assertEqual(session.snapshot().phase, '미연결')
        with self.assertRaises(ValueError):
            session.connect()
        self.assertEqual(session.snapshot().attempts, 0)

    def test_each_single_platform(self):
        for code in PLATFORM_CODES:
            with self.subTest(code=code):
                s = OfflinePlatformChatConnector([code])
                self.assertEqual(s.connect().connected, (code,))
                self.assertEqual(s.disconnect().connected, ())

    def test_multiple_platforms_keep_operator_order(self):
        s = OfflinePlatformChatConnector(['twitch', 'chzzk', 'youtube'])
        self.assertEqual(s.connect().connected, ('twitch', 'chzzk', 'youtube'))

    def test_selection_does_not_connect_automatically(self):
        s = OfflinePlatformChatConnector(list(PLATFORM_CODES))
        self.assertFalse(s.snapshot().connected)
        self.assertEqual(s.snapshot().attempts, 0)

    def test_reject_duplicate(self):
        with self.assertRaises(ValueError):
            OfflinePlatformChatConnector(['chzzk', 'chzzk'])

    def test_reject_unknown(self):
        with self.assertRaises(ValueError):
            OfflinePlatformChatConnector(['unknown'])

    def test_reject_invalid_types(self):
        for invalid in (None, 'chzzk', {'chzzk'}, [True], [1], ['youtube', None]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                OfflinePlatformChatConnector(invalid)

    def test_snapshot_immutable(self):
        s = OfflinePlatformChatConnector(['youtube'])
        before = s.snapshot()
        s.connect()
        self.assertEqual(before.connected, ())
        self.assertEqual(before.attempts, 0)

    def test_input_list_mutation_cannot_change_selection(self):
        selected = ['chzzk']
        s = OfflinePlatformChatConnector(selected)
        selected.append('youtube')
        self.assertEqual(s.connect().connected, ('chzzk',))

    def test_duplicate_connect_refused_without_state_change(self):
        s = OfflinePlatformChatConnector(['youtube'])
        s.connect()
        with self.assertRaises(ValueError):
            s.connect()
        self.assertEqual(s.snapshot().attempts, 1)
        self.assertEqual(s.snapshot().connected, ('youtube',))

    def test_disconnect_idempotent_and_no_retry(self):
        s = OfflinePlatformChatConnector(['youtube'])
        s.disconnect()
        s.disconnect()
        self.assertEqual(s.snapshot().attempts, 0)

    def test_manual_reconnect(self):
        s = OfflinePlatformChatConnector(['youtube'])
        s.connect()
        s.disconnect()
        self.assertEqual(s.connect().attempts, 2)

    def test_mock_failure_rolls_back_all(self):
        s = OfflinePlatformChatConnector(['chzzk', 'youtube', 'twitch'], fail_on='youtube')
        report = s.connect()
        self.assertEqual(report.connected, ())
        self.assertEqual(report.attempts, 1)
        self.assertIn('실패', report.phase)
        self.assertIn('자동 재시도 없음', report.error)

    def test_mock_failure_never_recovers_automatically(self):
        s = OfflinePlatformChatConnector(['youtube'], fail_on='youtube')
        s.connect()
        self.assertEqual(s.snapshot().attempts, 1)
        self.assertEqual(s.snapshot().connected, ())

    def test_failure_not_selected_has_no_effect(self):
        s = OfflinePlatformChatConnector(['chzzk'], fail_on='youtube')
        self.assertEqual(s.connect().connected, ('chzzk',))

    def test_invalid_failure_code_rejected(self):
        with self.assertRaises(ValueError):
            OfflinePlatformChatConnector(['youtube'], fail_on='wrong')

    def test_status_disclaims_real_connection(self):
        s = OfflinePlatformChatConnector(['youtube'])
        for state in (s.snapshot(), s.connect(), s.disconnect()):
            self.assertTrue(state.mock_only)
            self.assertIn('실제 치지직·유튜브·트위치 연결: 0건', state.describe())
            self.assertIn('채팅 수신: 0건', state.describe())

    def test_no_network_disk_subprocess_db_or_sleep(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('builtins.open', side_effect=AssertionError('disk')), \
             patch('sqlite3.connect', side_effect=AssertionError('db')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('time.sleep', side_effect=AssertionError('delay')):
            s = OfflinePlatformChatConnector(list(PLATFORM_CODES))
            s.connect()
            s.disconnect()

    def test_source_has_no_real_platform_client(self):
        source = (Path(__file__).resolve().parents[1] / 'src/ai_broadcaster/platform_chat_connector.py').read_text(encoding='utf8')
        for forbidden in ('import requests', 'import socket', 'import websocket', 'urllib.request', 'open(', 'subprocess'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main()
