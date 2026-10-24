## 167. 2026-10-25 — 실제 수신기 stopped·transport_stalled 즉시 ready 관측 종료 및 최초 공백 보존

### 기준 원문·사용자 지시 및 시작 상태
- 시작 GitHub `junggyeol4444/AISTING` 현재 `main` HEAD를 직접 재조회: `2801b1000872a320d373dc6fe4a205470eb1ad28` (166절 인수인계 이후).
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~166절 전체, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체, `docs/hourly-handoff-appendices/AISTING_20261022_97_NEXT_CHAT_HOURLY_HANDOFF.md`, 166절 개별 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `src/ai_broadcaster/multi_platform_session.py`, `multiplatform_readonly.py`, `twitch_readonly.py`, 166절 검사 소스 및 공식 Cubism/OBS 기존 코드 확인. 모든 과거 개별 부록의 본문을 하나씩 별도 재조회 완료한 것은 아니며, 누적 원문 문서 1~166절은 그대로 보존.
- 기존 사용자 원문 지시 유지: **AISTING 기존 전체 코드 개발을 먼저 누적 완료 → 전체 회귀/Windows 네이티브 EXE·GUI·OBS·로컬 모델 실제 통합검사 → 오류 수정 → 전체 재검증**. 기존 소스/캐릭터/SQLite/설정/기획/인수인계 원문 보존. 다른 프로젝트·Drive·예약 변경 및 중복 예약 생성 금지. 새 브랜치·force push·롤백·전면 재개발 금지. 승인 없는 계정/OAuth·방송·녹화·채팅 발신·모델 훈련·권리 없는 보이스 금지. 사용자 요청 없는 토큰 길이 96 또는 keep_alive 10m 설정 금지. 한국어 코드/문서/로그/보고.

### 이번 회차 실제 기존 소스 누적 개발
1. 기존 `src/ai_broadcaster/multi_platform_session.py` 수정, `main` 커밋 **`65739d56a1c18d1bd38cbee7af5625c822ad9940`**. 4플랫폼 수신기 콜백의 `transport_stalled` (실제 WebSocket 10분/15분 무응답 후 수신기가 발행) 시 즉시 해당 플랫폼 ready 구간과 전체 플랫폼 동시 ready 구간을 종료. 상위 `read_one` 예외 처리와 소켓 정리 지연을 계속 정상 연결로 세지 않도록 개선. 실제 관측 공백의 최초 단조시각을 `setdefault`로 보존해 뒤이은 stopped/예외가 공백 시작시각을 늦추지 않도록 함.
2. 같은 기존 파일의 실제 `stopped` 콜백에서 해당 플랫폼 ready 및 전체 동시 ready 구간을 즉시 종료. 정상 종료·유한 검사에는 실제 연결 장애가 확정되지 않았으므로 재연결 공백을 임의로 생성하지 않음. 중복 stopped에서도 누적 ready가 이중 계산되지 않게 기존 `_end_ready_interval_locked` 경로 재사용. 다른 플랫폼의 ready·AI FIFO·채팅 내용·SQLite·설정·수신기 객체·재연결 루프 변경 없음.
3. 신규 `tests/test_aisting_reader_lifecycle_ready_167.py` 가상 계약검사 **10건 작성**, `main` 커밋 **`042e0f553544c8ea0b2d56b24e6c9473d16031da`**. 실제 stopped의 즉시 종료/중복 무해성, 실제 무응답의 즉시 종료, 무응답 최초 공백 보존, 중복 무응답, 24시간 경계 과대계산 차단, 나머지 3개 채널 독립 ready, 정상 stopped의 공백 미생성, 채팅 발신 없는 상태 처리, 운영자 Stop 이후 시간 고정 검증. 테스트 값은 가상 단조시계·가상 수신기이며 실플랫폼/실24시간/실방송 증거가 아님.
4. 시작 HEAD 대비 GitHub 비교 `ahead_by=2`, `behind_by=0`, `status=ahead` 직접 확인. 기존 소스 1개 **+17줄/삭제 0**, 신규 검사 파일 **+145줄**. `main`에만 GitHub Contents API로 안전한 누적 커밋; 브랜치 생성/강제 갱신/롤백 없음.

### CI 최종 상태·실패 원문과 실제 검증 범위
- 96절 Windows CI `39722213656`: OBS 읽기·Twitch 공개 읽기·Windows EXE·실 Ollama 로컬 job **성공**, 한국 공개 채팅 읽기 job **취소**. 전체 성공 아님. 취소 job 로그 다운로드 404 BlobNotFound로 실패, 취소 원인은 확정 불가.
- 96절 실제 Ollama 500건 `39720448468`: job success, **500/500건 처리·실패 0·500/500건 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI 처리 p95 **7.875초**. GitHub 원격 로그 재확인.
- 164절 전체 회귀 `40103031646`: job failure, 원격 로그 **36 failures, 31 errors, 2 skipped**. 대표 과거 테스트 `transport_activity` 추가와 예상 목록 불일치, `twitch_ai_error` 대 `twitch_ai_ok`, AI FIFO 응답 누락·기대 수량 차이 등. 이 회차는 개발 단계이므로 오류 수정 및 전체 재검증 완료로 주장 금지.
- 164절 Windows `40103031611`: 공개 한국 채팅·Ollama·OBS·Twitch job 성공, Windows EXE job **취소**. 전체 성공 아님.
- 164절 실제 Ollama 500건 `40102973295`: job success, 500/500 처리·실패 0, **497건 3초 초과**, 전체 p95 **1516.657초**, FIFO 대기 p95 **1513.422초**, AI p95 **3.375초**, FIFO 접수 지연 p95 **0초**. 실수백 명 시청자 증거가 아닌 합성 채팅 부하.
- 본 167절 코드 HEAD의 GitHub commit combined statuses 조회는 빈 목록. 따라서 **167절 신규 계약검사 10건을 실행하지 않았고, CI 실행 번호·성공·실패를 확보하지 못함**. 165·166절 신규 CI 최종 상태도 이 회차에 확보하지 못함. 실제 Windows 네이티브 EXE·GUI·실 OBS·공식 Live2D·권리 있는 GPT-SoVITS 음성·24시간·실계정 시청자 통합 실행은 수행하지 않음.

### 실제로 하지 않은 것, 미완료, 진행 중 중단, 다음 시작
- 이번에 한 것: 실제 GitHub main/기획/로드맵/누적 원문 및 96·164절 CI 확인, 기존 소스 1개 기능 개발 및 10건 신규 가상 계약검사 작성, main 2커밋, 167절 원문 인수인계 추가.
- 이번에 안 한 것: 신규 검사 실행, 전체 회귀/Windows EXE·GUI 통합검사, 실제 권리 확인 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 실제 입 움직임→OBS 동일 발화 오디오/영상 실증, 실제 4플랫폼 수백 명·수백 건 무누락, 실제 24시간 무중단·재연결, 시청자 응답 1~3초 달성, 외부 계정/OAuth·방송·녹화·채팅 발신·모델 훈련. mock를 실제 사용으로 보고하지 않음.
- 남은 것: 위 모든 미완료 실제 통합 기능과 검증, 기존 전체 회귀 **36 실패·31 오류** 원인별 해결 및 전체 재검증, Windows 네이티브 EXE·GUI·OBS·로컬 모델 실제 검증, 1~3초 병목 해결. 특히 실제 Ollama FIFO 대기 p95가 1513초 이상인 현 상태에서 목표 달성이라고 보고 금지.
- 진행 중 멈춘 것: 수신기 stopped·무응답 구간 경계의 코드 작성/테스트 소스 작성까지만 완료. 실제 24시간 재연결 실증과 167절 검사 실행 미착수. 기능 개발 우선 원칙에 따라 다음 회차에서 나머지 기존 기능을 계속 개발하고, 전체 개발 완료 후 사용자 지정 검사→수정→전체 재검증.
- 다음 시작 시 **최신 `main` HEAD를 반드시 다시 조회**하고 CI 결과를 확인할 것. 167절 코드 HEAD `042e0f553544c8ea0b2d56b24e6c9473d16031da`; 인수인계 문서 커밋 후 HEAD 변경되므로 다음 회차는 이 값을 최신이라고 전제하지 말 것. 기존 예약은 변경하거나 중복 생성하지 않았고 다른 프로젝트도 건드리지 않았음.
