"""099 operator-maintenance checklist, strictly offline and approval-neutral.

All entries are operator claims, NEVER hardware test evidence. This code does not
inspect devices, logs, settings, processes, network, secrets or accounts.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

# A small daily review surface, not an assertion that any device or platform works.
CHECKS = (
    ('windows', 'Windows/EXE에서 화면·종료·설정 보존 직접 검증'),
    ('settings', '실제 사용자 설정 백업 및 무손상 복원 확인'),
    ('chat', '플랫폼별 실제 채팅 연결·누락·중복·재연결 확인'),
    ('ai', '실제 로컬 AI 응답 품질·지연·안전성 운영자 평가'),
    ('voice', '실제 한국어 TTS 장치·발음·중단·권리 확인'),
    ('avatar', '실제 선택 아바타 모델·립싱크·권리 확인'),
    ('obs', '운영자 승인 후 OBS 화면·소리·시작·종료 확인'),
    ('private', '승인 후 비공개 방송 공개 범위·전송 검증'),
    ('endurance', '실제 장시간/다회차 리소스·오류 점검'),
    ('cost', '운영 기간별 실청구·예산 및 권한·토큰 관리 확인'),
    ('rights', '캐릭터·음성·음악·방송 콘텐츠 사용 권리 확인'),
    ('approval', '100단계 최종 기능 검수·운영자 명시적 승인'),
)
CHECK_IDS = tuple(key for key, _ in CHECKS)
STATUS_PENDING = '대기'
STATUS_REVIEWED = '운영자 확인 입력'
STATUS_PROBLEM = '문제 발견'
STATUSES = (STATUS_PENDING, STATUS_REVIEWED, STATUS_PROBLEM)
KNOWN_UNRESOLVED = ('SQLite ResourceWarning: 테스트의 연결 미종료 5건 수정·회귀 확인; Windows 실기기 및 장시간 DB 자원 안정성은 미검증',)
MAX_CHECKS = 20


@dataclass(frozen=True)
class MaintenanceItem:
    key: str
    label: str
    status: str


@dataclass(frozen=True)
class MaintenanceReport:
    items: tuple[MaintenanceItem, ...]
    unresolved: tuple[str, ...]
    user_claims_only: bool = True
    hardware_verified: bool = False
    actual_stream_verified: bool = False
    final_approval_granted: bool = False
    can_release: bool = False

    @property
    def pending(self) -> int:
        return sum(x.status == STATUS_PENDING for x in self.items)

    @property
    def reviewed(self) -> int:
        return sum(x.status == STATUS_REVIEWED for x in self.items)

    @property
    def problems(self) -> int:
        return sum(x.status == STATUS_PROBLEM for x in self.items)

    def describe(self) -> str:
        lines = ['099 운영자 점검 및 유지보수 · 오프라인 수동 체크리스트',
                 f'운영자 입력: 확인 {self.reviewed}, 문제 {self.problems}, 대기 {self.pending}',
                 '※ 모든 표시는 운영자 자기보고이며 실제 기능 검사 증거/승인이 아닙니다.',
                 '※ 실기기·방송·권리·최종 승인 검증: 미확인 / 출시 허가: 아님',
                 '권장 일상 점검: 방송 이상 기록 → 채팅/음성/영상 이상 → 사용량·비용 → 권리·승인 → 재시험',
                 '', '운영자 수동 항목:']
        lines.extend(f'- [{entry.status}] {entry.label}' for entry in self.items)
        lines += ['', '개발 측 확인된 미해결 문제:']
        lines.extend(f'- {issue}' for issue in self.unresolved)
        lines.extend(['', '실제 PC 정보/계정/로그는 자동 수집하지 않습니다. 실제 송출·계정 연결·자동 재시도 없음.',
                      '모의 코드 도달 범위와 실제 제품 완성·사용자 승인 상태를 구분하세요.'])
        return '\n'.join(lines)

    def safe_export(self) -> dict:
        """Machine readable operator *claims*, never evidence or certification."""
        return {
            'schema': 'aisting_operator_maintenance_v1',
            'checklist': [{'id': x.key, 'label': x.label, 'operator_status': x.status}
                          for x in self.items],
            'known_unresolved': list(self.unresolved),
            'evidence_kind': 'operator_self_report_only',
            'hardware_verified': False,
            'actual_stream_verified': False,
            'final_approval_granted': False,
            'can_release': False,
            'autocollected_pc_data': False,
            'external_posted': False,
        }


class OfflineOperatorMaintenance:
    """Ephemeral self-report checklist. No auto probing, persistence or approvals."""

    def __init__(self):
        self._marks = {key: STATUS_PENDING for key in CHECK_IDS}

    def set_status(self, key: str, status: str) -> None:
        if type(key) is not str or key not in self._marks:
            raise ValueError('등록되지 않은 운영자 점검 항목입니다.')
        if type(status) is not str or status not in STATUSES:
            raise ValueError('대기/운영자 확인 입력/문제 발견 중 선택하세요.')
        self._marks[key] = status

    def clear(self) -> None:
        self._marks = {key: STATUS_PENDING for key in CHECK_IDS}

    def report(self) -> MaintenanceReport:
        if len(CHECKS) > MAX_CHECKS:
            raise ValueError('점검 항목 수가 허용 범위를 초과했습니다.')
        return MaintenanceReport(tuple(MaintenanceItem(key, name, self._marks[key])
                                       for key, name in CHECKS), KNOWN_UNRESOLVED)


def export_maintenance_snapshot(report: MaintenanceReport, path: Path) -> Path:
    """Explicitly requested snapshot. Never overwrite; no auto telemetry/log collection."""
    if type(report) is not MaintenanceReport:
        raise TypeError('유효한 운영자 점검 결과가 아닙니다.')
    if not isinstance(path, Path):
        raise TypeError('사용자가 선택한 저장 경로가 필요합니다.')
    if path.suffix.lower() != '.json':
        raise ValueError('JSON 파일만 내보낼 수 있습니다.')
    if len(report.items) != len(CHECKS) or tuple(x.key for x in report.items) != CHECK_IDS:
        raise ValueError('점검 항목 순서가 유효하지 않습니다.')
    # Validate trust boundaries on report supplied by callers, never serialize
    # secrets or arbitrary user-provided fields.
    if any(type(x.status) is not str or x.status not in STATUSES or x.label != CHECKS[i][1]
           for i, x in enumerate(report.items)):
        raise ValueError('점검 결과 값이 유효하지 않습니다.')
    if report.unresolved != KNOWN_UNRESOLVED or (not report.user_claims_only or report.hardware_verified
            or report.actual_stream_verified or report.final_approval_granted or report.can_release):
        raise ValueError('검증/승인 상태를 임의 변경한 보고서는 저장하지 않습니다.')
    content = json.dumps(report.safe_export(), ensure_ascii=False, indent=2) + '\n'
    with path.open('x', encoding='utf-8') as file:
        file.write(content)
    return path
