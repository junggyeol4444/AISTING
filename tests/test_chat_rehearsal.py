"""무료 다중 채팅 연습 기능: 모든 메시지 FIFO/실패 보존/실방송 차단 테스트."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ai_broadcaster.chat_rehearsal import (
    ChatRehearsal, ChatScriptError, MockKoreanReplyGenerator, parse_chat_script,
    MAX_MESSAGES_PER_BATCH, MAX_SCRIPT_CHARS,
)
from ai_broadcaster.session import ChatMessage


class FakeGenerator:
    def __init__(self):
        self.seen=[]
        self.should_fail=False

    def generate(self, message):
        self.seen.append(message.message_id)
        if self.should_fail:
            raise RuntimeError("로컬 모델 연결 실패")
        return f"{message.sender}: {message.text} 재현 답변"


class TestChatScript(unittest.TestCase):
    def test_parse_multiple_korean_viewers(self):
        messages=parse_chat_script("철수: 안녕\n영희: 나는 게임 좋아해\n홍길동: 반갑습니다")
        self.assertEqual([(m.sender,m.text) for m in messages],
                         [("철수","안녕"),("영희","나는 게임 좋아해"),("홍길동","반갑습니다")])
        self.assertEqual(len(set(m.message_id for m in messages)),3)

    def test_duplicate_text_never_filtered(self):
        messages=parse_chat_script("A: ㅋㅋㅋ\nA: ㅋㅋㅋ\nB: ㅋㅋㅋ")
        self.assertEqual([m.text for m in messages],["ㅋㅋㅋ"]*3)
        self.assertEqual(len(set(m.message_id for m in messages)),3)

    def test_colons_in_text_are_preserved(self):
        m=parse_chat_script("시청자: 시간은 12:34:56")[0]
        self.assertEqual(m.text,"시간은 12:34:56")

    def test_blank_lines_are_not_chat_events(self):
        m=parse_chat_script("\nA: 한 줄\n\nB: 둘\n")
        self.assertEqual(len(m),2)

    def test_invalid_line_rejects_entire_batch(self):
        for bad in ("A: 정상\n잘못된 줄","  ","A:   "," : no sender","A: yes\nB:"):
            with self.subTest(bad=bad),self.assertRaises(ChatScriptError):
                parse_chat_script(bad)

    def test_non_string_script_rejected(self):
        for bad in (None,[],123):
            with self.subTest(bad=bad),self.assertRaises(ChatScriptError):
                parse_chat_script(bad)

    def test_limits_explicit_not_silent(self):
        accepted="\n".join(f"A: {i}" for i in range(MAX_MESSAGES_PER_BATCH))
        self.assertEqual(len(parse_chat_script(accepted)),500)
        with self.assertRaises(ChatScriptError):
            parse_chat_script(accepted+"\nA: overflow")
        with self.assertRaises(ChatScriptError):
            parse_chat_script("A: "+"a" * MAX_SCRIPT_CHARS)

    def test_sender_text_bounds(self):
        for bad in ("A"*101+": hi","A: "+"가"*4001):
            with self.subTest(length=len(bad)),self.assertRaises(ChatScriptError):
                parse_chat_script(bad)


class TestChatRehearsal(unittest.TestCase):
    def setUp(self):
        self.generator=FakeGenerator()
        self.app=ChatRehearsal(self.generator)

    def test_no_external_calls_when_constructing(self):
        with patch("socket.create_connection") as conn:
            ChatRehearsal()
            conn.assert_not_called()

    def test_add_script_does_not_call_ai(self):
        self.assertEqual(self.app.add_script("A: 1\nB: 2"),2)
        self.assertEqual(self.generator.seen,[])
        self.assertEqual(self.app.status.pending,2)
        self.assertEqual(self.app.status.processed,0)

    def test_rollback_whole_invalid_script(self):
        self.app.add_script("A: existing")
        with self.assertRaises(ChatScriptError):
            self.app.add_script("B: valid\nINVALID")
        self.assertEqual(self.app.status.pending,1)
        self.assertEqual(self.app.status.total,1)

    def test_no_invented_delay_and_fifo_for_all(self):
        self.app.add_script("\n".join(f"시청자{i%7}: 질문{i}" for i in range(50)))
        results=[]
        while self.app.status.pending:
            results.append(self.app.process_next())
        self.assertEqual(len(results),50)
        self.assertEqual([x.original.text for x in results],[f"질문{i}" for i in range(50)])
        self.assertEqual(self.app.status.total,50)
        self.assertEqual(self.app.status.processed,50)
        self.assertEqual(self.app.status.pending,0)
        self.assertEqual(self.generator.seen,[x.original.message_id for x in results])
        self.assertEqual(len(set(self.generator.seen)),50)
        self.assertIsNone(self.app.process_next())

    def test_repeated_message_still_generates_repeated_answer(self):
        self.app.add_script("A: 같은 내용\nA: 같은 내용\nA: 같은 내용")
        replies=[self.app.process_next() for _ in range(3)]
        self.assertEqual(len(replies),3)
        self.assertEqual(self.app.status.processed,3)
        self.assertEqual(len(self.generator.seen),3)

    def test_generator_failure_does_not_remove_any_chat(self):
        self.app.add_script("A: 첫번째\nB: 두번째")
        self.generator.should_fail=True
        with self.assertRaises(RuntimeError):
            self.app.process_next()
        self.assertEqual(self.app.status.processed,0)
        self.assertEqual(self.app.status.pending,2)
        self.generator.should_fail=False
        self.assertEqual(self.app.process_next().original.text,"첫번째")
        self.assertEqual(self.app.process_next().original.text,"두번째")
        self.assertEqual(self.app.status.pending,0)

    def test_output_failure_retries_without_regenerating(self):
        self.app.add_script("A: 첫번째\nB: 두번째")
        self.app.output.deliver=lambda _: (_ for _ in ()).throw(OSError("mock display"))
        with self.assertRaises(OSError):
            self.app.process_next()
        self.assertEqual(self.app.status.pending,2)
        self.assertEqual(self.app.status.processed,0)
        self.assertEqual(len(self.generator.seen),1)
        self.app.output.deliver=lambda text: setattr(self.app.output,"last",text)
        self.app.process_next()
        self.assertEqual(len(self.generator.seen),1)
        self.assertEqual(self.app.status.pending,1)

    def test_mock_reply_is_explicitly_mock(self):
        r=MockKoreanReplyGenerator().generate(ChatMessage("1","A","안녕"))
        self.assertIn("모의 응답",r)

    def test_new_scripts_accumulate_not_overwrite(self):
        self.app.add_script("A: 먼저")
        self.app.add_script("B: 나중")
        self.assertEqual(self.app.status.total,2)
        self.assertEqual(self.app.process_next().original.sender,"A")
        self.assertEqual(self.app.process_next().original.sender,"B")

    def test_gui_contains_manual_start_and_stop_without_platform(self):
        s=(ROOT/"src/ai_broadcaster/desktop_rehearsal_tab.py").read_text(encoding="utf-8")
        self.assertIn('text="모두 답변"',s)
        self.assertIn('text="현재 답변 후 중지"',s)
        self.assertIn('ChatRehearsal()',s)
        self.assertIn('LocalOllamaReplyGenerator(',s)
        self.assertNotIn('StartStream',s)
        self.assertNotIn('schedule=',s)

    def test_exe_wires_rehearsal_tab(self):
        code=(ROOT/"src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn('(rehearsal, "시청자 채팅 연습")',code)
        self.assertIn('tabs.add(tab, text=label)',code)
        self.assertIn('self._build_rehearsal(rehearsal)',code)
        self.assertIn('self._runner = ChatRehearsal()',code)


if __name__=="__main__":
    unittest.main()
