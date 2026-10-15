# v26 개발 변경 기록 — 26단계 대화 맥락 전달 확인

기준: 실제 제공된 `AISTING_Offline_Development_v25.zip` (170개 파일), 원본 파일 삭제 없이 이어서 개발.

## 실제 변경 코드

- 수정 `src/ai_broadcaster/core_execution.py`: 답변 포트에 전달하는 최근 8개 이력을 `MAX_CONTEXT_TURNS`와 읽기 전용 `context_for_next_turn`으로 명시화. 기존 FIFO·500건 이력·실패 보존 정책 유지.
- 신규 `src/ai_broadcaster/context_retention_test.py`: 별도 모의 세션과 기록 포트로 맥락 전달/중복/순서/최대 8건 잘림을 검증. 실패 시 미처리 수와 실패 사유 표시.
- 수정 `src/ai_broadcaster/desktop.py`: `대화 맥락 전달 시험` 탭 및 수동 실행/입력 편집/재설정/결과 표시.
- 신규 `tests/test_context_retention_test.py`: 정상·경계·실패·결함 주입·무접속·선택값 보존 등 31개 회귀 테스트.
- 신규 `scripts/gui_context_retention_smoke.py`: Linux 가상 Tk GUI의 탭/수동 실행/오류/초기화/무접속 검증.
- 신규 `docs/CONTEXT_RETENTION_TEST.md`: 재현 방법, 정확한 검증 범위와 한계.
- 수정 `config/roadmap.json`, `docs/ROADMAP_100.md`, `docs/STATUS.md`, `README.md`, `TEST_RESULTS.txt`: 개발 증거 기록, 공식 승인/PC 확인은 `pending` 유지.

## 실행 검증 및 제약

- Linux Python 3.13 자동 테스트 **541/541** (기존 510 + 신규 31) 통과.
- Linux Xvfb GUI smoke **25/25** (기존 24 + 신규 1) 통과.
- 20단계 오프라인 자가점검 및 전체 소스 구문 검사, ZIP 재압축 검증 결과는 `docs/VALIDATION_v26_*.log` 참조.
- 이 시험은 실제 AI의 맥락 **이해 능력**을 검증하지 않음. Windows 실기기/EXE 및 로컬 모델 연결 미수행.
- 10단계 최종 승인·11단계 이후 PC 확인 보류, 공식 **9/100** 유지. GitHub·클라우드·설치·계정·OBS·방송·원격 제어 없음.
