# v28 개발 변경 기록 — 28단계 응답 기록 저장

기준: 이 대화에 실제 전달된 `AISTING_Offline_Development_v27.zip` (194개 파일). 기존 전체 파일 보존 후 다음 단계 구현.

## 실제 코드

- 신규 `src/ai_broadcaster/response_records.py`: 성공 응답 메모리 스냅샷, 별도 로컬 SQLite 수동 저장·중복 방지·조회·2회 확인 삭제, DB 식별값/구조 검증, 기존 파일 덮어쓰기·링크/정션·용량 초과 방지, 오류 시 롤백.
- 수정 `src/ai_broadcaster/core_execution.py`: 수동 저장 시에만 생성하는 세션 식별자와 초기화 시 식별자 재설정. 기존 FIFO/맥락/오류/재시도/선택값 불변.
- 수정 `src/ai_broadcaster/desktop.py`: `응답 기록 저장` 탭 및 미리보기/확인 후 저장/조회/2회 확인 삭제. 기본 코어 자동 기록 없음.
- 신규 `tests/test_response_records.py`: 수동 동의, 중복 채팅, 부분 성공, 실패 보존, 스냅샷/DB 경계, 롤백, 외부 부작용 차단, 기록 한도, 삭제 승인 및 기존 설정 불변 검사.
- 신규 `scripts/gui_response_records_smoke.py`: Xvfb GUI에서 동의 거부/저장/중복/조회/삭제 2회 확인/원본 설정·기억 보존 검증.
- 신규 `docs/RESPONSE_RECORDS.md`: 기능·개인정보·제한·실기기 미검증 사항 기록.
- 업데이트 `README.md`, `docs/STATUS.md`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `TEST_RESULTS.txt` 및 검증 로그.

## 승인과 검증 범위

28단계는 코드 및 가상 환경 테스트만 진행했으며 실제 Windows 사용자 PC 확인 전이므로 **pending**. 10단계 최종 사용자 승인과 11단계 이후 PC 정보 수집/실기기 확인도 **pending**. 공식 **9/100** 유지. GitHub/원격 저장소/설치/계정/유료 API/OBS/실방송/사용자 PC 접근 없음.

## 실제 검증 결과

Linux Python 3.13 자동 테스트 **609/609**(기존 572+신규 37), Xvfb Tkinter GUI smoke **27/27**(기존 26+신규 1), 오프라인 자가점검 **5/5**, Python AST **92/92** 통과. 기존 v27 원본 **194개 파일 전부 보존**, 원본 기획안 SHA256 동일. 결과는 `docs/VALIDATION_v28_*.log`에 기록했습니다. 실제 Windows EXE/실기기 시험은 수행하지 않았습니다.
