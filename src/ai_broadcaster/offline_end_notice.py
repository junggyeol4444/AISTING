"""089: strictly local virtual-end notice and opt-in result record.

No actual stream state, counters, personal data, network, automatic posting,
file discovery or unattended persistence. Export is explicit and refuses overwrite.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path

from .offline_broadcast_closing import ClosingSnapshot
from .offline_broadcast_duration import DurationDecision
from .offline_broadcast_schedule import KST
from .offline_prebroadcast_notice import _safe_line
from .offline_settings import CONTENTS, PLATFORMS, active_persona, validate_settings


@dataclass(frozen=True)
class OfflineEndNotice:
    text: str
    record: dict
    simulated_only: bool = True
    published: bool = False
    actual_broadcast_verified: bool = False

    def describe(self) -> str:
        return '089 가상 종료 결과 기록 초안 · 실제 방송/통계 미확인 · 게시하지 않음 · 자동 저장 없음'

    def export_json(self, destination: Path) -> None:
        """Save only after explicit user action; never overwrite existing records."""
        if not isinstance(destination, Path):
            raise ValueError('저장 위치를 직접 선택해야 합니다.')
        payload = json.dumps(self.record, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
        # Exclusive creation protects previous user data. No mkdir or implicit path.
        with destination.open('x', encoding='utf-8') as file:
            file.write(payload)


def create_offline_end_notice(settings: dict, announced_start: datetime,
                              decision: DurationDecision, closing: ClosingSnapshot,
                              note: str = '') -> OfflineEndNotice:
    """Build a mock result exclusively from explicitly supplied local simulation inputs."""
    selected = validate_settings(settings)
    if type(announced_start) is not datetime or announced_start.tzinfo is None or announced_start.utcoffset() != timedelta(hours=9):
        raise ValueError('운영자가 입력한 한국 시간(KST) 시작 시각이 필요합니다.')
    if type(decision) is not DurationDecision or not decision.maximum_reached or not decision.minimum_satisfied or decision.action != 'wrap_up_requested':
        raise ValueError('최대 시간 도달 가상 판단이 필요합니다.')
    if type(closing) is not ClosingSnapshot or not closing.virtual_stream_ended or closing.phase != 'virtual_ended':
        raise ValueError('두 마무리 문구를 표시하고 가상 종료한 상태만 허용합니다.')
    if closing.next_line is not None or len(closing.delivered_lines) != 2 or any(not isinstance(line, str) or not line for line in closing.delivered_lines):
        raise ValueError('마무리 문구 처리 기록이 불완전합니다.')
    if isinstance(decision.elapsed_seconds, bool) or not (0 <= decision.elapsed_seconds <= 86400):
        raise ValueError('가상 경과 시간이 올바르지 않습니다.')
    # Re-evaluation prevents accepting a tampered/internally inconsistent decision.
    from .offline_broadcast_duration import BroadcastDurationRules
    expected = BroadcastDurationRules(decision.minimum_minutes, decision.maximum_minutes).evaluate(decision.elapsed_seconds)
    if expected != decision:
        raise ValueError('시간 규칙과 가상 경과 기록이 일치하지 않습니다.')
    if type(note) is str and any(ord(ch) < 32 for ch in note):
        raise ValueError('운영자 메모에 제어 문자가 포함되어 있습니다.')
    context = _safe_line(note, title='운영자 메모', limit=120, optional=True)
    name = _safe_line(active_persona(selected)['name'], title='캐릭터 이름', limit=200)
    content = {code: label for label, code in CONTENTS.items()}[selected['content']]
    platforms = tuple({code: label for label, code in PLATFORMS.items()}[code] for code in selected['platforms'])
    start_text = announced_start.astimezone(KST).strftime('%Y-%m-%d %H:%M KST')
    lines = [f'[{name}] 오늘의 방송 마무리 안내 (검토용)',
             '함께해 주셔서 감사합니다. 다음에 또 만나요!',
             f'방송 예정 시작 시각(운영자 입력): {start_text}',
             f'방송 콘텐츠 설정: {content}',
             '선택 플랫폼: ' + (', '.join(platforms) if platforms else '미선택')]
    if context:
        lines.append(f'운영자 메모: {context}')
    lines.append('※ 가상 종료 시험 후 만든 오프라인 초안. 실제 방송 종료·게시 확인 아님')
    text = '\n'.join(lines)
    record = {
        'schema': 'aisting_offline_end_review_v1', 'stage': 89,
        'record_type': 'virtual_ending_only', 'actual_broadcast_verified': False,
        'published': False, 'auto_saved': False,
        'scheduled_start_operator_input': start_text,
        'elapsed_seconds_simulated': decision.elapsed_seconds,
        'minimum_minutes': decision.minimum_minutes,
        'maximum_minutes': decision.maximum_minutes,
        'virtual_end_confirmed': True, 'closing_lines_displayed_simulated': 2,
        'platforms_selected': list(platforms), 'content_selected': content,
        'persona_name_setting': name, 'operator_note': context,
        'notice_draft': text, 'viewer_count': None, 'actual_end_time': None,
        'actual_stream_status': 'not_checked',
        'disclaimer': 'Offline virtual test only; no actual broadcast, platform or OBS verification.',
    }
    return OfflineEndNotice(text, record)
