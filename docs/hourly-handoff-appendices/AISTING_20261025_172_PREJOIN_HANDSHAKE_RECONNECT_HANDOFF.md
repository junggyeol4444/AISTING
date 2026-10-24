## 172. 2026-10-25 — 치지직·SOOP JOIN 승인 전 채팅 프레임 재연결 보존 누적 개발

### 원본·지시·시작 기준
- 이번 매시간 개발 시작에 `junggyeol4444/AISTING` 실제 GitHub `main` HEAD **`bf05154f5a0f81719e35239c8dc16c51f09b49c3`**를 새로 조회했다. 이전 171회차 인수인계 최종 HEAD와 일치했다.
- 기존 `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~171절 전체, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체, 97절 및 171절 개별 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 실제 `multiplatform_readonly.py`·`multi_platform_session.py`·`twitch_readonly.py`·`original_plan_full_pipeline.py` 및 171절 계약검사 원문을 조회했다. 모든 개별 과거 부록을 이번 회차에 각각 다시 열어 확인한 것은 아니다. 두 전체 인수인계 문서의 기존 원문은 삭제·요약 대체하지 않았다.
- 사용자의 최종 지시 그대로 **AISTING 기존 코드 전체 개발 우선 → 전체 개발 후 전체 회귀/Windows 네이티브 EXE·GUI·OBS·로컬 모델 실검사 → 오류 수정 → 전체 재검증**. 4플랫폼 실제 수백 명 무누락, 실제 한국어 권리 보유 GPT-SoVITS WAV→공식 Cubism 입→OBS 동일 발화, 실제 24시간 안정성, 시청자 1~3초 목표는 아직 미완료다.
- 신규 브랜치·force push·롤백·재개발, 다른 프로젝트/Drive/예약 변경·중복 예약, 임의 계정·OAuth 동의·방송/녹화/채팅 발신·모델 훈련·권리 없는 음성, 토큰 96/keep_alive 10m 임의 설정 금지. 기존 캐릭터/SQLite/설정/원본 기획/과거 인수인계 원문 그대로 보존.

### 실제 172회차 개발 및 기존 main 누적 커밋
1. **`36ef1b407581dbcbeeb4a45d6d8168e9888150fb`** — 기존 `src/ai_broadcaster/multiplatform_readonly.py`에 `PreJoinChatResumeState` 추가. 치지직·SOOP가 서버 JOIN 승인 전 실제 소켓에서 이미 받은 채팅을 동일 서버 채팅방 ID와 함께 최대 4,096건 메모리 보관. 승인 전 연결 실패/재연결에도 수신한 프레임의 선두/뒤쪽 채팅을 보존하고, **같은 서버 방**에서 실제 JOIN 승인한 뒤 기존 미수용 FIFO 다음으로 넘긴다. 서버 이벤트 ID가 있는 재전송만 중복 차단하고, ID 없는 동일 본문은 서로 다른 채팅으로 유지. 새 서버 채팅방 ID가 확인되면 기존 미수용 채팅을 다른 방송으로 조용히 전달하지 않고 명시적 오류로 차단. 프로세스 재시작·서버가 보내지 않은 채팅의 복구는 보장하지 않는다.
2. **`4bda05b014c07537d8b3e49426d215c113d5d0d3`** — 기존 `src/ai_broadcaster/multi_platform_session.py`에 치지직·SOOP JOIN 전 상태를 수신기 재생성 사이 공유하도록 연결. 초기 수신기와 재연결 수신기 모두 동일 메모리 상태를 사용. 기존 4플랫폼 독립 수신, 트위치/YouTube 보류 처리, AI FIFO/SQLite/캐릭터/설정은 유지. 진단 스냅샷에 `JOIN전미수용보류`·`JOIN전중복서버ID차단`을 플랫폼별로 표시하며 채팅 본문·계정·토큰은 표시하지 않는다.
3. **`570f0bd57c452f8eed2512e362828195a9c9d09d`**, **`dd69096b5c12c55756afc18b22fe1594a594deec`**, **`a4dad45f3ce577dc702f0702e2ad261e750ed51c`** — `tests/test_aisting_prejoin_reconnect_172.py`에 가상 계약검사 **12건 작성**. 동일방 재연결 FIFO, 서버 ID 중복/ID 없는 같은 본문, 다른 방 차단, 기존 미수용 FIFO 차단, 4096건 한도, 잘못된 형식, 조정기 공유 진단, 치지직·SOOP 가상 JOIN 전 연결 실패 후 승인 전달 등. 마지막 커밋은 SOOP 가상 프레임의 파이썬 문자열 이스케이프 표기 정리. **검사 코드는 작성했으나 이번 회차에 실행하지 않았다**. 가상 데이터는 실제 플랫폼 500명/24시간 실증이 아니다.
- 실제로 수정한 기존 소스는 **2개**, 신규 검사 파일은 **1개**. 기존 사용자 파일/설정/캐릭터/SQLite/로드맵/기획은 수정하지 않았다. 매번 최신 HEAD와 파일 Blob SHA를 조회해 기존 `main`만 순차 갱신했고 새 브랜치/force push/롤백 없음.

### 이번에 실제 확인한 과거 CI 및 실패·제약
- 96절 Windows **`39722213656`**: job 조회상 `obs-real-readonly`, `twitch-public-readonly`, `windows-exe`, `ollama-real-local-e2e` 4개 **success**, `korean-public-chat-readonly` **cancelled**. 전체 성공 아님. 취소 job 로그는 GitHub 로그 보관 blob 404(BlobNotFound)로 이번 조회 실패, 상세 취소 원인은 단정할 수 없다.
- 96절 실제 Ollama 합성채팅 500건 **`39720448468`**: 실제 job 로그 재조회, **500/500 처리, 500/500 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, 모델 처리 p95 **7.875초**. 실제 시청자 500명 또는 24시간 방송 증거 아님.
- 164절 전체 회귀 **`40103031646`**: 실패 job 로그 재조회, **36 failures·31 errors·2 skipped**. 이 오류는 172 신규 코드로 해결했다고 보고하지 않는다.
- 164절 Windows **`40103031611`**: 4개 읽기/로컬 job success, **Windows EXE job cancelled**. 전체 성공 아님.
- 164절 실제 Ollama 500건 **`40102973295`**: 실제 로그 재조회, 500/500 처리·497건 3초 초과, 전체 p95 **1516.657초**, FIFO 대기 p95 **1513.422초**, AI p95 **3.375초**, `passed_three_second_local=false`. 실제 시청자 1~3초 목표 달성 아님.
- 171/172회차 최신 CI 실행 번호와 최종 상태는 이번 회차에 확인하지 못했다. 이번 신규 12개 계약검사·전체 회귀·Windows EXE/GUI·OBS·실제 GPT-SoVITS/공식 Live2D 통합검사를 실행하지 않았으며 성공으로 표기 금지.

### 실제로 한 것·안 한 것·미완료·중단·다음 회차
- **한 것**: 최신 HEAD 및 기존 인수인계/기획/로드맵/실제 소스 조회, 과거 96·164절 CI job/가능한 실패 로그 조회, JOIN 전 치지직·SOOP 프레임 보존 및 동일방 재연결 공유 기능 개발, 진단 추가, 가상 계약검사 12건 작성, 기존 main 코드 누적.
- **안 한 것**: 신규 12건 검사 실행, 171회차 이하 누적 신규 검사 실행, 전체 회귀/Windows 네이티브 EXE·GUI 클릭/OBS/실모델 통합검사, 실제 권리 있는 한국어 GPT-SoVITS WAV·공식 Live2D Cubism·OBS 동일 발화 PCM/영상 출력 실증, 4플랫폼 실수백 명 무누락/실제 24시간 안정성, 시청자 E2E 1~3초 달성, OAuth 대리 동의/실방송/녹화/채팅 발신/모델 훈련.
- **미완료**: 사용자 지정 전체 기능 중 실제 GPT-SoVITS→Cubism→OBS 동일 발화 검증 경로, 4플랫폼 실제 대량 채팅·재연결·24시간 무누락 실증, AI FIFO·로컬 모델 처리량 병목 개선과 1~3초 목표, 과거 전체 회귀 실패·오류, Windows EXE·GUI·OBS·로컬 모델 실기기 통합검사 및 최종 재검증. JOIN 전 수신기 재연결 개발도 실제 서버에서 미검증이며, 프로세스 종료나 서버 미전송 사건은 복구하지 못한다.
- **진행 중 멈춘 위치**: 172회차 치지직·SOOP JOIN 전 채팅 보존 개발·검사 소스 작성까지. 검증 실행 전에서 멈춤. 다음 회차는 최신 `main` HEAD 및 최신 CI부터 재조회하고 기존 1~172절 원문·모든 과거 부록·원본 기획/로드맵·실제 소스를 보존하며 **남은 기능 개발부터** 이어간다. 전체 개발 후 전체 회귀/Windows 실사용 검증→오류 수정→전체 재검증.
- 172회차 **인수인계 작성 직전 코드 HEAD `a4dad45f3ce577dc702f0702e2ad261e750ed51c`**. 인수인계 커밋 이후 HEAD가 변경되므로 다음 시작 시 반드시 현재 main HEAD를 다시 조회한다. 기존 매시간 예약/다른 프로젝트/Drive/브랜치는 변경하지 않았다.
