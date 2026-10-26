"""운영자 승인 실제 방송의 로컬 GPT-SoVITS 수신 포트 관찰.

기존 공식 설정의 127.0.0.1/localhost/::1 주소만 허용. TCP 연결
가능 여부만 조사하며 음성 합성, 모델 다운로드/훈련, API 호출이나
방송/OBS 제어는 일절 수행하지 않는다. 서버가 받는 합성 결과나
시청자 최종 출력은 이 관찰만으로 증명할 수 없다.
"""
from __future__ import annotations

import math
import socket
from urllib.parse import urlsplit

from .original_plan_tts import validate_local_gpt_sovits_url


def local_korean_tts_listener_alive(api_url: str, *, timeout: float = 0.75) -> bool:
    """실제 원본 설정에 기록된 로컬 음성 서비스 TCP 포트만 확인."""
    validated = validate_local_gpt_sovits_url(api_url)
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0.1 <= timeout <= 2.0):
        raise ValueError("로컬 한국어 음성 확인 제한 시간은 0.1~2초입니다.")
    parsed = urlsplit(validated)
    # 외부 DNS를 요청하지 않도록 localhost도 고정 루프백 주소만 검사한다.
    hosts = (
        ("127.0.0.1", "::1") if parsed.hostname == "localhost"
        else (parsed.hostname,)
    )
    for host in hosts:
        if host not in ("127.0.0.1", "::1"):
            raise ValueError("외부 음성 서버 연결 확인은 허용하지 않습니다.")
        try:
            with socket.create_connection((host, parsed.port), timeout=timeout):
                return True
        except (TimeoutError, ConnectionError, OSError):
            continue
    return False
