"""Original 093: offline manual recall, bounded context, stale-state rejection."""
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch
from ai_broadcaster.offline_broadcast_journal import OfflineBroadcastJournal
from ai_broadcaster.offline_memory_recall import (
    OfflineMemoryRecall, MAX_HANDOFF_EXCERPTS, MockNextSessionContext,
)
from ai_broadcaster.offline_past_broadcast_memory import OfflinePastBroadcastMemory


def memory():
    mem = OfflinePastBroadcastMemory()
    j = OfflineBroadcastJournal('지난 게임')
    j.add_mock_event('operator_note', '보스전 성공')
    j.add_mock_event('game_mock', '광산 탐험')
    mem.add_journal(j)
    k = OfflineBroadcastJournal('수다 회차')
    k.add_mock_event('operator_note', '다음에 영화 이야기')
    mem.add_journal(k)
    return mem


class MemoryRecallTests(unittest.TestCase):
    def setUp(self):
        self.mem = memory()
        self.recall = OfflineMemoryRecall(self.mem)

    def test_empty_has_no_hits(self):
        self.assertEqual(OfflineMemoryRecall(OfflinePastBroadcastMemory()).search('보스'), ())

    def test_case_insensitive_search(self):
        self.assertEqual(len(self.recall.search('보스전')), 1)
        self.assertEqual(self.recall.hits[0].session_label, '지난 게임')

    def test_search_label(self):
        self.assertEqual(self.recall.search('수다')[0].session_label, '수다 회차')

    def test_multiple_words_and(self):
        self.assertEqual(len(self.recall.search('게임 보스전')), 1)
        self.assertFalse(self.recall.search('게임 영화'))

    def test_match_zero_does_not_create_context(self):
        self.assertEqual(self.recall.search('존재하지않는검색어'), ())
        self.assertIsNone(self.recall.context)

    def test_operator_selection(self):
        hits = self.recall.search('보스전')
        context = self.recall.prepare_for_next_mock_session(0)
        self.assertEqual(context.session_label, hits[0].session_label)
        self.assertIn('보스전', context.preview())
        self.assertFalse(context.automatically_injected)
        self.assertFalse(context.model_connected)
        self.assertFalse(context.actual_broadcast_verified)
        self.assertEqual(context.approval, 'pending')

    def test_no_automatic_context(self):
        self.recall.search('광산')
        self.assertIsNone(self.recall.context)

    def test_no_selection_before_search(self):
        with self.assertRaises(ValueError):
            self.recall.prepare_for_next_mock_session(0)

    def test_reject_out_of_bounds(self):
        self.recall.search('보스')
        for i in (-1, 1, True, 0.0):
            with self.subTest(i=i), self.assertRaises(ValueError):
                self.recall.prepare_for_next_mock_session(i)

    def test_blank_invalid_query_clears(self):
        self.recall.search('보스')
        self.recall.prepare_for_next_mock_session(0)
        with self.assertRaises(ValueError):
            self.recall.search('   ')
        self.assertFalse(self.recall.hits)
        self.assertIsNone(self.recall.context)

    def test_control_char_and_overlength(self):
        for q in ('\n', 'test\nword', 'x' * 101, 'a b c d e f g h i'):
            with self.subTest(q=q), self.assertRaises(ValueError):
                self.recall.search(q)

    def test_wrong_query_type(self):
        with self.assertRaises(ValueError):
            self.recall.search(None)

    def test_clear(self):
        self.recall.search('보스')
        self.recall.prepare_for_next_mock_session(0)
        self.recall.clear()
        self.assertEqual(self.recall.hits, ())
        self.assertIsNone(self.recall.context)

    def test_remove_after_search_invalidates(self):
        self.recall.search('보스')
        self.mem.remove_card(0)
        self.assertFalse(self.recall.hits)
        with self.assertRaises(ValueError):
            self.recall.prepare_for_next_mock_session(0)

    def test_add_after_handoff_invalidates(self):
        self.recall.search('보스')
        self.recall.prepare_for_next_mock_session(0)
        j = OfflineBroadcastJournal('새 가상 회차')
        j.add_mock_event('operator_note', '새 기록')
        self.mem.add_journal(j)
        self.assertIsNone(self.recall.context)

    def test_research_invalidates_previous_context(self):
        self.recall.search('보스')
        self.recall.prepare_for_next_mock_session(0)
        self.recall.search('영화')
        self.assertIsNone(self.recall.context)

    def test_multiple_results_not_mixed(self):
        self.recall.search('회차')
        context = self.recall.prepare_for_next_mock_session(0)
        self.assertNotIn('보스전', context.preview())

    def test_bounded_excerpts(self):
        mem = OfflinePastBroadcastMemory()
        j = OfflineBroadcastJournal('많은 기록')
        for n in range(12):
            j.add_mock_event('operator_note', '광산 ' + str(n))
        mem.add_journal(j)
        rec = OfflineMemoryRecall(mem)
        rec.search('광산')
        self.assertEqual(len(rec.prepare_for_next_mock_session(0).excerpts), MAX_HANDOFF_EXCERPTS)

    def test_no_data_change(self):
        before = self.mem.preview()
        self.recall.search('보스')
        self.recall.prepare_for_next_mock_session(0)
        self.assertEqual(before, self.mem.preview())

    def test_no_external_access(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
             patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
            self.recall.search('보스')
            self.recall.prepare_for_next_mock_session(0)

    def test_source_provenance_not_just_label(self):
        self.recall.search('보스')
        ctx = self.recall.prepare_for_next_mock_session(0)
        self.assertEqual(ctx.source_checksum_sha256, self.mem.cards[0].source_checksum_sha256)
        self.assertFalse(ctx.mock_only is False)

    def test_immutable_context(self):
        self.recall.search('보스')
        ctx = self.recall.prepare_for_next_mock_session(0)
        with self.assertRaises(FrozenInstanceError):
            ctx.model_connected = True

    def test_next_mock_reply_requires_selected_memory(self):
        self.recall.search('보스전')
        with self.assertRaises(ValueError):
            self.recall.rehearse_next_mock_reply('지난 방송에 뭐 했어?')

    def test_next_mock_reply_reuses_existing_generator(self):
        self.recall.search('보스전')
        self.recall.prepare_for_next_mock_session(0)
        answer = self.recall.rehearse_next_mock_reply('가상 대화 다시 해봐')
        self.assertIn('보스전', answer)
        self.assertIn('가상 대화', answer)
        self.assertIn('실제 사실 아님', answer)

    def test_next_mock_reply_stale_state_denied(self):
        self.recall.search('보스전')
        self.recall.prepare_for_next_mock_session(0)
        self.mem.remove_card(0)
        with self.assertRaises(ValueError):
            self.recall.rehearse_next_mock_reply('가상 질문')

    def test_next_mock_reply_invalid_input_rejected(self):
        self.recall.search('보스전')
        self.recall.prepare_for_next_mock_session(0)
        with self.assertRaises(ValueError):
            self.recall.rehearse_next_mock_reply('q' * 181)

    def test_reject_other_memory_type(self):
        with self.assertRaises(ValueError):
            OfflineMemoryRecall([])


if __name__ == '__main__':
    unittest.main()
