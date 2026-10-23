# AISTING 125회차 개발 우선 누적 인수인계

## 125. 2026-10-23 — 공식 Live2D 공개 채팅의 매건 8초 고정 관찰 병목 해소를 위한 선택형 실시간 입력 신규 개발

### 현재 main·기준 계획·기존 CI 확인
- 사용자 최신 요청 **"계속"**. 기존 `junggyeol4444/AISTING`의 `main` 소스 전체 신규 기능 누적 개발 우선 → 기능 개발 뒤 전체 회귀/Windows 네이티브 EXE/GUI·OBS·실제 모델 검사 → 오류 수정 → 전체 재검증. 기존 원본 코드·캐릭터·SQLite·모델/설정·전체 인수인계 절과 부록 원문 보존, 새 브랜치/force push/롤백/전면 재개발 금지, 다른 프로젝트·Drive·다른 예약 변경 금지, 사용자 승인 없는 방송·녹화·OAuth/외부 채팅 발신·모델 훈련·권리 없는 보이스 금지. 임의 토큰 길이 96 또는 `keep_alive=10m` 추가 금지.
- 시작 실제 `main` HEAD `6647f48f8f4ddbf912add7f801fb7e1c47166747` 조회. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~124절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 97절 원본 및 124절 부록과 `desktop_chat_tab.py`, `original_plan_frontend.py`, `multiplatform_readonly.py`, `multi_platform_session.py`의 실제 현재 코드를 확인.
- 과거 Windows CI `39722213656` 재조회: workflow `completed/cancelled` (전체 성공 아님, 기존 4개 작업 성공·한국 공개채팅 작업 취소, 취소 작업 로그 404 기록 보존). 기존 실제 Ollama 500 합성 채팅 CI `39720448468`은 workflow `completed/success`이나 **500건 전부 로컬 3초 초과**, 전체 p95 2,979.984초, FIFO 대기 p95 2,973.875초, AI 모델 처리 p95 7.875초. 실제 사용자 수백 명, 서버 메시지 전부 수신, 24시간 방송, 시청자 E2E 1~3초 달성의 증거가 아님.

### 이번 회차 신규 기능 구현 및 안전한 main 반영
- 개발 커밋 `0a56278e108fd1aa928f7053f8a471738537200e` **기존 `main`의 실제 최신 HEAD를 확인하고 `force:false` 안전 fast-forward 반영 성공**. 기존 Windows 네이티브 tkinter `src/ai_broadcaster/desktop_chat_tab.py`의 **공식 Live2D 공개 채팅 단일 AI FIFO 워커**가 매 수신 채팅마다 `send_to_native_live2d_session_with_observation(...duration=8)`을 호출해, 하나의 채팅을 전송한 뒤 다음 채팅까지 고정 **8초 Live2D 입/RMS 관찰**을 차례로 기다리는 병목 경로를 확인.
- 새 메모리 전용 tkinter 체크박스 `공식 창 빠른 전송: 채팅당 8초 립싱크 실증 대기 생략`과 상태 `_official_fast_send`를 추가. 초기 선택은 켜짐이며 운영자가 수신 연결 전에 직접 끄면 **기존 8초 동시 립싱크 실증 경로**가 보존·사용된다. 기존 실제 공식 Live2D 프로세스/React 화면/동일 WebSocket 경로를 재활용하며 새로운 AI 모델 호출/프롬프트 중복/음성 복제·학습 기능은 추가하지 않는다.
- 운영자가 기존 **공식 AI·Live2D 연결 승인 대화상자**에서 음성/입 실증과 빠른 전송의 증거 차이를 고지받는 절차 보존. `_work_twitch_ai(..., fast_official_mode=True)`는 각 실제 채팅을 `send_to_native_live2d_session(chat.text, operator_approved=True)`로 **한 번** 전송하고 기존 공식 브라우저 `input-result accepted=True`를 받으면 다음 AI FIFO 채팅을 시작한다. 기존 네트워크 수신·AI FIFO 순서/원본문장, Stop과 세션 구분 안전 경로 유지. 전송 실패·응답 형식 오류는 기존 오류 처리하며 중복 자동 재전송하지 않음.
- 실제 브라우저 WebSocket 텍스트 전송 사실만 확인한 새 `twitch_live2d_forwarded` 이벤트는 `_twitch_official_forwarded`로 따로 집계하고 GUI에 `공식 WebSocket 채팅 전달 확인 · 모델 답변·GPT-SoVITS 음성·입 움직임은 미검증`이라고 표시한다. **공식 서버가 답변 생성/한국어 TTS 출력/Live2D 립싱크를 완료했다는 사실을 성공 응답으로 허위 계수하지 않는다.** 기존 `twitch_live2d_ok`의 유효 입·RMS 실제 8초 관측 증거와 별도로 표시. 기존 `_work_twitch_ai` 직접 호출 계약의 새로운 인자는 `fast_official_mode=False` 기본값이므로 기존 직접 호출 검사의 요청 방식을 유지한다.
- 이 변경은 고정된 관찰 시간을 **빠른 입력 경로에서 생략하도록 개발한 사실**이지, 실제 GPT-SoVITS 음성 생성·발화·입·OBS 렌더링·시청자 수신 전체 지연 1~3초 달성의 증명은 아니다. 이 경로는 서버가 실제 응답했는지 자체를 아직 확인하지 않으므로 원본 계획의 모든 채팅 **실제 답변 완료** 요구 역시 미완료로 구분한다. 모델 느림/FIFO 수백 건 적체와 네트워크 소켓/OBS 시청자 지연도 남아 있다.

### 실제 수행/미수행/다음 인계
- **실제 수행:** AISTING main HEAD·원본 계획·로드맵·원문/CI 조회, 기존 4플랫폼+공식 AI 처리 소스의 채팅당 8초 실측 병목 발견, Windows GUI 체크박스 및 기존 공식 WebSocket 실시간 전달 경로 누적 개발, 125회차 기능 커밋 안전 fast-forward 반영, 기존 인수인계 원문 뒤 새 125절 및 새 부록 생성.
- **이번 회차 수행하지 않음:** 신규 단위검사·전체 회귀 CI/Windows EXE 빌드·실제 Windows PC 네이티브 GUI 작동/본인 소유·라이선스 음성 GPT-SoVITS 합성·실제 Cubism·OBS 통합 실증, 4플랫폼 실제 수백 명·24시간 운영/실수신 무누락, 실제 1~3초 시청자 E2E 실측, 코드 오류 수정 및 전체 재검증. 구 CI mock/합성 이벤트를 실사용 인원 또는 목표 지연 달성으로 보고하지 않음.
- **다음 전체 기능 개발 우선:** 공식 채팅으로 전송한 *실제 각 발화별* AI·TTS·Live2D·OBS 응답 여부와 동기화 실증, 로컬 Ollama 실제 추론 처리량과 단일 FIFO 적체 해소(원본 기억/순서 유지), 실제 네 플랫폼 복구 가능한 메시지 커서·수백 명 무누락, 24시간 운영/시청자 E2E 병목 개발. 모든 기능을 누적 완성한 후 전체 회귀→Windows 네이티브 EXE/GUI·OBS·실모델 실통합검사→오류 수정→전체 재검증 순서 고수.
- 신규 코드 커밋 HEAD `0a56278e108fd1aa928f7053f8a471738537200e`. 인수인계 반영 후 `main` HEAD가 바뀌므로 **다음 회차 시작 때 재조회**. 과거 1~124절 원문 및 과거 부록·다른 프로젝트/기존 예약 불변.
