"""Original 038: no-chat-only simulated speech proposal, operator decides quality."""
import copy
import unittest
from unittest.mock import patch

from ai_broadcaster.idle_speech import IdleSpeechSession
from ai_broadcaster.offline_settings import DEFAULTS


class EchoPort:
    def __init__(self, *, fail=False):
        self.received = []
        self.fail = fail

    def generate(self, item, history):
        self.received.append((item, tuple(history)))
        if self.fail:
            raise RuntimeError('do-not-display-secret')
        return '모의 답변 ' + item.text


class IdleSpeechTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)
        self.port = EchoPort()
        self.session = IdleSpeechSession(self.settings, reply_port=self.port)

    def test_default_off_even_after_time_and_preview(self):
        self.session.advance(100)
        a = self.session.preview_if_idle()
        self.assertFalse(a.enabled)
        self.assertEqual(a.suggestions, ())
        self.assertEqual(self.port.received, [])

    def test_operator_arms_before_any_proposal(self):
        self.session.configure(enabled=True, threshold_seconds=5, utterance='내가 입력한 말')
        self.assertEqual(self.session.preview_if_idle().suggestions, ())
        self.session.advance(4)
        self.assertEqual(self.session.preview_if_idle().suggestions, ())
        self.session.advance(1)
        self.assertEqual(self.session.preview_if_idle().suggestions, ('내가 입력한 말',))

    def test_no_repeat_in_same_idle_period_even_long_wait(self):
        self.session.configure(enabled=True, threshold_seconds=3, utterance='안녕')
        self.session.advance(3)
        for _ in range(4):
            self.session.preview_if_idle()
            self.session.advance(500)
        self.assertEqual(self.session.audit().suggestions, ('안녕',))

    def test_chat_arrival_preempts_even_when_threshold_reached(self):
        self.session.configure(enabled=True, threshold_seconds=2, utterance='자발 발화')
        self.session.advance(2)
        self.session.receive_chat('철수: 안녕')
        self.assertEqual(self.session.audit().quiet_seconds, 0)
        self.session.advance(100)
        self.assertEqual(self.session.preview_if_idle().suggestions, ())
        self.assertIn('채팅 처리 우선', self.session.audit().reason)
        self.assertEqual(self.port.received, [])

    def test_chat_handled_fifo_without_default_delay(self):
        self.session.configure(enabled=True, threshold_seconds=1, utterance='모의 혼잣말')
        self.session.receive_chat('가: ㅋㅋㅋ\n가: ㅋㅋㅋ\n나: 안녕')
        self.session.process_batch()
        a = self.session.audit()
        self.assertEqual([i.input_text for i in a.chat.replied], ['ㅋㅋㅋ','ㅋㅋㅋ','안녕'])
        self.assertEqual(a.chat.attempts, 3)
        self.assertEqual(a.quiet_seconds, 0)
        self.assertEqual(a.suggestions, ())
        self.assertEqual(len(self.port.received), 3)

    def test_after_chat_idle_proposal_rearmed(self):
        self.session.configure(enabled=True, threshold_seconds=3, utterance='새 대화')
        self.session.advance(3)
        self.session.preview_if_idle()
        self.session.receive_chat('가: 하이')
        self.session.process_chat()
        self.session.advance(3)
        self.assertEqual(self.session.preview_if_idle().suggestions, ('새 대화','새 대화'))

    def test_failure_blocks_proposals_without_skipping(self):
        bad = EchoPort(fail=True)
        session = IdleSpeechSession(self.settings, reply_port=bad)
        session.configure(enabled=True, threshold_seconds=2, utterance='말')
        session.receive_chat('가: 실패\n나: 대기')
        result = session.process_chat()
        self.assertEqual(result.chat.failed_sequence, 1)
        session.advance(50)
        result = session.preview_if_idle()
        self.assertEqual(result.suggestions, ())
        self.assertEqual(len(result.chat.pending), 2)
        self.assertNotIn('do-not-display-secret', result.describe())

    def test_invalid_script_atomic_does_not_rearm(self):
        self.session.configure(enabled=True, threshold_seconds=2, utterance='말')
        self.session.advance(2)
        before = self.session.audit()
        with self.assertRaises(ValueError):
            self.session.receive_chat('잘못된 줄')
        self.assertEqual(before, self.session.audit())

    def test_invalid_configuration_atomic(self):
        self.session.configure(enabled=True, threshold_seconds=2, utterance='좋음')
        before = self.session.audit()
        for args in ({'enabled':1, 'threshold_seconds':2, 'utterance':'a'},
                     {'enabled':True, 'threshold_seconds':0, 'utterance':'a'},
                     {'enabled':True, 'threshold_seconds':True, 'utterance':'a'},
                     {'enabled':True, 'threshold_seconds':3601, 'utterance':'a'},
                     {'enabled':True, 'threshold_seconds':2, 'utterance':''},
                     {'enabled':True, 'threshold_seconds':2, 'utterance':'x'*241},
                     {'enabled':True, 'threshold_seconds':2, 'utterance':'a\nb'}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.session.configure(**args)
            self.assertEqual(before, self.session.audit())

    def test_virtual_time_strict_bounds_and_no_mutation(self):
        for value in (True, 0, -1, 86401, 1.5, '3'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.session.advance(value)
        self.assertEqual(self.session.audit().quiet_seconds, 0)

    def test_disabled_after_proposals_prevents_next_proposal(self):
        self.session.configure(enabled=True, threshold_seconds=1, utterance='문구')
        self.session.advance(1)
        self.session.preview_if_idle()
        self.session.configure(enabled=False, threshold_seconds=1, utterance='문구')
        self.session.receive_chat('가: 테스트')
        self.session.process_chat()
        self.session.advance(30)
        self.assertEqual(len(self.session.preview_if_idle().suggestions), 1)

    def test_changed_topic_reset_but_previous_audit_preserved(self):
        self.session.configure(enabled=True, threshold_seconds=1, utterance='문구1')
        self.session.advance(1)
        self.session.preview_if_idle()
        self.session.configure(enabled=True, threshold_seconds=5, utterance='문구2')
        self.assertEqual(self.session.audit().quiet_seconds, 0)
        self.session.advance(5)
        self.assertEqual(self.session.preview_if_idle().suggestions, ('문구1', '문구2'))

    def test_no_connection_storage_process_sleep_or_pc_probe(self):
        saved = copy.deepcopy(self.settings)
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as network, \
             patch('sqlite3.connect', side_effect=AssertionError('sqlite')) as db, \
             patch('time.sleep', side_effect=AssertionError('delay')) as sleep, \
             patch('platform.system', side_effect=AssertionError('PC')) as pc, \
             patch('subprocess.Popen', side_effect=AssertionError('launch')) as process:
            s = IdleSpeechSession(self.settings)
            s.configure(enabled=True, threshold_seconds=2, utterance='사용자 문구')
            s.receive_chat('가: hi')
            s.process_chat()
            s.advance(2)
            self.assertEqual(s.preview_if_idle().suggestions, ('사용자 문구',))
            network.assert_not_called(); db.assert_not_called(); sleep.assert_not_called()
            pc.assert_not_called(); process.assert_not_called()
        self.assertEqual(saved, self.settings)

    def test_new_session_isolated(self):
        self.session.configure(enabled=True, threshold_seconds=1, utterance='이전')
        self.session.advance(1)
        self.session.preview_if_idle()
        fresh = IdleSpeechSession(self.settings)
        self.assertEqual(fresh.audit().suggestions, ())
        self.assertFalse(fresh.audit().enabled)


if __name__ == '__main__':
    unittest.main()

class IdleRetryTests(unittest.TestCase):
    def test_manual_retry_recovers_without_background_retries(self):
        port = EchoPort(fail=True)
        s = IdleSpeechSession(copy.deepcopy(DEFAULTS), reply_port=port)
        s.configure(enabled=True, threshold_seconds=1, utterance='혼잣말')
        s.receive_chat('가: 실패\n나: 후속')
        s.process_batch()
        self.assertEqual(len(port.received), 1)
        s.advance(20)
        self.assertEqual(s.preview_if_idle().suggestions, ())
        port.fail = False
        s.process_chat(manual_retry=True)
        s.process_batch()
        self.assertEqual(s.audit().chat.attempts, 3)
        s.advance(1)
        self.assertEqual(s.preview_if_idle().suggestions, ('혼잣말',))

    def test_retry_without_failure_is_rejected(self):
        s = IdleSpeechSession(copy.deepcopy(DEFAULTS))
        with self.assertRaises(ValueError):
            s.process_chat(manual_retry=True)
