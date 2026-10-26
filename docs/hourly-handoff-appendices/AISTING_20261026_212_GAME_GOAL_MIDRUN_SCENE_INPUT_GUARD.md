# AISTING 212절 — 2026-10-26, 승인형 자율 게임 중간 목표 확인·OBS 게임 장면 입력 보호

## 시작 시 실제 기준
- `junggyeol4444/AISTING/main` 시작 HEAD: `7d87a8a6f9bbbedefbd86bd0e7be3acd71db39c4`(211절 최종 기록). 이번 회차의 마지막 HEAD는 커밋 뒤 별도 조회해서 보고한다.
- 확인한 실제 소스: `approved_local_game_control.py`, `approved_game_goal_journal.py`, `approved_local_game_vision.py`, `game_goal_evidence.py`, `desktop_obs_tab.py` 및 211절 부록. 원본 기획 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 이전 두 대용량 인수인계는 기존 내용을 유지한다.
- Windows GUI/기존 OBS WebSocket·Ollama·SQLite 게임 장부 위에서 개발했다. 사용자 승인 없는 게임 입력/실제 OBS 방송/녹화/장면 변경·OAuth·채팅/공지 발신 없음.

## 실제 제품 소스 커밋 4개 — 기존 main 정상 반영
1. `c5f417c5fd6d6922f5a13751e17ee8c068caf689`: 기존 `src/ai_broadcaster/approved_local_game_control.py`의 장기 게임 입력 루프에 운영자 설정 `progress_check_every`(1~10회) 추가. 예전에는 전체 행동 종료 후에만 두 시점 목표 판정을 했다. 이제 지정한 행동 간격마다 **새 실제 OBS 후속 화면**을 로컬 시각 모델로 읽고 이전 관찰과 기존 목표 판정 함수로 `진행중/불확실/달성후보`를 분리한다. 두 시점에서 목표 달성 후보가 나타나면 후속 키·마우스 입력을 중단한다. 실제 목표 성공/보상 수령으로 단정하지 않는다. 기존 SQLite 장부에 `후속관찰/목표판정`을 남기고 이전 승인 세션의 입력시도는 재실행하지 않는다. 첫 OBS 관찰 장면을 승인된 세션 고정 장면으로 취급하고 중간에 다른 장면으로 변경되면 추가 입력을 차단, 원본 장부에 `중단`을 기록한다.
2. `4f9d68a6cf413e9d2f58caacc0510e7291e4e643`: 기존 `src/ai_broadcaster/desktop_obs_tab.py` Windows GUI에 자율 게임 목표 판정 간격 입력(기본 3회, 1~10회), 실제 게임 조작 승인창의 간격/장면 변경 제약 고지, 게임 장면 변경 차단 상태 메시지 추가. 매 실행 1~100회 행동 한도와 새 수동 승인 유지.
3. `c3946cec6f5fb079cb654815738737f304487e9c`: 신규 `src/ai_broadcaster/approved_game_scene_identity.py`는 **입력 직전** 현재 OBS 실제 장면 이름이 시작 당시 OBS 장면과 같음을 읽기 전용 WebSocket으로 확인한다. OBS 송출/장면/계정 조작 없음. 소켓 종료 후 반환; 게임 Win32 HWND/PID/포커스 확인은 기존 모듈에 그대로 유지.
4. `762db4b42be3a81efb4c7a813ae706a8724cc908`: 기존 `approved_local_game_control.py`의 Win32 SendInput 직전에 키/클릭의 OBS 장면 동일성 재확인 및 미확인 시 SQLite `중단` 기록과 후속 입력 차단. `wait/stop`은 무출력 행동으로 기존 경로 유지. 실제 OBS 장면 이름 확인은 게임 창/게임 내용 동일성의 완전한 증명은 아니다.

## 완료와 남은 작업
- **이번 회차 실제 소스 개발/기존 main 커밋 완료. 전체 100단계 및 필수 방송 기능 개발 미완료.** 새 승인 없이 자동 게임 재시작, 과거 게임 입력 재생, 새 브랜치 생성/삭제, 강제 push, Drive/다른 프로젝트 변경 없음.
- 한국어 모델/캐릭터/기억, 사용자 SQLite/게임 목표 장부, `num_predict=96`, `keep_alive=10m`, 기존 OBS/공식 Live2D/GPT-SoVITS 기능 변경하지 않음.
- **테스트 NOT_RUN / 통합 회귀 NOT_RUN / CI 미조회·미확인 / Windows 10·11 EXE·GUI 및 실제 게임 조작 NOT_RUN / GPT-SoVITS 실제 한국어 WAV→공식 Cubism 입→OBS 4플랫폼 장기 방송·시청자 1~3초 NOT_RUN**. 원래 500건 CI 39720448468은 500/500건 3초 초과, FIFO p95 2973.875초, 전체 p95 2979.984초 실패; Windows CI 39722213656 취소 이력 보존.
- 추가 미개발: 4플랫폼 수백 명 SQLite 전체 내구/재연결·관측 불가 공백, AI 선행 추론과 FIFO 실제 1~3초 달성, 권리 한국어 WAV·공식 Cubism 입·OBS 출력의 동일 발화 장시간 인과, 사용자 승인형 24시간 운영/장애 복구, 원본 AI 게임/방송 콘텐츠의 실사용 완성.

## 다음 회차
현재 `main` HEAD를 새로 읽고 이번 212절 부록 및 이후 소스를 확인하여 **남은 핵심 제품 코드를 먼저 누적 구현**. 모든 기능 개발을 끝낸 후에만 Windows 10/11 EXE/GUI·실모델·OBS·공식 Live2D·4플랫폼·장시간 통합 검증 → 발견 오류 일괄 수정 → 전체 재검증.
기존 AISTING 대화에 보고를 우선 시도하며 예약 생성·삭제·비활성화, 다른 대화로 이동 요구, 다른 저장소·Drive 조작 금지. 실제 연결에 권한/보안이 없으면 우회하지 않음.
