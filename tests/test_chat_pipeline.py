import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.session import ChatMessage, SessionController
from ai_broadcaster.chat_pipeline import ChatPipeline


class FakeGenerator:
    def __init__(self):
        self.requests = []
        self.fail = False
    def generate(self, m):
        self.requests.append(m.message_id)
        if self.fail:
            raise ConnectionError('model unavailable')
        return f'{m.sender}: {m.text}에 대한 테스트 답변'


class FakeOutput:
    def __init__(self):
        self.lines = []
        self.fail = False
    def deliver(self, reply):
        if self.fail:
            raise ConnectionError('speaker unavailable')
        self.lines.append(reply)


class TestChatPipeline(unittest.TestCase):
    def setUp(self):
        self.queue = SessionController()
        self.generator = FakeGenerator()
        self.output = FakeOutput()
        self.pipeline = ChatPipeline(self.queue, self.generator, self.output)

    def test_empty_queue(self):
        self.assertIsNone(self.pipeline.process_next())
        self.assertEqual(self.pipeline.drain(), [])

    def test_all_chats_in_order(self):
        for i in range(30):
            self.queue.receive_chat(ChatMessage(str(i), 'viewer', 'ㅋㅋㅋ'))
        result = self.pipeline.drain()
        self.assertEqual([r.original.message_id for r in result], [str(i) for i in range(30)])
        self.assertEqual(len(self.output.lines), 30)
        self.assertEqual(self.queue.processed_chats, 30)
        self.assertEqual(self.queue.pending_chats, 0)

    def test_generator_failure_keeps_chat(self):
        msg = ChatMessage('1', 'viewer', '안녕')
        self.queue.receive_chat(msg)
        self.generator.fail = True
        with self.assertRaises(ConnectionError):
            self.pipeline.process_next()
        self.assertEqual(self.queue.peek_chat(), msg)
        self.generator.fail = False
        self.assertEqual(self.pipeline.process_next().original, msg)
        self.assertEqual(self.queue.pending_chats, 0)

    def test_speaker_failure_does_not_acknowledge_chat(self):
        msg = ChatMessage('1', 'viewer', '안녕')
        self.queue.receive_chat(msg)
        self.output.fail = True
        with self.assertRaises(ConnectionError):
            self.pipeline.process_next()
        self.assertEqual(self.queue.pending_chats, 1)
        self.assertEqual(self.queue.processed_chats, 0)
        self.output.fail = False
        self.assertEqual(self.pipeline.process_next().original, msg)
        self.assertEqual(self.generator.requests, ['1'])  # no duplicate generation

    def test_cannot_acknowledge_wrong_head(self):
        msg = ChatMessage('1', 'viewer', 'hello')
        self.queue.receive_chat(msg)
        with self.assertRaises(RuntimeError):
            self.queue.acknowledge_chat(ChatMessage('2', 'viewer', 'hello'))
        self.assertEqual(self.queue.peek_chat(), msg)

    def test_empty_reply_rejected_not_dropped(self):
        self.queue.receive_chat(ChatMessage('1', 'u', 'Hi'))
        self.generator.generate = lambda m: '   '
        with self.assertRaises(ValueError):
            self.pipeline.process_next()
        self.assertEqual(self.queue.pending_chats, 1)

    def test_output_order_equal_input_order(self):
        self.queue.receive_chat(ChatMessage('a', '하나', '첫번째'))
        self.queue.receive_chat(ChatMessage('b', '둘', '두번째'))
        self.pipeline.process_next()
        self.pipeline.process_next()
        self.assertIn('첫번째', self.output.lines[0])
        self.assertIn('두번째', self.output.lines[1])


if __name__ == '__main__':
    unittest.main()
