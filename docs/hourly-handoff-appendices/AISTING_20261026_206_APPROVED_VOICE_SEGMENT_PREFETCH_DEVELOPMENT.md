# AISTING 206절 — 2026-10-26 08시대 승인형 한국어 실제 WAV 다음 구간 선행 합성 개발

## 기준·원본
- 시작 시 실제 GitHub main HEAD: `769aa2a7bd8e56a7d917f918cd3f00d004cfd879` (205절 인수인계).
- 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `approved_live_voice_output.py`, `approved_live_voice_outbox.py`, `approved_live_voice_playback_watch.py`, `approved_live_voice_causal_journal.py`, `ordered_parallel_local_ai.py`, `desktop_chat_tab.py`, `durable_public_chat_queue.py`, `multi_platform_session.py` 등 관련 원본을 조회했다.
- 기존 전체 인수인계 2개는 GitHub Contents API가 빈 본문을 반환하여 각 blob SHA로 원문을 조회했다. 97·185·187~190·192~195·205절 등 확인한 부록은 조회했으며, 과거 모든 부록을 전수 열람했다고 주장하지 않는다.
- 기존 대화 유지 최우선. 예약 중복 생성·변경/다른 저장소·Drive·브랜치 조작 없음. 기존 원본/사용자 SQLite/캐릭터/말투/96토큰/keep_alive 10m 보존.

## 실제 제품 소스 개발 및 기존 main 커밋
1. `26b3f69f9e32bbc8a4915db11edd0eff70f77fe8` — 신규 `src/ai_broadcaster/approved_live_voice_prefetch.py`. 동일 방송의 다음 한국어 WAV 구간 **한 건만** 기존 승인된 GPT-SoVITS 모델로 선행 합성하는 단일 작업자 구현. 현재 방송 구간의 재생 경로에서만 다음 작업을 시작, FIFO 텍스트 순서 검사, 사용자 중지·작업 종료 시 미래 WAV를 재생하지 않음. 음성/OBS/계정 자체 발신 기능 없음.
2. `a03478e8182e2cee88b192c1e80ccc9a0b23bb5c` — 기존 `src/ai_broadcaster/approved_live_voice_output.py` 수정. Windows DPAPI·SQLite 영구 음성 대기 FIFO와 기존 직접 FIFO 양쪽에 한 구간 선행 합성 연결. 첫 WAV는 원래 OBS 송출·공식 Cubism 확인 후 동기 합성하고, 현재 WAV가 공식 Cubism·OBS 음성 입력에 연결된 뒤 다음 구간 합성을 병행. **실제 출력은 원래 순서대로** 진행. 기존 8초 초과 WAV 재분절, OBS 스트림 Lease, 재생 중 감시, 동일 WAV 인과 기록, 발화 실패 시 불명·중단 처리 및 자동 재전송 금지 보존.
- 실제 제품 소스 커밋 2개 / 신규 Python 1개 / 기존 Python 수정 1개. 개발 소스는 문서보다 먼저 기존 `main`에 정상 반영.
- 선행 합성은 **구간 사이 합성 대기 감소 가능성을 위한 코드**이며, 실제 모델 처리량·시청자 응답 1~3초 달성이나 24시간 방송 안정성을 증명하지 않는다. 백그라운드 합성은 이미 시작된 HTTP 호출을 즉시 강제 종료하지 못하며, 완료되더라도 중지 이후 재생하지 않는다.

## 검증 및 미완료
- **개발 소스 반영 완료 / 전체 AISTING 개발 미완료**.
- **테스트 NOT_RUN / 통합 회귀 NOT_RUN / CI 미조회·미확인 / Windows 10·11 네이티브 EXE·GUI NOT_RUN / 실제 권리 한국어 GPT-SoVITS·공식 Live2D Cubism·OBS·4플랫폼·수백 명·24시간·시청자 1~3초 NOT_RUN**.
- 기존 실모델 CI `39720448468` 500/500 모두 3초 초과, FIFO p95 2973.875초·전체 p95 2979.984초 실패 및 Windows CI `39722213656` 취소 기록 유지.
- 남은 원래 핵심: 4플랫폼 대규모 채팅 SQLite 전량 내구·재연결, 로컬 AI 추론·음성·화면 최종 1~3초 병목, 실제 동일 WAV/Cubism/OBS 장시간 인과·동기 및 24시간 장애 복구, 자율 게임·콘텐츠 장기 수행, 원본 100단계 미완 기능. **모든 개발 완료 후** 통합 Windows/실계정/OBS/Live2D 검증 → 발견 오류 일괄 수정 → 전체 재검증.
- 다음 회차에는 반드시 최신 `main` HEAD를 다시 조회하고 이전 부록과 기존 원본을 보존한 채 **실질 제품 소스 개발부터** 이어간다. 원래 AISTING 대화 유지 우선, 새 대화 생성 요구 금지.
