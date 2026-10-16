"""Only protocol contract checks. Does NOT run real LLM, sound, or stream."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload/src'))
from ai_broadcaster import original_plan_conversation as chat


class LocalSocketFixture:
    def __init__(self):
        self.sent = []
        self.closed = False
    def sendall(self, data):
        self.sent.append(data)
    def shutdown(self, *_):
        pass
    def close(self):
        self.closed = True


def init(name='known-conf'):
    return {'type': 'set-model-and-conf', 'conf_name': name,
            'client_uid': 'server-generated-id',
            'model_info': {'name': 'real-configured-model',
                           'url': '/live2d-models/mao_pro/runtime/mao_pro.model3.json'}}


def answer(text):
    return {'type': 'audio', 'audio': 'BASE64_IS_NEVER_PLAYED',
            'display_text': {'name': 'AI', 'text': text}}


def end():
    return {'type': 'control', 'text': 'conversation-chain-end'}


class RealUpstreamSessionContract(unittest.TestCase):
    def test_two_approved_turns_reuse_connection_without_replaying_old_prompt(self):
        fake = LocalSocketFixture()
        events = [init(), answer('첫 번째'), end(), answer('두 번째'), end()]
        with (patch.object(chat.socket, 'create_connection', return_value=fake) as connector,
              patch.object(chat, '_read_http_upgrade', return_value=bytearray()),
              patch.object(chat, '_read_upstream_json', side_effect=events),
              patch.object(chat, '_send_masked') as send):
            session = chat.OfficialConversationSession()
            self.assertFalse(session.connected)
            result1 = session.ask('안녕', operator_approved=True)
            result2 = session.ask('두 번째 질문', operator_approved=True)
            self.assertEqual((result1.text, result2.text), ('첫 번째', '두 번째'))
            self.assertEqual([result1.turn_number, result2.turn_number], [1, 2])
            self.assertEqual(connector.call_count, 1)
            self.assertEqual(send.call_count, 2)
            self.assertIn('안녕', send.call_args_list[0].args[2].decode('utf-8'))
            self.assertIn('두 번째 질문', send.call_args_list[1].args[2].decode('utf-8'))
            session.close()
            self.assertTrue(fake.closed)

    def test_each_turn_still_requires_new_explicit_approval(self):
        fake = LocalSocketFixture()
        with (patch.object(chat.socket, 'create_connection', return_value=fake) as conn,
              patch.object(chat, '_read_http_upgrade', return_value=bytearray()),
              patch.object(chat, '_read_upstream_json', side_effect=[init(), answer('답'), end()])):
            with chat.OfficialConversationSession() as session:
                with self.assertRaises(PermissionError):
                    session.ask('미승인')
                conn.assert_not_called()
                session.ask('승인된 질문', operator_approved=True)
                with self.assertRaises(PermissionError):
                    session.ask('미승인된 다음 질문')
                self.assertEqual(conn.call_count, 1)

    def test_upstream_error_does_not_fake_reply_or_automatically_resend(self):
        fake = LocalSocketFixture()
        with (patch.object(chat.socket, 'create_connection', return_value=fake) as conn,
              patch.object(chat, '_read_http_upgrade', return_value=bytearray()),
              patch.object(chat, '_read_upstream_json', side_effect=[init(), {'type': 'error', 'message': 'backend failure'}]),
              patch.object(chat, '_send_masked') as send):
            with chat.OfficialConversationSession() as session:
                with self.assertRaisesRegex(chat.RealConversationError, 'backend failure'):
                    session.ask('실제 서버 질문', operator_approved=True)
                self.assertFalse(session.connected)
                self.assertEqual(session.turns_completed, 0)
                self.assertEqual(send.call_count, 1)
                self.assertEqual(conn.call_count, 1)


if __name__ == '__main__':
    unittest.main()
