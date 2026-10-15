# 32단계 성격 및 취향 반영 — 2026-10-13

- `src/ai_broadcaster/personality_preferences.py`: 운영자 입력 취향만 프롬프트에 포함하는 읽기 전용 검증 기능.
- `src/ai_broadcaster/desktop.py`: '성격·취향 반영' 탭, 선택적 좋아하는 것/싫어하는 것 입력, 수동 미리보기 추가.
- `tests/test_personality_preferences.py`: 6개 단위 테스트 추가.
- 미설정 취향을 추측하지 않음. 취향은 저장하지 않으며 기존 설정·SQLite 데이터를 변경하지 않음.
- 실제 모델/Windows 실기기/방송 연결은 검증하지 않음.
- 개발 범위 32/100; 사용자 승인과 실기기 검증은 별도 대기. 기존 문서의 9/100 표기는 과거 승인 기준 기록이며 현재 개발 범위를 뜻하지 않음.
