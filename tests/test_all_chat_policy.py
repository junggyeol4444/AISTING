"""Original roadmap 037: all accepted chats get distinct, non-filtered handling."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_broadcaster.all_chat_policy import AllChatPolicySession
from ai_broadcaster.offline_settings import DEFAULTS


class IntermittentPort:
    def __init__(self, bad_at=None):
        self.calls = []
        self.bad_at = bad_at

    def generate(self, item, history):
        self.calls.append((item, tuple(history)))
        if len(self.calls) == self.bad_at:
            raise RuntimeError('private-token-never-print')
        return '응답: ' + item.text


class AllChatPolicyTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def test_append_only_queues_never_answers_automatically(self):
        port = IntermittentPort()
        queue = AllChatPolicySession(self.settings, reply_port=port)
        self.assertEqual(queue.append('가: 안녕\n가: 안녕\n나: ㅋㅋㅋ'), 3)
        audit = queue.audit()
        self.assertEqual((audit.accepted, len(audit.pending), len(audit.replied), audit.attempts), (3, 3, 0, 0))
        self.assertEqual([p[0] for p in audit.pending], [1, 2, 3])
        self.assertEqual(port.calls, [])

    def test_duplicate_events_all_replied_once_and_fifo(self):
        port = IntermittentPort()
        q = AllChatPolicySession(self.settings, reply_port=port)
        q.append('가: ㅋㅋㅋ\n가: ㅋㅋㅋ\n나: 😊')
        audit = q.run_batch()
        self.assertTrue(audit.all_responded)
        self.assertEqual([p.sequence for p in audit.replied], [1, 2, 3])
        self.assertEqual([p.input_text for p in audit.replied], ['ㅋㅋㅋ', 'ㅋㅋㅋ', '😊'])
        self.assertEqual(audit.attempts, 3)
        self.assertEqual([c[0].sender for c in port.calls], ['가', '가', '나'])

    def test_multi_batch_append_keeps_all_events_and_context(self):
        port = IntermittentPort()
        q = AllChatPolicySession(self.settings, reply_port=port)
        q.append('가: one\n가: two')
        self.assertEqual(len(q.run_batch(1).replied), 1)
        q.append('나: three\n가: one')
        result = q.run_batch()
        self.assertTrue(result.all_responded)
        self.assertEqual([x.input_text for x in result.replied], ['one', 'two', 'three', 'one'])
        self.assertEqual([len(h) for _, h in port.calls], [0, 1, 2, 3])

    def test_failure_blocks_implicit_progress_and_keeps_every_chat(self):
        port = IntermittentPort(bad_at=2)
        q = AllChatPolicySession(self.settings, reply_port=port)
        q.append('가: a\n나: b\n다: c')
        failed = q.run_batch()
        self.assertFalse(failed.all_responded)
        self.assertEqual((len(failed.replied), len(failed.pending), failed.failed_sequence), (1, 2, 2))
        self.assertNotIn('private-token-never-print', failed.describe())
        self.assertEqual(q.run_batch().attempts, 2)
        self.assertEqual(q.run_next().attempts, 2)
        recovered = q.run_next(manual_retry=True)
        self.assertEqual((len(recovered.replied), recovered.attempts), (2, 3))
        done = q.run_batch()
        self.assertTrue(done.all_responded)
        self.assertEqual(done.attempts, 4)
        self.assertEqual([x.input_text for x in done.replied], ['a', 'b', 'c'])

    def test_manual_retry_requires_failure(self):
        q = AllChatPolicySession(self.settings)
        q.append('가: 안녕')
        with self.assertRaises(ValueError):
            q.run_next(manual_retry=True)
        self.assertTrue(q.run_next().all_responded)
        with self.assertRaises(ValueError):
            q.run_next(manual_retry=True)

    def test_failing_reply_not_auto_discarded_and_limit_remains(self):
        class AlwaysFails:
            def generate(self, item, history):
                raise TimeoutError('secret')
        q = AllChatPolicySession(self.settings, reply_port=AlwaysFails())
        q.append('a: 1\na: 2')
        q.run_next()
        q.run_next(manual_retry=True)
        a = q.run_next(manual_retry=True)
        self.assertEqual((len(a.pending), a.attempts), (2, 3))
        a = q.run_next(manual_retry=True)
        self.assertEqual((len(a.pending), a.attempts, a.failed_sequence), (2, 4, 1))
        self.assertNotIn('secret', a.describe())

    def test_atomic_invalid_append_and_existing_data_intact(self):
        q = AllChatPolicySession(self.settings)
        q.append('가: ok')
        before = q.audit()
        for bad in ('malformed', '', '가: ok\nmalformed'):
            with self.assertRaises(ValueError):
                q.append(bad)
            self.assertEqual(q.audit(), before)
        self.assertTrue(q.run_next().all_responded)

    def test_total_limit_and_batch_limit_are_strict(self):
        q = AllChatPolicySession(self.settings)
        q.append('\n'.join('가: ㅋㅋㅋ' for _ in range(500)))
        self.assertEqual(q.audit().accepted, 500)
        with self.assertRaises(ValueError):
            q.append('나: +1')
        for value in (0, 51, True, '3'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                q.run_batch(value)
        self.assertEqual(len(q.run_batch().replied), 50)
        for _ in range(9):
            audit = q.run_batch()
        self.assertTrue(audit.all_responded)
        self.assertEqual([x.sequence for x in audit.replied], list(range(1, 501)))

    def test_no_silent_skipping_even_for_whitespace_or_emoji(self):
        q = AllChatPolicySession(self.settings)
        q.append('가: ?\n나: ㅋㅋㅋ\n가: ?\n다: 🍀')
        result = q.run_batch()
        self.assertTrue(result.all_responded)
        self.assertEqual(len(result.replied), 4)

    def test_failed_append_does_not_mutate_settings(self):
        saved = copy.deepcopy(self.settings)
        q = AllChatPolicySession(self.settings)
        q.append('가: 안녕')
        q.run_batch()
        self.assertEqual(self.settings, saved)

    def test_no_file_network_sleep_pc_probe_or_auto_broadcast(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as network, \
             patch('sqlite3.connect', side_effect=AssertionError('sqlite')) as sqlite, \
             patch('time.sleep', side_effect=AssertionError('wait')) as sleep, \
             patch('platform.system', side_effect=AssertionError('PC')) as pc, \
             patch('subprocess.Popen', side_effect=AssertionError('launch')) as process:
            q = AllChatPolicySession(self.settings)
            q.append('a: hi\na: hi')
            self.assertTrue(q.run_batch().all_responded)
            network.assert_not_called(); sqlite.assert_not_called(); sleep.assert_not_called()
            pc.assert_not_called(); process.assert_not_called()

    def test_new_session_isolated(self):
        q1 = AllChatPolicySession(self.settings)
        q1.append('가: hi')
        q1.run_next()
        q2 = AllChatPolicySession(self.settings)
        self.assertEqual((q2.audit().accepted, q2.audit().attempts), (0, 0))


if __name__ == '__main__':
    unittest.main()
