"""Original 077: finite synthetic chat -> mock reply -> SILENT text -> Canvas check.

No audio sample, microphone, speaker, OBS, credentials, live message or broadcast.
Every operation happens on a caller-supplied *isolated* local Canvas and temporary
chat session. A PASS cannot mean a viewer received a frame or sound.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_broadcast_scene import BroadcastSceneDraft, draw_broadcast_scene
from .offline_broadcast_output_audit import audit_broadcast_output
from .offline_broadcast_voice_link import OfflineBroadcastVoiceLink
from .offline_chat_receiver import OfflineChatReceiveBuffer
from .offline_chat_order import OfflineChatOrder
from .offline_chat_reactions import OfflineChatReactions
from .platform_chat_connector import OfflinePlatformChatConnector


@dataclass(frozen=True)
class ChatVoiceScreenIntegrationResult:
    passed: bool
    received: int
    responded: int
    displayed: int
    rendered_segments: int
    ordinals: tuple[int, ...]
    issues: tuple[str, ...]
    actual_audio: bool = False
    actual_video: bool = False
    actual_streaming: bool = False
    approval: str = 'pending'

    def describe(self) -> str:
        return (
            '원본 077 채팅·음성·화면 통합 · 독립 메모리 모의\n'
            + ('모의 연결 확인' if self.passed else '모의 검사 실패/미완료') + '\n'
            + f'접수 {self.received} / 응답 {self.responded} / 화면 문자 표시 {self.displayed}건 '
            + f'/ 무음 음성 구간 {self.rendered_segments}개\n'
            + ('문제: ' + '; '.join(self.issues) + '\n' if self.issues else '')
            + '실제 플랫폼 수신 0 / 실제 AI 생성 0 / 실제 음성 재생 0 / 실제 영상 전송 0 / OBS 송출 0.\n'
            + '모의 텍스트 표시 일치만 확인. Windows 실기기, 자연스러운 말소리/립싱크, '
              '시청자 경험, 네트워크 지연, 실제 방송 및 사용자 최종 승인은 미검증·대기.'
        )


def run_offline_chat_voice_screen_integration(
    canvas, draft: BroadcastSceneDraft, volume: int, *, fault_at: int | None = None,
) -> ChatVoiceScreenIntegrationResult:
    """Draw a fake scene, inject 3 mock chats, verify each reply has visible text.

    ``fault_at`` deliberately interrupts before drawing a message (1..3).
    Test failure is fail-closed; no external state or user settings are changed.
    """
    if type(draft) is not BroadcastSceneDraft:
        raise ValueError('현재 방송 화면 선택이 필요합니다.')
    if not draft.platforms:
        raise ValueError('오프라인 시험용 플랫폼을 먼저 하나 이상 선택하세요. 자동 선택하지 않습니다.')
    if draft.voice != 'windows_system':
        raise ValueError('선택 목소리는 무음 가상 구간 미지원 · 임의 대체하지 않습니다.')
    if type(volume) is not int or not 0 <= volume <= 100:
        raise ValueError('설정 음량은 0~100 정수여야 합니다.')
    if fault_at is not None and (type(fault_at) is not int or fault_at not in (1, 2, 3)):
        raise ValueError('고의 장애는 1~3번째 메시지 중 하나여야 합니다.')
    if not callable(getattr(canvas, 'itemcget', None)) or not callable(getattr(canvas, 'type', None)):
        raise ValueError('Canvas 문자 표시를 읽어 확인할 수 없습니다.')

    received = responded = displayed = segments = 0
    ordinals: list[int] = []
    issues: list[str] = []
    try:
        draw_broadcast_scene(canvas, draft)
        first = audit_broadcast_output(canvas, draft, draft, volume)
        if not first.screen_ok:
            raise ValueError('초기 화면 검사 실패: ' + '; '.join(first.issues))
        connector = OfflinePlatformChatConnector(draft.platforms)
        receiver = OfflineChatReceiveBuffer()
        queue = OfflineChatOrder(receiver)
        reactions = OfflineChatReactions(receiver, queue)
        connector.connect()
        receiver.attach(connector)
        script = ((draft.platforms[0], '가상시청자A', '안녕하세요'),
                  (draft.platforms[-1], '가상시청자B', '안녕하세요'),
                  (draft.platforms[0], '가상시청자A', '오늘도 안녕하세요'))
        for event in script:
            receiver.inject(*event)
        received = len(receiver.snapshot().buffered)
        queue.sync()
        reactions.sync()
        reactions.enable_viewer_context()
        for ordinal in range(1, len(script) + 1):
            reply = reactions.reply_next()
            responded = len(reactions.snapshot().responded)
            if reply.event.ordinal != ordinal:
                raise ValueError('모의 응답 FIFO 순번 불일치')
            if ordinal == fault_at:
                raise RuntimeError(f'{ordinal}번째 메시지에 고의 화면 장애 주입')
            # Never auto-use a real TTS adapter: this path is intentionally text-only.
            canvas.delete('aisting_scene_voice')
            link = OfflineBroadcastVoiceLink(draft, reply.text)
            for chunk_index, chunk in enumerate(link.chunks, start=1):
                status = link.step(canvas, draft)
                expected = f'무음 가상 출력 {chunk_index}/{len(link.chunks)} · {chunk[:44]}'
                ids = canvas.find_withtag('aisting_scene_voice')
                if not any(canvas.type(item_id) == 'text' and canvas.itemcget(item_id, 'text') == expected
                           for item_id in ids):
                    raise ValueError(f'{ordinal}번 응답의 화면 문자 표시 불일치')
                if status.delivered != link.chunks[:chunk_index]:
                    raise ValueError(f'{ordinal}번 무음 구간 처리 상태 불일치')
                segments += 1
            if link.status().remaining:
                raise ValueError(f'{ordinal}번 응답의 미표시 무음 구간 존재')
            checked = audit_broadcast_output(canvas, draft, draft, volume, link)
            if not checked.screen_ok:
                raise ValueError('화면/음성 오버레이 검사 실패: ' + '; '.join(checked.issues))
            displayed += 1
            ordinals.append(ordinal)
        state = reactions.snapshot()
        if (not state.all_responded or received != responded or responded != displayed
                or tuple(ordinals) != tuple(range(1, received + 1))):
            raise ValueError('접수/응답/화면 표시 건수 또는 순서 불일치')
    except Exception as exc:
        # This is a contained synthetic exercise; failure must never be reported as a PASS.
        issues.append(f'{type(exc).__name__}: {str(exc)[:240]}')
    return ChatVoiceScreenIntegrationResult(
        not issues and received == responded == displayed == 3 and segments >= 3,
        received, responded, displayed, segments, tuple(ordinals), tuple(issues),
    )
