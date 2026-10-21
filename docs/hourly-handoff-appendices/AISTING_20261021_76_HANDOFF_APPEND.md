## 76. 2026-10-21 — 75절 소스 실제 main 반영·회귀 실패 수정·최신 Windows CI 실증

### 반영된 실제 코드와 원문 보존
- 73~75절 누적 source/test/문서 9개 경로의 최초 코드 커밋 `ce7b4da1fd323a0f17ebdfbad79fbe98495b6093` (부모 `37ae19498f845ec7a0576fd68fc829a30d9a5de0`). 24시간 paced 입력 완료 결과 지속 회수, OBS 임시 ffmpeg_source UUID 재생·정리 직전 확인 및 5개 회귀 테스트를 원본 코드 안에 반영.
- 실제 GitHub `main`에서 전체 회귀 실패를 확인: [39594238437](https://github.com/junggyeol4444/AISTING/actions/runs/39594238437), 2,515개 중 1개 실패, 2개 건너뜀. `test_actual_worker_reports_bounded_live_checkpoints_without_chat_text`가 25·50건 체크포인트를 기대하지만 대량 결과 회수 뒤 집계를 한 번만 호출하면서 checkpoint 2개로 줄어듦. 이 실패를 새 기능 PASS로 바꾸지 않음.
- `scripts/aisting_real_ollama_fifo_soak.py` 처리 완료 이벤트 `twitch_ai_timing`마다 기존 `publish_progress()`를 실행하도록 수정. 25·50건 중간 체크포인트 보존. 수정 커밋 `59057fc1bf8600b1516107c06ee65ed82befe141`.
- 수정한 바로 그 HEAD의 전체 회귀 [39594452116](https://github.com/junggyeol4444/AISTING/actions/runs/39594452116) **성공**: 2,515개 통과, 2개 건너뜀, 실패 0. 신규 5개 계약 검사를 포함. 이 테스트들은 모의 의존성을 포함하며 실제 24시간·송출·음성 모델 실증을 의미하지 않음.

### 최신 Windows 네이티브/실제 연결 결과 (코드 HEAD 59057fc)
- [Windows 통합 실행 39594452083](https://github.com/junggyeol4444/AISTING/actions/runs/39594452083): **전체 workflow FAILURE**, 5개 작업 중 4 success, 1 failure. 반드시 실패 상태 유지.
- `windows-exe` **success**: 네이티브 Windows EXE 실제 빌드·실행 자가점검과 Tk GUI 계약 검사. Artifact `AISTING-Windows-EXE-integrated` ID `12344275721`, 크기 19,981,994바이트, SHA256 `c2837b3552f95834306293610d87ceb8220f25acadb5bdbd635f8eff4bef0d76`; 500/24h 테스트 EXE 별도 artifact ID `12343541482`, 크기 17,910,583바이트, SHA256 `008f0becc6ba73c84c01edd005730fc1833f1a14a3966a065223fe4257324f23`.
- `obs-real-readonly` **success**: 임시 Windows CI의 OBS 실제 장면/프레임 읽기. 이것은 GPT-SoVITS WAV+Cubism 동일 발화 송출 검증이 아님.
- `korean-public-chat-readonly` **success**: 공개 치지직/SOOP 읽기 점검.
- `ollama-real-local-e2e` **success**: Windows Tk GUI 실제 Ollama 한국어 18글자 답변 및 Twitch 공개 시청자 채팅 **실제 1건→기존 단일 AI FIFO 응답 1건** 확인, 별도 합성 4플랫폼 입력 4건의 실제 Ollama 출력 4건 확인. 이 작은 표본의 로컬 p95 **4.64초**, 1~3초 목표 미달이며 실제 4플랫폼 시청자 실증 아님.
- `twitch-public-readonly` **failure**: `ow_esports`, `xqc`, `valorant` 채널 IRC JOIN 3개 모두 성공했지만 실제 공개 `PRIVMSG` **0건**. 테스트는 이를 `No actual viewer chat read`로 실패 처리. 별도 E2E job에서 관찰된 1건과 구별. 시청자가 없었는지/인증 제한인지/다른 외부 원인인지 아직 최종 특정하지 않음.

### 실제 500건·24시간 진행 상태 및 정직한 판정
- 변경 HEAD `59057fc`의 [Windows 실제 Ollama 500건 부하 39594451950](https://github.com/junggyeol4444/AISTING/actions/runs/39594451950)은 본 76절 기록 시점 **in_progress**, 최종 artifact·완주·3초 결과 확인 전. 이전 코드 `ce7b4da1` 실행 [39594238432](https://github.com/junggyeol4444/AISTING/actions/runs/39594238432)도 진행 중으로 기록됨.
- 과거 **완료된** 실모델 synthetic 500건 [39572382928](https://github.com/junggyeol4444/AISTING/actions/runs/39572382928): 500/500 완료, 누락 0, 3초 초과 500/500, 전체 p95 2781.218초, FIFO 대기 2775.281초, AI 6.078초. **1~3초 목표 실패**를 덮어쓰지 않음.
- 실제 권리 있는 GPT-SoVITS 한국어 WAV→공식 Live2D Cubism 입 움직임→OBS 같은 발화 오디오/영상 출력 증거, 4플랫폼 수백 명 실제 실시간 동시 접속·무손실, **실제 24시간 송출/재연결**, 최종 시청자 1~3초는 **미완료·미실증**. 테스트 준비 코드나 synthetic 입력으로 성공을 선언하지 않음.

### 미변경·다음 회차
- 원래 1~75절 원문 전체, 과거 appendix, ORIGINAL_PLAN/ROADMAP_100/config roadmap 및 pending, 캐릭터·성격·말투·SQLite·사용자 설정·OBS 기존 장면은 그대로. 다른 프로젝트·예약·Drive 변경, 새 브랜치, 강제 푸시, 롤백, 임의의 토큰 길이·keep_alive 변경 없음. 방송·녹화·채팅 발신·사용자 계정 로그인·사용권 없는 모델 훈련/합성 없음.
- 다음 회차: 같은 HEAD의 500건 검사 완료 여부와 artifact·누락·속도·24h 지속 구분 확인; Windows Twitch 0건은 외부 미수신과 코드 원인 별도 추적; 1~3초 FIFO/AI/TTS/영상 실제 구간 병목 및 권리 있는 GPT-SoVITS→Cubism→OBS 동일 발화 통합 계속 개발. 핵심 코드 여러 기능 수정 후 전체 회귀 및 Windows 통합 재검증, 실패 수정 후 전체 재검증. 이후 77절 원문 추가.
