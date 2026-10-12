"""Run only a platform-neutral example. No network or actual streaming."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.session import ChatMessage, SessionController, SessionPolicy

s = SessionController(SessionPolicy(minimum_seconds=60, maximum_seconds=90))
print(s.start(0).name)
s.receive_chat(ChatMessage("msg-001", "시청자1", "안녕하세요"))
s.receive_chat(ChatMessage("msg-002", "시청자2", "ㅋㅋㅋ"))
while s.pending_chats:
    msg = s.next_chat()
    print(f"chat #{msg.message_id} {msg.sender}: {msg.text}")
print(s.tick(90).name)
print(s.farewell_finished().name)
print("주의: 위 출력은 모의 실행이며 실제 방송을 송출하지 않았습니다.")
