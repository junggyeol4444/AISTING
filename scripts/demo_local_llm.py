"""PC에서 사용자가 승인한 뒤에만 수동 실행하는 로컬 텍스트 대화 테스트.

명령: python scripts/demo_local_llm.py <이미 PC에 설치된 모델 이름>
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.chat_pipeline import ChatPipeline
from ai_broadcaster.local_llm import LocalModelConfig, LocalModelError, LocalOllamaReplyGenerator
from ai_broadcaster.operator_settings import load_settings
from ai_broadcaster.session import ChatMessage, SessionController


class ConsoleOutput:
    def deliver(self, reply: str) -> None:
        print(f"AI: {reply}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("사용법: python scripts/demo_local_llm.py <이미 설치된 모델 이름>")
        return 2
    try:
        generator = LocalOllamaReplyGenerator(LocalModelConfig(argv[1]), load_settings())
    except (ValueError, TypeError) as exc:
        print(f"모델 설정 오류: {exc}")
        return 2
    queue = SessionController()
    pipeline = ChatPipeline(queue, generator, ConsoleOutput())
    print("무료 로컬 AI 텍스트 테스트. 방송과 음성 송출은 하지 않습니다. 종료: /quit")
    count = 0
    while True:
        try:
            line = input("나: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line == "/quit":
            return 0
        count += 1
        queue.receive_chat(ChatMessage(str(count), "운영자", line))
        try:
            pipeline.drain()
        except (LocalModelError, ValueError) as exc:
            print(f"로컬 모델 오류: {exc}. 처리하지 못한 채팅은 대기열에 남습니다.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
