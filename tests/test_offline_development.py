"""Real unit tests for local-only AISTING. No actual platform / paid API."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ai_broadcaster.offline_chat import (
    ChatMessage, ChatRehearsal, LocalMemory, LocalOllamaGenerator,
    MockReplyGenerator, parse_script,
)
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings, validate_settings


class DummyGenerator:
    def __init__(self):
        self.calls=[]
        self.fail=False

    def generate(self, chat, history):
        self.calls.append((chat,history))
        if self.fail:
            raise RuntimeError('local model test failure')
        return f'{chat.sender}님에게 응답: {chat.text}'


class TestScript(unittest.TestCase):
    def test_normal_script(self):
        msg=parse_script('철수: 안녕\n영희: 12:30인가?')
        self.assertEqual(msg,[ChatMessage('철수','안녕'),ChatMessage('영희','12:30인가?')])

    def test_same_message_kept(self):
        self.assertEqual(len(parse_script('A: ㅎㅎ\nA: ㅎㅎ\nA: ㅎㅎ')),3)

    def test_invalid_all_or_nothing(self):
        chat=ChatRehearsal()
        chat.add_script('A: 첫 글')
        with self.assertRaises(ValueError):chat.add_script('B: 정상\n잘못된 줄')
        self.assertEqual(chat.accepted,1)
        self.assertEqual(len(chat.pending),1)

    def test_invalid_limits(self):
        for script in ('','   ','nameonly',': no sender', 'A: ',
                       'A'*101+': text','A: '+'a'*4001,'a'*100001):
            with self.subTest(length=len(script)),self.assertRaises(ValueError):parse_script(script)

    def test_batch_limit(self):
        lines='\n'.join('A: '+str(i) for i in range(500))
        self.assertEqual(len(parse_script(lines)),500)
        with self.assertRaises(ValueError):parse_script(lines+'\nA: 500')

    def test_nonstring_rejected(self):
        with self.assertRaises(ValueError):parse_script(None)


class TestCore(unittest.TestCase):
    def setUp(self):
        self.gen=DummyGenerator()
        self.chat=ChatRehearsal(self.gen)

    def test_no_generator_before_click(self):
        self.chat.add_script('A: a')
        self.assertEqual(len(self.gen.calls),0)

    def test_all_fifo(self):
        self.chat.add_script('\n'.join(f'A{i}: 질문{i}' for i in range(40)))
        out=[]
        while self.chat.pending:
            self.chat.process_next(out.append)
        self.assertEqual([x.original.text for x in out], [f'질문{i}' for i in range(40)])
        self.assertEqual(self.chat.accepted,40)
        self.assertEqual(len(self.chat.completed),40)

    def test_duplicate_reply(self):
        self.chat.add_script('A: same\nA: same')
        one=self.chat.process_next(lambda a:None)
        two=self.chat.process_next(lambda a:None)
        self.assertEqual(one.original.text,two.original.text)
        self.assertEqual(len(self.gen.calls),2)

    def test_generator_failure_no_drop(self):
        self.chat.add_script('A: 안녕\nB: 반가워')
        self.gen.fail=True
        with self.assertRaises(RuntimeError):self.chat.process_next(lambda a:None)
        self.assertEqual(len(self.chat.pending),2)
        self.gen.fail=False
        self.chat.process_next(lambda a:None)
        self.assertEqual(len(self.chat.pending),1)

    def test_delivery_failure_reply_cached(self):
        self.chat.add_script('A: 안녕')
        with self.assertRaises(OSError):
            self.chat.process_next(lambda a: (_ for _ in ()).throw(OSError('display failure')))
        self.assertEqual(len(self.gen.calls),1)
        self.assertEqual(len(self.chat.pending),1)
        self.chat.process_next(lambda a:None)
        self.assertEqual(len(self.gen.calls),1)
        self.assertEqual(len(self.chat.pending),0)

    def test_context_for_following_messages(self):
        self.chat.add_script('A: 처음\nB: 나중')
        self.chat.process_next(lambda a:None)
        self.chat.process_next(lambda a:None)
        self.assertEqual(len(self.gen.calls[1][1]),1)
        self.assertEqual(self.gen.calls[1][1][0].original.text,'처음')

    def test_mock_offline(self):
        with patch('socket.create_connection') as conn:
            self.assertIn('모의 답변',MockReplyGenerator().generate(ChatMessage('A','hi'),[]))
            conn.assert_not_called()


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.p=Path(self.temp.name)/'data'/'history.sqlite3'
        self.mem=LocalMemory(self.p)

    def test_persist(self):
        chat=ChatRehearsal(DummyGenerator(),memory=self.mem)
        chat.add_script('A: 저장\nB: 다시')
        chat.process_next(lambda a: None)
        self.assertEqual(LocalMemory(self.p).recent()[0].original.text,'저장')
        chat.process_next(lambda a: None)
        self.assertEqual(len(LocalMemory(self.p).recent()),2)

    def test_failed_output_no_memory(self):
        chat=ChatRehearsal(memory=self.mem)
        chat.add_script('A: 저장안됨')
        with self.assertRaises(RuntimeError):
            chat.process_next(lambda a: (_ for _ in ()).throw(RuntimeError('fail')))
        self.assertEqual(self.mem.recent(),[])

    def test_clear_and_closed_database(self):
        chat=ChatRehearsal(memory=self.mem)
        chat.add_script('A: 저장')
        chat.process_next(lambda a: None)
        self.mem.clear()
        self.assertEqual(self.mem.recent(),[])
        # Critical for Windows: the sqlite handle must already be closed.
        self.p.unlink()
        self.assertFalse(self.p.exists())

    def test_history_zero_and_limit(self):
        self.assertEqual(self.mem.recent(0),[])
        with self.assertRaises(ValueError):self.mem.recent(51)


class TestOfflineSettings(unittest.TestCase):
    def test_default_restricts_real_actions(self):
        d=validate_settings(DEFAULTS)
        self.assertEqual(d['host'],'local_pc')
        self.assertEqual(d['budget'],'free_only')
        for field in ('scheduled_execution','streaming_enabled','external_publish_enabled'):
            self.assertFalse(d[field])

    def test_cannot_enable_schedule_or_broadcast(self):
        for flag in ('scheduled_execution','streaming_enabled','external_publish_enabled'):
            val=copy.deepcopy(DEFAULTS)
            val[flag]=True
            with self.subTest(flag=flag),self.assertRaises(ValueError):validate_settings(val)

    def test_save_roundtrip_no_network(self):
        with tempfile.TemporaryDirectory() as dirname:
            p=Path(dirname)/'settings.json'
            val=copy.deepcopy(DEFAULTS)
            val['platforms']=['chzzk','youtube']
            val['persona']['name']='시험'
            save_settings(val,p)
            self.assertEqual(load_settings(p),val)
            self.assertEqual(json.loads(p.read_text(encoding='utf-8'))['budget'],'free_only')

    def test_bad_platform_rejected(self):
        val=copy.deepcopy(DEFAULTS)
        val['platforms']=['fake']
        with self.assertRaises(ValueError):validate_settings(val)

    def test_no_automation_config_files(self):
        self.assertFalse((ROOT/'.github').exists())
        self.assertFalse((ROOT/'.git').exists())
        self.assertFalse((ROOT/'requirements.txt').exists())
        cfg=json.loads((ROOT/'config'/'requirements.json').read_text(encoding='utf-8'))
        self.assertIn('비활성',cfg['development_policy']['scheduled_work'])

    def test_exe_build_is_manual_only(self):
        build=(ROOT/'build_exe_windows.bat').read_text(encoding='utf-8')
        self.assertIn('PyInstaller',build)
        self.assertNotIn('pip install',build)
        self.assertNotIn('curl',build)
        self.assertNotIn('schtasks',build)


class FakeOllama(BaseHTTPRequestHandler):
    requests=[]

    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']))
        self.__class__.requests.append(json.loads(raw))
        content=json.dumps({'message':{'content':'안녕하세요!'}},ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self,*args):pass


class TestLocalModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),FakeOllama)
        cls.worker=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)

    def setUp(self):
        FakeOllama.requests=[]

    def test_manual_trigger_only(self):
        model=LocalOllamaGenerator('free-model',port=self.server.server_port)
        self.assertEqual(FakeOllama.requests,[])
        value=model.generate(ChatMessage('시청자','안녕'),[])
        self.assertEqual(value,'안녕하세요!')
        self.assertEqual(len(FakeOllama.requests),1)
        self.assertEqual(FakeOllama.requests[0]['stream'],False)

    def test_cannot_set_external_hostname(self):
        for model in ('https://evil.example','http://someplace','a b',''):
            with self.subTest(model=model),self.assertRaises(ValueError):
                LocalOllamaGenerator(model)


if __name__=='__main__':unittest.main()
