## 170. 2026-10-25 — 트위치 IRC 전체 프레임 미수용 채팅의 JOIN 승인·재연결 보류 개발

### 기준 및 원문 보존
- AISTING만 기존 `main` 코드 실제 누적 개발. 사용자의 마지막 명령: 개발 우선 누적 완성 → 전체 회귀·Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검사 → 오류 수정 → 전체 재검증. 실사용·mock·코드 작성 구분, 실패 은폐 금지.
- 시작 `main` HEAD **`c33aa2a522c986bbf2ab0807e40eac6c7d5f3d5a`**를 GitHub에서 직접 확인했다. `docs/AISTING_HOURLY_FULL_HANDOFF.md` 전체 1~169절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 97절/169절 개별 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 실제 `src/ai_broadcaster/twitch_readonly.py`, `multiplatform_readonly.py`, `multi_platform_session.py` 및 169절 계약검사 원문을 확인. 통합 문서에 있는 과거 절 원문 보존. 모든 과거 개별 부록을 하나하나 별도 API로 열어 확인하지는 않았다.
- 기존 캐릭터·SQLite·설정·원본 기획·로드맵·원문은 변경하지 않았다. 새 브랜치/force push/롤백/전면 재개발, 다른 프로젝트/Drive/기존 예약 변경·중복 예약, 승인 없는 OAuth/로그인·방송·녹화·채팅 발신·모델 훈련·권리 없는 보이스, 토큰 96·keep_alive 10m 임의 설정은 수행하지 않았다.

### 실제 코드 개발 및 main 커밋
1. **`0483e52362bf9cac21270ac7b2e8feff8fa4cd88`**: 기존 `src/ai_broadcaster/twitch_readonly.py`에 `_pending_chats` deque와 `_flush_pending_chats()` 추가. 한 IRC WebSocket 프레임의 모든 파싱된 `PRIVMSG`를 AI FIFO 전달 전에 메모리에 보관. 중간 채팅 콜백 `False`/예외 발생 시 미수용 선두 및 같은 프레임의 뒤쪽 채팅을 보존. 기존 IRC JOIN 승인 뒤에만 FIFO 순서로 전달하고, JOIN 전 채팅과 재연결 이전 보류 채팅도 같은 deque로 관리. 운영자 Stop 이후 미전달. IRC PING/PONG, 서버 RECONNECT, 채널·OAuth 기존 경로는 유지.
2. **`aa71e856d65b2211931caa15a5222ccad22e98e3`**: 기존 `src/ai_broadcaster/multi_platform_session.py`에서 `_pending_websocket_chats` 공유 대상을 치지직·SOOP에서 **트위치·치지직·SOOP**으로 확장. 새 트위치 수신기에 같은 메모리 보류 큐를 연결하고 `reconnect_snapshot()`의 `수신프레임미수용보류`로 실제 미수용 건수를 구분. 기존 단일 AI FIFO, 승인된 채팅만 ID 중복 차단, SQLite·캐릭터·설정은 유지.
3. **`62a7e55cd5eee17f3217e6f73946157b49f513d3`**: 신규 `tests/test_aisting_twitch_frame_pending_170.py`에 **10건의 가상 계약검사 작성**. JOIN 전 보류, 한 프레임 내 JOIN 전/후 순서, 콜백 False·예외 후 뒤쪽 보존, 새 수신기 공유, 서버 RECONNECT 전 채팅 처리, Stop 후 미전달, 서버 ID 없는 동일 본문 두 건, 합성 500건 한 프레임, 4플랫폼 조정기의 트위치 공유·진단 검증. 가상 소켓·가상 시청자·가상 채팅이며 실제 Twitch 서버/실제 500명/실모델/OBS 증거가 아니다.
- 기존 소스 2개 수정·신규 검사 1개 작성. **신규 계약검사는 실행하지 않았다.** 전체 회귀 및 Windows EXE·GUI 실기기 실행도 이번 회차에 하지 않았다. 기존 main HEAD와 blob SHA를 조회하고 main에 순차 반영. 실제 무누락 보장은 파싱된 트위치 프레임의 미수용 사건을 **프로세스 생존 중** 보존하는 범위로 한정. 연결 끊김 이전 미수신 서버 사건, 프로세스 종료 시 메모리 유실, 24시간 실증은 해결되지 않았다.

### 반드시 숨기지 않을 CI·실모델 지연
- 96절 Windows CI **`39722213656`**: OBS/Twitch/Windows EXE/Ollama 네 job 성공, `korean-public-chat-readonly` **취소**. 취소 job 로그 직접 요청은 원격 BlobNotFound 404. 전체 성공 아님.
- 96절 실모델 500건 CI **`39720448468`**: 실제 로그 직접 재조회, 500/500 처리·실패 0, **500건 전부 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI p95 **7.875초**.
- 164절 전체 회귀 **`40103031646`**: 로그 직접 재조회, **36 실패·31 오류·2 건너뜀**. 기존 mock/가상 객체의 `_live_queue_wait_tracker`, `_update_platform_health` 누락 및 YouTube `resume_state` 계약 불일치 등을 포함. 미수정·통과 주장 금지.
- 164절 Windows **`40103031611`**: 4 job 성공, Windows EXE **취소**. 전체 통과 아님.
- 164절 실제 Ollama 500건 **`40102973295`**: 로그 직접 재조회, 500/500 처리·실패 0이나 **497건 3초 초과**, 전체 p95 **1516.657초**, FIFO 대기 p95 **1513.422초**, AI p95 **3.375초**. 이는 합성 500건/로컬 추론이며 실제 수백 명·시청자 E2E 1~3초 성공 증거가 아니다.
- **170회차 신규 코드 테스트·전체 회귀·Windows CI 결과 미확인.** GitHub Actions 새 실행 번호를 확인하지 않았고, 이 회차 변경의 실사용 성공으로 주장하지 않는다.

### 완료·미완료·진행 중 멈춘 것·다음 회차
- **실제로 한 것**: main HEAD·인수인계·기획·로드맵·실제 소스 확인, 96/164절 CI job 및 실패 로그 재확인, 트위치 IRC 프레임 보류·JOIN 승인·재연결 보존 코드 작성, 조정기 공유, 가상 검사 10건 작성, 기존 main 순차 누적, 이 170절 인수인계 작성.
- **하지 않은 것**: 170절 신규 검사 실행, 전체 회귀, Windows EXE 빌드·GUI 실제 클릭, 실계정·실시청자 공개 채팅·24시간 실방송, 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 입→OBS 동일 PCM·영상 실증, 시청자 응답 1~3초 달성. 금지된 무단 계정/OAuth·방송·녹화·채팅 발신·모델 훈련도 하지 않음.
- **미완료**: 실제 한국어 음성/공식 Cubism/OBS 동일 발화 검증, Twitch·치지직·SOOP·YouTube 네 플랫폼 실제 수백 명 무누락 및 재연결 중 미수신 서버 사건 대응, 실제 24시간 안전성, 단일 Ollama FIFO 적체로 발생하는 1~3초 지연 목표 미달, 전체 회귀 36 실패·31 오류 해결, Windows EXE/GUI·OBS·로컬 모델 실제 통합검사·오류 수정·전체 재검증.
- **진행 중 멈춘 것**: 기존 미완료 기능 개발은 계속 진행 중. 이번에 트위치 파싱 완료 프레임 메모리 보존 코드·계약검사 작성까지 완료했으나, 사용자가 정한 전체 개발 완료 전이므로 신규 검사 실행 및 통합 실증은 미착수. 권리 있는 모델·실제 Windows/OBS·사용자 계정 권한이 필요한 실증도 미완료.
- **다음 시작**: 매번 GitHub `main` HEAD와 CI 최신 상태부터 재확인. 이번 **코드 커밋 HEAD** `62a7e55cd5eee17f3217e6f73946157b49f513d3`이나 인수인계 커밋으로 최종 HEAD는 달라지므로 고정 가정 금지. 전체 원문 1~170절 보존·누적, 개발 우선→전체 검사→오류 수정→전체 재검증 순서 유지. 기존 매시간 예약·다른 프로젝트/Drive/브랜치 변경 금지.
