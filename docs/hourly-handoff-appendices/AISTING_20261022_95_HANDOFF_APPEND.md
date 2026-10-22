## 95. 2026-10-22 — 같은 발화 시간 경계 0초 접촉 오판 방지

### 사용자 원문과 진행 기준
- 대상은 `junggyeol4444/AISTING` 저장소 기존 `main`만. 시작 HEAD `48df5509fbcac2501960322fddc917c9e80f0540`. `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 및 `docs/AISTING_HOURLY_FULL_HANDOFF.md`의 **1~94절 원문 전부**, 모든 `docs/hourly-handoff-appendices` 과거 원문, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 모든 코드·캐릭터·SQLite·사용자 설정을 보존하고 본 절만 뒤에 추가. 로드맵 pending 상태 유지.
- 새 브랜치·강제 푸시·롤백·재개발·다른 프로젝트·예약·Drive·사용자 계정/OAuth 변경 금지. 사용자 승인 없는 로그인/OBS 방송·녹화/채팅 송신/모델 학습/사용권 없는 음성 합성 금지. 원래 답변 토큰 길이, 기억/캐릭터, 모델 옵션 임의 변경(`num_predict=96`, `keep_alive=10m` 강제 등) 금지. 실제 모델/방송/시청자 실증과 모의 성공을 구분.

### 94절 최종 실제 검증 및 91~94절 Ollama 병목 증거
- 원본 HEAD `48df5509` [94절 전체 CI 39710567250](https://github.com/junggyeol4444/AISTING/actions/runs/39710567250) **success**, [94절 Windows EXE/GUI·OBS 실읽기·Twitch·치지직/SOOP 공개읽기·실제 로컬 Ollama 39710567262](https://github.com/junggyeol4444/AISTING/actions/runs/39710567262) **success**.
- [94절 실제 Ollama 500건 Windows 부하검사 39710567307](https://github.com/junggyeol4444/AISTING/actions/runs/39710567307) **500/500 처리, 누락/모델 오류 0**, 전체 응답 p95 **2767.640초**, FIFO 대기 p95 **2762.187초**, 모델 처리 p95 **7.391초**, 3초 초과 **500/500**. 서버 단계별 실측 p95(각 500건): 모델 로딩 **0.118673초**, 입력 평가 **6.591132초**, 답변 생성 **0.509012초**, 서버 내부 합계 **7.216993초**. **최종 1~3초 목표 실패**. CI workflow success는 수집/완료 성공이며 시청자 500명·실제 송출/실시간 성능 성공 아님.
- [91절 실모델 39702241916](https://github.com/junggyeol4444/AISTING/actions/runs/39702241916) 전체 p95 **3499.515초**·FIFO **3492.297초**·AI **9.5초** (500/500, 499/500 3초 초과).
- [92절 실모델 39704987503](https://github.com/junggyeol4444/AISTING/actions/runs/39704987503) 전체 p95 **3459.109초**·FIFO **3451.969초**·AI **9.219초** (500/500, 500/500 3초 초과).
- [93절 실모델 39706777993](https://github.com/junggyeol4444/AISTING/actions/runs/39706777993) 전체 p95 **3390.562초**·FIFO **3383.765초**·AI **9.0초** (500/500, 500/500 3초 초과).
- 변경 내역 없는 CI/모의 메시지 처리는 실제 4플랫폼 시청자 수백 명/24시간 검증과 다름. 동일한 단일 FIFO에서 모델 실제 입력 평가만 수 초 걸리므로 사용자 요구 1~3초를 이미 달성했다고 주장하지 않음.

### 이번 회차 소스 실제 개발
- `src/ai_broadcaster/original_plan_full_pipeline.py`: 실제 승인 받은 공식 AI→Cubism 실제 입/RMS→OBS 선택 입력 미터 동시 관측에서, 기존의 겹침 조건 `first <= mouth_last and last >= mouth_first`를 **양방향 strict overlap** `first < mouth_last and last > mouth_first`로 보강. 오디오 끝시각과 입 시작시각이 같은 순간, 또는 입 끝시각과 오디오 시작시각이 같은 순간 등 **겹친 지속시간이 0초**인 서로 다른 발화를 같은 발화 후보로 오판하지 않음. 기존 현재 질문 요청 구간 경계, OBS 방송/녹화/장면 변화 거부, 운영자 승인·음성 사용 권리 게이트, 질문 1회 전송 정책·실측/미측정 지표 그대로 유지.
- `tests/test_aisting_official_chat_obs_pipeline.py`: 모의 OBS 정확 오디오 미터 구간과 모의 Cubism RMS/입 구간을 동기화한 **경계점 접촉 두 사례**를 한 테스트의 두 subTest로 추가, 관측 증거가 false·시청자 E2E false인지 확인. 네이티브 음성 실제 재생이나 방송을 실행한 테스트가 아니므로 실증 주장 없음.

### 검증·미완료·다음 회차
- 변경 코드를 안전한 GitHub `main` fast-forward로 반영하고, **같은 수정 HEAD** 전체 저장소 회귀/Windows EXE·GUI/OBS 실읽기/실제 로컬 Ollama/4플랫폼 읽기 CI 결과를 확인. 실패 시 소스·테스트 수정 후 전체 재검증하고 결과 원문 추가. 진행 중인 CI는 성공으로 쓰지 않음.
- 실제 권리 있는 한국어 GPT-SoVITS WAV→공식 Cubism 입 움직임→OBS 동일 발화 오디오·영상 실증, 실제 4플랫폼 수백 명 채팅 무누락 및 24시간 방송 재연결, 최종 시청자 응답 **1~3초 달성**은 계속 **미완료**. 메모리·캐릭터·기존 사용자 설정·SQLite·원본 100단계 pending 및 다른 프로젝트/예약/Drive 미변경.
- 다음 **96절**은 이번 수정 CI 실패/성공 결과와 실제 Ollama 프롬프트 처리·대기열 병목을 이어받고, 같은 기존 모델·사용자 설정 안에서 GPT-SoVITS→Cubism→OBS 실제 흐름의 남은 기능/검증을 소스부터 개발·검사·수정한다.
