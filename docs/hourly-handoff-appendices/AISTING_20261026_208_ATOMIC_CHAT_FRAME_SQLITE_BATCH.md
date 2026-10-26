# AISTING 208절 — 2026-10-26, 4플랫폼 채팅 프레임 SQLite 원자적 묶음 수신 개발

## 작업 기준
- 시작 직전 확인한 기존 `main` HEAD: `8c57aaaa15f0c9074d8144d226043ba0d4fd4162`. 이 SHA를 미래 최신으로 단정하지 않는다.
- 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 207절 부록과 기존 `durable_public_chat_queue.py`, `desktop_chat_tab.py`, `multi_platform_session.py`, `multiplatform_readonly.py`, `twitch_readonly.py` 원본 확인.
- 전체 인수인계 원문 두 개는 GitHub Contents API에서 내용이 빈 것으로 반환되어 기존 Git blob 원문으로 별도 조회. 원문 1글자도 삭제하지 않고 append-only 유지.
- 기존 캐릭터·말투·96토큰·keep_alive 10m·설정·채팅 SQLite·100단계 원본 보존, 신규 브랜치/강제 push/rollback/외부 서비스 실제 연결 없음.

## 이번 회차 개발한 제품 소스 — GitHub main 정상 누적 커밋
1. `ccf35bd5f0ab9df670d021fd15fab396cfe9ad3a` — `durable_public_chat_queue.py`: `append_batch`로 1~256건을 단일 SQLite 트랜잭션에 확정. 도중 DB/보호한도 오류 발생 시 전량 롤백. 서버가 실제 제공한 동일 ID의 중복만 차단하며 서로 다른 메시지/ID 없는 채팅은 그대로 저장. COMMIT 성공 뒤에만 잔여 건수·시각·FIFO 상태 업데이트.
2. `bacbdb93c566a8ef2bd51dd2126f7a4fa2b6e85f` — `multiplatform_readonly.py`: 치지직·SOOP 인증/방 입장 확인 후 같은 수신 프레임 채팅을 배치 전달. 실패한 프레임은 공유 미처리 deque 보존.
3. `255b5a65799b4bc038a04707b81588540277dc72` — `twitch_readonly.py`: 트위치 IRC JOIN 후 채팅을 256건씩 묶어 수용. 원본 단건 콜백은 유지.
4. `1bd84617eb01f89daa160da0fdeea821ea18dacd` — `multi_platform_session.py`: 명시적인 실제 SQLite GUI 수신에서만 배치 모드 켜고 재연결 대체 수신기에도 적용. 원래 채널별 콜백/재연결 계수와 파싱→접수 메트릭 유지.
5. `c653f2626e24dfb173dfdeb11d1d5cdf4da76015` — `desktop_chat_tab.py`: 4플랫폼 중 트위치·치지직·SOOP의 프레임 묶음을 기존 SQLite에 먼저 확정, 기존 복구 작업자가 전역 sequence 순서로 AI FIFO에 등록. SQLite가 실패하면 접수 성공으로 처리하지 않음.
6. `380177d6ce5a0814fe9e4ff8f52187ed32a36c5f`, `65efaa9814675e30d3d9b42b4c6228a51ef9940f` — 2개 소켓 수신기에서 대기열 전체 복사를 없애고 정확히 256건까지만 추출.

## 완료와 미완료
- **이번 회차 제품 소스 코드 개발 및 main 반영: 완료. AISTING 전체 제품 개발: 미완료.**
- 유튜브의 기존 페이지 커서 영구 수신은 수정하지 않았다. 기존 SQLite 미처리 20만 건 한도 유지; 무제한 적체/수백 명·24시간·1~3초 실효 입증하지 않음. 서버 네트워크 공백 중 애초에 놓친 채팅을 복원할 수 있다는 주장 금지.
- **테스트 NOT_RUN, 전체 통합 회귀 NOT_RUN, CI 미조회·미확인, Windows 10/11 EXE·GUI NOT_RUN, 실제 GPT-SoVITS·공식 Live2D Cubism·OBS·4플랫폼 실계정·수백 명·24시간·시청자 최종 1~3초 NOT_RUN.**
- 과거 실모델 CI `39720448468`: 500/500건 모두 3초 초과, FIFO p95 2973.875초 / 전체 p95 2979.984초 실패. Windows CI `39722213656` 취소. 기록 훼손 금지.

## 다음 시간 개발
- 실행 때 최신 `main` HEAD와 본 절 이후 인수인계를 확인하고 미완료 핵심 기능 실제 소스 개발부터 계속.
- 우선 원본 기획의 4플랫폼 수백 명 채팅 내구 보존·재연결, 로컬 AI 선행 추론/FIFO/백프레셔 및 1~3초 병목, 권리 한국어 GPT-SoVITS WAV→공식 Live2D 입→OBS 동일 발화·24시간 장애 복구, 자율 게임·콘텐츠 장기 수행. 개발 전체 완료 뒤에만 통합 Windows/실방송 검증→오류 일괄 수정→재검증.
- 기존 AISTING 대화 유지 우선, 새 예약이나 새 브랜치 만들지 않음. 사용자 승인 없는 실제 방송·채팅·공지 발신·OAuth·음성 학습 금지.
