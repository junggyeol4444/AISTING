"""요구사항 검사 및 진행 상태를 보여 주는 읽기 전용 명령행 도구."""
from __future__ import annotations
import sys
from .requirements import ROOT, load_json, status, validate


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {'validate', 'status'}:
        print('사용법: python tools.py {validate|status}')
        return 2
    config = load_json(ROOT / 'config' / 'requirements.json')
    roadmap = load_json(ROOT / 'config' / 'roadmap.json')
    if sys.argv[1] == 'validate':
        errors = validate(config, roadmap)
        if errors:
            for error in errors:
                print('오류:', error)
            return 1
        print('검증 통과: 핵심 기본값·승인 원칙·100단계 로드맵')
        return 0
    s = status(roadmap)
    print(f"진행률: {s['completed']}/{s['total']}")
    if s['current']:
        current = s['current']
        print(f"현재 단계: {current['number']} — {current['title']} ({current['status']})")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
