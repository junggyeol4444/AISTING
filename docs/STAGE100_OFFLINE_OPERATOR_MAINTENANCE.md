# v100 / 원본 099 운영자 점검 및 유지보수 체계 — 오프라인 수동 체크리스트

## 원본 요구사항과 구현 범위

원본 099 ‘운영자 점검 및 유지보수 체계 확정’ 및 `docs/ORIGINAL_PLAN.txt`의
‘완전 무인’이 아닌 ‘운영자가 가끔 로그·이상 발언·비용·권리·안정성 점검’하는
운영 원칙을 따른다. 외부 연결 금지 상태에서 구현한 것은 **사용자 수동 자기보고 점검표**다.
실제 운영 점검 완료, 출시 허가, 방송 신뢰성 확보를 의미하지 않는다.

- `src/ai_broadcaster/offline_operator_maintenance.py`: 12개 고정 운영자 확인 항목,
  `대기/운영자 확인 입력/문제 발견` 상태, 요약·미해결 이슈·실제 검증/승인 차단 플래그.
- `src/ai_broadcaster/desktop.py`: `운영자 유지보수 수동 점검` 탭에서 항목별 수동 기록,
  보고서 표시·초기화·사용자가 명시적으로 선택한 JSON 저장.
- 수동 JSON 저장은 새 파일 전용(`x`), 덮어쓰기 거부. 다른 로컬 프로젝트 파일·로그·
  Windows 사양·계정 정보·인증키를 읽거나 자동 수집하지 않음. 상태 기본값은 모두 `대기`.
- 모든 항목을 운영자가 `확인 입력`으로 표시하더라도 `can_release=false`,
  `final_approval_granted=false`, `hardware_verified=false`, `actual_stream_verified=false`.
  **운영자 입력은 객관적 실기기 검증의 증거가 아니므로 100단계 승인을 대체하지 않는다.**
- 이전 단계부터 남은 SQLite 연결 미종료 `ResourceWarning`은 **항상 미해결**로 표시;
  GUI 임의 상태 변경으로 이를 해소할 수 없음.

## 실제 검증 및 제약

- `tests/test_offline_operator_maintenance.py` 24개 신규 테스트: 항목 중복/유효성,
  상태 수동 입력, 독립 세션·불변 스냅샷, 승인 플래그 조작 거부, 덮어쓰기 차단,
  네트워크·프로세스·임의 파일 접근이 없는 읽기 전용 경로.
- `scripts/gui_offline_operator_maintenance_smoke.py`: Linux/Xvfb GUI 수동 기록,
  수동 JSON 파일 저장, 동일 파일 덮어쓰기 차단 및 기존 설정 보존.
- 정확한 전체 자동/GUI/압축 해제본 결과는 `logs/STAGE100_FINAL_VALIDATION.txt` 참조.

### 미구현/미검증 — 최종 승인 대기

Windows 10/11 실기기·EXE·실제 AI 모델·TTS·2D/3D 모델·OBS·플랫폼 인증·
실시간 방송·디스코드/카페 실제 게시·수일간 메모리/자원 안정성·SQLite 경고 수정,
실제 운영 로그/지출·권리 검사·사용자 최종 승인은 수행되지 않았다.
**코드 개발 도달 범위 99/100 ≠ 제품 완성률**이며 원본 099/010 상태와
`config/roadmap.json`의 `pending` 상태를 유지한다.
다음 원본 100: 최종 기능 검수 및 **운영자 승인**. 사용자 직접 결정이 필요하다.
