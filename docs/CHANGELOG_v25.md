# v25 개발 변경 기록 — 25단계 한국어 대화 시험

기준 누적 소스: `AISTING_Offline_Development_v24.zip` (158개 파일). **기존 파일 삭제 없음.**

## 코드 변경

- 신규 `src/ai_broadcaster/korean_dialogue_test.py`: 7건 한국어 예시/사용자 편집 대본, 30건·10,000자 상한, 별도 모의 코어 실행, FIFO/중복/한글 포함·Unicode 깨짐 검사, 건별 결과 및 중단 시 미처리 수 보존.
- 수정 `src/ai_broadcaster/desktop.py`: `한국어 대화 시험` 탭, 수동 실행·예시 재설정, 입력 오류/실패/미검증 구분 표시.
- 신규 `tests/test_korean_dialogue_test.py`: 입력·응답·예외·순서·무접속·설정 보존 검증.
- 신규 `scripts/gui_korean_dialogue_test_smoke.py`: Linux 가상 Tk GUI에서 시험·오류·재설정·무조회 검증.
- 변경 `config/roadmap.json`, `docs/ROADMAP_100.md`, `docs/STATUS.md`, `README.md`: 25단계 구현 증거 기록, 공식 상태는 `pending`/9·100 유지.
- 신규 `docs/KOREAN_DIALOGUE_TEST.md`: 시험의 정확한 범위와 한계, 재현 방법.

## 검증 및 보류

- Linux Python 3.13 unittest **510/510** 통과 (v24 479 + 신규 31).
- Linux Xvfb Tk GUI smoke **24/24** 통과 (v24 23 + 신규 1).
- 오프라인 환경 자가점검 **5/5**, Python AST **83/83**.
- v24 기존 158개 파일 모두 유지(의도적 수정은 `TEST_RESULTS.txt` 포함 6개); 원본 기획안 SHA256 불변.
- Windows 실기기·EXE 실행 및 실제 Ollama 한국어 품질 검증 **미수행**. 모의 구조 검증은 의미/자연스러움 검증이 아님.
- 10단계 최종 승인·11단계 이후 사용자 PC 확인은 승인 대기. GitHub/클라우드/설치/계정/실방송/원격 제어 없음.
