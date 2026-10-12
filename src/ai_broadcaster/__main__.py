"""CLI: 개발 상태 조회 및 원본 기획안 제약 검사."""
import sys
from .requirements import ROOT, load_json, validate, validate_features, status

def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"validate", "status"}:
        print("사용법: python tools.py {validate|status}")
        return 2
    config = load_json(ROOT / "config" / "requirements.json")
    roadmap = load_json(ROOT / "config" / "roadmap.json")
    features = load_json(ROOT / "config" / "features.json")
    if sys.argv[1] == "validate":
        errors = validate(config, roadmap) + validate_features(features)
        for error in errors:
            print("오류:", error)
        if errors:
            return 1
        print("검증 통과: 기획안 원칙 · 핵심 기능 · 100단계")
        return 0
    s = status(roadmap)
    print(f"진행률: {s['completed']}/{s['total']}")
    if s["current"]:
        x = s["current"]
        print(f"다음 단계: {x['number']} — {x['title']} ({x['status']})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
