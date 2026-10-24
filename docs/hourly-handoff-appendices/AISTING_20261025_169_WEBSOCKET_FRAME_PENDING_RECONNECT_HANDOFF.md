## 169. 2026-10-25 — 치지직·SOOP WebSocket 프레임 미수용 채팅을 재연결까지 FIFO 보존하는 실제 누적 개발

### 원문·기존 지시·작업 기준
- 사용자 최종 지시: **AISTING만 매시간 실제 기존 코드 누적 개발.** 개발 우선 전체 완성 → 전체 회귀검사/Windows 네이티브 EXE·GUI·OBS·실제 로컬 모델 통합검사 → 오류 수정 → 전체 재검증. mock/합성·실계정·실시청자/24시간 구분. 기존 1~168절 원문 보존.
- 이번 시작 `main` HEAD를 실제 조회: `0bd3ce08ec9aaf05bde300310935a17666b94200`. 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` 전체 1~168절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체, 97절 및 168절 개별 부록, `src/ai_broadcaster/multi_platform_session.py`, `src/ai_broadcaster/multiplatform_readonly.py`, `src/ai_broadcaster/twitch_readonly.py`와 168절 검사 원문을 확인. 전체 원문 통합 문서를 읽었으나 모든 과거 개별 부록 파일을 별도 요청으로 전수 열람한 것은 아님.
- 원본 사용자 금지: 새 브랜치·force push·rollback·전면 재개발, 기존 캐릭터/SQLite/설정/기획·원문 삭제, 다른 프로젝트/Drive/다른 예약 수정·중복 생성, 무단 OAuth/계정 동의·방송·녹화·채팅 발신·모델 학습·권리 없는 음성, 토큰 96/keep_alive 10m 임의 변경 모두 금지. `config/roadmap.json`의 원본 pending 유지.

### 이번 실제 신규 코드 개발
1. `114e60c80c859c74b4268a709cb3d985f7d87c7a`: 기존 `src/ai_broadcaster/multiplatform_readonly.py`의 `ReadOnlySession`에 수신 WebSocket **프레임 전체**를 로컬 AI FIFO 접수 전 메모리 deque에 보관하는 `_queue_received_chats` 및 `_flush_pending_chats` 개발. 콜백이 `False` 반환 또는 예외를 내면 미수용 선두 사건과 프레임 뒤쪽 사건을 제거하지 않으며, 새 연결에서 이전 사건을 먼저 재전달할 수 있게 함. 실제 JOIN 승인 전에는 전달하지 않음. 치지직 JOIN 전 임시 채팅도 승인 뒤 기존 보류 프레임 뒤에 넣고 순서대로 전송. SOOP JOIN 확인 후에만 보류 프레임 전달. 채팅 본문 디스크 저장/외부 발신 없음.
2. `d4eda432d341bf11c05ebf454361d237db776a1e`: 기존 `src/ai_broadcaster/multi_platform_session.py`에서 치지직·SOOP별 `_pending_websocket_chats`를 세션 수명 동안 보존하고, 최초 수신기 및 재연결 수신기에 동일 deque 연결. `reconnect_snapshot()`에 플랫폼별 `수신프레임미수용보류` 건수 추가. 실제 콜백 완료와 보류를 구분하고 기존 ID 중복 차단·단일 AI FIFO·SQLite·설정 보존.
3. `4ec68fefc81ba89f1ba958fb49d4ffe586b5d55c`, `3594315ae2a349ce6f7354bbe7f41b4fb4ab82c4`: 신규 `tests/test_aisting_websocket_pending_169.py`의 가상 계약검사 **10건 작성**. JOIN 전 보류, JOIN 뒤 FIFO, False/예외 시 프레임 꼬리 보존, 새 리더 공유, 전체 프레임 보관, 이전 프레임 우선 처리, Stop 중 미전달, 치지직·SOOP 세션 공유, 진단 보류 건수 확인. 가상 이벤트/소켓만 사용하며 실제 서버·OBS·AI·시청자 검증 아님. 테스트 코드의 가상 상태 알림과 채팅 순서 계측 구분도 반영.
- 총 기존 소스 2개 수정, 신규 검사 소스 1개 작성. 기존 `main` HEAD·blob SHA 확인 뒤 순차 커밋, 새 브랜치/force push/롤백 없음. 기존 캐릭터/SQLite/설정/원본 기획·로드맵 파일 무수정.
- 보장하지 않는 것: 소켓이 끊긴 **이전** 미수신 서버 사건, 프레임 파싱 이전 연결 장애, Twitch/YouTube 전체 무누락, 실제 수백 명, 24시간, 1~3초 응답. 이번 보존은 **이미 파싱한 치지직·SOOP 프레임의 미수용 사건에 한정**. 로컬 메모리 소실/프로세스 종료 시 지속 보존하지 않음.

### 이전 CI 최종 상태 및 실제 실패
- 96절 Windows CI `39722213656`: obs/twitch/windows-exe/ollama 네 작업 성공, korean-public-chat-readonly **취소**. 해당 취소 job 로그 직접 조회는 원격 보관 BlobNotFound 404로 실패. 전체 CI 성공으로 보고 금지.
- 96절 실제 Ollama 500건 `39720448468`: job 성공, 500/500 처리·모델 실패 0이지만 **500/500건 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI p95 **7.875초**. 로그 직접 확인.
- 164절 전체 회귀 `40103031646`: **36 실패·31 오류·2 건너뜀**. 로그에 `_live_queue_wait_tracker` 및 `_update_platform_health` 누락 가상 객체 오류, 일부 가상 YouTube Reader의 `resume_state` 인자 불일치 등이 확인됨. 미수정·전체 회귀 통과 주장 금지.
- 164절 Windows `40103031611`: 공개 한국 채팅/실제 로컬 Ollama/OBS 읽기/트위치 네 작업 성공, Windows EXE **취소**. 전체 성공 아님.
- 164절 Ollama `40102973295`: 500/500 처리·모델 실패 0이지만 **497건 3초 초과**, 전체 p95 **1516.657초**, FIFO 대기 p95 **1513.422초**, AI p95 **3.375초**. 실수백 명/시청자 지연 증명 아님.
- **169회차 신규 가상 검사 직접 실행하지 않음**, 전체 회귀·Windows EXE·GUI·OBS·권리 있는 GPT-SoVITS 실증도 수행하지 않음. 신규 HEAD의 CI 실행 번호/최종 결과는 확인되지 않았음. 실패 은폐 없음.

### 완료 / 안 한 것 / 미완료 / 진행 중 중단 / 다음 회차
- **완료:** 현재 HEAD·기존 원문·기획·로드맵·실제 소스·96/164 CI 조회, WebSocket 프레임 미수용 채팅의 메모리 FIFO 보존 개발, 4플랫폼 조정기 치지직·SOOP 재연결 공유 개발, 10건 가상 계약검사 **작성**, GitHub 기존 main 순차 누적, 169절 전체 인수인계.
- **안 한 것:** 신규 검사 실행/전체 회귀/Windows 네이티브 EXE 빌드·GUI 클릭/OBS 실제 통합검증/실계정 공개 채팅·권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism 입→OBS 동일 발화 PCM·영상 실증/실제 24시간·수백 명·1~3초 달성, 무단 OAuth/방송/녹화/채팅 발신·훈련.
- **남은 것:** 실제 한국어 음성·입·OBS 동일 발화 통합 완성·실증, Twitch/YouTube 등 4플랫폼 고부하 실수신 무누락/중단 중 미수신 사건 처리, 24시간 재연결·안전성, AI/음성/영상/시청자 1~3초 병목 해소, 기존 36 실패·31 오류 수정 및 전체 재검증, Windows EXE/GUI·OBS·로컬 모델 실기기 검증.
- **진행 중 멈춘 것:** 기존 미완료 기능 개발을 지속 중이며, 이번에 이미 파싱한 치지직·SOOP 프레임 보류 코드·가상 검사는 작성 완료; **실행 검증 단계는 사용자 지시 순서에 따라 아직 시작하지 않음**. 운영자 승인과 실제 Windows·OBS·권리 있는 보이스가 필요한 통합 실증은 미완료.
- **다음 시작:** GitHub 현재 `main` HEAD 및 CI 상태부터 다시 확인. 이번 169회차 **코드 커밋 HEAD** `3594315ae2a349ce6f7354bbe7f41b4fb4ab82c4`; 문서 누적 커밋으로 HEAD는 변경되므로 다음 실행에서는 이 SHA를 최신이라고 단정하지 말 것. 전체 원문 1~169절과 모든 기존 지시·금지·실패를 그대로 유지. 다른 프로젝트/Drive/브랜치/예약 변경·중복 예약 금지.
