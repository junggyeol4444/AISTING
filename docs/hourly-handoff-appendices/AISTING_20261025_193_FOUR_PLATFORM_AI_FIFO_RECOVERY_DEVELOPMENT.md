# AISTING 193절 — 2026-10-25 · 4플랫폼 실제 AI FIFO 실패 복구·영구 사건 장부 개발

## 사용자 최우선 지시
- **이 AISTING 대화를 계속 사용하고 기존 매시간 예약 유지.** 다른 프로젝트·예약·대화·브랜치 변경 없음.
- 대상: GitHub `junggyeol4444/AISTING` 기존 `main`. 이 회차 시작 실제 HEAD `8a04a2029d9a1fdf30b1cdbcd4d0ba52c581ba61` (192절).
- 기존 저장소 원본·설정·모든 캐릭터/성격/말투·기획·SQLite 대화·과거 인수인계 전부 유지. 사용자 허가 없는 OAuth/실송출/채팅/공지/녹화/모델 훈련/타 프로젝트·Drive 접근 없음.
- **개발 전부 완료 → 전체 회귀 및 Windows 10/11 실제 EXE/GUI·실계정/실장비 통합 검증 → 오류 일괄 수정 → 전체 재검증**. 이번 회차는 소스 개발만 수행. 수동 단위/통합/Windows 검사 **NOT_RUN**; 자동 CI는 아래에 별도로 기록.

## 기존 코드 확인
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` 및 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체 내용을 GitHub에서 조회. 191·192절 부록 원문도 조회.
- 기존 `src/ai_broadcaster/desktop_chat_tab.py`의 실제 4플랫폼 큐, `multi_platform_session.py`의 수신/재연결, `durable_public_chat_queue.py`의 원자적 미처리 보존 및 서버 ID 확인, `local_llm.py`와 `desktop_chat.py`의 기존 Ollama 순차 FIFO/기억 저장 코드를 필요한 구간에서 검토. 저장소 내 모든 파일 및 과거 부록 전체를 열람했다고는 주장하지 않음.
- 원본 100단계 `config/roadmap.json`의 completed/pending 및 사용자 최종 승인은 임의 변경하지 않음.

## 이번 실제 기존 main 소스 개발 — 기능 설명
1. **동일 메시지 로컬 AI 복구:** 신규 `src/ai_broadcaster/live_ai_recovery.py`. 기존 Ollama API `LocalModelError`(연결 실패/응답 오류)만 세션별 최대 6회 제한적 재시도. 실제 실패 뒤 0.5→1→2→4→8초 대기, 사용자 Stop 이벤트가 먼저 오면 즉시 중단. 최초 성공에는 대기 없음. 사용자가 고른 모델·96 토큰·keep_alive·동일 캐릭터·대화 기억 설정 일절 변경하지 않음. 메시지별 추론이 완료된 뒤에만 기존 ChatPipeline이 기억/응답을 확정함. 공식 원본 GPT-SoVITS/WebSocket에는 중복 음성 위험 때문에 적용하지 않음.
2. **4플랫폼 FIFO 실제 재시도 연결:** 기존 `desktop_chat_tab.py`의 `_work_twitch_ai` 순차 AI 작업자에 재시도 도입. 전체 응답 및 선택적 Ollama 텍스트 스트림 미리보기 양쪽 경로 지원. 실패한 채팅을 처리하기 전에는 후속 채팅 처리로 앞지르지 않음. 부분 텍스트 미리보기는 확정 응답이나 방송 발신으로 기록하지 않음. GUI에 각 플랫폼의 실패 횟수와 다음 대기 시간 표시.
3. **확정 불가 시 SQLite 보존/전체 수신 중단:** 실제 4플랫폼 세션에서 로컬 AI 재시도가 끝까지 실패하거나 공식 Live2D의 실제 전달이 불확실할 경우 해당 `pending_sequence`를 ACK하지 않고 보존하며, 후속 채팅으로 넘어가기 전에 현재 수신 세션 Stop. 공식 WebSocket은 전달됐는지 모를 수 있어 자동 재전송하지 않음. 기존 커밋 데이터, 사용자 설정, 기존 페르소나/메모리는 불변. 이것이 장애 후 완전 자동 복구나 정확히 1회 외부 발신 증거는 아님.
4. **AI 확정 실패 append-only 영구 사건 장부:** 기존 `durable_public_chat_queue.py`에 원본 기존 테이블/행을 유지하며 `public_chat_processing_incidents(sequence, incident_kind, recorded_at)` 전용 테이블 추가. 유일 `(sequence,incident_kind)` 키, 실제 해당 pending 시퀀스 존재 때만 서버 송신 상태 불명/로컬 확정 실패 기록; 메시지·닉네임·계정·토큰/로그 없음. 같은 사건을 재시작 후 무한 중복 기록하지 않음. `recent_processing_incidents` 조회 API 제공.
5. **실제 GUI와 복구 안내 결합:** 기존 `desktop_chat_tab.py`의 새 연결 전 영구 기록 상위 25건 읽기, 실제 AI 실패 재시도/최종 FIFO 중단/장부 기록 실패 표시. 원래 SQLite 미처리 보존 여부와 실제 발화가 불명확함을 분리 표시.

## 실제 소스 커밋 (기존 main 직접 정상 커밋)
- `446b94de98d9b7caff6e3d878e08d7820978a7d3` — 실제 FIFO 재시도 모듈 신설.
- `4ba78200e4b3f01c1311c3cbc67b04d57ed9388e` — 기존 4플랫폼 AI/GPT-SoVITS GUI 경로 결합.
- `d12e29718a29f249b714ed09812ac2f96c5c5cc6` — 기존 공개 채팅 SQLite 영구 실패 사건 장부.
- `4e518155ac2c1e3f492d27688ed2fb966a70c977` — 실제 FIFO 영구 실패 사건 작성 및 GUI 안내.
- 마지막 실제 개발 코드 HEAD `4e518155ac2c1e3f492d27688ed2fb966a70c977`; 본 부록 및 누적 문서 커밋 후 최종 main HEAD 다시 확인할 것.

## 완료·미완료·진행 중 구분
- **이번 회차 코드 개발 완료:** 제한적 실제 로컬 Ollama 재시도, 후속 채팅 순서 역전 차단, 공식 세션의 중복 발신 거절, 사용자 Stop, 기존 SQLite 미완료 본문 보존, 실패 시퀀스 영구 사건 기록과 GUI 운영자 안내. **전체 제품 개발 완료 아님.**
- **여전히 미완료:** 수백 명 실제 4플랫폼 서버 전체 이벤트 무누락, Ollama 전체 FIFO 500건 실모델 지연 p95 문제, 시청자 최종 1~3초, 한국어 권리 GPT-SoVITS WAV→공식 Cubism 실제 입→OBS 동시 음성/영상 인과관계 및 실제 시청자 수신, 장기간 24시간 무인 운용 자율 복구, 자율 게임 플레이, 네이버 카페 실제 게시 등.
- **검증 상태:** 이번 실행 수동 단위/전체 통합/Windows 10/11 네이티브 EXE·GUI, 실제 수백 명·24시간·시청자 지연: NOT_RUN / 미실증. 과거 실제 500건 모델 CI `39720448468` 500/500 모두 3초 초과, FIFO p95 2973.875초 / 전체 p95 2979.984초 실패, 이전 Windows CI `39722213656` cancelled와 원래 회귀 실패를 그대로 보존. GitHub 자동 실행 상태는 확인한 것만 별도 기록.
- **다음 회차:** 이 대화와 기존 매시간 예약/기존 main 유지. HEAD 새로 확인 → 미완료 실제 기능 **추가 코딩**. 모든 코드 개발 완료 전 테스트·오류 수정만 반복 금지. 사용자 승인 없는 방송·계정/OAuth 사용 금지.

