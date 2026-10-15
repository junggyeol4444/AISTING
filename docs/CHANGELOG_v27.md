# v27 개발 변경 기록 — 27단계 기본 응답 오류 처리

기준: 실제 이 대화에 전달된 `AISTING_Offline_Development_v26.zip` (182개 파일). 원본 누적 파일 삭제 없이 이어서 개발.

## 실제 코드 변경

- 수정 `src/ai_broadcaster/core_execution.py`: 6종 오류 분류, 민감한 원본 예외 내용 비노출, 실패 선두/성공 이력 보존, 명시적 수동 재시도(최대 2회 추가), 총 3회 시도 상한, 확인 후 실패 입력 1건 제외, 초기화 시 오류 상태 정리. 기존 코어 계약/FIFO/선택형 설정 유지.
- 수정 `src/ai_broadcaster/korean_dialogue_test.py`, `context_retention_test.py`: 신규 세부 오류 클래스를 기존 보고서의 `RuntimeError`/`ValueError` 분류와 호환 표시해 기존 25·26단계 회귀 시험 유지.
- 신규 `src/ai_broadcaster/response_error_test.py`: 실제 모델 없이 8종 결함 주입/오류 처리·복구·데이터 보존 검사.
- 수정 `src/ai_broadcaster/desktop.py`: 기존 코어 탭의 수동 재시도/확인 후 제외 버튼, 오류 코드 표시 및 신규 `응답 오류 처리 시험` 탭.
- 신규 `tests/test_response_error_handling.py`: 오류 처리·회귀·보안·무접속 단위 테스트.
- 신규 `scripts/gui_response_error_smoke.py`: 가상 Tk 화면에서 오류 8종, 수동 재시도, 확인 대화상자 취소/승인, 상한, 무접속 검사.
- 신규 `docs/RESPONSE_ERROR_HANDLING.md`: 기능 범위·안전 정책·검증 한계.
- 수정 `README.md`, `docs/STATUS.md`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `TEST_RESULTS.txt`: 증거와 승인 대기 상태 유지.

## 검증 결과

Linux Python 3.13 자동 테스트 **572/572** (기존 541 + 신규 31), Xvfb Tkinter GUI smoke **26/26** (기존 25 + 신규 1), 오프라인 자가점검 **5/5**, Python AST **89/89** 통과. 기존 v26 파일 **182개 누락 없이 보존**, 원본 기획안 SHA256 동일. 실제 실행 결과는 `docs/VALIDATION_v27_*.log`와 `TEST_RESULTS.txt`에 기록. 이 기능의 테스트는 **모의 포트**만 사용합니다. Windows PC 실제 AI/방송 장애 복구는 아직 검증하지 않았습니다. 10단계 최종 승인과 11단계 이후 실제 PC 확인은 보류, 공식 진행률 **9/100**. GitHub·원격 서버·설치·결제·계정·OBS·방송·PC 정보 조회/원격 제어 없음.
