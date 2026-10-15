"""Original stage 100: local *final review dossier*, NOT operator approval.

No network, OS/device/secret inspection, streaming, account connection or
unattended scanning. Only a known set of bundled project documents is read
on explicit operator request. Archived logs are NOT fresh test execution proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .offline_operator_maintenance import (
    MaintenanceReport, CHECK_IDS, CHECKS, KNOWN_UNRESOLVED, STATUS_REVIEWED,
)

# Baselines of the user-authored original specification and roadmap status at v100.
EXPECTED_ORIGINAL_SHA256 = 'd4482d539bf733fddc65263566b436e2547d64d43545ac3279581bc21c58180c'
EXPECTED_ROADMAP_SHA256 = 'bcaee31766fc5db4307f2d6f86becbe7dce28931d55c51ff8b39296beba5d48e'
ALLOWED_FILES = (
    'docs/ORIGINAL_PLAN.txt',
    'docs/ROADMAP_100.md',
    'config/roadmap.json',
    'docs/REAL_DEVICE_ACCEPTANCE_CHECKLIST.md',
    'logs/STAGE100_FINAL_VALIDATION.txt',
    'logs/STAGE100_UNITTEST.log',
)
MAX_EVIDENCE_BYTES = 2_000_000

# Classifications are deliberately not dependent on self-reported checkmarks.
REVIEW_ITEMS = (
    ('requirements', '원본 기획안·100단계 로드맵 보존', '동봉 문서만 점검'),
    ('program', '누적 소스·자동/GUI 회귀 시험', '개발 환경 기록만 있음'),
    ('settings', '설정·사용자 데이터 보존', '샘플 경로 시험만 있음'),
    ('windows', 'Windows 10/11 실행·EXE', '실기기 미검증'),
    ('chat', '실제 플랫폼 채팅·재연결', '실제 연결 미구현·미검증'),
    ('ai', '실제 AI 모델·안전한 대화', '실모델 미검증'),
    ('voice', '실제 TTS·음성 품질·권리', '실장치·품질 미검증'),
    ('avatar', '실제 2D/3D 아바타·립싱크', '실모델 미검증'),
    ('obs', 'OBS·비공개/실제 송출 및 종료', '실제 송출 미검증'),
    ('notices', '디스코드·카페 공지 실제 게시', '계정·권한·게시 미검증'),
    ('endurance', '실시간 장시간·다회차 안정성', '가속 모의만 검증'),
    ('resources', 'SQLite 연결 수명 및 자원 안정성', '테스트 경고 수정, Windows 장시간 운영 미검증'),
    ('rights', '콘텐츠/아바타/음성 권리 확인', '운영자 직접 확인 대기'),
    ('approval', '운영자 명시적 최종 검수·승인', '승인 대기'),
)


@dataclass(frozen=True)
class ArchivedFile:
    path: str
    status: str
    digest: str = ''


@dataclass(frozen=True)
class AcceptanceReport:
    archived: tuple[ArchivedFile, ...]
    blockers: tuple[str, ...]
    operator_claims: int
    original_roadmap_pending: bool
    hardware_verified: bool = False
    actual_broadcast_verified: bool = False
    approval_granted: bool = False
    can_release: bool = False

    def describe(self) -> str:
        lines = [
            '100 최종 기능 검수 자료 · 미승인 오프라인 검토',
            '출시/실방송 승인: 차단 · Windows/OBS/음성/아바타 실검증: 미완료',
            '※ 보관된 파일의 존재·해시 점검은 테스트 재실행 또는 실제 제품 검증이 아닙니다.',
            f'099 운영자 자기보고 확인 입력: {self.operator_claims}건 (승인·검증 증거가 아님)',
            '원본 로드맵 010/100 승인 대기: ' + ('확인' if self.original_roadmap_pending else '검증 불가/변경 감지'),
            '', '동봉 프로젝트 문서/기존 로그 검토:'
        ]
        lines += [f'- {x.path}: {x.status}' + (f' (SHA256 {x.digest[:12]}…)' if x.digest else '')
                  for x in self.archived]
        lines += ['', '최종 승인을 막는 사항:']
        lines += [f'- {b}' for b in self.blockers]
        lines += ['', '원본 100단계 실제 최종 승인은 운영자만 결정합니다.',
                  '이 화면은 최종 승인 버튼/플래그를 제공하지 않습니다.',
                  '외부 접속·사용자 PC 정보 수집·OBS 실행·실제 방송은 수행하지 않았습니다.']
        return '\n'.join(lines)

    def safe_export(self) -> dict:
        return {
            'schema': 'aisting_final_review_dossier_v1',
            'type': 'unapproved_offline_review_only',
            'review_items': [dict(id=x, subject=y, evidence_scope=z) for x, y, z in REVIEW_ITEMS],
            'archived_project_files': [dict(path=x.path, status=x.status, sha256=x.digest) for x in self.archived],
            'operator_self_report_count': self.operator_claims,
            'blockers': list(self.blockers),
            'roadmap_010_100_pending': self.original_roadmap_pending,
            'hardware_verified': False,
            'actual_broadcast_verified': False,
            'approval_granted': False,
            'can_release': False,
            'external_posted': False,
            'user_pc_autocollected': False,
        }


def inspect_bundled_project(root: Path) -> tuple[tuple[ArchivedFile, ...], bool]:
    """Inspect ONLY six known files within an explicitly selected project root.

    Never glob, inspect user environment, follow symlinks, or call network.
    Invalid or missing files are blockers; inspection cannot grant approval.
    """
    if not isinstance(root, Path):
        raise TypeError('동봉 프로젝트 루트 경로가 필요합니다.')
    results: list[ArchivedFile] = []
    payloads: dict[str, bytes] = {}
    for name in ALLOWED_FILES:
        path = root.joinpath(*name.split('/'))
        try:
            # Reject symlinks in any component, including root and its ancestors.
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError('심볼릭 링크 파일은 검사하지 않습니다')
            if not path.is_file():
                raise ValueError('파일 없음')
            if path.stat().st_size > MAX_EVIDENCE_BYTES:
                raise ValueError('검토 허용 용량 초과')
            data = path.read_bytes()
            if len(data) > MAX_EVIDENCE_BYTES:
                raise ValueError('검토 허용 용량 초과')
            payloads[name] = data
            digest = sha256(data).hexdigest()
            status = '보관 파일 존재(실제 동작 증거 아님)'
            if name == ALLOWED_FILES[0] and digest != EXPECTED_ORIGINAL_SHA256:
                status = '원본 기획안 해시 불일치'
            if name == 'config/roadmap.json' and digest != EXPECTED_ROADMAP_SHA256:
                status = '로드맵 원본 해시 불일치'
            results.append(ArchivedFile(name, status, digest))
        except (OSError, ValueError) as exc:
            results.append(ArchivedFile(name, '검토 불가: ' + str(exc)))
    roadmap_pending = False
    try:
        raw = payloads['config/roadmap.json']
        roadmap = json.loads(raw.decode('utf-8'))
        steps = roadmap['steps']
        by_number = {x['number']: x for x in steps}
        roadmap_pending = (len(steps) == 100 and len(by_number) == 100
                           and set(by_number) == set(range(1, 101))
                           and by_number[10]['status'] == 'pending'
                           and by_number[100]['status'] == 'pending'
                           and sha256(raw).hexdigest() == EXPECTED_ROADMAP_SHA256)
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        pass
    return tuple(results), roadmap_pending


def build_final_acceptance(archived: tuple[ArchivedFile, ...] = (),
                           roadmap_pending: bool = False,
                           operator_report: MaintenanceReport | None = None) -> AcceptanceReport:
    if type(archived) is not tuple or any(type(x) is not ArchivedFile for x in archived):
        raise TypeError('검증되지 않은 보관 파일 목록입니다.')
    if type(roadmap_pending) is not bool:
        raise TypeError('로드맵 상태가 올바르지 않습니다.')
    count = 0
    if operator_report is not None:
        if type(operator_report) is not MaintenanceReport or tuple(x.key for x in operator_report.items) != CHECK_IDS:
            raise TypeError('099 운영자 점검 입력 형식이 올바르지 않습니다.')
        count = sum(x.status == STATUS_REVIEWED for x in operator_report.items)
    blockers = [x[1] + ': ' + x[2] for x in REVIEW_ITEMS if x[0] not in ('requirements', 'program', 'settings')]
    blockers.append(KNOWN_UNRESOLVED[0])
    if not archived:
        blockers.append('동봉 문서 검사 미실행(운영자가 수동 검토 필요)')
    else:
        names = {x.path for x in archived if x.status.startswith('보관 파일 존재')}
        if names != set(ALLOWED_FILES) or len(archived) != len(ALLOWED_FILES):
            blockers.append('동봉 프로젝트 파일 누락/변경/검토 불가')
    if not roadmap_pending:
        blockers.append('원본 로드맵 010/100 승인 대기 상태 미확인')
    return AcceptanceReport(archived, tuple(blockers), count, roadmap_pending)


def export_final_acceptance(report: AcceptanceReport, path: Path) -> Path:
    """Manual JSON export, no overwrite. Never write a release authorization."""
    if type(report) is not AcceptanceReport or not isinstance(path, Path):
        raise TypeError('올바른 최종 검수 결과와 운영자 선택 파일 경로가 필요합니다.')
    if path.suffix.lower() != '.json':
        raise ValueError('JSON 파일만 저장합니다.')
    if report.can_release or report.approval_granted or report.hardware_verified or report.actual_broadcast_verified:
        raise ValueError('실제 확인/승인 상태가 조작된 보고서는 저장할 수 없습니다.')
    if not report.blockers or not any('SQLite' in x for x in report.blockers):
        raise ValueError('미해결 문제가 삭제된 검수 보고서는 저장할 수 없습니다.')
    payload = json.dumps(report.safe_export(), ensure_ascii=False, indent=2) + '\n'
    with path.open('x', encoding='utf-8') as out:
        out.write(payload)
    return path
