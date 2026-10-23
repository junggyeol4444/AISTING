# AISTING 127회차 개발 우선 누적 인수인계

## 127. 2026-10-23 — 로컬 Ollama 실제 NDJSON 응답 스트리밍·Windows 조기 미리보기와 Stop 후 출력/기억 차단 기능 개발

### 현재 사용자 요구와 시작 HEAD
- 최신 사용자 지시는 `계속`; **AISTING만, 기존 전체 소스의 미완료 기능을 먼저 누적 개발하고, 개발이 완료된 후 전체 회귀·Windows 네이티브 EXE/GUI·OBS/실제 모델 통합검사 → 오류 수정 → 전체 재검증**을 수행한다. 매번 현재 `main` HEAD를 새로 확인하고 과거 1~126절, 모든 과거 `docs/hourly-handoff-appendices/*` 원문, 캐릭터·SQLite·설정·기획/로드맵을 보존한다.
- 시작 실제 `main` HEAD `d631564184c223a5cbe3d5669ebc5fa8e36c1a1a` 재조회. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~126절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 원문 97절 및 126절 부록, `local_llm.py`, `chat_pipeline.py`, `desktop_chat.py`, `desktop_chat_tab.py`, `conversation_memory.py`와 4플랫폼 관련 실제 소스를 확인했다.
- 기존 Windows CI `39722213656`: `completed/cancelled`. 과거 성공한 부분 작업은 존재하지만 workflow 전체 성공이 아니며 과거 미완료·실패/접근 불가 로그는 기존 절에 원문 보존. 기존 실제 Ollama 500건 CI `39720448468`: workflow `completed/success`이지만 실제로는 **합성 채팅 이벤트 500/500건 전부 3초 초과**. 기존 전체 p95 `2979.984초`, 단일 FIFO 대기 p95 `2973.875초`, 추론 처리 p95 `7.875초`. 실제 500명·24시간 운영·1~3초 시청자 E2E 성공이 아님.

### 이번 회차 실제 신규 소스 개발 1 — 운영자 선택형 Ollama 토큰 스트리밍
- 코드 개발 커밋 `4920cb37ae1c34c96abaed3f4eca2b4b1a151bd2`을 현재 main에서 `expected_sha` 확인하고 `force=false` 안전 fast-forward 갱신 성공.
- `src/ai_broadcaster/local_llm.py`에 기존 `LocalOllamaReplyGenerator.generate()` 경로와 별개의 `generate_stream(message,on_chunk)`를 추가. 운영자가 스트리밍 미리보기를 선택한 경우에만 원래 사용자 선택 모델과 기존 `127.0.0.1` Ollama `/api/chat`, 동일 캐릭터 프롬프트·기존 SQLite 최근 맥락과 기존 `max_reply_chars`를 유지하며 `stream:true` NDJSON 응답을 읽는다. 서버 에러·비정상 JSON·빈 응답·최종 `done:true` 누락·1MB 제한 초과·최대 답변 글자 제한 위반의 경우 중간 생성물을 완료 답변으로 사용하지 않는다. 사용자 미승인 `num_predict=96`, `keep_alive=10m` 등 Ollama 추가 옵션을 넣지 않았다.
- `src/ai_broadcaster/chat_pipeline.py`에는 기존 `process_next()` 기본 경로를 바꾸지 않고 선택 시에만 `on_stream_chunk` 콜백을 전달하는 경로 추가. `src/ai_broadcaster/desktop_chat.py`의 `LocalChatRunner.reply(...on_stream_chunk=...)`는 기존 SessionController/FIFO/실제 ChatPipeline의 최종 응답 전달·SQLite `on_delivered()` 시점을 유지한다. **미완성 중간 조각은 사용자 대화 기억/OBS/TTS/외부 플랫폼 채팅 발신으로 전달하지 않는다.**
- `src/ai_broadcaster/desktop_chat_tab.py`의 실제 Windows tkinter에 `로컬 Ollama 생성 중 답변 미리보기` 체크박스(기본 **꺼짐**) 추가. 운영자가 선택한 **로컬 Ollama 채팅 수신 세션에서만** 같은 단일 AI FIFO 워커가 네트워크 NDJSON 청크를 수신하고 0.35초 이상 간격으로 현재까지 첫 160자 이내 및 총 생성 글자 수를 임시 GUI 상태에 표시한다. 완료 후에는 기존 완성 답변 처리/음성 조건/SQLite 기억 표시를 그대로 수행하고, 새로운 채팅·별도 모델/백그라운드 송신 작업을 만들지 않는다. 다른 4플랫폼의 메시지 원본·도착 순서나 사용자 설정 파일에 체크박스 상태를 임의 저장하지 않는다.
- 이 기능의 성과는 **실제 서버 생성 중간 텍스트가 완성 전에 화면에 보일 수 있다는 점**이며, 전체 추론 시간이 감소하거나 실제 음성/OBS·시청자 전달 1~3초를 달성했다고 주장하지 않는다. 모델이 첫 조각을 늦게 보내거나 아예 스트리밍을 지원하지 않으면 기존 실행보다 빨라졌다고 할 수 없다.

### 이번 회차 실제 신규 소스 개발 2 — Stop 중 미확정 답변 및 기억 저장 차단
- 후속 코드 개발 커밋 `af4222282df08c755dcb0b6414f43dc25e0eb7ff`을 첫 개발 커밋의 자식으로 `expected_sha` 확인, `force=false` 안전 fast-forward 반영 성공.
- `local_llm.py`의 신규 스트리밍은 `should_cancel` 선택 콜백을 요청 시작 전, 실제 서버 NDJSON 프레임을 읽기 전/읽은 직후, `done:true` 이후 최종 확정 전에 확인하여 운영자 Stop 시 수신된 미완성 토큰을 표시·확정하지 않고 예외로 종료한다. 네트워크 응답이 전혀 오지 않는 경우에는 기존 Ollama 연결 읽기 제한시간이 남아 있을 수 있으므로 즉시 소켓 I/O가 강제 종료됨을 보장하지 않는다.
- `chat_pipeline.py`에서 선택 취소 신호가 들어오면, 최종 응답 생성이 끝났더라도 **실제 텍스트 출력·FIFO 승인(ack) 및 SQLite 기억 저장 직전에** 차단하는 경로 추가. `desktop_chat.py`는 선택적 `should_cancel` 인자를 기존 처리 파이프에 전달한다. `desktop_chat_tab.py` 실제 운영자 라이브 세션은 **세션 Stop 이벤트**를 선택적 스트리밍과 기존 비스트리밍 로컬 Ollama 둘 다에 전달한다. 중지된 세션의 늦은 결과는 기존 scoped GUI 경로에서도 제외되도록 유지. 사용자 Stop 이전 실제 완료된 응답·기억을 사후 삭제하지 않으며 실행 중단 직전의 경쟁 상태·네트워크 응답 누락은 향후 전수검증에서 별도 확인한다.
- 기존 전역 SQLite 스키마/인물 프로필, 설정·기획, 원래 단일 AI FIFO 순서, 최종 응답 길이, 기존 AI 작업 등록/복구/실시간 채팅 수신 경로, 방송·OBS 실제 출력 상태는 변경하지 않았다.

### 실제 수행 / 하지 않은 작업 / 남은 개발
- **한 것**: 실제 AISTING main HEAD·기획·과거 인수인계·두 기존 CI 최종 상태 및 4플랫폼·로컬 Ollama 코드 조사. 기존 4파일에 실제 선택형 생성 스트리밍을 개발하고 안전 fast-forward 반영. 기존 4파일에 중지 시 스트림·기억 확정 차단 안전 로직을 누적 개발하고 다음 fast-forward 반영. 기존 전체 인수인계 원문 뒤 127절 추가 및 별도 부록 생성.
- **이번 회차 하지 않은 것**: 신규 CI/단위검사·전체 회귀, 실제 Windows 10/11 EXE 빌드·GUI/Ollama/OBS·GPT-SoVITS·공식 Live2D 통합 실사용 검사, 권리 있는 한국어 음성 WAV 실제 합성·Cubism 입·OBS 동일 발화 영상/음성 증명, 실제 네 플랫폼 수백 명 수신·24시간 실행, 시청자 E2E 1~3초 실측, 오류 수정/전체 재검증. **코드 커밋만 확인했고 실행 성공·성능 개선은 아직 확인하지 않았다.**
- **미완료/중단**: 기존 500건 단일 AI FIFO의 수천 초 적체와 모델 자체 평균/상위 생성 시간; 오디오/영상 최종 시청자 측 재생 구간, 실제 수백 명 원격 서버 메시지 무누락, 24시간 네트워크 복구 실증, 사용자 소유 음성 권리 확인·실장비 통합. 스트리밍 UI 자체는 실제 답변/방송을 미리 전달하지 않으므로 위 요구의 실증은 아님.
- **다음 개발 우선**: 로컬 Ollama·공식 GPT-SoVITS 음성/Live2D/OBS 동일 발화의 실제 생성·출력 파이프 연결 개발, 잔여 4플랫폼 대량 이벤트를 전부 응답 처리하는 병목 기능 개발, 실제 24시간 안정·복구에 필요한 기능 누적 개발. 전체 개발 완료 후에만 기존 사용자 순서대로 전체 회귀→Windows 네이티브 EXE·GUI·OBS·실모델 검사→오류 수정→전체 재검증.
- 이번 기능 개발 기준 `main` HEAD `af4222282df08c755dcb0b6414f43dc25e0eb7ff`. 이 문서가 main에 반영되면 HEAD는 앞으로 전진하므로 다음 실행 시작 시 실제 `main`을 새로 조회. 1~126절/모든 과거 부록/설정/캐릭터/SQLite 원문을 그대로 보존하고 새 브랜치·force push·롤백·다른 프로젝트·Drive·다른 예약은 생성·변경하지 않았다.
