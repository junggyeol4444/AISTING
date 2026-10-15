"""Original roadmap 035: reaction coverage, non-dropping and opt-in execution."""
from __future__ import annotations
import copy
import unittest
from unittest.mock import patch

from ai_broadcaster.basic_reaction_test import (
    SAMPLE_REACTION_SCRIPT, MAX_REACTION_TURNS, MAX_REACTION_SCRIPT,
    run_basic_reaction_test,
)
from ai_broadcaster.offline_settings import DEFAULTS


class SpyPort:
    def __init__(self, *, fail_at=None, invalid_at=None):
        self.calls = []
        self.fail_at = fail_at
        self.invalid_at = invalid_at

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        if self.fail_at == len(self.calls):
            raise RuntimeError('secret/token should not leak')
        if self.invalid_at == len(self.calls):
            return '  '
        return f'반응: {item.text}'


class BasicReactionTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def test_default_all_answered_once_and_duplicates_preserved(self):
        result = run_basic_reaction_test(self.settings)
        self.assertTrue(result.passed)
        self.assertEqual((result.total, result.passed_count, result.attempts, result.remaining), (6, 6, 6, 0))
        self.assertEqual([(x.sender, x.input_text) for x in result.checks[:3]],
                         [('별', '안녕!'), ('달', 'ㅋㅋㅋ'), ('별', '안녕!')])
        self.assertEqual([x.context_count for x in result.checks], list(range(6)))

    def test_user_defined_exact_fifo_and_unicode(self):
        port = SpyPort()
        result = run_basic_reaction_test(self.settings, '가: ㅋㅋㅋ\n나: hi 🎈\n가: ㅋㅋㅋ', reply_port=port)
        self.assertTrue(result.passed)
        self.assertEqual([x.text for x, _ in port.calls], ['ㅋㅋㅋ', 'hi 🎈', 'ㅋㅋㅋ'])
        self.assertIn('🎈', result.checks[1].reply)

    def test_context_exact_latest_eight_no_skips(self):
        port = SpyPort()
        script = '\n'.join(f'가: 내용{i}' for i in range(12))
        result = run_basic_reaction_test(self.settings, script, reply_port=port)
        self.assertTrue(result.passed)
        self.assertEqual([t.context_count for t in result.checks], list(range(9)) + [8] * 3)
        self.assertEqual([x.input.text for x in port.calls[11][1]], [f'내용{i}' for i in range(3, 11)])

    def test_failure_keeps_remaining_queue_without_auto_retry_and_redacts_error(self):
        port = SpyPort(fail_at=3)
        result = run_basic_reaction_test(self.settings, SAMPLE_REACTION_SCRIPT, reply_port=port)
        self.assertFalse(result.passed)
        self.assertEqual((result.passed_count, result.remaining, result.attempts), (2, 4, 3))
        self.assertNotIn('secret/token', result.describe())
        self.assertIn('자동 재시도 없음', result.stopped_reason)

    def test_blank_reply_does_not_mark_complete(self):
        port = SpyPort(invalid_at=2)
        result = run_basic_reaction_test(self.settings, SAMPLE_REACTION_SCRIPT, reply_port=port)
        self.assertFalse(result.passed)
        self.assertEqual((result.remaining, result.attempts), (5, 2))

    def test_zero_truncated_and_invalid_input(self):
        with self.assertRaises(ValueError): run_basic_reaction_test(self.settings, '')
        with self.assertRaises(ValueError): run_basic_reaction_test(self.settings, '말머리 누락')
        for invalid in (None, 123, b'bytes', 'a' * (MAX_REACTION_SCRIPT + 1)):
            with self.subTest(invalid=type(invalid)), self.assertRaises(ValueError):
                run_basic_reaction_test(self.settings, invalid)
        with self.assertRaises(ValueError):
            run_basic_reaction_test(self.settings, '\n'.join('가: 안녕' for _ in range(MAX_REACTION_TURNS + 1)))

    def test_thirty_accepted_and_independent_runs(self):
        script = '\n'.join('가: 안녕' for _ in range(MAX_REACTION_TURNS))
        self.assertTrue(run_basic_reaction_test(self.settings, script).passed)
        self.assertEqual(run_basic_reaction_test(self.settings, '나: 안녕').attempts, 1)

    def test_never_mutates_original_settings(self):
        saved = copy.deepcopy(self.settings)
        run_basic_reaction_test(self.settings)
        self.assertEqual(saved, self.settings)

    def test_no_network_sqlite_process_or_pc_probe(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as net, \
             patch('sqlite3.connect', side_effect=AssertionError('sqlite')) as sql, \
             patch('subprocess.Popen', side_effect=AssertionError('process')) as proc, \
             patch('platform.system', side_effect=AssertionError('pc')) as pc:
            self.assertTrue(run_basic_reaction_test(self.settings).passed)
            net.assert_not_called(); sql.assert_not_called(); proc.assert_not_called(); pc.assert_not_called()

    def test_does_not_inject_unapproved_reaction_or_boundaries(self):
        with patch('ai_broadcaster.operator_boundaries.load_boundaries', side_effect=AssertionError('operator file')) as boundary:
            self.assertTrue(run_basic_reaction_test(self.settings).passed)
            boundary.assert_not_called()

    def test_no_implicit_delay_or_sleeps(self):
        with patch('time.sleep', side_effect=AssertionError('artificial delay')):
            self.assertTrue(run_basic_reaction_test(self.settings).passed)


if __name__ == '__main__':
    unittest.main()
