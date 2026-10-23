# AISTING 124회차 신규 실개발 누적 인수인계

## 124. 2026-10-23 — 실제 소켓 반열림 감지·재연결 및 SOOP/Twitch 입장 전 메시지 FIFO 보존 개발

### 시작 기준 / 반드시 유지하는 사용자 지시
- 최신 사용자 지시 `계속`: **AISTING만 현재 main 원본 전체 누적 개발을 먼저 진행**, 완료 이후 전체 회귀·Windows 네이티브 EXE/GUI·OBS·실모델 통합검사, 오류 수정, 전체 재검증 순서. 지시받지 않은 API·방송·녹화·채팅 발신·OAuth 대행·음성 학습·토큰 설정 금지, 다른 프로젝트/Drive/다른 예약/브랜치/force push 금지.
- 시작 실제 GitHub `main` HEAD `3d896678f22485e42a7fc99dc06a344b58f58861` 재조회. 이전 1~123절 `docs/AISTING_HOURLY_FULL_HANDOFF.md`, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 원본 97절 부록과 123절 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 실제 수신·AI/GUI·기억/LLM 코드를 조회했다. 기존 전체 문서 원문/캐릭터/SQLite/설정은 변경하지 않고 이 절만 뒤에 누적한다.

### 실제 신규 개발 내용 및 main 반영 3커밋
1. `e7143812330b40ea105363e9b1a8391d1a47a58e` **main 안전 fast-forward 완료**. 기존 `multiplatform_readonly.py`의 치지직·SOOP WebSocket 읽기 루프에 실제 서버 프레임 도착 `time.monotonic()` 갱신을 추가했다. 채팅이 없는 것과 통신 끊김을 구분해, 무기한 읽기 세션에서만 600초 동안 *실제 소켓 프레임이 단 하나도 안 들어올 때* `transport_stalled` 이벤트 후 `ConnectionError`로 기존 플랫폼별 재연결 관리자에 전달한다. Twitch `twitch_readonly.py`에도 같은 방식으로 실제 IRC PING·서버 이벤트를 포함해 900초 무프레임 시 `TwitchReadError`를 발생시킨다. 사용자 Stop 또는 시간 제한이 있는 기존 짧은 CI 읽기는 원래대로 취급. `multi_platform_session.py`에 플랫폼별 실제 무응답 감지 횟수(메타데이터만), `desktop_chat_tab.py`에 Windows GUI 실제 응답 정지 재연결 횟수를 연결. YouTube는 기존 서버 API 폴링/오류·페이지 이어받기 방식 유지(웹소켓 반열림 감지 적용 없음). 소켓 내용·채팅·토큰 저장/송신 없음. 무프레임 임계시간은 네트워크 무누락 증명이 아니며, 특정 서비스의 매우 조용한 정상 서버에서 늦은 재연결을 만들 가능성을 이후 실제 Windows/플랫폼에서 검증해야 한다.
2. `c615bcc12e8ef6ec3030727a22fb96e3f0a8c675` **main 안전 fast-forward 완료**. `multiplatform_readonly.py`의 기존 실제 SOOP JOIN/연결 승인 흐름에서 연결은 되었어도 실제 0002 JOIN 승인이 아직 없을 때 0005 채팅이 들어오면 해당 채팅을 **원본 순서대로** 메모리 FIFO 보류한다. 실제 JOIN 승인이 확인된 뒤에는 이전 수신 건과 같은 프레임에 실려온 채팅을 순서대로 한 번씩 기존 AI 수신 콜백에 전달한다. 임시 보류 4096건 한도 초과시 조용히 삭제하지 않고 명시적 오류·수신 장애로 보고한다. 전반적인 SOOP 접속/keepalive/중지 안전 경로, 원본 중복 채팅 및 AI 단일 FIFO 계약은 그대로 유지한다.
3. `072449b5c8faf2f9f64946b7d38230768176bbc1` **main 안전 fast-forward 완료**. `twitch_readonly.py`에서 IRC 실제 JOIN 승인 전에 간혹 앞서 도착한 `PRIVMSG`를 즉시 AI에 보내지 않고 최대 4096건 FIFO 보류한다. 채널과 일치하는 JOIN ACK 후 `ready`를 전달하고 해당 보류 채팅들을 정확한 도착 순서대로 `emit("chat")`해 기존 AI 큐의 명시적 수용 여부를 확인한다. 반환값이 정확히 `False`이면 성공 카운트 대신 수신 오류로 보고한다. JOIN 실패/초과는 성공이라고 하지 않는다. 4096건 초과는 명시적 오류이며 원격 Twitch 과거 채팅 복구/무누락 보장은 아니다.
- 세 신규 기능 모두 과거 `main` 확인→자식 커밋 생성→`force:false`, `expected_sha` 확인한 fast-forward 갱신에 성공했다. 브랜치 생성·롤백·기존 파일 전체 교체 없음.

### 옛 CI 기록 확인 및 아직 안 한 일 / 다음 기능
- 기존 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656) 최종 `completed/cancelled` 재확인. 과거 4작업 성공·한국 공개 채팅 1작업 취소, 취소 작업 로그의 404 접근 불가 원문 기록 유지, 전체 성공으로 표시하지 않음.
- 기존 실제 Ollama 500건 CI [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468) 최종 `completed/success` 재확인. **500개의 합성 채팅 처리 전부 3초 초과**, 전체 p95 2,979.984초, 단일 AI FIFO 대기 p95 2,973.875초, 로컬 추론 p95 7.875초. 실제 시청자 수백 명의 플랫폼 메시지 누락 없음을 증명하지 않으며, 시청자 E2E 1~3초 미달.
- 이번 회차 **실제로 한 것**: 새 GitHub main HEAD와 원본 계획/로드맵/1~123절 전체 인수인계/관련 AI·4플랫폼 소스 조사, 실제 24시간 복구에 필요한 반열림 소켓 재연결 기능, Twitch/SOOP JOIN 승인 전 수신 채팅 보류 기능 3건을 기존 코드에 추가, GitHub main 개발 커밋 3건 반영, 이 124절 및 새 부록 누적 기록.
- 이번 회차 **안 한 것**: 전체 기능 개발 완료, 신규 CI, 단위검사/전체 회귀, 실제 Windows 네이티브 EXE·GUI 실행, 실 Twitch/치지직/SOOP/YouTube 방송 채팅 연결·수백 명 부하 실측, 진짜 24시간 구동, 본인 권리 있는 GPT-SoVITS WAV→공식 Live2D Cubism 실제 입→OBS 동일 발화의 실장비 파형 검증, 시청자 E2E 지연 실측, 오류 수정·전체 재검증. 전부 미완료·미검증이며 mock 결과를 실수신 성공으로 둔갑시키지 않는다.
- 남은 기능은 사용자가 지정한 핵심 전체: 실제 4플랫폼 수백건/수백 명 무누락(가능한 서버 이어받기/측정), 실제 24시간 안전 재연결, 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism 립싱크→OBS 동일 음성·영상의 실제 프로그램 경로, AI/음성/영상/시청자 실제 1~3초 지연 병목 코드 개발. 특히 현재 Ollama 로컬 단일 FIFO의 실측 병목 대기는 매우 크므로 **수신 기록만 개발했다고 해결됐다고 보고하지 않는다.** 전체 개발을 마친 이후 사용자가 지정한 순서대로 회귀·Windows 실행·통합검사·수정·전체 재검증 수행.
- 이번 신규 소스 마지막 HEAD `072449b5c8faf2f9f64946b7d38230768176bbc1`이며 이 인수인계 커밋 이후 실제 HEAD는 변경된다. 다음 회차에는 항상 실제 main HEAD부터 재조회하고 원문과 부록을 이어서 사용한다. 사용자 지시 없는 토큰 96/keep_alive 10분을 설정하지 않았고 캐릭터·SQLite·기존 모델/개인 설정 및 다른 예약·프로젝트·Drive를 변경하지 않았다.
