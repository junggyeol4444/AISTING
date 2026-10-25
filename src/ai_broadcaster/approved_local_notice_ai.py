"""기존 로컬 Ollama와 저장된 캐릭터를 이용한 실제 방송 공지 문구 생성.

Windows 운영자가 버튼으로 요청한 경우에만 localhost Ollama를 한 번
호출한다. 대화 SQLite·원본 캐릭터·모델 설정·방송 계정·웹훅은 변경하지
않는다. 생성 결과는 GUI 검토용 텍스트이며 외부 게시는 별도 승인이다.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from .local_llm import LocalModelConfig, LocalOllamaReplyGenerator
from .operator_settings import load_settings as load_operator_settings
from .offline_settings import active_persona, load_settings as load_gui_settings
from .session import ChatMessage

_BLOCKED = ("@everyone", "@here", "http://", "https://", "www.", "<@", "<#")
_URL = re.compile(r"(?i)(?:[a-z0-9-]+\.)+(?:com|net|org|kr|io|gg|tv)(?:/|\b)")
_MAX_NOTICE = 1500


def _safe_notice(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("생성된 공지 내용이 문자열이 아닙니다.")
    cleaned = text.strip()
    if (not cleaned or len(cleaned) > _MAX_NOTICE
            or any((ord(ch) < 32 and ch not in "\n\t") or ord(ch) == 127
                   for ch in cleaned)
            or any(token in cleaned.lower() for token in _BLOCKED)
            or _URL.search(cleaned)):
        raise ValueError(
            "생성된 문구에 비허용 링크·대량 멘션·제어 문자 또는 길이 오류가 있습니다."
        )
    return cleaned


def generate_approved_notice_drafts(
    model_name: str,
    *,
    scheduled_at: datetime,
    topic: str = "",
    end_message: str = "",
) -> tuple[str, str]:
    """시작/종료 공지를 각각 한 번씩 모델로 생성, 본문만 반환.

    현재 사용자 선택 모델을 그대로 사용한다. 실제 방송 성공을 추정하지
    않으며 종료 문구도 송출 종료가 실제 확인된 경우에만 기존 어댑터가
    전송한다. 예상 시각을 본문에 넣지 않고 운영자가 지정한 시각만 사용.
    """
    if (not isinstance(scheduled_at, datetime)
            or scheduled_at.tzinfo is None
            or scheduled_at.utcoffset() != timedelta(hours=9)):
        raise ValueError("운영자가 저장한 한국 시간 방송 일정이 필요합니다.")
    if type(topic) is not str or len(topic) > 100:
        raise ValueError("방송 주제는 100자 이내여야 합니다.")
    if (type(end_message) is not str or not end_message.strip()
            or len(end_message) > 300):
        raise ValueError("운영자 종료 인사 설정을 확인하세요.")
    for value in (topic, end_message):
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("주제/종료 인사에 제어 문자가 포함되어 있습니다.")

    settings = load_operator_settings()
    persona = active_persona(load_gui_settings())
    settings["persona"]["name"] = persona["name"]
    settings["persona"]["traits"] = persona["character"]
    settings["persona"]["speech_style"] = persona["style"]
    # 기존 모델/포트/timeout/토큰 상한/keep_alive는 임의 변경하지 않는다.
    generator = LocalOllamaReplyGenerator(
        LocalModelConfig(model=model_name), settings, memory=None)
    generator.system = (
        f"당신은 한국어 버추얼 방송인 '{persona['name']}'의 공지 작성자입니다. "
        f"캐릭터 성격: {persona['character']}. "
        f"말투: {persona['style']}. "
        "입력된 운영자 사실만 사용해 한국어 공지 본문 한 개만 작성하세요. "
        "가짜 방송 주소, 계정, 시청자 수, 실제 송출 성공을 만들어 내지 마세요. "
        "링크·대량 멘션·마크다운 코드블록·설명 없이 1,500자 이하의 "
        "짧은 방송 공지 텍스트만 출력하세요."
    )
    moment = scheduled_at.strftime("%Y-%m-%d %H:%M KST")
    subject = topic.strip() or "운영자가 주제를 아직 지정하지 않음"
    start_request = (
        "아래 사실을 근거로 방송 시작 전/시작 직후 사용할 안내 공지 한 개를 작성하세요. "
        f"운영자 저장 예정 방송 시각: {moment}. "
        f"운영자 지정 주제: {subject}. "
        "방송이 이미 시작됐다고 단정하지 말고 '방송 시작을 안내합니다'처럼 표현하세요."
    )
    end_request = (
        "방송의 실제 OBS 종료가 확인된 뒤에만 게시할 방송 종료 공지 한 개를 "
        f"작성하세요. 캐릭터 운영자 지정 마무리 인사: {end_message.strip()}. "
        "가짜 성과나 방송 길이, 시청자 수를 만들어 내지 마세요."
    )
    start_text = _safe_notice(generator.generate(
        ChatMessage("공지-시작-초안", "운영자", start_request)))
    end_text = _safe_notice(generator.generate(
        ChatMessage("공지-종료-초안", "운영자", end_request)))
    return start_text, end_text
