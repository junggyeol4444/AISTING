"""GitHub CI에서 외부 AI나 실제 방송 없이 대화 기억을 검증."""
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.chat_pipeline import ChatPipeline
from ai_broadcaster.conversation_memory import ConversationMemory
from ai_broadcaster.desktop_chat import run_local_chat
from ai_broadcaster.local_llm import LocalModelConfig, LocalModelError, LocalOllamaReplyGenerator
from ai_broadcaster.operator_settings import default_settings, save_settings
from ai_broadcaster.session import ChatMessage, SessionController


class FakeOllama(BaseHTTPRequestHandler):
    requests = []
    fail = False

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        data = json.loads(raw)
        type(self).requests.append(data)
        if type(self).fail:
            self.send_response(503)
            self.end_headers()
            return
        reply = f"대답{len(type(self).requests)}"
        body = json.dumps({"message": {"content": reply}}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class Collector:
    def __init__(self):
        self.lines = []
        self.fail = False

    def deliver(self, text):
        if self.fail:
            raise OSError("test output failure")
        self.lines.append(text)


class TestConversationMemory(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "history.sqlite3"
        self.memory = ConversationMemory(self.path)

    def test_foreign_database_is_refused_without_changing_existing_bytes(self):
        import sqlite3
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE foreign_data (secret TEXT)")
            db.execute("INSERT INTO foreign_data VALUES ('keep')")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "대화 기억 전용"):
            ConversationMemory(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT secret FROM foreign_data").fetchone()[0], "keep")

    def test_corrupt_sqlite_not_replaced_or_reinitialized(self):
        self.path.write_bytes(b"not-sqlite-user-data")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            ConversationMemory(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_valid_existing_memory_survives_read_only_schema_preflight(self):
        self.memory.append(ChatMessage("persist", "시청자", "같은 질문"), "응답")
        before = self.path.read_bytes()
        reopened = ConversationMemory(self.path)
        self.assertEqual(reopened.count(), 1)
        self.assertEqual(reopened.recent(1)[0].user_text, "같은 질문")
        self.assertEqual(self.path.read_bytes(), before)

    def test_symlinked_memory_path_is_refused_without_target_mutation(self):
        external = Path(self.folder.name) / "external.sqlite3"
        with sqlite3.connect(external) as db:
            db.execute("CREATE TABLE external_data(value TEXT)")
        before = external.read_bytes()
        link = Path(self.folder.name) / "linked.sqlite3"
        try:
            link.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("현재 Windows CI 계정은 심볼릭 링크 생성 권한이 없습니다")
        with self.assertRaisesRegex(ValueError, "심볼릭 링크"):
            ConversationMemory(link)
        self.assertEqual(external.read_bytes(), before)

    def test_empty_memory(self):
        self.assertEqual(self.memory.count(), 0)
        self.assertEqual(self.memory.recent(), [])

    def test_recent_order(self):
        for n in range(4):
            self.memory.append(ChatMessage(str(n), "시청자", f"메시지{n}"), f"답변{n}")
        self.assertEqual([r.reply for r in self.memory.recent(2)], ["답변2", "답변3"])

    def test_no_message_suppression(self):
        for n in range(2):
            self.memory.append(ChatMessage(str(n), "시청자", "ㅋㅋㅋ"), "하하")
        self.assertEqual(self.memory.count(), 2)

    def test_retention_policy(self):
        memory = ConversationMemory(self.path, max_exchanges=2)
        for n in range(3):
            memory.append(ChatMessage(str(n), "viewer", str(n)), "답변")
        self.assertEqual([r.user_text for r in memory.recent()], ["1", "2"])

    def test_unicode_and_restart_persistence(self):
        self.memory.append(ChatMessage("한글", "한국어", "이름은 세종"), "안녕하세요")
        again = ConversationMemory(self.path)
        self.assertEqual(again.recent()[0].user_text, "이름은 세종")

    def test_clear_all(self):
        self.memory.append(ChatMessage("1", "user", "안녕"), "하이")
        self.memory.clear()
        self.assertEqual(self.memory.count(), 0)

    def test_connection_closed_allows_file_delete_on_windows(self):
        self.memory.append(ChatMessage("1", "user", "hi"), "hello")
        self.memory.recent()
        self.memory.count()
        self.memory.clear()
        # 열린 sqlite 파일 핸들이 남았다면 Windows에서 PermissionError.
        self.path.unlink()
        self.assertFalse(self.path.exists())

    def test_invalid_limit(self):
        for limit in (-1, 101, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.memory.recent(limit)

    def test_recent_zero(self):
        self.memory.append(ChatMessage("1", "user", "안녕"), "하이")
        self.assertEqual(self.memory.recent(0), [])

    def test_invalid_max_records(self):
        with self.assertRaises(ValueError):
            ConversationMemory(self.path, max_exchanges=0)

    def test_invalid_reply(self):
        with self.assertRaises(ValueError):
            self.memory.append(ChatMessage("1", "user", "hi"), "   ")

    def test_long_text_bounded(self):
        self.memory.append(ChatMessage("1", "viewer", "가"*9000), "나"*9000)
        row = self.memory.recent()[0]
        self.assertEqual(len(row.user_text), 4000)
        self.assertEqual(len(row.reply), 6000)


class TestContextWithPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "memory.sqlite3"
        self.memory = ConversationMemory(self.path)
        self.cfg = LocalModelConfig("test", port=self.server.server_port)
        FakeOllama.requests = []
        FakeOllama.fail = False

    def pipeline(self, output=None, config=None):
        queue=SessionController()
        gen=LocalOllamaReplyGenerator(config or self.cfg, default_settings(), self.memory)
        return ChatPipeline(queue, gen, output or Collector())

    def test_next_message_has_previous_exchange(self):
        p = self.pipeline()
        p.queue.receive_chat(ChatMessage("1","A","오늘 이름은 뭐야"))
        p.process_next()
        p.queue.receive_chat(ChatMessage("2","B","방금 뭐라고 했어"))
        p.process_next()
        prompts = FakeOllama.requests
        self.assertEqual(len(prompts[0]["messages"]), 2)
        self.assertEqual(len(prompts[1]["messages"]), 4)
        self.assertEqual(prompts[1]["messages"][1]["content"], "A: 오늘 이름은 뭐야")
        self.assertEqual(prompts[1]["messages"][2]["content"], "대답1")
        self.assertEqual(self.memory.count(), 2)

    def test_output_failure_does_not_create_memory(self):
        output=Collector()
        output.fail=True
        p=self.pipeline(output)
        p.queue.receive_chat(ChatMessage("1","user","첫 채팅"))
        with self.assertRaises(OSError):
            p.process_next()
        self.assertEqual(self.memory.count(), 0)
        output.fail=False
        p.process_next()
        self.assertEqual(self.memory.count(), 1)
        self.assertEqual(len(FakeOllama.requests),1)

    def test_model_failure_does_not_create_memory(self):
        FakeOllama.fail=True
        p=self.pipeline()
        p.queue.receive_chat(ChatMessage("1","user","메시지"))
        with self.assertRaises(LocalModelError):
            p.process_next()
        self.assertEqual(self.memory.count(), 0)
        FakeOllama.fail=False
        p.process_next()
        self.assertEqual(self.memory.count(), 1)

    def test_context_window_bounds(self):
        cfg=LocalModelConfig("test",port=self.server.server_port,max_context_exchanges=1)
        p=self.pipeline(config=cfg)
        for n in range(3):
            p.queue.receive_chat(ChatMessage(str(n),"user",str(n)))
            p.process_next()
        self.assertEqual([len(p["messages"]) for p in FakeOllama.requests], [2,4,4])

    def test_context_zero(self):
        cfg=LocalModelConfig("test",port=self.server.server_port,max_context_exchanges=0)
        p=self.pipeline(config=cfg)
        for n in range(2):
            p.queue.receive_chat(ChatMessage(str(n),"user",str(n)))
            p.process_next()
        self.assertEqual([len(p["messages"]) for p in FakeOllama.requests],[2,2])

    def test_restart_keeps_context(self):
        p=self.pipeline()
        p.queue.receive_chat(ChatMessage("1","A","기억 테스트"))
        p.process_next()
        p2=self.pipeline()
        p2.queue.receive_chat(ChatMessage("2","B","기억해?"))
        p2.process_next()
        self.assertEqual(len(FakeOllama.requests[-1]["messages"]),4)

    def test_failed_history_callback_does_not_duplicate_output(self):
        class BrokenGenerator:
            def generate(self, message):
                return "답변"
            def on_delivered(self, message, reply):
                raise OSError("disk full")
        output=Collector()
        queue=SessionController()
        queue.receive_chat(ChatMessage("1","viewer","hi"))
        p=ChatPipeline(queue,BrokenGenerator(),output)
        p.process_next()
        self.assertEqual(output.lines,["답변"])
        self.assertEqual(queue.pending_chats,0)
        self.assertEqual(len(p.post_delivery_errors),1)
        self.assertIsNone(p.process_next())

    def test_desktop_chat_manual_text_only(self):
        with tempfile.TemporaryDirectory() as d:
            location=Path(d)
            settings=location/"settings.json"
            db=location/"remember.sqlite3"
            save_settings(default_settings(),settings)
            result=run_local_chat("test","안녕",port=self.server.server_port,
                                  settings_path=settings,memory_path=db)
            self.assertTrue(result.reply)
            self.assertEqual(result.remembered_count,1)

    def test_no_network_until_user_calls_generate(self):
        gen=LocalOllamaReplyGenerator(self.cfg,default_settings(),self.memory)
        self.assertEqual(FakeOllama.requests,[])
        gen.generate(ChatMessage("1","viewer","hello"))
        self.assertEqual(len(FakeOllama.requests),1)
        self.assertEqual(self.memory.count(),0)
