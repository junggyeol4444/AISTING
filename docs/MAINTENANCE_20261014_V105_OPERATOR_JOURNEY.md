# AISTING v105 유지보수 — Windows 사용자 관점 오프라인 전체 흐름 점검

**원본 100단계 개발표의 새 단계가 아닙니다.** v101의 `100/100`은 코드 도달 범위일 뿐 실제 제품 완성률/승인률이 아닙니다. 원본 010/100 최종 사용자 승인과 Windows/실제 방송 검증은 계속 `pending`입니다.

## 실제 입력 자료와 기준

- 실제로 연 입력: `AISTING_Offline_Development_v104.zip` (1,035개 엔트리, ZIP CRC 이상 없음).
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `config/requirements.json`, `README.md`, 기존 유지보수·단위·GUI 테스트 로그와 사용자 요구를 대조했습니다.
- `config/roadmap.json`: 정확히 100개, `completed` 9개, `pending` 91개. 이전의 100/100 **코드 범위** 표현과 구분합니다.
- 운영자 설정은 플랫폼 0~3개 복수 선택, 콘텐츠/캐릭터/음성/아바타 자유 변경, 로컬 저장 및 기본 방송/예약/외부 업로드 비활성입니다.
- 원본 계획의 서버/24시간 자동 방송 목표는 현재 오프라인 Windows 소스의 구현·검증 사실과 다릅니다. 사용자가 금지한 외부 서비스/실제 송출은 실행하지 않았습니다.

## 실제 재현한 기존 결함

v104 `ChatRehearsal.process_next()`는 모의/로컬 AI 답변을 이미 전달해 `pending`에서 제거한 뒤 선택형 `LocalMemory.append()`가 `ValueError`를 내면 이를 처리하지 않았습니다. v104의 새 SQLite 외부 DB 거부 검증에서 `ValueError`가 발생할 수 있어, 이미 화면에 전달된 답변을 다시 대기열에서 재시도할 수 있다는 잘못된 GUI 오류 표시가 나타났습니다.

`tests/test_memory_failure_reporting.py`의 **실제 SQLite 교체 시나리오**를 수정 전 코드에 실행한 결과 3건 중 2건 통과, 1건 오류를 확인했습니다(`logs/MAINTENANCE_20261014_V105_BASELINE_FAIL.log`). 이 재현은 개발용 임시 DB에서만 했으며 사용자 파일을 사용하지 않았습니다.

## 수정 내용

- `src/ai_broadcaster/offline_chat.py`: 답변 전달 후 기억 저장에서 `ValueError`도 안전하게 기록합니다. 기존 답변/미처리 대기열을 보존하고, 외부 DB에 쓰거나 삭제하지 않습니다.
- `src/ai_broadcaster/desktop.py`: SQLite 기억 저장 실패가 1건 이상이면 연습 완료/중단/오류 상태에 **기억 저장 실패 건수**를 표시합니다. 답변이 화면에 표시됐다는 사실과 DB 저장 성공을 혼동하지 않도록 했습니다.
- `tests/test_memory_failure_reporting.py`: 정상 저장, SQLite 쓰기 오류, 전달 후 외부 DB 교체(비파괴)를 회귀 검증합니다.
- `scripts/gui_operator_journey_smoke.py`: 실제 Tk 창에서 첫 실행 → 플랫폼/콘텐츠/캐릭터/음성/2D 선택 → 저장 → 종료/재시작/복원 → 중복 모의 채팅 FIFO → 가짜 로컬 AI로 SQLite 저장 → 기억 저장 실패 경고 → 종료/재시작/DB 재조회까지 순서대로 확인합니다. **가짜 로컬 AI는 실제 Ollama 모델이 아닙니다.**
- `scripts/run_gui_regression_offline.py`: 기존 GUI 스모크 전체를 격리된 임시 HOME/LOCALAPPDATA 경로로 실행해 결과를 개별 기록하는 오프라인 실행기입니다. Linux는 `xvfb-run -a python scripts/run_gui_regression_offline.py`로 실행합니다.

## 실제 시험과 분명한 미검증

- 자동 테스트 및 Linux 가상 화면 Tk GUI 검사 결과는 별도 로그에 기록합니다. 통과 수는 원본 ZIP 및 재압축 ZIP을 **실제로 실행한 결과만** 적습니다.
- Windows 10/11 실제 사용자 PC에서 `run_windows.bat` 실행, Windows EXE 빌드·설치·실행, PowerShell/System.Speech TTS, 실제 VRM/Live2D, 실제 OBS/송출, 플랫폼 채팅/로그인, 실제 Ollama 모델, 장시간 실방송은 **실행하지 않았습니다**.
- 프로그램의 실제 방송 자동화 전체 동작은 이 소스에 아직 구현되지 않은 부분이 있어 **처음부터 끝까지 실제 방송 제품으로 작동한다고 주장할 수 없습니다**.
- SQLite 경고 0건은 Linux 자동/GUI 테스트에서만 해당하며, Windows 장시간 핸들 누수 없음의 증명이 아닙니다.
- 실사용자 데이터/음성/계정/외부 서비스/사용자 PC 접근·설치·결제·송출은 하지 않았습니다. 사용자 최종 승인도 수행하지 않았습니다.

## Windows 실기기에서 운영자가 나중에 직접 확인할 항목 (이번 실행 결과 아님)

Windows 10/11의 별도 승인된 테스트 환경에서 이미 설치된 Python 3.11+와 Tkinter로 `run_windows.bat` 첫 실행을 확인하고, 설정 변경/저장·재시작 복원·모의 채팅·SQLite 저장·오류/재시도·2D 창 열고 닫기·정상 종료를 점검해야 합니다. 그 뒤 **사용자가 별도 승인한 경우에만** 실제 Windows 음성/아바타/로컬 AI·OBS·실시간 채팅 및 장시간 방송을 별도 검증합니다. 이 목록은 실행 완료 보고가 아닙니다.

## 2026-10-14 실제 실행 수치 (Linux Python 3.13.5)

- v104 결함 재현: 신규 3개 테스트 중 2개 통과, 1개 오류(외부 SQLite 교체 후 `ValueError` 전파).
- 수정 후 신규 회귀: 3/3 통과. 전체 `unittest`: **2,017/2,017 통과**, `ResourceWarning` 로그 0건.
- Linux Xvfb 실제 Tk GUI 스모크: **100/100 통과**(기존 99개 + 사용자 전체 흐름 1개).
- 통합 사용자 흐름: 첫 실행/설정/2D 창/재시작/모의 중복 채팅/가짜 로컬 모델/SQLite/저장 실패 경고/최종 재시작 **5개 체크포인트 통과**.
- Python AST 파싱: **316/316 통과**.
- Windows 실행 파일과 빌드 배치: **정적 문자열/경로 검사만 통과**, 실제 Windows 실행 미검증.
- v104 기존 상대 파일 경로 **1,035/1,035 보존**, 기존 파일 변경 4개(README, TEST_RESULTS, offline_chat, desktop). 원본 기획안/로드맵/요구사항 JSON 해시 불변.
- 후보 ZIP을 별도 폴더에 압축 해제하여 전체 단위 테스트 **2,017/2,017 재통과**, 선택 GUI 3개 스크립트 통과. 최종 ZIP의 별도 압축 해제 재검증은 ZIP 외부 결과 보고서를 확인하세요.

**주의:** 위 수치는 Linux 오프라인 모의·통합 검증 결과이지 Windows 실사용 성공이나 실제 방송 제품 검증 결과가 아닙니다.
