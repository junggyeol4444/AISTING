"""Original 090: operator-triggered, fail-closed offline automation integration audit.

Bridges *existing* stage 077, 081-089 implementations with one shared virtual
occurrence. No live clock, scheduling, I/O, API, AI provider, TTS playback, OBS,
account/credential handling or genuine publication. The caller owns a SEPARATE
scratch Tk canvas; never use the operator's active scene or real chat buffer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .offline_broadcast_schedule import BroadcastScheduleDraft
from .offline_broadcast_scene import BroadcastSceneDraft
from .offline_settings import active_persona, validate_settings
from .offline_start_control import OfflineStartController
from .offline_broadcast_duration import BroadcastDurationRules
from .offline_broadcast_closing import OfflineBroadcastClosing
from .offline_prebroadcast_notice import make_prebroadcast_notice
from .offline_discord_notice_link import prepare_discord_notice_dry_run
from .offline_naver_cafe_review import review_naver_cafe_official_link
from .offline_notice_variation import NoticeVariationOptions, make_notice_variation
from .offline_notice_posting_rehearsal import OfflineNoticePostingRehearsal
from .offline_chat_voice_screen_integration import run_offline_chat_voice_screen_integration
from .offline_end_notice import create_offline_end_notice


@dataclass(frozen=True)
class AutomationCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class AutomationAuditReport:
    checks: tuple[AutomationCheck, ...]
    simulated_only: bool = True
    actual_broadcast_verified: bool = False
    actual_publication_verified: bool = False
    approval: str = 'pending'

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.ok for check in self.checks) and self.checks[-1].name == '가상 완료·미게시·미검증 경계 보존'

    def describe(self) -> str:
        failed = next((check.name for check in self.checks if not check.ok), None)
        return (f'090 방송 자동화 통합 모의 검증 {"통과" if self.passed else "미통과"} '
                f'{sum(c.ok for c in self.checks)}/{len(self.checks)}'
                + (f' · 첫 실패: {failed}' if failed else '')
                + ' · 실제 방송/공지·AI·TTS·OBS·Windows 검증 안 됨 · 승인 대기')


class _HaltAudit(Exception):
    pass


def run_offline_broadcast_automation_audit(
    schedule: BroadcastScheduleDraft, when: datetime, settings: dict,
    scene: BroadcastSceneDraft, volume: int, canvas, *, topic: str = '',
    chat_integration: Callable = run_offline_chat_voice_screen_integration,
    display_notice: Callable[[str], None] | None = None,
    display_closing: Callable[[str], None] | None = None,
) -> AutomationAuditReport:
    """Run a single *virtual* occurrence across the existing offline contracts.

    Each check is evaluated once in order, with an explicit stop on first failure.
    Optional local callbacks support fault injection. Nothing is persisted.
    """
    checks: list[AutomationCheck] = []

    def check(name, operation):
        try:
            if operation() is not True:
                raise AssertionError('기존 연결 계약 불일치 또는 미검증 상태')
            checks.append(AutomationCheck(name, True, '메모리 모의 확인'))
        except Exception as exc:
            checks.append(AutomationCheck(name, False, f'{type(exc).__name__}: {str(exc)[:180]}'))
            raise _HaltAudit from exc

    state: dict = {}
    try:
        def prerequisites():
            if type(schedule) is not BroadcastScheduleDraft or type(scene) is not BroadcastSceneDraft:
                raise ValueError('검증된 기존 일정·화면 초안만 사용할 수 있습니다.')
            if type(settings) is not dict:
                raise ValueError('로컬 설정이 필요합니다.')
            validated = validate_settings(settings)
            if type(volume) is not int or not 0 <= volume <= 100:
                raise ValueError('음량 설정은 0~100 정수여야 합니다.')
            # Do not silently switch 3D to 2D, voice, platform, or a user persona.
            if (tuple(validated['platforms']) != scene.platforms
                    or validated['content'] != scene.content
                    or validated['avatar'] != scene.avatar
                    or validated['voice'] != scene.voice
                    or active_persona(validated)['name'] != scene.persona_name):
                raise ValueError('화면 초안과 사용자 선택 설정이 달라졌습니다.')
            if not scene.platforms or scene.voice != 'windows_system':
                raise ValueError('무음 화면 통합 모의를 위한 선택 플랫폼/Windows 무료 음성이 필요합니다. 임의 대체 없음.')
            if not callable(getattr(canvas, 'create_text', None)):
                raise ValueError('격리된 실제 Tk Canvas 모의 시험이 필요합니다.')
            state['controller'] = OfflineStartController(schedule)
            return state['controller'].inspect(when, settings).code == 'mock_ready'
        check('일정·선택·격리 Canvas·가상 시작 준비', prerequisites)

        def notice_drafts():
            draft = make_prebroadcast_notice(settings, when, topic)
            discord = prepare_discord_notice_dry_run(draft).to_preview_dict()
            cafe = review_naver_cafe_official_link(draft).to_report_dict()
            variation = make_notice_variation(draft, settings, NoticeVariationOptions())
            state['notice'] = draft
            return (not draft.published and not draft.ai_generated and not draft.scheduled
                    and discord['send_ready'] is False and discord['published'] is False
                    and cafe['api_payload_ready'] is False and cafe['published'] is False
                    and cafe['official_api_capability'] == 'unverified'
                    and variation.published is False and variation.ai_generated is False)
        check('공지 초안·디스코드·카페·변주 미게시 검사', notice_drafts)

        def start():
            controller = state['controller']
            recorded: list[str] = []
            result = controller.simulate_start(when, settings, show_mock_start=recorded.append)
            return (result.code == 'mock_started' and controller.active
                    and controller.simulated_count == 1
                    and recorded == [controller.active_occurrence])
        check('가상 방송 시작 확인', start)

        check('중복 가상 시작 차단', lambda: state['controller'].simulate_start(when, settings).code == 'mock_active')

        def mock_post():
            local_notice = []
            callback = display_notice if display_notice is not None else local_notice.append
            poster = OfflineNoticePostingRehearsal()
            result = poster.simulate_display(state['notice'], state['controller'], settings, show_local=callback)
            state['poster'] = poster
            state['posted'] = result
            return (result.code == 'mock_displayed' and result.published is False
                    and not result.transport_used and not result.scheduled
                    and poster.simulated_count == 1
                    and (display_notice is not None or local_notice == [state['notice'].text]))
        check('가상 공지 표시·전송 없음', mock_post)

        check('중복 가상 공지 표시 차단', lambda: state['poster'].simulate_display(
            state['notice'], state['controller'], settings,
            show_local=lambda _: None).code == 'duplicate' and state['poster'].simulated_count == 1)

        def chat_screen():
            if not callable(chat_integration):
                raise ValueError('기존 채팅·음성·화면 연결 시험을 호출할 수 없습니다.')
            result = chat_integration(canvas, scene, volume)
            state['chat'] = result
            return (result.passed is True and result.received == 3
                    and result.responded == result.displayed == 3
                    and result.ordinals == (1, 2, 3)
                    and result.rendered_segments >= 3 and not result.issues
                    and result.actual_audio is False and result.actual_video is False
                    and result.actual_streaming is False and result.approval == 'pending')
        check('모의 채팅 3건→무음 음성→화면 문자 표시', chat_screen)

        rules = BroadcastDurationRules()
        check('최소 방송 시간 직전 가상 종료 차단', lambda: not rules.evaluate(rules.minimum_minutes * 60 - 0.1).can_consider_ending)
        check('최대 방송 시간 직전 마무리 차단', lambda: not rules.evaluate(rules.maximum_minutes * 60 - 0.1).maximum_reached)

        def close():
            decision = rules.evaluate(rules.maximum_minutes * 60)
            state['decision'] = decision
            closing = OfflineBroadcastClosing(decision, active_persona(settings)['name'])
            state['closing'] = closing
            shown: list[str] = []
            callback = display_closing if display_closing is not None else shown.append
            first = closing.advance(callback)
            if first.phase != 'farewell_pending' or len(first.delivered_lines) != 1:
                return False
            second = closing.advance(callback)
            state['closed'] = second
            return (second.virtual_stream_ended and second.phase == 'virtual_ended'
                    and len(second.delivered_lines) == 2
                    and (display_closing is not None or shown == list(second.delivered_lines)))
        check('예고→인사→가상 종료 순서 확인', close)

        def end_notice():
            notice = create_offline_end_notice(settings, when, state['decision'], state['closed'])
            state['end_notice'] = notice
            record = notice.record
            return (notice.published is False and notice.actual_broadcast_verified is False
                    and record['actual_broadcast_verified'] is False and record['published'] is False
                    and record['actual_end_time'] is None and record['viewer_count'] is None
                    and record['scheduled_start_operator_input'] == state['notice'].announcement_time)
        check('가상 종료 공지·실측 통계 미확인', end_notice)

        check('가상 시작 세션 마무리', lambda: state['controller'].simulate_finish().code == 'mock_finished' and not state['controller'].active)
        check('가상 중복 종료 차단', lambda: state['controller'].simulate_finish().code == 'not_active')
        check('완료 후 동일 일정 재시작 차단', lambda: state['controller'].simulate_start(when, settings).code == 'duplicate')
        check('가상 완료·미게시·미검증 경계 보존', lambda: (
            state['end_notice'].record['actual_stream_status'] == 'not_checked'
            and state['posted'].published is False and state['posted'].transport_used is False
            and state['chat'].actual_streaming is False))
    except _HaltAudit:
        pass
    except Exception as exc:
        checks.append(AutomationCheck('예상하지 못한 통합 오류', False, f'{type(exc).__name__}: {str(exc)[:180]}'))
    return AutomationAuditReport(tuple(checks))
