"""091 manual synthetic chat and event journal, security and persistence boundaries."""
import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_journal import (
    MAX_ENTRIES, OfflineBroadcastJournal, JournalEntry, EVENT_KINDS,
)
from ai_broadcaster.offline_chat_receiver import MockReceivedChat, ReceiveSnapshot


def mock_state(*texts):
    messages = tuple(MockReceivedChat(i, 'youtube' if i % 2 else 'twitch',
                                      f'가상시청자{i}', text)
                     for i, text in enumerate(texts, 1))
    return ReceiveSnapshot(messages, False, len(messages))


class OfflineJournalTests(TestCase):
    def setUp(self):
        self.journal = OfflineBroadcastJournal('수동 가상 1회')

    def test_no_automatic_capture(self):
        self.assertEqual(self.journal.entries, ())
        self.assertEqual(self.journal.imported_chats, 0)

    def test_manual_mock_chat_import(self):
        self.assertEqual(self.journal.import_mock_chats(mock_state('안녕', '또 만나요')), 2)
        self.assertEqual([e.source_ordinal for e in self.journal.entries], [1, 2])
        self.assertEqual(self.journal.imported_chats, 2)

    def test_duplicate_messages_are_distinct(self):
        self.journal.import_mock_chats(mock_state('같은말', '같은말'))
        self.assertEqual(len(self.journal.entries), 2)
        self.assertNotEqual(self.journal.entries[0].index, self.journal.entries[1].index)

    def test_repeat_import_does_not_duplicate(self):
        state = mock_state('a', 'b')
        self.journal.import_mock_chats(state)
        self.assertEqual(self.journal.import_mock_chats(state), 0)
        self.assertEqual(len(self.journal.entries), 2)

    def test_incremental_import_interleaved_events(self):
        self.journal.import_mock_chats(mock_state('a'))
        self.journal.add_mock_event('game_mock', '스테이지 완료 (모의)')
        self.journal.import_mock_chats(mock_state('a', 'b'))
        self.assertEqual([x.kind for x in self.journal.entries], ['chat_mock', 'game_mock', 'chat_mock'])
        self.assertEqual([x.index for x in self.journal.entries], [1, 2, 3])
        self.assertEqual([x.source_ordinal for x in self.journal.entries], [1, None, 2])

    def test_import_rejects_changed_history_atomically(self):
        self.journal.import_mock_chats(mock_state('first'))
        prior = self.journal.entries
        with self.assertRaises(ValueError):
            self.journal.import_mock_chats(mock_state('changed', 'second'))
        self.assertEqual(self.journal.entries, prior)

    def test_import_rejects_invalid_ordinal(self):
        bad = ReceiveSnapshot((MockReceivedChat(2, 'youtube', '가상', 'hi'),), True, 1)
        with self.assertRaises(ValueError):
            self.journal.import_mock_chats(bad)
        self.assertFalse(self.journal.entries)

    def test_import_rejects_invalid_platform(self):
        bad = ReceiveSnapshot((MockReceivedChat(1, 'unknown', '가상', 'hi'),), True, 1)
        with self.assertRaises(ValueError):
            self.journal.import_mock_chats(bad)

    def test_import_rejects_invalid_count(self):
        bad = replace(mock_state('hello'), accepted_count=3)
        with self.assertRaises(ValueError):
            self.journal.import_mock_chats(bad)

    def test_import_rejects_fake_snapshot(self):
        with self.assertRaises(ValueError):
            self.journal.import_mock_chats(object())

    def test_event_categories(self):
        for cat in EVENT_KINDS:
            self.journal.add_mock_event(cat, '운영자 입력')
        self.assertEqual(len(self.journal.entries), len(EVENT_KINDS))

    def test_event_invalid_inputs(self):
        for kind, content in [('real_superchat', '돈'), ('operator_note', ''),
                              ('game_mock', 'x\ny'), ('other_mock', 'X' * 1001)]:
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    self.journal.add_mock_event(kind, content)
        self.assertEqual(len(self.journal.entries), 0)

    def test_session_label_invalid(self):
        for label in ('', 'a\nb', 'x' * 81, None):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    OfflineBroadcastJournal(label)

    def test_capacity_preserves_existing(self):
        for i in range(MAX_ENTRIES):
            self.journal.add_mock_event('other_mock', str(i))
        with self.assertRaises(ValueError):
            self.journal.add_mock_event('other_mock', 'over')
        with self.assertRaises(ValueError):
            self.journal.import_mock_chats(mock_state('over'))
        self.assertEqual(len(self.journal.entries), MAX_ENTRIES)

    def test_no_writes_before_explicit_export(self):
        with TemporaryDirectory() as temp, patch('builtins.open', side_effect=AssertionError('unwanted IO')):
            self.journal.add_mock_event('game_mock', '모의 이벤트')
            self.journal.import_mock_chats(mock_state('hello'))
            self.assertEqual(len(list(Path(temp).iterdir())), 0)

    def test_export_import_roundtrip(self):
        self.journal.import_mock_chats(mock_state('hello', 'hello'))
        self.journal.add_mock_event('operator_note', '가상 테스트')
        with TemporaryDirectory() as temp:
            path = Path(temp) / '내기록.json'
            self.journal.export_json(path)
            loaded = OfflineBroadcastJournal.load_json(path)
            self.assertEqual(loaded.preview(), self.journal.preview())
            self.assertEqual(loaded.imported_chats, 2)
            self.assertEqual(loaded.import_mock_chats(mock_state('hello', 'hello', 'new')), 1)

    def test_export_never_overwrites(self):
        self.journal.add_mock_event('operator_note', '수동')
        with TemporaryDirectory() as temp:
            p = Path(temp) / 'test.json'
            p.write_text('existing', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                self.journal.export_json(p)
            self.assertEqual(p.read_text(encoding='utf-8'), 'existing')

    def test_cannot_export_empty(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'empty.json'
            with self.assertRaises(ValueError):
                self.journal.export_json(path)
            self.assertFalse(path.exists())

    def test_export_has_no_real_verified_flags(self):
        self.journal.add_mock_event('support_mock', '가상 후원')
        body = self.journal.preview()
        self.assertFalse(body['actual_broadcast_verified'])
        self.assertFalse(body['real_platform_collected'])
        self.assertFalse(body['memory_integrated'])
        self.assertFalse(body['auto_saved'])
        self.assertEqual(body['approval'], 'pending')

    def test_import_detects_tampering(self):
        self.journal.add_mock_event('game_mock', '가상 게임')
        with TemporaryDirectory() as temp:
            p = Path(temp) / 'journal.json'
            self.journal.export_json(p)
            raw = json.loads(p.read_text(encoding='utf-8'))
            raw['entries'][0]['text'] = '변조'
            p.write_text(json.dumps(raw), encoding='utf-8')
            with self.assertRaises(ValueError):
                OfflineBroadcastJournal.load_json(p)

    def test_import_detects_forged_actual_verified_flag(self):
        self.journal.add_mock_event('game_mock', 'mock')
        with TemporaryDirectory() as temp:
            p = Path(temp) / 'journal.json'
            self.journal.export_json(p)
            data = json.loads(p.read_text(encoding='utf-8'))
            data['actual_broadcast_verified'] = True
            p.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(ValueError):
                OfflineBroadcastJournal.load_json(p)

    def test_import_detects_gap_even_if_checksum_forged(self):
        self.journal.import_mock_chats(mock_state('a', 'b'))
        with TemporaryDirectory() as temp:
            p = Path(temp) / 'journal.json'
            self.journal.export_json(p)
            data = json.loads(p.read_text(encoding='utf-8'))
            data['entries'][1]['source_ordinal'] = 4
            p.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(ValueError):
                OfflineBroadcastJournal.load_json(p)

    def test_import_size_bound(self):
        with TemporaryDirectory() as temp:
            p = Path(temp) / 'huge.json'
            p.write_bytes(b'x' * 3_000_001)
            with self.assertRaises(ValueError):
                OfflineBroadcastJournal.load_json(p)

    def test_import_invalid_json(self):
        with TemporaryDirectory() as temp:
            p = Path(temp) / 'bad.json'
            p.write_bytes(b'\xff')
            with self.assertRaises(ValueError):
                OfflineBroadcastJournal.load_json(p)

    def test_missing_folder_does_not_get_created(self):
        self.journal.add_mock_event('game_mock', '가상')
        with TemporaryDirectory() as temp:
            p = Path(temp) / 'missing' / 'result.json'
            with self.assertRaises(OSError):
                self.journal.export_json(p)
            self.assertFalse(p.parent.exists())

    def test_export_does_not_use_network_or_process(self):
        self.journal.add_mock_event('game_mock', '가상')
        with TemporaryDirectory() as temp, patch('socket.socket.connect', side_effect=AssertionError('no net')), \
             patch('subprocess.Popen', side_effect=AssertionError('no process')):
            self.journal.export_json(Path(temp) / 'local.json')
