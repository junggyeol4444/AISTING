# AISTING 198절 — 2026-10-26 00:33 KST 승인된 실제 방송 자율 콘텐츠 주제 진행 개발

## 이 회차 사용자 지시
- 기존 AISTING 대화와 기존 1시간 예약 그대로 유지. 다른 프로젝트·예약·대화·Drive·브랜치 접근/변경 금지.
- **미완성 제품 기능 실제 소스 전체 개발 먼저 → 개발 전부 끝나면 통합검증 → 발견 오류 일괄 수정 → 전체 재검증.** 이번 회차 테스트/CI/실방송/Windows EXE 검증 실행 금지. 원본 기획·캐릭터·모델·96토큰/keep_alive·SQLite·기존 인수인계 전체 보존.
- GitHub `junggyeol4444/AISTING` 기존 `main`만 누적. 신규 브랜치·강제 push·전면 재개발 없음.

## 기존 소스와 계획 확인
- 이 실행 시작 시 GitHub main HEAD: `74ebb1fb1a2dd4d3a4c637ead2e47308564c7901` (197절).
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md`, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`를 GitHub main에서 읽고 원본 내용 유지.
- `docs/hourly-handoff-appendices` 97·185·187~197절(있는 파일)의 기록 확인. 이외 과거 모든 부록을 이번 실행에서 각각 읽었다고 주장하지 않음.
- 기존 `approved_live_scheduler.py`, `approved_live_slot_journal.py`, `approved_live_idle_speech.py`, `approved_local_game_control.py`, `desktop_obs_tab.py`, `desktop_chat_tab.py`, `durable_public_chat_queue.py` 및 관련 원본 함수/GUI/실제 채팅 FIFO 구조 확인.
- 원본 기획의 자율 콘텐츠·24시간 방송·채팅 우선 원칙과 이미 개발된 승인형 실제 주간 OBS 방송/4플랫폼 수신·공식 Live2D 한 작업자 경로를 재사용.

## 이번 회차 실제 제품 소스 개발 — 1. 방송 콘텐츠 주제 순환·영구 장부
- 신규 `src/ai_broadcaster/approved_live_content_agenda.py` 구현.
- 운영자가 지정한 1~30개 한국어 방송 주제를 원문 그대로 수용하고 60~3600초 간격으로 순환. 기존 공식 Live2D AI 서버에 주제/순번/시청자 반응을 꾸미지 말라는 지침을 한 건씩 보내 자율 콘텐츠 진행을 요청. AI/목소리/캐릭터 설정 변경 없음.
- 실제 OBS 방송이 **해당 예약에서 시작되고 여전히 소유/진행 중인 상태**, 기존 4플랫폼 공개 채팅 FIFO가 비어 있고 선택한 채널 SQLite 미처리 건수가 0인 무채팅 구간에서만 다음 콘텐츠 질문을 준비. 새 채팅이 있으면 콘텐츠보다 실제 채팅을 우선 처리.
- 별도 `data_dir()/approved_live_content.sqlite3` 독립 장부. 파일 소유권 `PRAGMA application_id`, 테이블 구조, 일반 파일·symlink 검사. 기존 사용자 대화 기억·방송 슬롯·캐릭터/설정 DB 변경 없음.
- `(occurrence, sequence)` 영구 UNIQUE 슬롯을 **공식 AI에 전달하기 전에** 커밋. 강제 종료/공식 서버 응답 불명 시 같은 슬롯 자동 재발화 금지. 시도/공식 서버 전달확인/전달불명 상태를 기록하고 재시작 후 다음 순번부터 진행.
- 실제 음성·입 움직임·OBS 출력·시청자 수신은 공식 AI 질문 전달만으로 증명하지 않음.

## 이번 회차 실제 제품 소스 개발 — 2. 4플랫폼 실제 AI 채팅 단일 FIFO 통합
- 기존 `src/ai_broadcaster/desktop_chat_tab.py`의 **공식 AI 실제 채팅 단일 작업자**에 별도 승인된 콘텐츠 `ApprovedLiveContentAgenda` 연결.
- 기존 `_work_twitch_ai`의 0.5초 채팅 대기 구간에만 무채팅 콘텐츠 후보를 조회. 기존 영구 공개 채팅 복구 DB를 조회해 선택한 채널 미처리 건수가 있으면 콘텐츠 진행 금지.
- 기존 공식 `send_to_native_live2d_session`을 재사용해 한 콘텐츠 질문을 한 번만 전달하고, 성공/불명 사건을 세션 전용 GUI 이벤트로 보고. 기존 4플랫폼 채팅 답변·기억 저장·SQLite ACK 경로를 바꾸지 않음.
- 실제 공개 채팅이 들어오면 콘텐츠 무채팅 간격 다시 계산. 방송 종료, 채팅 수신기 종료, 운영자 Stop, 실제 OBS 송출 소유 상태 해제 시 새 콘텐츠 발화 차단.
- 기존 수동 무채팅 고정 발화와 자동 콘텐츠 주제 진행은 별개. 예약형 콘텐츠는 별도 OBS GUI 승인을 받은 경우만 동작하며 이전 수동 발화의 별도 승인 경계를 변경하지 않음.

## 이번 회차 실제 제품 소스 개발 — 3. Windows OBS 예약 GUI 운영자 승인·기록
- 기존 `src/ai_broadcaster/desktop_obs_tab.py`에 기본 해제인 "승인한 방송 주제로 무채팅 중 자율 콘텐츠 진행" 체크박스, 주제 다중행 입력, 진행 간격 입력, 영구 시도/전달 결과 조회 버튼 추가.
- 콘텐츠 기능은 기존 "방송 시작 시 4플랫폼 공식 AI 채팅 자동 연결" 승인과 함께 사용해야만 활성화. 실제 방송 자동 실행 최종 승인창에서 주제 진행/간격/기록/전달 불명을 별도로 명시.
- 예약 방송 시작 확인 후 기존 채팅 세션 승인 토큰에 **그 방송 occurrence·승인 주제·간격·OBS 실제 송출 확인 함수**를 귀속. 이전 세션/다른 방송에 자동 승계하지 않음. 예약 종료/채팅 Stop 시 메모리 승인 계획 해제. 다음 주간 슬롯은 새 occurrence로 별도 장부 사용.
- GUI에서 지난 콘텐츠 발화 시도·공식 서버 전달/불명 상태를 로컬 조회만 할 수 있으며, 조회가 실제 외부 방송/게시를 시작하지 않음.

## 실제 main 제품 소스 커밋 7개
1. `5891480829f615975930a87b7c81266b23cd2ea9` — 주제 순환·SQLite 중복 방지 신규 모듈
2. `b6a845f6cbf2764596ed3f06e7951103b6d8f96d` — 실제 4플랫폼 채팅 FIFO 공식 AI 작업자에 주제 진행 연결
3. `1f66924bf5b3d2f041c43b77ddbc7c30c1e92099` — OBS 예약 GUI 주제·간격·최종 승인 연결
4. `4a28ce49f250e8de9270264d9da57ae458be3a61` — Windows GUI 영구 콘텐츠 기록 조회
5. `a5441609cc8066ec89168f4aef559dffbb357e8f` — 예약 소유 실제 OBS 방송 중에만 콘텐츠 진행 허용
6. `04bef94e75c9d0a590393fd7bed5ade30c0c3d70` — 방송 종료·4플랫폼 수신 종료 시 새 콘텐츠 차단
7. `8c409f586b68efebf7e522e429bfad103dbdbfb4` — OBS 예약 송출 상태 확인을 실제 콘텐츠 발화 허가에 연결

제품 소스 신규 1개, 기존 변경 2개. 이번 개발 기록과 전체 인수인계 2개는 **제품 코드 반영 후** append-only 커밋한다.

## 정확한 미실행/미완료 상태
- 이번 회차 제품 소스 **코드 작성·GitHub main 반영 완료**. AISTING 전체 개발 완료 아님.
- **테스트 NOT_RUN / CI 조회하지 않음·결과 미확인 / Windows 10·11 EXE GUI NOT_RUN / 실제 OBS·Live2D·GPT-SoVITS·4플랫폼 계정·방송/시청자 수신 NOT_RUN.** 새 콘텐츠 진행 실제 성공/24시간 무인 방송/1~3초 달성 주장 금지.
- 과거 실제 500건 모델 CI `39720448468` 500/500 모두 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초, Windows CI `39722213656` 취소 기록 보존. 기존 실패를 성공으로 덮어쓰지 않음.
- 아직 남은 개발: 실제 수백 명 4플랫폼 영구 수신·서버 커서·적체/백프레셔·1~3초 목표 처리량, 권리 있는 동일 GPT-SoVITS WAV→공식 Cubism 입→OBS 영상·음성 인과성, 24시간 자동 복구와 자율 콘텐츠/게임 장기 수행, 공식 네이버 카페 공지 및 원본 기획 나머지 기능.
- 다음 회차도 **실제 미완 핵심 제품 소스 개발부터**. 전체 개발이 끝나기 전 CI/통합검증/오류 수정으로 넘어가지 않는다. 기존 AISTING 대화·기존 매시간 예약·GitHub main 및 원본 문서 보존.
