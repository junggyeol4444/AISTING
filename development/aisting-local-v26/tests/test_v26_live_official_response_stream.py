"""Offline upstream-wire contract tests only. NO real AI/voice/avatar execution."""
import base64
import io
from pathlib import Path
import queue
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import wave

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'payload/src'))
from ai_broadcaster import original_plan_conversation as chat
from ai_broadcaster import original_plan_studio as studio
from test_v22_upstream_session_reuse import LocalSocketFixture, init, answer, end


def wav_packet():
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        file.writeframes(b'\0\0' * 200)
    return base64.b64encode(buffer.getvalue()).decode('ascii')


class Output:
    def __init__(self):
        self.text = ''
    def configure(self, **_kwargs):
        pass
    def insert(self, _where, text):
        self.text += text
    def see(self, _where):
        pass


class Indicator:
    def __init__(self):
        self.value = ''
    def set(self, value):
        self.value = value


class FakeSession:
    def __init__(self):
        self.closed = False
    def close(self):
        self.closed = True


def ui_mock(items, *, busy=True, generation=4):
    q = queue.Queue()
    for item in items:
        q.put(item)
    output = Output()
    indicator = Indicator()
    state = Indicator()
    button = SimpleNamespace(configure=lambda **_kw: None)
    instance = SimpleNamespace(
        _closed=False, _events=q, _after_id=None,
        parent=SimpleNamespace(after=lambda *_args: 'scheduled'),
        _real_ai_generation=generation, _real_ai_busy=busy,
        _real_ai_window=SimpleNamespace(winfo_exists=lambda: True),
        _real_ai_output=output, _real_ai_stream_parts=[],
        _real_ai_stream_started=False, _ai_indicator=indicator,
        _ai_submit_button=button, real_ai_status=state,
        _real_ai_session=FakeSession(),
    )
    instance._consume_events = lambda: None
    return instance


class RealResponseStreamingContract(unittest.TestCase):
    def test_only_genuine_audio_display_text_is_delivered_in_arrival_order(self):
        socket = LocalSocketFixture()
        upstream = [init(), {'type':'full-text','text':'Thinking...'},
                    answer('안녕'), answer('하세요'), end()]
        events=[]
        with (patch.object(chat.socket,'create_connection',return_value=socket),
              patch.object(chat,'_read_http_upgrade',return_value=bytearray()),
              patch.object(chat,'_read_upstream_json',side_effect=upstream),
              patch.object(chat,'_send_masked')):
            with chat.OfficialConversationSession() as s:
                result=s.ask('질문',operator_approved=True,on_progress=lambda k,v:events.append((k,v)))
        self.assertEqual(result.text,'안녕하세요')
        self.assertEqual([v for k,v in events if k=='text'],['안녕','하세요'])
        self.assertEqual(events.count(('audio_invalid',0)), 2)
        self.assertNotIn(('text','Thinking...'),events)

    def test_audio_notifications_contain_size_only_never_wav_bytes(self):
        socket = LocalSocketFixture()
        events=[]
        upstream=[init(), {'type':'audio','audio':wav_packet(),'display_text':{'text':'대답'}},
                  {'type':'audio','audio':None,'display_text':{'text':' 끝'}},end()]
        with (patch.object(chat.socket,'create_connection',return_value=socket),
              patch.object(chat,'_read_http_upgrade',return_value=bytearray()),
              patch.object(chat,'_read_upstream_json',side_effect=upstream),
              patch.object(chat,'_send_masked')):
            with chat.OfficialConversationSession() as s:
                result=s.ask('테스트',operator_approved=True,on_progress=lambda k,v:events.append((k,v)))
        self.assertEqual(result.text,'대답 끝')
        self.assertEqual(len([x for x in events if x[0]=='audio_wav']),1)
        self.assertEqual(len([x for x in events if x[0]=='audio_silent']),1)
        self.assertTrue(all(isinstance(value,(int,str)) for _,value in events))

    def test_callback_exception_never_resends_prompt_or_breaks_core_response(self):
        socket = LocalSocketFixture()
        with (patch.object(chat.socket,'create_connection',return_value=socket),
              patch.object(chat,'_read_http_upgrade',return_value=bytearray()),
              patch.object(chat,'_read_upstream_json',side_effect=[init(),answer('응답'),end()]),
              patch.object(chat,'_send_masked') as send):
            with chat.OfficialConversationSession() as s:
                def bad_callback(*_):
                    raise RuntimeError('UI failure')
                result=s.ask('질문',operator_approved=True,on_progress=bad_callback)
        self.assertEqual(result.text,'응답')
        send.assert_called_once()

    def test_approval_required_even_with_callback(self):
        with patch.object(chat.socket,'create_connection') as con:
            with chat.OfficialConversationSession() as s:
                with self.assertRaises(PermissionError):
                    s.ask('질문',on_progress=lambda *_: None)
            con.assert_not_called()

    def test_invalid_callback_is_rejected_without_network(self):
        with patch.object(chat.socket,'create_connection') as con:
            with chat.OfficialConversationSession() as s:
                with self.assertRaises(TypeError):
                    s.ask('질문',operator_approved=True,on_progress='not callable')
            con.assert_not_called()

    def test_error_does_not_falsely_complete_partial_turn(self):
        events=[]
        with (patch.object(chat.socket,'create_connection',return_value=LocalSocketFixture()),
              patch.object(chat,'_read_http_upgrade',return_value=bytearray()),
              patch.object(chat,'_read_upstream_json',side_effect=[init(),answer('부분'),{'type':'error','message':'backend crash'}]),
              patch.object(chat,'_send_masked')):
            with chat.OfficialConversationSession() as s:
                with self.assertRaisesRegex(chat.RealConversationError,'backend crash'):
                    s.ask('질문',operator_approved=True,on_progress=lambda k,v:events.append((k,v)))
                self.assertEqual(s.turns_completed,0)
                self.assertFalse(s.connected)
        self.assertIn(('text','부분'),events)

    def test_gui_renders_real_arrival_order_without_duplicate_final_text(self):
        final=chat.RealConversationResult(text='안녕하세요',config_name='conf',model_name='model',
                                         segments=2,frames_received=4)
        app=ui_mock([('ai_progress',(4,'질문','text','안녕')),
                     ('ai_progress',(4,'질문','text','하세요')),
                     ('ai_result',(4,'질문',final))])
        studio.OriginalPlanStudio._consume_events(app)
        self.assertEqual(app._real_ai_output.text.count('안녕하세요'),1)
        self.assertIn('나: 질문\nAI: 안녕하세요',app._real_ai_output.text)
        self.assertIn('소리/립싱크는 미확인',app._real_ai_output.text)
        self.assertEqual(app._after_id,'scheduled')

    def test_gui_whitespace_trimmed_official_final_does_not_duplicate(self):
        final=chat.RealConversationResult(text='안녕하세요',config_name='conf',model_name='model',
                                         segments=2,frames_received=4)
        app=ui_mock([('ai_progress',(4,'질문','text',' 안녕')),
                     ('ai_progress',(4,'질문','text','하세요 ')),
                     ('ai_result',(4,'질문',final))])
        studio.OriginalPlanStudio._consume_events(app)
        self.assertEqual(app._real_ai_output.text.count('안녕하세요'),1)
        self.assertNotIn('[최종 응답]',app._real_ai_output.text)

    def test_gui_shows_partial_reply_as_incomplete_on_error(self):
        app=ui_mock([('ai_progress',(4,'질문','text','부분')),('ai_error',(4,'질문','LLM 오류'))])
        studio.OriginalPlanStudio._consume_events(app)
        self.assertIn('부분',app._real_ai_output.text)
        self.assertIn('부분 출력은 완료된 대화가 아닙니다',app._real_ai_output.text)
        self.assertIn('새 세션',app._ai_indicator.value)

    def test_stale_or_post_close_messages_are_never_drawn(self):
        app=ui_mock([('ai_progress',(3,'질문','text','오래된 응답')),
                     ('ai_progress',(4,'질문','text','바른 응답'))],busy=False)
        studio.OriginalPlanStudio._consume_events(app)
        self.assertEqual(app._real_ai_output.text,'')

    def test_real_progress_path_uses_main_thread_queue(self):
        source=(BASE/'payload/src/ai_broadcaster/original_plan_studio.py').read_text('utf-8')
        self.assertIn("self._events.put(('ai_progress'",source)
        self.assertIn("session.ask(message, operator_approved=True, on_progress=progress)",source)
        self.assertNotIn('audio_bytes_as_base64_for_widget',source)


if __name__=='__main__':
    unittest.main()
