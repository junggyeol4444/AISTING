## 181. 2026-10-25 — 4플랫폼 미처리 공개 채팅 원본 SQLite 분리 영속 큐와 강제 종료 복구 기능 누적 개발

### 시작점·원문·사용자 순서
- 이번 실행 첫 GitHub `junggyeol4444/AISTING` `main` HEAD: **`8a6135d2af041b5d49ac24f00a7dd5a046cc74af`**. 원본의 1~180절이 포함된 `docs/AISTING_HOURLY_FULL_HANDOFF.md`, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 180회차 부록 및 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`의 실제 내용을 읽음. 실제 `desktop_chat_tab.py`, `multi_platform_session.py`, `multiplatform_readonly.py`, `twitch_readonly.py`, `conversation_memory.py`, `original_plan_frontend.py`, `original_plan_full_pipeline.py`, `original_plan_voice_obs_bridge.py`, `offline_settings.py` 등 핵심 소스도 확인.
- **사용자 명령 변경 없음: 전체 기능 개발 → 전체 회귀 및 Windows EXE/GUI·OBS·Live2D·한국어 GPT-SoVITS·로컬 실모델 통합검증 → 오류 수정 → 전체 재검증.** `검증하지 말라`는 뜻이 아니며, 기능 한 개 개발 후 부분 검증·수정하는 반복 금지. AISTING만 수행하고 다른 프로젝트·Drive·매시간 예약·브랜치 임의 변경 금지.

### 실제 개발 반영 — 단순 관측이 아닌 기능 코드
1. **`src/ai_broadcaster/durable_public_chat_queue.py` 신규 코드** — 별도 `LOCALAPPDATA/AISTING/pending_public_chat.sqlite3` 미처리 공개 채팅 보관소 생성(Windows 이외 기존 설정 폴더 사용). 기존 대화 기억 `conversation_history.sqlite3`·캐릭터·settings.json·기획·원본 데이터는 변조하지 않음. 수신 이벤트의 플랫폼/채널/작성자/본문/서버가 부여한 event_id를 AI 큐 등록 전 트랜잭션 확정. 자체 `application_id`와 스키마 확인, 다른 DB·심볼릭 링크·미확인 빈 DB 덮어쓰기 거부. 저장 용량 한도 도달 시 조용히 폐기하지 않고 예외 발생. 처리 성공 건은 자체 행만 개별 삭제.
2. **같은 모듈의 복구·중복 방지** — 이전 프로그램 종료 뒤 삭제되지 않은 미처리 항목을 **같은 플랫폼·동일 채널에 한해서만**, 저장된 전역 시퀀스 오름차순으로 복구. 다른 방송/채널은 섞지 않음. 실제 서버 event_id가 같고 여전히 보류 중인 항목만 재등록 차단. 서버 ID 없는 동일 본문/작성자의 별개 발언은 모두 유지. 최대 4096건을 안전 복구 단위로 처리하며 초과 시 순서 왜곡 대신 연결 중단·오류 알림. 재부팅 이후 이전 `monotonic` 시각은 유효하지 않아 시각 미확인으로 별도 처리. 로컬 디스크 복구이며 서버 단에서 수신되지 않은 채팅까지 복구하는 기능은 아님.
3. **`src/ai_broadcaster/desktop_chat_tab.py` 실제 수신·GUI·AI 실행 경로 수정** — 운영자가 공개 채팅 연결을 요청한 시점에만 큐를 초기화하고 이전 작업을 먼저 AI FIFO에 복구한 뒤 새 수신기를 시작. 실제 각 네트워크 콜백에서 디스크 트랜잭션 완료 **이후**에만 기존 `_results`, `_ai_arrival_times`, `_twitch_ai_inbox`로 전달. 기존 GUI 이벤트·FIFO 원래 순서를 보존하고 반복 서버 ID만 중복 등록하지 않음. AI worker에서 `PendingChat`을 해제해 기존 `chat` 객체를 그대로 Ollama/공식 Live2D 경로에 전달; 로컬 AI 응답 성공, 공식 WebSocket 실제 텍스트 전달 확인, 공식 느린 입 관찰의 긍정적 표본 확인 뒤에만 미처리 키를 확인·삭제. AI/공식 전송 실패나 사용자 Stop은 미완료 레코드를 유지하여 다음 실행 때 복구. GUI의 기존 플랫폼 상태 창에 현재 별도 SQLite 보관 건수와 장애 경계 중복 가능 경고 추가(매 갱신 시 DB 읽기로 Tk를 멈추지 않도록 메모리 카운터 사용).
4. 기존 모델 파라미터·기본 토큰 길이·keep_alive·TTS·캐릭터·SQLite 대화 기록·GitHub 브랜치·사용자 장비 설정·OBS/채팅 발신/녹화/송출·OAuth·모델 훈련은 변경하지 않음. 모든 반영은 기존 `main` blob SHA 확인 후 일반 fast-forward 커밋으로 순차 수행.
5. **신규 기능 개발 단계**이므로 신규 기능/전체 회귀/Windows EXE·GUI/OBS/모델 실사용 검증 및 오류 수정 단계는 이번 회차에서 시작하지 않음. **검증 금지가 아니라 사용자 요구한 전체 개발 완료 이후 실행 순서 준수**.

### 잔여 결함과 정확한 한계
- 원본 서비스의 채팅 수신 ACK·실제 서버 재연결의 이벤트 완전성은 사용자가 보는 모든 메시지 무누락과 같지 않음. DB는 callback이 실제로 받은 메시지만 내구화한다. 200,000건까지 보관하도록 막았으나 장기간 디스크 공간 부족·DB 잠금·전원 차단 순간 등의 실기기 검증은 없음.
- AI 결과 생성·전송이 끝난 직후와 DB 삭제 확정 직전 사이에 프로그램이 강제 종료되면 **재시작 시 동일 입력의 재처리/중복 가능**. 이를 exactly-once로 주장하지 않음. 다른 실행 인스턴스에서 동시에 해당 DB를 사용하는 환경과 YouTube 실계정 전송·읽기 24시간은 미검증.
- `source`의 메시지/채널이 데이터 보존 상한을 초과하거나 데이터 저장 장치에 문제가 있으면 실패를 표시하고 성공인 척 채팅을 버리지 않음. 미처리 채팅은 공개 송신 메시지의 로컬 복구 목적에 한해 SQLite에 남을 수 있음. 음성·WAV·인증 토큰/비밀번호는 새 DB에 보관하지 않음.
- 여전히 **사용자 권리 있는 실제 한국어 GPT-SoVITS WAV → 공식 Live2D Cubism 실제 입 움직임 → OBS 동일 발화 소리/영상 인코더 및 최종 시청자 전달 증명**이 미완료. 공식 기존 WebSocket/WAV/PCM/RMS 상관계수는 후보일 뿐 동작 완료 아님.
- 기존 실모델 500건의 FIFO 대기 p95 수천 초 및 1~3초 실패, 실제 4플랫폼 수백 명 무누락, Windows 네이티브 GUI/EXE 실제 조작, 실방송 24시간 안정성 등 미완료. 새로운 큐가 이 병목을 자체 해결한다고 주장하지 않음.

### 과거 CI 실패 로그 및 이번 확인
- 96절 Windows `39722213656`: obs-real-readonly/twitch-public-readonly/windows-exe/ollama-real-local-e2e **4개 성공**, korean-public-chat-readonly **cancelled**. 해당 취소 작업 로그 재요청은 404 `BlobNotFound`; 전체 성공·실사용 증빙 아님.
- 96절 실제 Ollama 500건 `39720448468`: 모델 작업 실행 자체는 성공, 500/500 처리(실패 0), **500/500 모두 3초 초과**; 실제 로그 확인 p95 전체 **2979.984초**, FIFO 대기 **2973.875초**, AI **7.875초**. 500명 실제 시청자가 아니라 모델 합성 부하 입력.
- 177절 전체 회귀 `40155307503`: **36 failures, 33 errors, 2 skipped**를 CI 로그에서 확인. 177절 Windows `40155307396`: 4 성공/EXE 취소. 177절 500건 `40155307463`: 전체 p95 **2867.219초**, FIFO p95 **2861.109초**, AI p95 약 **6.469초**, 500/500 3초 초과.
- 181회차 신규 코드의 CI 번호·최종 실행 상태는 **확보하지 못함**. 실행 전이므로 신규 프로그램 통과 주장하지 않음.

### 다음 대화 필수 인계
- 이번 실제 반영 시작 HEAD `8a6135d2af041b5d49ac24f00a7dd5a046cc74af`; **181회차 기능 코드 반영 마지막 HEAD `5c7738d156bd165de0697e3e882bafca52c8d059`**. 아래 두 인수인계 문서까지 갱신하면 최종 HEAD는 달라지므로 **다음 시작 시 현재 `main` 조회** 필수.
- **실제로 한 것:** GitHub main/기획·전체 인수인계/원본 소스/기존 CI 재확인, 새 공개 채팅 durable FIFO 모듈, GUI 네트워크 ingress·AI 처리 성공 ACK·재시작 복구와 상태창 연결, 7개 기능 커밋, 이번 절 누적.
- **안 한 것:** 신규 검사 통과/Windows 실 PC 실행·GUI 클릭, OBS·실한국어 TTS·공식 Cubism·시청자 동일 발화 증명, 실계정 방송/채팅 발신/녹화·OAuth, 24시간 실운영 및 실 수백 명 무누락, 모든 남은 기능 완료 선언.
- **진행 중 멈춘 것:** 새 SQLite 미처리 큐와 실제 4플랫폼·AI 연동 소스 반영 단계 완료, 후속 핵심 통합 기능 전체 개발 완료 전. 장애/충돌/동시 인스턴스·정확히 한 번 처리 보장은 추가 개발/전체 검증 대상. 기존 36 failures/33 errors 미수정.
- **다음:** 1~181절 원문과 모든 과거 파일 무삭제 보존, 사용자 요구 핵심 기능을 **모두 개발한 다음** 전체 회귀→Windows 실제 EXE/GUI·OBS/로컬 모델 통합검사→오류 수정→전체 재검증. 다른 프로젝트·예약·Drive·브랜치 금지. 메모리/사용자 설정 원본 파일 삭제·초기화 금지.
