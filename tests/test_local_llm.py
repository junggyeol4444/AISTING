"""실제 Ollama 설치 없이 테스트용 localhost 서버를 사용한다."""
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.local_llm import (
    LocalModelConfig, LocalModelError, LocalOllamaReplyGenerator, persona_prompt,
)
from ai_broadcaster.operator_settings import default_settings
from ai_broadcaster.session import ChatMessage, SessionController
from ai_broadcaster.chat_pipeline import ChatPipeline


class LocalFakeServer(BaseHTTPRequestHandler):
    mode = "ok"
    requests = []

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.__class__.requests.append((self.path, data))
        if self.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "https://example.com/external")
            self.end_headers()
            return
        if self.mode == "error":
            self.send_response(500)
            self.end_headers()
            return
        result = {
            "ok": {"message": {"content": "반가워요!"}},
            "empty": {"message": {"content": ""}},
            "broken": {"unknown": True},
            "long": {"message": {"content": "가" * 100}},
        }[self.mode]
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class Collector:
    def __init__(self): self.lines = []
    def deliver(self, text): self.lines.append(text)


class TestLocalModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LocalFakeServer)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        LocalFakeServer.mode = "ok"
        LocalFakeServer.requests = []
        self.settings = default_settings()
        self.config = LocalModelConfig("qwen2.5:7b", port=self.server.server_port, timeout_seconds=3)

    def generator(self, config=None):
        return LocalOllamaReplyGenerator(config or self.config, self.settings)

    def test_no_connection_on_construction(self):
        self.generator()
        self.assertEqual(LocalFakeServer.requests, [])

    def test_endpoint_is_only_loopback(self):
        self.assertEqual(self.config.endpoint, f"http://127.0.0.1:{self.server.server_port}/api/chat")

    def test_persona(self):
        self.settings["persona"]["name"] = "새 캐릭터"
        self.assertIn("새 캐릭터", persona_prompt(self.settings))

    def test_http_contract_korean(self):
        result = self.generator().generate(ChatMessage("1", "시청자", "안녕"))
        self.assertEqual(result, "반가워요!")
        path, payload = LocalFakeServer.requests[0]
        self.assertEqual(path, "/api/chat")
        self.assertEqual(payload["model"], "qwen2.5:7b")
        self.assertIs(payload["stream"], False)
        self.assertEqual(payload["keep_alive"], "10m")
        self.assertEqual(payload["options"]["num_predict"], 96)
        self.assertIn("시청자: 안녕", payload["messages"][1]["content"])

    def test_bounded_response_and_persistent_model_are_configurable(self):
        self.assertEqual(LocalModelConfig("qwen2.5:0.5b").num_predict, 96)
        self.assertEqual(LocalModelConfig("qwen2.5:0.5b").keep_alive, "10m")
        for length in (0, 7, 2049, True, -5):
            with self.subTest(length=length), self.assertRaises(ValueError):
                LocalModelConfig("qwen2.5:0.5b", num_predict=length)
        for duration in ("", "unlimited", "-1m", "0s", "1000m", "10minutes"):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                LocalModelConfig("qwen2.5:0.5b", keep_alive=duration)

    def test_paid_api_permission_cannot_be_enabled(self):
        self.settings["operation"]["allow_paid_api"] = True
        with self.assertRaises(ValueError): self.generator()

    def test_bad_names_ports(self):
        for name in ("", "hello world", "model?key=abc"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                LocalModelConfig(name)
        with self.assertRaises(ValueError): LocalModelConfig("valid", port=0)
        with self.assertRaises(ValueError): LocalModelConfig("valid", timeout_seconds=0)

    def test_failures_preserve_chat_for_retry(self):
        LocalFakeServer.mode = "error"
        queue = SessionController()
        message = ChatMessage("1", "viewer", "test")
        queue.receive_chat(message)
        pipeline = ChatPipeline(queue, self.generator(), Collector())
        with self.assertRaises(LocalModelError): pipeline.process_next()
        self.assertEqual(queue.peek_chat(), message)
        LocalFakeServer.mode = "ok"
        self.assertEqual(pipeline.process_next().original, message)
        self.assertEqual(queue.pending_chats, 0)

    def test_redirect_denied(self):
        LocalFakeServer.mode = "redirect"
        with self.assertRaises(LocalModelError):
            self.generator().generate(ChatMessage("1", "viewer", "test"))

    def test_invalid_responses(self):
        for mode in ("empty", "broken", "long"):
            with self.subTest(mode=mode):
                LocalFakeServer.mode = mode
                cfg = LocalModelConfig("test", port=self.server.server_port, max_reply_chars=20)
                with self.assertRaises(LocalModelError):
                    self.generator(cfg).generate(ChatMessage("1", "viewer", "test"))

    def test_every_chat_fifo(self):
        queue, output = SessionController(), Collector()
        for n in range(10):
            queue.receive_chat(ChatMessage(str(n), "시청자", f"안녕{n}"))
        done = ChatPipeline(queue, self.generator(), output).drain()
        self.assertEqual(len(done), 10)
        self.assertEqual(len(output.lines), 10)
        self.assertEqual(queue.pending_chats, 0)
        self.assertEqual(
            [payload["messages"][-1]["content"] for _, payload in LocalFakeServer.requests],
            [f"시청자: 안녕{n}" for n in range(10)],
        )
