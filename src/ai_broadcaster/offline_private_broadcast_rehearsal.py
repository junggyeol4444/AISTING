"""Stage 076: in-memory *private-broadcast procedure* rehearsal, NOT a broadcast.

No OBS, transport, output-device, camera, account, filesystem, or network code.
The stage cannot verify that a real streaming destination is private.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_broadcast_output_audit import BroadcastOutputAudit
from .offline_broadcast_output_settings import (
    OfflineOutputSettingsDraft, prepare_offline_output_settings,
)
from .offline_broadcast_scene import BroadcastSceneDraft
from .offline_broadcast_voice_link import OfflineBroadcastVoiceLink

PHASES = ('사전 점검', '가상 시작', '가상 화면·음성 확인', '가상 종료', '송출 비활성 확인')


@dataclass(frozen=True)
class PrivateRehearsalResult:
    """A deterministic report: `passed` refers ONLY to local simulated procedure."""
    passed: bool
    phases: tuple[tuple[str, str], ...]
    cautions: tuple[str, ...]
    private_visibility_verified: bool = False
    streaming_performed: bool = False
    user_approval: str = 'pending'

    def describe(self) -> str:
        result = '모의 절차 통과' if self.passed else '모의 절차 중단/미통과'
        steps = '\n'.join(f' · {name}: {status}' for name, status in self.phases)
        warnings = '\n'.join(' · ' + caution for caution in self.cautions)
        return (
            '원본 076 비공개 방송 절차 · 오프라인 리허설 (' + result + ')\n'
            + steps + '\n'
            + ('주의:\n' + warnings + '\n' if warnings else '')
            + '실제 송출/OBS/계정·스트림 목적지 연결 0건. 비공개 공개범위 확인 0건.\n'
            + '실제 비공개 방송 성공, Windows 실기기, 음질·화질 및 사용자 최종 승인은 미검증·대기.'
        )


def rehearse_private_broadcast(
    canvas, scene: BroadcastSceneDraft, current_scene: BroadcastSceneDraft,
    volume: int, prior_audit: BroadcastOutputAudit,
    prior_draft: OfflineOutputSettingsDraft,
    voice_link: OfflineBroadcastVoiceLink | None = None,
    *, inject_failure_at: str | None = None,
) -> PrivateRehearsalResult:
    """Manually run fixed fake phases, fail-closed on stale/unsafe inputs.

    `inject_failure_at` is for local fault simulation only. No wall-clock delay,
    worker/thread, file or output endpoint is introduced.
    """
    if inject_failure_at is not None and inject_failure_at not in PHASES:
        raise ValueError('모의 장애 단계가 올바르지 않습니다.')
    if type(prior_draft) is not OfflineOutputSettingsDraft:
        raise ValueError('먼저 75단계 오프라인 송출 설정 초안을 준비하세요.')
    checked = prepare_offline_output_settings(
        canvas, scene, current_scene, volume, prior_audit, voice_link)
    if checked != prior_draft:
        raise ValueError('송출 초안 또는 화면·음량·음성 선택이 바뀌어 재점검이 필요합니다.')
    outputs = checked.review_mapping()['outputs']
    if (set(outputs) != {'obs_connected', 'video_connected', 'audio_connected',
                         'streaming_enabled', 'account_connected', 'destination'}
            or any(outputs[k] is not False for k in outputs if k != 'destination')
            or outputs['destination'] is not None):
        raise ValueError('외부 출력이 비활성화된 검토 초안만 시험할 수 있습니다.')

    notes = list(checked.caution_messages)
    notes.append('플랫폼의 실제 비공개/미등록 설정은 확인할 수 없습니다.')
    if not scene.platforms:
        notes.append('플랫폼 미선택: 실방송 전 운영자의 플랫폼 선택 필요.')
    # Phase statuses never mean that an actual stream was started or stopped.
    steps: list[tuple[str, str]] = []
    for phase in PHASES:
        if phase == inject_failure_at:
            steps.append((phase, '모의 장애 주입 · 즉시 중단 (실제 송출 없음)'))
            return PrivateRehearsalResult(False, tuple(steps), tuple(notes))
        steps.append((phase, {
            '사전 점검': '현재 로컬 Canvas/음량/설정 초안 일치 · 외부 출력 비활성',
            '가상 시작': '메모리 내 시작 이벤트만 통과 (방송 시작 없음)',
            '가상 화면·음성 확인': '가상 Canvas 태그/무음 음성 문자 상태만 검사',
            '가상 종료': '메모리 내 종료 이벤트만 통과 (방송 종료 호출 없음)',
            '송출 비활성 확인': 'OBS·영상·음성·계정·목적지 연결 모두 비활성',
        }[phase]))
    return PrivateRehearsalResult(True, tuple(steps), tuple(notes))
