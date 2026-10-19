"""Official Open-LLM-VTuber single-session dispatch, never two LLM calls."""
import queue
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.desktop_chat_tab import LocalChatTab
from ai_broadcaster.multiplatform_readonly import PlatformChat

class Live2DOfficialRoutingTests(unittest.TestCase):
    def test_every_message_goes_once_to_official_ipc_not_ollama(self):
        inbox,outbox=queue.SimpleQueue(),queue.SimpleQueue()
        for t in ("안녕","안녕","다음 채팅"):
            inbox.put(PlatformChat("room","user",t,"chzzk"))
        inbox.put(None)
        receiver=SimpleNamespace(_results=outbox)
        accepted=[]
        def send(text,*,operator_approved,duration):
            self.assertTrue(operator_approved)
            self.assertEqual(duration,8)
            accepted.append(text)
            return SimpleNamespace(verified_signal=True)
        with patch("ai_broadcaster.original_plan_frontend.send_to_native_live2d_session_with_observation",
                   side_effect=send), patch("ai_broadcaster.desktop_chat_tab.run_local_chat",
                                            side_effect=AssertionError("duplicate Ollama call")):
            LocalChatTab._work_twitch_ai(receiver, "", inbox, True)
        self.assertEqual(accepted,["안녕","안녕","다음 채팅"])
        self.assertEqual([outbox.get_nowait()[0] for _ in accepted],
                         ["twitch_live2d_ok"]*3)

    def test_fail_one_official_request_does_not_skip_next(self):
        inbox,outbox=queue.SimpleQueue(),queue.SimpleQueue()
        inbox.put(PlatformChat("room","user","실패","soop"))
        inbox.put(PlatformChat("room","user","성공","soop"))
        inbox.put(None)
        seen=[]
        def send(text,**kwargs):
            seen.append(text)
            if text=="실패":
                raise RuntimeError("공식 창 통신 실패")
            return SimpleNamespace(verified_signal=False)
        with patch("ai_broadcaster.original_plan_frontend.send_to_native_live2d_session_with_observation",
                   side_effect=send):
            LocalChatTab._work_twitch_ai(SimpleNamespace(_results=outbox),"",inbox,True)
        self.assertEqual(seen,["실패","성공"])
        self.assertEqual(outbox.get_nowait()[0],"twitch_ai_error")
        self.assertEqual(outbox.get_nowait()[0],"twitch_live2d_ok")

if __name__=="__main__":
    unittest.main()
