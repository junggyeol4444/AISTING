# 22단계 — 기본 코어 수동 모의 실행 (실방송 코어 아님)

## 실제 구현

`src/ai_broadcaster/core_execution.py`에 `OfflineCoreSession`을 추가했습니다.
21단계의 `CoreInput`/`CoreReply` 타입을 사용하여 **사용자 입력 → 기존 모의 답변기 → 메모리 이력**을
실제로 실행합니다. `MockCoreReplyPort`가 기존 `MockReplyGenerator`에 입력과 최근 8건의 이력을 전달합니다.
외부 Open-LLM-VTuber 코드를 다운로드하거나 통합하지 않았습니다.

- `enqueue()`는 `닉네임: 메시지` 대본을 전부 검증한 후 FIFO 대기열에 추가합니다. 중복 채팅을 삭제하지 않습니다.
- `process_one()`은 성공할 때만 대기열에서 제거하고 이력을 추가합니다. 실패하면 실패 항목은 그대로 보존됩니다.
- `run_batch()`는 한 번에 최대 50건을 처리합니다. 중간 실패 시 이미 성공한 답변과 미처리 대기열을 구분해 오류로 반환합니다.
- 메모리 이력은 최근 500건만 유지하며, 대기열도 최대 500건입니다. 사용자 파일·기존 SQLite는 읽거나 쓰지 않습니다.
- `update_selection()`은 선택형 설정을 검증해 메모리 스냅샷만 갱신합니다. 기존 대기열·이력을 지우지 않습니다.
- `reset()`은 모의 코어 세션만 초기화합니다. 기존 방송 설정·채팅 연습·기억에는 영향을 주지 않습니다.

GUI의 `기본 코어 수동 실행` 탭은 **사용자가 누르는 버튼에서만** 대본 추가/1건 실행/최대 50건 실행/초기화를
수행합니다. 탭을 열거나 앱을 시작해도 코어 실행, PC 사양 조회, 모델 연결, 사용자 파일 저장은 없습니다.
시청자 채팅 연습 탭의 Ollama 모드를 선택했더라도 이 모의 코어는 해당 모드를 **사용하지 않습니다**.

## 엄격한 구현 범위

**구현됨:** 로컬 Python 프로세스 안에서의 입력·모의 응답·이력 연결과 GUI 수동 구동.

**미구현:** Open-LLM-VTuber 등 외부 방송 코어, 실제 LLM 응답 연결, OBS/플랫폼 송출, 실제 채팅 수신,
SQLite 장기 기억 연동, 방송용 음성/아바타 출력, 자동 방송 실행, Windows EXE 검증.
기존 채팅 연습의 수동 localhost Ollama 기능은 변경하지 않았습니다.

10단계 전체 개발 기준 최종 승인과 11단계 이후 사용자 PC 실제 확인은 여전히 **pending**입니다.
22단계의 코드 구현만으로 공식 로드맵 완료 표시를 하지 않으며, 공식 진행률은 **9/100**입니다.

## 검증

- `python -m unittest discover -s tests -q` — 기존 회귀 테스트 + 신규 22단계 단위 테스트
- GUI 가능한 환경: `python scripts/gui_core_execution_smoke.py` — 탭 이동/버튼/FIFO/오류/무전송 검사
- 전체 GUI 회귀: `scripts/gui_*_smoke.py` 및 `scripts/gui_smoke.py`
- 실제 실행/로그: `docs/VALIDATION_v22_*.log`, `TEST_RESULTS.txt`

Windows 10/11 실제 PC 실행과 Windows EXE 빌드는 이 환경에서 확인하지 못했습니다.
