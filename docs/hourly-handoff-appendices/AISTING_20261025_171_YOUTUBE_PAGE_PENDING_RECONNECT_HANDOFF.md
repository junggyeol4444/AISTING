## 171. 2026-10-25 — YouTube API 채팅 페이지 중간 미수용 사건 보존·재연결 FIFO 누적 개발

### 기준·원문 보존·사용자 지시
- 이번 자동 개발 회차 시작 시 GitHub `junggyeol4444/AISTING/main` HEAD 직접 조회: **`6a977bc354618ac2e8429cdcc8fea87d46e55413`**. 이전 170회차의 최종 HEAD와 일치함을 확인한 뒤 기존 main 소스에만 순차 변경했다.
- 기존 `docs/AISTING_HOURLY_FULL_HANDOFF.md` 전체 1~170절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체, 특히 `docs/hourly-handoff-appendices/AISTING_20261022_97_NEXT_CHAT_HOURLY_HANDOFF.md` 및 170절 원문, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 `multiplatform_readonly.py`, `multi_platform_session.py`, `twitch_readonly.py`와 170절 계약검사 원문을 조회했다. 모든 과거 개별 부록을 별도 파일로 하나하나 다시 열어 본 것은 아니며, 앞의 전체 원문 문서는 삭제·요약 대체하지 않았다.
- 사용자의 최신 지시는 **AISTING만**, 기존 전체 기능 **개발 우선** → 전체 회귀/Windows 네이티브 EXE·GUI·OBS·로컬 모델 통합검사 → 오류 수정 → 전체 재검증. 실제 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 실제 입→OBS 동일 발화, 4플랫폼 실제 수백 명·24시간·1~3초 병목은 계속 미완료. 신규 브랜치/force push/롤백/전면 재개발 금지, main의 안전한 누적 fast-forward만 허용. 기존 캐릭터·SQLite·설정·기획·인수인계 원문 보존. 다른 프로젝트/Drive/예약 변경·중복 예약, 무단 계정·OAuth 동의·방송·녹화·채팅 발신·모델 훈련·권리 없는 음성 사용, 사용자 요청 없는 토큰 96/keep_alive 10m 설정 금지.

### 실제로 작성하고 main에 반영한 코드
1. **`85d2d64d3798650b4fe48e26f20e8246e71cfa4f`** — 기존 `src/ai_broadcaster/multiplatform_readonly.py`의 `YouTubeChatResumeState`에 `pending_page_chats`와 한 페이지의 `nextPageToken`·서버 폴링 간격·정상 방송 종료 표시를 메모리로만 보존하는 상태를 추가했다. 실제 YouTube 읽기 루프는 정상 API 응답 전체를 먼저 파싱해 보류 큐에 넣고, 로컬 AI FIFO 콜백이 성공한 선두 사건만 큐에서 제거한다. 콜백 `False`/예외 시 미수용 선두와 같은 페이지의 뒤쪽 사건을 유지하고, **재연결된 새 수신기가 기존 페이지를 다시 HTTP로 조회하기 전에** 남은 사건부터 순서대로 전달한다. 서버 ID가 없는 동일 본문의 별개 사건도 임의 합치지 않으며, 이미 수용한 서버 ID만 재전달을 차단한다. 페이지 전체를 수용한 뒤에만 커서를 확정하고 보류 메모리를 해제한다. 운영자 Stop 시 남은 사건은 전달하지 않으며, 재연결 상태는 프로세스 메모리에만 보존된다. 승인 없는 인증·방송·녹화·채팅 발신·디스크 기록 없음.
2. **`ebadb62b630f07d872fb13975e5336020bb4cc20`** — 기존 `src/ai_broadcaster/multi_platform_session.py`의 읽기 전용 `reconnect_snapshot()`에 YouTube `수신페이지미수용보류`, `수신페이지확정대기`를 추가했다. 기존 Twitch·치지직·SOOP `수신프레임미수용보류`와 구별해 실제 수용 전 채팅을 성공 처리하지 않는다. 채팅 본문·사용자·토큰을 진단에 노출하지 않는다.
3. **`ba604da4a51aa69b2e7ce13a780ba1e247ce9b88`** — `tests/test_aisting_youtube_page_pending_171.py`에 **가상 계약검사 10건 작성**. 한 페이지 중간 `False` 뒤쪽 보존/재연결 HTTP 재조회 없음, 서버 ID 없는 동일 본문 3건, 콜백 예외, Stop, 가상 500건, 이미 전달된 서버 ID 재수신, 잘못된 폴링 간격, 보류 페이지 덮어쓰기 차단, 다른 채팅방 연결 차단, 4플랫폼 조정기 보류 진단. 가상 API·가상 시청자이며 실제 YouTube 수백 명·실방송·24시간 성공 증거가 아니다.
- **코드 개발만 수행**. 새 가상 계약검사는 작성했으나 실행하지 않았고 전체 회귀·Windows EXE·GUI·OBS 실기기 통합검사도 이 회차에 수행하지 않았다. 기존 main 원본 소스 2개 변경 + 신규 검사 1개 추가. 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 캐릭터·SQLite·설정 파일은 변경하지 않았다.

### 이번 회차 재조회한 CI 원문과 실패/한계
- 96절 Windows CI **`39722213656`**: GitHub 작업 재조회 결과 `obs-real-readonly`, `twitch-public-readonly`, `windows-exe`, `ollama-real-local-e2e` 네 작업 성공, `korean-public-chat-readonly` 취소. 전체 통과 아님. Windows EXE 작업의 실제 로그는 조회했으나 취소된 한국 채팅 작업의 원격 실패 로그는 확보하지 못함.
- 96절 실제 Ollama 500건 **`39720448468`**: 실제 job 로그 재조회. 500/500 처리·모델 실패 0이지만 **500/500건 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI p95 **7.875초**. `passed_three_second_local=false`.
- 164절 전체 회귀 **`40103031646`**: 실패 job 로그 재조회, **36 실패·31 오류·2 건너뜀**. 기존 mock 속성/YouTube 이어받기 계약 불일치 등 남아 있고 171 신규 개발의 전체 회귀 통과 여부는 모름.
- 164절 Windows **`40103031611`**: 한국 공개 채팅·로컬 Ollama·OBS 읽기·Twitch 읽기 네 작업 성공, Windows EXE 작업 **취소**. 전체 성공 아님.
- 164절 실제 Ollama 합성 채팅 500건 **`40102973295`**: 실제 job 로그 재조회. **500/500 처리, 모델 실패 0, 497건 3초 초과**, 전체 p95 **1516.657초**, FIFO 대기 p95 **1513.422초**, AI p95 **3.375초**. `passed_three_second_local=false`. 실제 수백 명/실제 시청자 E2E 지연 검증 아님.
- 170·171회차 최신 전체 회귀 및 Windows EXE/실모델 CI 실행 번호와 최종 결과는 이번 회차에 확보하지 못했다. 이 신규 코드의 통과·실사용 성공 주장 금지.

### 한 것·안 한 것·미완료·진행 중 멈춘 것·다음 회차
- **실제로 한 것**: main HEAD 및 원본 문서/기획/로드맵/실제 4플랫폼 수신 소스 확인, 과거 CI job/실패 로그 재조회, YouTube 페이지 전량 메모리 보류·부분 전달·재연결 FIFO 이어받기 개발, 4플랫폼 진단 연결, 가상 검사 10건 작성, 기존 main 누적 커밋, 기존 1~170절 원문 뒤에 171절 인수인계 추가.
- **실제로 안 한 것**: 171 신규 검사 실행, 전체 회귀, Windows EXE 빌드·실제 GUI 클릭·OBS·실제 한국어 권리 보유 GPT-SoVITS 음성/공식 Live2D 입 동일 PCM 실증, 실제 4플랫폼 수백 명 무누락·실제 24시간 방송, 실제 시청자 응답 1~3초 달성, 승인 없는 OAuth/방송/녹화/채팅 발신/모델 훈련. 코드가 파싱·수용한 페이지 내부 사건만 **프로세스 생존 중** 이어받으며, API 서버가 전달하지 않은 사건·프로세스 종료·재시작·페이지 내용 변경에 따른 모든 누락을 복구하지는 못한다.
- **미완료/진행 중**: 사용자 지정 전체 개발 목표의 실제 GPT-SoVITS WAV→공식 Cubism→OBS 동기화/실증, 4플랫폼 진짜 수백 명·24시간 안전성, 1~3초 지연 병목 해소, 전체 회귀 36 실패/31 오류 해결, Windows EXE·GUI·OBS·로컬 모델 전수검사와 오류 수정/재검증. 이번 개발은 YouTube 수신 페이지 중간 실패 보존까지 진행했으며 신규 검사 실행 전에서 멈춤.
- **다음 시작**: GitHub `main` HEAD와 신규 CI를 다시 확인하고 1~171절 원문/모든 부록·기획·로드맵·실제 소스를 보존하며 미완료 기능을 계속 **개발 우선**. 전체 기능 개발 후 회귀/Windows 실사용 검증→오류 수정→전체 재검증. 기존 예약·다른 프로젝트·Drive·브랜치 변경 금지.
- 본 절 작성 직전 **코드 HEAD `ba604da4a51aa69b2e7ce13a780ba1e247ce9b88`**. 인수인계 문서 추가 커밋 후 HEAD는 다시 바뀌므로 **다음 회차 반드시 main HEAD 새로 확인**.
