## 71. 2026-10-21 — 실제 500건/24시간 로컬 Ollama FIFO 부하검사에서 부분 수신의 거짓 성공 판정 수정

### 이 회차에 실제 반영한 소스 변경
- `scripts/aisting_real_ollama_fifo_soak.py`: 요청 500건 가운데 검사 마감 시각까지 1건만 들어왔더라도 기존에는 `accepted=1/completed=1/model_success=1`이면 `passed_no_drops=true`가 될 수 있던 오류를 수정. 요청 메시지 수 `messages`와 실제 큐 접수 `emitted`를 반드시 일치시킨 후에만 `passed_no_drops`/ `passed_three_second_local` 성공으로 판정. 기간/초당 수신률 제한으로 전부 넣지 못하면 `requested_messages_not_fully_accepted` 오류와 `not_accepted`, `requested_load_fully_accepted=false`를 결과에 표시. 실제 모델 실패 또는 시간 초과를 1~3초 달성으로 표시하지 않음.
- 기존 25건/60초 진행 집계에도 `not_accepted` 추가. 결과에 `local_p95_sample_count` 추가해 메모리 내 최대 1024건의 최근 샘플 p95를 전체 기간 p95로 오해하지 않도록 함. 기존 메시지 FIFO, 중복 보존, 실제 Ollama 호출, 96토큰 임의 제한 철회, Windows native EXE, 사용자 캐릭터/SQLite, 모든 원본 파일 보존.
- `tests/test_aisting_real_local_fifo_soak.py`: 500건 요청에 1초/0.1건초로 일부만 접수되지만 접수분은 전부 응답하는 모의 모델에서 **성공 금지** 회귀 검사, 36건 전량 처리 성공 및 p95 표본 수 확인 검사 2개 추가. 이 두 테스트의 모델 응답은 의도적으로 mock이며 실제 Ollama 500건 실증이 아님.

### 이 회차의 미반영 작업 및 안전 경계
- `src/ai_broadcaster/original_plan_voice_obs_bridge.py`에서 OBS CreateInput이 반환한 `inputUuid`를 검증해 사용자가 같은 이름으로 대체한 입력을 재생/삭제하지 않는 안전 보완을 준비했으나, GitHub `create_blob` 쓰기가 **safety checks에 의해 차단**됨. 이 경로는 이번 commit에 **반영되지 않았으며**, 기존 68절 '미터 구독 후 고유 임시 WAV 재생' 코드만 유지. 차단 우회하지 않음. 다음 회차에는 실제 main과 권한 확인 후 안전한 허용 범위에서 다시 개발.
- 실제 사용자 소유 GPT-SoVITS 모델·합법 한국어 참조 WAV, 공식 Live2D Cubism 모델과 OBS 같은 발화의 실제 Windows 음성·입·영상 동기화 실증, 실제 YouTube 소유자 OAuth, 실제 수백 명 시청자, 24시간 송출 및 최종 시청자 1~3초는 아직 확인하지 못했음. 합성 500건 모델 FIFO 검증은 시청자 실증과 구분.
- 본 회차는 OBS 송출·녹화·채팅 발신·계정 로그인·모델 훈련·타 프로젝트/예약/Drive·다른 브랜치·강제푸시·원본 roadmap/설정/SQLite 변경 없음.

### 직전 검증 및 다음 회차 필수
- 이번 작업 전 `main c65cde076aa8495bcbf3e71d88426117ed1ce518`의 전체 회귀 [39558769419](https://github.com/junggyeol4444/AISTING/actions/runs/39558769419) 성공, Windows EXE/Tk GUI/OBS 실제 읽기/Ollama 실제 로컬/공개 채팅 5/5 [39558769435](https://github.com/junggyeol4444/AISTING/actions/runs/39558769435) 성공. **이들은 이번 71절 코드의 검증이 아님.**
- 실제 500건 최신 [39554567985](https://github.com/junggyeol4444/AISTING/actions/runs/39554567985): 500/500 처리 성공, 499건 3초 초과, 총 p95 1962.984초, 대기 p95 1959.265초, AI p95 5.344초. 1~3초 목표 실패. 이 기록은 71절 새 수정 후의 재측정이 아님.
- 이번 코드의 main 안전 fast-forward 이후 **전체 회귀 + Windows native EXE/GUI·실제 로컬 Ollama/OBS/공개 채팅 CI**를 같은 HEAD에서 확인하고, 오류 발생 시 수정한 뒤 전량 재검증. 진행 중인 CI는 성공으로 단정하지 않음.
- 다음 회차는 이 문서 **1~71절 원문 전체**와 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, `docs/hourly-handoff-appendices/`의 모든 파일, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 최신 main 소스와 CI를 읽고, 남은 핵심 GPT-SoVITS→공식 Cubism→OBS 동일 발화 실통합, 실제 500건·24h 재연결·1~3초 병목을 계속 구현. 사용자가 요청한 '개발 여러 핵심 단위 먼저 → 전체 검증 → 수정 → 전체 재검증'을 지키고 무단 기능/정책 변경 금지.
