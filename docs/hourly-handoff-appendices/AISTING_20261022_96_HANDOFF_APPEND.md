## 96. 2026-10-22 — GPT-SoVITS 실제 WAV 길이 기준 OBS 관찰 개선 및 95절 Windows 테스트 경합 수정

### 지시·기존 원문 보존
- AISTING 기존 `junggyeol4444/AISTING` `main` 시작 HEAD `da91df42f77160c74e1be835b09ab387547a5c46`. 기존 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`·`docs/AISTING_HOURLY_FULL_HANDOFF.md`의 **1~95절 원문 전부**, `docs/hourly-handoff-appendices/` 모든 과거 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 캐릭터·SQLite·음성/모델/운영자 설정·기존 코드를 보존하고 본 절만 추가.
- 새 브랜치, force push, 롤백, 다른 저장소/프로젝트/예약/Drive 변경 없음. 사용자 동의 없는 YouTube OAuth/계정 로그인/채팅 발신/OBS 방송·녹화/모델 훈련/사용 권리 없는 음성 금지. 임의 `num_predict=96`·`keep_alive=10m`·기억 제한·답변 길이/캐릭터 변경 없음.

### 이전 95절 실제 검사 결과 및 오류 재현
- [95절 최초 전체 회귀 39718127265](https://github.com/junggyeol4444/AISTING/actions/runs/39718127265): **2,543개 실행, 2개 skipped, 실패 0 성공**.
- 같은 초기 HEAD [Windows 39718127244](https://github.com/junggyeol4444/AISTING/actions/runs/39718127244): **windows-exe 실패(모의 동시 음성/OBS 성공형 4개)**; OBS·Twitch·치지직/SOOP·Ollama 다른 job 네 개 성공. 95절 모의 립싱크 표본이 zero-duration에서 양의 구간으로 바뀌었지만 일부 Windows 스케줄링에서 OBS 검사보다 빨리 끝나 성공형 모의 결과가 false였던 검사 경합.
- 95절 수정 HEAD `da91df42` [전체 재검증 39718736644](https://github.com/junggyeol4444/AISTING/actions/runs/39718736644): success. [Windows 39718736665](https://github.com/junggyeol4444/AISTING/actions/runs/39718736665): **windows-exe 실패 2건** (`test_existing_official_ai_turn_only_once_and_obs_read_only`, `test_slow_korean_voice_uses_later_obs_meter_window`); 나머지 obs-real-readonly, twitch-public-readonly, korean-public-chat-readonly, ollama-real-local-e2e 성공. 원인: 모의 OBS 미터 관찰과 모의 립 움직임 사이에 경합이 아직 남음. 이 실패를 숨기지 않으며 같은 수정본의 전체/Windows 검사를 재실행해 확인해야 함.

### 이번 회차 실제 코드 개발과 테스트 보정
- `src/ai_broadcaster/original_plan_voice_obs_bridge.py`: 기존 **실제 사용권 확인/운영자 승인** GPT-SoVITS WAV 합성→OBS 유일 임시 미디어 입력→실제 선택 입력 미터 신호 검사 경로를 그대로 사용. 기존 OBS 미터 관찰시간 고정 **3초**는 실제 WAV가 5~8초일 때 뒤쪽 소리 확인 기회를 잃게 하므로, 실제 합성에서 반환된 `frame_count / sample_rate`로 계산한 WAV 길이에 따라 **3초 이상·최대 8초** 관찰 `min(8, max(3, wav_duration+0.25))`로 보완. 샘플레이트·프레임 수 부정확/0이면 새 OBS 입력 생성 전에 실패. 새로운 `RealVoiceObsResult` 읽기 전용 필드 `wav_duration_seconds`, `meter_observation_seconds`, `observation_covers_wav_duration` 추가. WAV가 8초를 넘으면 마지막까지 관찰하지 못한 사실을 false로 표시. 임시 WAV 삭제·원본 OBS 입력 보호·송출/녹화 중지/읽기 권한·동일 UUID 정리 로직 유지.
- `src/ai_broadcaster/desktop_chat_tab.py`, `src/ai_broadcaster/original_plan_studio.py`: 기존 Windows 네이티브 GPT-SoVITS→OBS 버튼 결과에 실제 WAV 길이/OBS 미터 관찰기간/8초 초과시 후반 미관찰 상태를 **한국어로 명확하게 표시**. OBS 신호 확인을 Live2D 립싱크/실제 방송 시청자 전달 증거로 격상하지 않음. 버튼 실행 시에만 원래 승인 과정을 거침.
- `tests/test_aisting_gpt_sovits_obs_integration.py`: 합성된 5초 WAV가 OBS 미터 5.25초 범위를 요청, 12초 WAV는 OBS 제한 8초를 요청하며 `observation_covers_wav_duration=False`, 검사 후 유일 임시 OBS 입력이 제거됨을 확인하는 계약 검사 1개(두 사례) 신규 추가. 실제 TTS 모델/OBS에 접속하는 테스트는 아님.
- `tests/test_aisting_official_chat_obs_pipeline.py`: 기존 Windows에서 불안정했던 2개 검사를 포함한 양의 정상 음성·OBS 관찰 경로의 스레드 경합 보정. 모의 OBS 미터는 자신의 관측 시작 이벤트를 기록하고 모의 립 움직임 종료 이벤트를 기다려 두 모의 구간이 실제로 겹치도록 구성. 두 번째 관찰창도 립 완료 이벤트와 동기화. 기존 **운영 코드의 strict positive overlap 정책과 이전/미래 발화 차단은 변경·완화하지 않음**. 실제 음성/입 움직임 실증은 아니며 모의 검사임.

### 마지막으로 확인한 실모델·FIFO 병목
- [94절 실제 Ollama synthetic 500건 39710567307](https://github.com/junggyeol4444/AISTING/actions/runs/39710567307): 500/500 무누락, 모델 실패 0, 네 플랫폼별 125건씩. 3초 초과 **500/500**, 전체 p95 **2767.640초**, FIFO 대기 p95 **2762.187초**, AI 처리 p95 **7.391초**. Ollama 서버 입력 평가 p95 **6.591132초**, 모델 로딩 0.118673초, 출력 0.509012초, 총 7.216993초. 최대 관측 FIFO 적체 **499건**. **1~3초 목표 실패**, 실사용 시청자 500명 아님.
- 92·93절 실제 500건도 500건 처리에는 성공했으나 1~3초에 실패. 모델/사용자 메모리 설정을 임의로 줄이는 해결책을 적용하지 않음.

### 미완료·후속 검증 필수
- 이 96절 코드 반영 HEAD의 전체 회귀 및 Windows 네이티브 EXE/GUI·실제 OBS 읽기·실제 Ollama·4플랫폼 공개 읽기 CI를 반드시 확인하고, 실패가 있으면 소스 고쳐 전체 재검증. GitHub Actions가 아직 대기/진행 중이면 성공이라 주장하지 않음.
- 기존 공식 Live2D Cubism과 GPT-SoVITS의 **같은 실제 발화** OBS 영상·오디오 결과/증거, 4플랫폼 **실제 시청자** 수백 명 처리, 24시간 실제 송출 안정성, E2E 시청자 1~3초는 미실증/미완료. 별개 WAV→OBS 입력 미터 단독 테스트는 Cubism 립싱크 증명이 아님. 기존 모든 인계·원본 코드/설정/캐릭터/SQLite 유지.
- 다음 97절에서는 최신 96절 main과 전체 Windows CI 오류부터 수정, 실제 GPT-SoVITS→공식 Cubism→OBS 연결 미완료 및 FIFO 병목을 기존 소스에서 계속 개발·재검증·원문 누적.


### 96절 첫 Windows 전체 검사 실패와 회귀 테스트 수정
- 최초 96절 코드 HEAD `6935e202c163825c4f20061df19e51110d44781a` [Windows CI 39720448453](https://github.com/junggyeol4444/AISTING/actions/runs/39720448453)의 `windows-exe` 작업 **실패**. Windows 원래 테스트 322건 중 **7개 error, 3개 failure**; 7개는 과거 `test_aisting_gpt_sovits_obs_integration.py`에서 TTS 모의 응답이 `wav_data`만 제공하고 새 WAV 길이 계산에 필요한 `sample_rate`와 `frame_count`를 제공하지 않아 `AttributeError`가 발생한 테스트 입력 계약 불일치. 3개는 `test_aisting_official_chat_obs_pipeline.py`의 Windows 모의 립싱크·OBS 동시 **positive** 샘플이 동시 시계 간격을 짧게 잡아 `verified_observation=False`가 된 스레드/시간 경합. 실제 모델/WAV/OBS 장치에 연결한 실사용 검사 오류라고 주장하지 않음. 첫 실패 기록 유지, 결과 은폐 금지.
- 이번 수정: `tests/test_aisting_gpt_sovits_obs_integration.py` 기존 7개 모의 WAV 응답 모두 `sample_rate=24000, channels=1, frame_count=80`을 추가하여 원래 음성 반환 데이터 계약을 충족. 기존 스트림 시작·장면 변경·녹화 상태·생성/정리 실패 시 기존 OBS 소스를 건드리지 않는 안전성 검사를 삭제하지 않고 지속 실행.
- `tests/test_aisting_official_chat_obs_pipeline.py` positive 구간 2개에서 OBS 동시 미터+입 샘플 시작 이벤트/립 종료 이벤트 동기화를 유지하면서 65ms의 **테스트 안 모의 화자 구간**을 확보하고, 느린 2차 OBS 관찰 중 동일 65ms 화자 구간을 확보. 음성 길이·실제 모델 출력·OBS 설정·FIFO·동일 발화 strict overlap **운영 코드 변경 없음**. 단위검사에서의 짧은 모의 시간 조정만 포함.
- 위 수정 `main` 안전한 fast-forward 반영 후 **같은 HEAD 전체 회귀 및 Windows EXE/GUI·OBS 실제 읽기·Twitch/치지직/SOOP 읽기·로컬 Ollama CI** 최종 확인 필요. 성공 확인 전 Windows 96절 전체 성공이라 기록하지 않음. 무단 로그인/송출/녹화/모델 학습·다른 저장소/예약/Drive 변경 없음.
