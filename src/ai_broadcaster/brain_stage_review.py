"""30단계: 로컬 모의 두뇌의 1차 준비 상태만 점검하는 무부작용 감사.

실제 LLM 품질, Windows 실기기, 방송 코어 완성 여부를 인증하지 않는다.
"""
from dataclasses import dataclass
from typing import Mapping
from .core_execution import OfflineCoreSession
from .offline_settings import validate_settings

@dataclass(frozen=True)
class BrainReview:
    checks: tuple[tuple[str, bool], ...]
    actual_model_verified: bool = False
    windows_verified: bool = False
    operator_approved: bool = False

    @property
    def mock_ready(self) -> bool:
        return all(ok for _, ok in self.checks)

    def describe(self) -> str:
        lines = ['30단계 · AI 두뇌 1차 작동 점검 (오프라인 모의 전용)']
        lines.extend(('통과' if ok else '실패') + ' · ' + name for name, ok in self.checks)
        lines.extend([
            '모의 코어 구조 점검: ' + ('통과' if self.mock_ready else '실패'),
            '실제 AI 모델 생성/한국어 자연스러움: 미검증',
            'Windows 실기기 및 방송 통합: 미검증',
            '10단계 사용자 최종 승인: 대기 · 공식 진행률 9/100',
            '네트워크·PC 정보 수집·설치·OBS 실행·DB 쓰기 없음',
        ])
        return '\n'.join(lines)


def review_brain(settings: Mapping[str, object]) -> BrainReview:
    """사용자가 버튼을 누른 경우에만 메모리 안에서 모의 입력/출력 검증."""
    safe = validate_settings(dict(settings))
    session = OfflineCoreSession(safe)
    session.enqueue('시청자: 안녕하세요\n시청자: 안녕하세요\n시청자: 오늘 방송 어때요?')
    result = session.run_batch()
    replies = result.processed
    checks = (
        ('모의 입력 3건 처리', len(replies) == 3 and result.remaining == 0),
        ('입력 순서·중복 보존', [r.input.text for r in replies] == ['안녕하세요', '안녕하세요', '오늘 방송 어때요?']),
        ('한국어 모의 응답 형식', all(isinstance(r.text, str) and r.text.strip() for r in replies)),
        ('모의 응답 모드 고정', result.mode == 'mock' and session.ai_plan.mode == 'mock'),
        ('실제 송출·자동 시작 비활성', not session.blueprint.streaming_enabled and not session.blueprint.auto_start_enabled and not session.blueprint.external_publish_enabled),
    )
    return BrainReview(checks)
