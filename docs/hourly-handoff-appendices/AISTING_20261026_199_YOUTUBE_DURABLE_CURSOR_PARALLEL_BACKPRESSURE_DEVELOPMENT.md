# AISTING 199절 — 실제 YouTube 영구 페이지 커서·4플랫폼 Ollama 선행 추론 백프레셔 개발

작성: 2026-10-26 01:29 KST 이후. 대상: junggyeol4444/AISTING 기존 main.
실행 시작 시 실제 확인한 main HEAD: e2aecf34be3b60a4287a9b15d48d4a0983f60f39 (198절).
이번 실제 제품 소스 최종 커밋: 592d8d288936f9d7f16176ba78dbebd06dea7032.

## 기존 사용자 최우선 지시
- 이 기존 AISTING 대화와 기존 매시간 예약 유지. 다른 대화/프로젝트/예약/Drive/브랜치 변경 금지.
- 남은 모든 제품 기능 실제 개발 먼저 → 전체 Windows 10/11 네이티브 EXE GUI·로컬 모델·OBS·공식 Live2D·4플랫폼 통합검증 → 오류 일괄 수정 → 전체 재검증. 이번에는 소스 개발만, 테스트/CI/실기기/실계정 미실행.
- 기존 소스·캐릭터 이름/성격/말투·SQLite·기획·설정·모델/96토큰/keep_alive 10m·인수인계 원문 보존. 사용자 승인 없는 OAuth·방송·녹화·외부 채팅/공지 발신·모델 훈련 없음.

## 실제로 확인한 기존 원본
- GitHub main HEAD 새로 조회. docs/AISTING_HOURLY_FULL_HANDOFF.md, docs/AISTING_NEXT_CONVERSATION_HANDOFF.md, docs/ORIGINAL_PLAN.txt, docs/ROADMAP_100.md, config/roadmap.json 읽음.
- 존재하는 docs/hourly-handoff-appendices 97·185·187~198절 파일을 읽음. 그 밖의 모든 과거 부록을 각각 읽었다고 주장하지 않음.
- 기존 durable_public_chat_queue.py, multiplatform_readonly.py, multi_platform_session.py, desktop_chat_tab.py, ordered_parallel_local_ai.py, approved_live_content_agenda.py, approved_live_scheduler.py, live_ai_recovery.py의 함수와 경계 확인.
- 195~198절의 실제 음성·게임·방송 자율 콘텐츠 소스/승인 경계를 삭제하거나 다른 프로젝트로 바꾸지 않음.

## 이번 실제 제품 소스 개발 1 — YouTube API 페이지 커서 영구 복구
- 신규 src/ai_broadcaster/youtube_page_checkpoint.py: 독립 로컬 data_dir()/youtube_page_checkpoints.sqlite3 파일에 운영자가 선택한 YouTube 채널·실제 liveChatId별 마지막 **전체 수용 완료** 페이지의 nextPageToken, 페이지 수, 방송 종료 상태를 저장.
- 별도 SQLite application_id·정확한 소유 테이블/열·파일 종류·symlink 검사. 기존 사용자 채팅·대화 기억·캐릭터/설정 DB 수정·삭제 없음.
- OAuth 접근 토큰·API 키·시청자 메시지 본문·닉네임을 새 커서 DB에 저장하지 않음. 저장하는 nextPageToken은 유튜브 API 페이지 위치이지 OAuth 인증 토큰이 아님.
- 기존 src/ai_broadcaster/multiplatform_readonly.py: YouTubeChatResumeState에 선택적 영구 커서 연결. 기존 보류 페이지의 모든 메시지가 기존 DurablePublicChatQueue.append()로 SQLite 수용된 뒤에만 페이지 커서를 디스크에 확정. 커서 쓰기 실패 시 메모리 위치도 앞으로 이동하지 않음. 일부만 수용 후 재시작하면 이전 확정 페이지를 재조회하고 기존 SQLite의 실제 서버 이벤트 ID로 중복 수용을 방지. 본문/닉네임이 같은 별개 메시지는 임의로 합치지 않음.
- 이전에 종료 페이지까지 수용한 같은 liveChatId는 다음 실행에서 종료 상태를 유지. '내 활성 방송' 입력을 사용해도 다른 실제 liveChatId에 과거 커서를 섞지 않음.
- 기존 src/ai_broadcaster/multi_platform_session.py 및 desktop_chat_tab.py: 승인된 Windows 단일 YouTube 채팅과 4플랫폼 동시 수신의 실제 YouTube 리더에 이 커서를 연결. 단순 GUI 조회만으로 OAuth/방송/채팅 발신 없음.
- 서버가 애초에 보내지 않은 채팅·연결 공백·만료된 서버 커서의 무누락을 보장하지 않음.

## 이번 실제 제품 소스 개발 2 — 실제 로컬 AI 4개 병렬 FIFO 백프레셔
- 기존 src/ai_broadcaster/ordered_parallel_local_ai.py: 최대 4개 동시 모델 추론 유지, 기본 32건(4~512 설정 범위) 선행 작업 창 및 can_submit() 추가. 창이 가득 차면 원본 SQLite 순번을 건너뛰거나 4096개 미래 모델 작업을 스레드풀에 무제한 등록하지 않음.
- 기존 desktop_chat_tab.py: 4플랫폼 실제 SQLite 복구→AI FIFO 순차 인계 시 선행 작업 슬롯을 먼저 확인. 가득 차면 원래 SQLite에 채팅을 남기고 20ms 뒤 다시 시도. 직접 실시간 인계 경로에도 동일 조건 적용.
- 기존 Windows 상태 표시: 선행 AI 대기 현재 건수/32건 한도와 SQLite 보류 구분. 기존 응답/대화 기억/성공 ACK의 FIFO 순서, 사용자 모델·캐릭터·96토큰·keep_alive 설정 유지.
- 실제 1~3초 최종 시청자 응답 달성/처리량 성능 향상 실증으로 주장하지 않음.

## 실제 main 제품 소스 커밋 6개
1. efad8ea34185003e45b763810e5ebd915261151f — 영구 YouTube 페이지 체크포인트 신규 파일.
2. 31c261bfea91b70776169bdcb4867979c6742442 — YouTube 전체 페이지 수용 후 커서 확정/종료 복구.
3. 2d13ed22ce656aab222dd548b483313b4843e505 — 4플랫폼 실제 수신기 영구 커서 주입.
4. fecdce05c0da16c8ecd7766fd95e850b217d80c0 — Windows 단일/4플랫폼 YouTube 수신 GUI 영구 커서 연결.
5. 326354ba8d540b44a06287b23243a924df465a7b — 로컬 Ollama 4개 병렬 추론 32건 선행 작업 창.
6. 592d8d288936f9d7f16176ba78dbebd06dea7032 — 4플랫폼 실제 SQLite 복구→AI 선행 창 백프레셔 및 GUI 상태.

제품 소스 신규 1개, 기존 변경 4개, 소스 커밋 6개. 모두 기존 main에 정상 비강제 반영. 이 기록과 두 전체 인수인계는 제품 소스 커밋 이후 원문 끝에 append-only로 누적.

## 정확한 미실행·미완료
- 이번 실제 소스 작성/기존 main 반영: 완료. **전체 AISTING 개발은 미완료**.
- 테스트 NOT_RUN. CI 미조회·미확인. Windows 10/11 EXE GUI NOT_RUN. 실제 YouTube/Twitch/치지직/SOOP/OBS/공식 Cubism/GPT-SoVITS/실계정/실방송 NOT_RUN.
- 기존 500건 실제 로컬 AI CI 39720448468의 500/500 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초 실패 및 Windows CI 39722213656 취소는 그대로 보존. 이전 실패를 성공으로 바꾸지 않음.
- 다음 미완 핵심: 4플랫폼 서버 재연결/이벤트 보존 경계·대규모 FIFO, 한국어 GPT-SoVITS 동일 WAV→공식 Cubism 입→OBS 영상·음성 실제 인과성, 24시간 승인 방송·채팅·자율 콘텐츠/게임 장애 복구, 공식 네이버 카페 공지 등 기존 원본 기획의 미개발 기능.
- 다음 매시간 예약도 **이 기존 AISTING 대화**에서 가능한 한 보고하고 최신 main부터 제품 기능 개발을 계속한다. 새 예약·새 대화·다른 프로젝트/브랜치/Drive 변경 금지. 전체 개발 끝나기 전 테스트/오류 수정으로 작업 전환 금지.
