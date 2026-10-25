"""운영자가 지정한 OBS 실제 장면을 *로컬* 시각 AI로 이해하는 어댑터.

선택한 모델이 Ollama 이미지 입력을 실제 지원할 때에만 사용한다.
기존 OBS GetSourceScreenshot 경로로 PNG 1장을 메모리에서 읽고,
127.0.0.1 Ollama로만 보낸다. 디스크 저장·원격 서버·자동 마우스/키보드
조작·방송 송출·시청자 채팅 송신은 수행하지 않는다.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import HTTPHandler, ProxyHandler, Request, build_opener

from .local_llm import LocalModelConfig, _NoRedirect
from .offline_settings import active_persona, load_settings as load_gui_settings
from .original_plan_obs import OfficialObsWebsocket


@dataclass(frozen=True)
class GameSceneObservation:
    scene: str
    width: int
    height: int
    description: str
    local_model: str
    # 단일 프레임은 움직임/상대 입력/시청자 출력/게임 제어 증거가 아니다.
    screenshot_only: bool = True


def observe_game_scene_with_local_vision(
    obs_password: str, obs_port: int, model_name: str,
    *, operator_approved: bool = False,
    question: str = "현재 실제 게임 장면에서 눈에 보이는 상황만 한국어로 설명해.",
) -> GameSceneObservation:
    """운영자가 그때그때 승인한 실제 OBS 화면 한 장을 로컬 분석.

    OBS 프레임의 비공개 정보가 Ollama에 전달되므로 승인 없이는 HTTP나
    OBS 접속 자체를 시작하지 않는다. 실제 시각 입력을 지원하지 않는
    텍스트 전용 모델은 성공으로 치지 않고 오류를 그대로 알린다.
    """
    if operator_approved is not True:
        raise PermissionError("실제 OBS 화면을 로컬 AI로 분석할 운영자 승인이 필요합니다.")
    if type(obs_password) is not str or not obs_password:
        raise ValueError("운영자가 입력한 OBS 암호가 필요합니다.")
    if type(obs_port) is not int or not 1 <= obs_port <= 65535:
        raise ValueError("OBS WebSocket 포트가 올바르지 않습니다.")
    if (type(question) is not str or not question.strip() or len(question) > 500
            or any(ord(x) < 32 or ord(x) == 127 for x in question)):
        raise ValueError("화면 질문은 한 줄 500자 이내여야 합니다.")

    cfg = LocalModelConfig(model=model_name, timeout_seconds=30.0)
    obs = OfficialObsWebsocket(obs_password, port=obs_port)
    try:
        obs.connect()
        frame = obs.read_current_scene_frame(operator_approved=True)
    finally:
        inner = getattr(obs, "_client", None)
        disconnect = getattr(inner, "disconnect", None)
        if callable(disconnect):
            try:
                disconnect()
            except Exception:
                pass

    if not isinstance(frame.png_data, bytes) or len(frame.png_data) > 2_500_000:
        raise ValueError("OBS가 반환한 이미지가 유효하지 않습니다.")
    persona = active_persona(load_gui_settings())
    system = (
        f"한국어 방송인 '{persona['name']}'의 화면 이해를 도와주세요. "
        f"선택된 성격은 '{persona['character']}', 말투는 '{persona['style']}'입니다. "
        "이 OBS 실제 화면에서 직접 보이는 사실과 불확실한 추측을 명확히 "
        "구분하세요. 게임 이름·플레이 상황을 모르면 모른다고 하세요. "
        "게임에 없는 목표·조작 결과를 지어내지 마세요. "
        "이 텍스트는 방송에 자동 출력되지 않습니다."
    )
    body = {
        "model": cfg.model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question.strip(), "images": [
                base64.b64encode(frame.png_data).decode("ascii")]}],
    }
    # 사용자의 기존 모델과 기본 생성 토큰 정책을 변경하지 않는다.
    request = Request(
        cfg.endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    client = build_opener(ProxyHandler({}), HTTPHandler(), _NoRedirect())
    try:
        with client.open(request, timeout=cfg.timeout_seconds) as response:
            raw = response.read(65_537)
    except (OSError, TimeoutError, HTTPError, URLError) as exc:
        raise RuntimeError("로컬 시각 AI 요청 실패 · 모델의 이미지 지원을 확인하세요.") from exc
    if len(raw) > 65_536:
        raise ValueError("로컬 시각 AI 응답 크기 한도 초과")
    try:
        parsed = json.loads(raw.decode("utf-8"))
        reply = parsed.get("message", {}).get("content")
    except (UnicodeError, ValueError, AttributeError) as exc:
        raise ValueError("로컬 시각 AI 응답 JSON 형식 오류") from exc
    if (type(reply) is not str or not reply.strip() or len(reply) > 5000
            or any((ord(ch) < 32 and ch not in "\n\t") or ord(ch) == 127
                   for ch in reply)):
        raise ValueError("로컬 시각 AI 설명이 비어 있거나 형식이 잘못됐습니다.")
    return GameSceneObservation(
        frame.scene, frame.width, frame.height, reply.strip(), cfg.model)
