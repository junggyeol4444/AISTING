"""Local mocked Korean chat replies. Does NOT call a real LLM/TTS or broadcast."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.session import ChatMessage, SessionController
from ai_broadcaster.chat_pipeline import ChatPipeline


class MockGenerator:
    def generate(self, message: ChatMessage) -> str:
        return f"(모의 응답) {message.sender}님, '{message.text}' 읽었어요."


class ConsoleOutput:
    def deliver(self, reply: str) -> None:
        print(reply)


session = SessionController()
for msg in [ChatMessage('01', '시청자A', '안녕'), ChatMessage('02', '시청자B', 'ㅋㅋㅋ')]:
    session.receive_chat(msg)
results = ChatPipeline(session, MockGenerator(), ConsoleOutput()).drain()
print(f"모의 응답 처리: {len(results)}개 / 실제 음성·라이브 방송 없음")
