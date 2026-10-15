"""Original stage 075: **non-executable** broadcast-output settings bridge.

Binds an already rendered local scene and a current stage-074 audit into a
review-only snapshot. It never selects a remote endpoint, starts a transport,
looks up OBS, talks to an audio device, saves secrets, or writes a file.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from .offline_broadcast_output_audit import BroadcastOutputAudit, audit_broadcast_output
from .offline_broadcast_scene import BroadcastSceneDraft
from .offline_broadcast_voice_link import OfflineBroadcastVoiceLink


@dataclass(frozen=True)
class OfflineOutputSettingsDraft:
    """Immutable local selection snapshot, deliberately NOT an OBS profile."""
    scene: BroadcastSceneDraft
    nominal_volume: int
    virtual_voice_overlay: bool
    caution_messages: tuple[str, ...]

    def review_mapping(self) -> dict:
        """Return a new plain-data review copy; not accepted by any streaming API."""
        return {
            'schema': 'aisting.offline_output_settings.review.v1',
            'mode': 'offline_review_only',
            'source_canvas': {'width': 640, 'height': 360, 'type': 'local_placeholder'},
            'selected_platforms': list(self.scene.platforms),
            'composition': {
                'content': self.scene.content,
                'avatar': self.scene.avatar,
                'persona_name': self.scene.persona_name,
                'title_overlay': self.scene.show_title,
                'chat_placeholder': self.scene.show_chat,
            },
            'nominal_voice': {
                'selected_source': self.scene.voice,
                'volume_setting_0_100': self.nominal_volume,
                'virtual_text_overlay_visible': self.virtual_voice_overlay,
                'speaker_connected': False,
            },
            'outputs': {
                'obs_connected': False,
                'video_connected': False,
                'audio_connected': False,
                'streaming_enabled': False,
                'account_connected': False,
                'destination': None,
            },
            'approval': 'pending_user_and_windows_real_device_verification',
        }

    def review_json(self) -> str:
        return json.dumps(self.review_mapping(), ensure_ascii=False, indent=2)

    def describe(self) -> str:
        summary = ', '.join(self.scene.platforms) if self.scene.platforms else '미선택'
        return (
            '75단계 송출 설정 연결 초안 · 오프라인 검토 전용 (실제 연결 0건)\n'
            f'선택 플랫폼: {summary} · 콘텐츠: {self.scene.content} · 아바타: {self.scene.avatar}\n'
            f'Canvas 640×360 · UI 설정 음량 {self.nominal_volume}/100 (실측값 아님) · '
            f'가상 음성 문자 표시: {"있음" if self.virtual_voice_overlay else "없음"}\n'
            '송출 비활성 / OBS·스피커·영상장치·계정·목적지 미연결 / 인증정보 미생성\n'
            '이 초안은 미리보기 선택값만 묶은 것으로 OBS 설정을 변경하거나 파일에 저장하지 않습니다.\n'
            '실제 방송/Windows 실기기/장치/최종 사용자 승인: 별도 대기.'
        )


def prepare_offline_output_settings(
    canvas, scene: BroadcastSceneDraft, current_scene: BroadcastSceneDraft,
    volume: int, prior_audit: BroadcastOutputAudit,
    voice_link: OfflineBroadcastVoiceLink | None = None,
) -> OfflineOutputSettingsDraft:
    """Require a previously accepted *and still current* stage-074 check.

    Calling this function performs a fresh read-only Canvas audit, so a stale
    preview or subsequently removed drawing marker cannot yield a linked draft.
    """
    if type(prior_audit) is not BroadcastOutputAudit or not prior_audit.screen_ok:
        raise ValueError('먼저 정상적인 74단계 음량·화면 점검을 완료하세요.')
    fresh = audit_broadcast_output(canvas, scene, current_scene, volume, voice_link)
    if not fresh.screen_ok or fresh != prior_audit:
        raise ValueError('화면/음량 상태가 이전 점검과 달라 다시 점검해야 합니다.')
    return OfflineOutputSettingsDraft(
        scene=scene,
        nominal_volume=fresh.volume_setting,
        virtual_voice_overlay=bool(voice_link is not None and voice_link.cursor > 0),
        caution_messages=fresh.cautions,
    )
