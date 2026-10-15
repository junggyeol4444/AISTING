"""Original 092: isolated, operator-selected synthetic past-session memory cards."""
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_journal import OfflineBroadcastJournal
from ai_broadcaster.offline_past_broadcast_memory import (
    OfflinePastBroadcastMemory, MemoryCard, MAX_CARDS, MAX_EXCERPTS, _digest,
)


def journal(label='가상 지난 방송', chats=False):
    obj = OfflineBroadcastJournal(label)
    obj.add_mock_event('operator_note', '어제 모의 게임 연습')
    if chats:
        from ai_broadcaster.offline_chat_receiver import ReceiveSnapshot, MockReceivedChat
        obj.import_mock_chats(ReceiveSnapshot((MockReceivedChat(1, 'youtube', '가상시청자', '어제 모의 인사'),), False, 1))
    return obj


class PastMemoryTests(unittest.TestCase):
    def setUp(self):
        self.memory = OfflinePastBroadcastMemory()

    def test_empty_initially(self):
        self.assertEqual(self.memory.cards, ())

    def test_explicit_one_session(self):
        card = self.memory.add_journal(journal())
        self.assertEqual(card.session_label, '가상 지난 방송')
        self.assertFalse(card.includes_mock_chat)

    def test_opt_in_chat_default_excluded(self):
        card = self.memory.add_journal(journal(chats=True))
        self.assertEqual(len(card.excerpts), 1)
        self.assertNotIn('모의 인사', str(card.excerpts))

    def test_explicit_chat_opt_in(self):
        card = self.memory.add_journal(journal(chats=True), include_mock_chat=True)
        self.assertEqual(len(card.excerpts), 2)
        self.assertIn('어제 모의 인사', str(card.excerpts))

    def test_duplicate_archive_refused(self):
        self.memory.add_journal(journal())
        with self.assertRaises(ValueError):
            self.memory.add_journal(journal())
        self.assertEqual(len(self.memory.cards), 1)

    def test_same_title_different_content_allowed(self):
        self.memory.add_journal(journal())
        j = journal()
        j.add_mock_event('operator_note', '새 가상 사건')
        self.memory.add_journal(j)
        self.assertEqual(len(self.memory.cards), 2)

    def test_bad_input_does_not_modify(self):
        for value in (None, object(), 'a'):
            with self.assertRaises(ValueError):
                self.memory.add_journal(value)
        self.assertFalse(self.memory.cards)

    def test_chat_opt_in_type_checked(self):
        with self.assertRaises(ValueError):
            self.memory.add_journal(journal(), include_mock_chat=1)

    def test_only_chat_requires_explicit_opt_in(self):
        j = journal(chats=True)
        j._entries.pop(0)  # deliberately malformed synthetic setup: no event
        with self.assertRaises(ValueError):
            self.memory.add_journal(j)
        self.assertFalse(self.memory.cards)

    def test_capacity(self):
        for i in range(MAX_CARDS):
            self.memory.add_journal(journal(str(i)))
        with self.assertRaises(ValueError):
            self.memory.add_journal(journal('extra'))
        self.assertEqual(len(self.memory.cards), MAX_CARDS)

    def test_excerpt_bounded(self):
        j = journal()
        for i in range(30):
            j.add_mock_event('other_mock', f'{i} 가상 사건')
        self.assertEqual(len(self.memory.add_journal(j).excerpts), MAX_EXCERPTS)

    def test_remove_card(self):
        self.memory.add_journal(journal('first'))
        self.memory.add_journal(journal('second'))
        self.memory.remove_card(0)
        self.assertEqual(self.memory.cards[0].session_label, 'second')

    def test_invalid_remove_preserves(self):
        self.memory.add_journal(journal())
        for i in (-1, 1, 0.0, True):
            with self.assertRaises(ValueError):
                self.memory.remove_card(i)
        self.assertEqual(len(self.memory.cards), 1)

    def test_no_automatic_files(self):
        with tempfile.TemporaryDirectory() as temp:
            self.memory.add_journal(journal())
            self.assertFalse(list(Path(temp).iterdir()))

    def test_roundtrip(self):
        self.memory.add_journal(journal(chats=True), include_mock_chat=True)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / '기억.json'
            self.memory.export_json(file)
            other = OfflinePastBroadcastMemory.load_json(file)
            self.assertEqual(other.cards, self.memory.cards)
            self.assertEqual(other.preview(), self.memory.preview())

    def test_existing_file_never_overwritten(self):
        self.memory.add_journal(journal())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / '기억.json'
            file.write_text('old')
            with self.assertRaises(FileExistsError):
                self.memory.export_json(file)
            self.assertEqual(file.read_text(), 'old')

    def test_export_empty_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'empty.json'
            with self.assertRaises(ValueError):
                self.memory.export_json(file)
            self.assertFalse(file.exists())

    def test_corrupt_digest_refused(self):
        self.memory.add_journal(journal())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'bad.json'
            self.memory.export_json(file)
            data = json.loads(file.read_text())
            data['cards'][0]['excerpts'][0] = 'operator_note: forged'
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                OfflinePastBroadcastMemory.load_json(file)

    def test_forged_actual_broadcast_flag_rejected_even_with_digest(self):
        self.memory.add_journal(journal())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'bad.json'
            data = self.memory.preview()
            data['actual_broadcast_verified'] = True
            data['checksum_sha256'] = _digest({k: v for k, v in data.items() if k != 'checksum_sha256'})
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                OfflinePastBroadcastMemory.load_json(file)

    def test_reject_opt_out_chat_forgery_with_matching_checksum(self):
        self.memory.add_journal(journal(chats=True), include_mock_chat=True)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'bad.json'
            data = self.memory.preview()
            data['cards'][0]['includes_mock_chat'] = False
            data['checksum_sha256'] = _digest({k: v for k, v in data.items() if k != 'checksum_sha256'})
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                OfflinePastBroadcastMemory.load_json(file)

    def test_duplicate_cards_in_file_rejected(self):
        self.memory.add_journal(journal())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'bad.json'
            data = self.memory.preview()
            data['cards'].append(data['cards'][0].copy())
            data['checksum_sha256'] = _digest({k: v for k, v in data.items() if k != 'checksum_sha256'})
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                OfflinePastBroadcastMemory.load_json(file)

    def test_corrupt_file_preserves_existing_memory(self):
        self.memory.add_journal(journal())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'bad.json'
            file.write_text('not json')
            with self.assertRaises(ValueError):
                OfflinePastBroadcastMemory.load_json(file)
            self.assertEqual(len(self.memory.cards), 1)

    def test_missing_directory_not_created(self):
        self.memory.add_journal(journal())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'nonexistent' / 'memory.json'
            with self.assertRaises(FileNotFoundError):
                self.memory.export_json(file)
            self.assertFalse(file.parent.exists())

    def test_no_network_or_process(self):
        self.memory.add_journal(journal())
        with patch('socket.socket.connect', side_effect=AssertionError('external network forbidden')), \
             patch('subprocess.Popen', side_effect=AssertionError('external process forbidden')):
            self.assertEqual(len(self.memory.preview()['cards']), 1)

    def test_empty_cards_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'empty.json'
            file.write_text(json.dumps(self.memory.preview()))
            self.assertEqual(OfflinePastBroadcastMemory.load_json(file).cards, ())

    def test_reject_string_list_in_card(self):
        self.memory.add_journal(journal())
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'bad.json'
            data = self.memory.preview()
            data['cards'][0]['excerpts'] = 'operator_note: text'
            data['checksum_sha256'] = _digest({k: v for k, v in data.items() if k != 'checksum_sha256'})
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                OfflinePastBroadcastMemory.load_json(file)


if __name__ == '__main__':
    unittest.main()
