# AISTING 202절 — 2026-10-26 실제 핵심 제품 개발: 네이버 카페 공식 API 공지·SQLite 중복 방지·OBS 승인 일정 연동

## 실행 시작점과 사용자 지시
- 기존 GitHub `junggyeol4444/AISTING` **main** 시작 HEAD `806b9af4ad06e3daf3b48c50cdcccb0df2d0d8cd` (201절 이후)을 실제 조회했다.
- 사용자 명령은 **이 원래 AISTING 대화에서만 매시간 계속 개발**을 최우선 시도, 새 예약/다른 프로젝트/Drive/브랜치 건드리지 않기. 플랫폼의 결과 게시 대화 보장 여부를 허위 주장하지 않음.
- **기획상 남은 기능 실제 개발을 먼저 끝까지 누적 → 모든 기능 개발 완료 뒤 전체 Windows 10/11 EXE GUI·OBS·공식 Live2D·GPT-SoVITS·4플랫폼·실방송 통합검증 → 오류 일괄 수정 → 전체 재검증**. 이번 실행은 개발만 진행. CI 조회·테스트·Windows/OBS/실계정 실행·오류 수정 단계로 전환하지 않음.
- 기존 원본 기획 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 전체 인수인계 2개 전문, 97·185·187~201절 주요 부록 및 실제 변경 대상 `approved_live_scheduler.py`, `desktop_obs_tab.py`, 기존 디스코드 공지/OBS 슬롯 장부 소스와 공개 채팅·음성 구조를 조회. **모든 1546개 저장소 파일과 모든 과거 부록의 전문을 전부 읽었다는 주장은 하지 않는다.**
- 공식 카페 API 명세: https://developers.naver.com/docs/login/cafe-api/cafe-api.md . 네이버 OAuth 2.0 카페 글쓰기 권한과 POST `https://openapi.naver.com/v1/cafe/{clubid}/menu/{menuid}/articles`, 제목/본문 URL 인코딩, `message.status=200` 및 `articleId`를 근거로 구현. 외부 사이트 조회는 개발 사양 참고일 뿐 실제 네이버 계정 로그인/게시 테스트가 아니다.

## 이번 회차 실질 제품 개발
1. **신규 `src/ai_broadcaster/approved_naver_cafe_notice.py`**: 운영자 본인이 발급받은 OAuth 접근 토큰을 현재 프로세스 메모리에서만 사용해 네이버 공식 카페 일반 게시판에 실제 방송 시작·종료 글을 POST하는 API 클라이언트. `clubid`·`menuid` 숫자 제한, 권한 승인 필수, 제목 150자/본문 4000자 제한, 네이버 공식 샘플의 UTF-8→MS949 이중 URL 인코딩, HTTPS 단일 공식 호스트, 프록시·리다이렉트 차단, 12초 요청 타임아웃, 응답 크기 제한. HTTP 200뿐 아니라 `message.status`와 실제 `articleId`를 확인한 경우에만 서버 게시 확인 후보로 반환. 실패·응답 불명·토큰 만료 시 자동 재발신 없음. 응답 본문·OAuth 토큰/헤더를 로그·GUI에 출력하지 않음. OAuth 로그인/토큰 갱신/브라우저 자동화·게시판 가입은 구현하거나 실행하지 않음.
2. **신규 `src/ai_broadcaster/approved_naver_cafe_notice_journal.py`**: 별도 독립 SQLite `approved_naver_cafe_notices.sqlite3`의 application_id/스키마 소유권 확인. KST 방송 슬롯 × 시작/종료 × 카페·게시판 UNIQUE 키로 HTTP **이전**에 시도를 원자적으로 영구 커밋. 같은 슬롯을 다른 창/재시작에서 중복 게시하지 않음. 제목·본문은 SHA-256만, 토큰·원문은 DB에 저장하지 않음. `발신시도`/`서버게시확인`/`서버응답불명` 및 서버 글 번호만 기록. 이전 방송/채팅/캐릭터/디스코드 SQLite에 쓰지 않음. 최근 20건 읽기 전용 조회 API.
3. **기존 `src/ai_broadcaster/approved_live_scheduler.py` 확장**: 별도 `on_cafe_started`/`on_cafe_finished` 콜백과 승인 인자. 기존 OBS 실제 송출 시작 확인·채팅 시작 시도 후에만 카페 시작 공지 콜백을 호출, 내가 소유한 OBS 종료 실제 확인 후에만 종료 공지 콜백 호출. 디스코드 시작·종료 공지와 별도 상태값 `cafe_start_notice`/`cafe_end_notice`를 GUI snapshot에 전달. 외부 게시 실패가 기존 OBS 종료를 임의로 막거나 같은 공지를 자동 재발신하지 않음. 기존 방송 시간/종료 룰·권한·OBS 장면·소스·모델·96토큰/keep_alive 설정 변경 없음.
4. **기존 `src/ai_broadcaster/desktop_obs_tab.py` 확장**: 네이버 카페 공지 기본 꺼짐 체크박스, clubid/menuid, 사용자 수동 발급 OAuth 접근 토큰 비표시 입력, 시작/종료 공지 각각 제목·본문 수동 입력, 최종 승인 팝업에 실제 외부 글쓰기/중복 금지/토큰 권한 안내. 사용자 승인 후 선택한 방송 주간 슬롯과 카페 영구 장부를 결합. 실제 송출/종료 확인 콜백만 네이버 API를 호출. 승인 후 토큰 입력 UI 지움(실행 중 승인된 sender 메모리에서만 사용). 카페 공지 시도/서버 확인 기록 조회 버튼과 상태 표시. Discord/기존 자율 콘텐츠/4플랫폼 채팅 경로 보존.
5. **명시적 제한**: 네이버 카페 앱 등록/글쓰기 OAuth 권한 및 토큰 발급은 사용자가 직접 수행. 만료/403/네트워크 오류·응답 불명 시 자동 재게시 금지. 글쓰기 API의 서버 성공 후보는 게시글 노출·운영자 카페 관리 권한·외부 시청자 확인을 증명하지 않음. 사용자가 실제 승인하기 전에는 외부 게시가 전혀 실행되지 않음.

## 이번 회차 GitHub main 실제 제품 코드 커밋
1. `f5dbe9cfc16c0d0f7792991c16c7bc12192e3dce` — 네이버 카페 공식 OAuth 글쓰기 API 클라이언트 신규.
2. `209aa120d92f386fe362aea4d05962df3be01849` — 카페 시작/종료 SQLite 슬롯 청구·무중복·결과 장부 신규.
3. `2a1d98204896a8150679014dee98d1b28ec6611f` — 기존 OBS 승인 방송 스케줄러에 카페 독립 공지 콜백/상태 연결.
4. `d9b82011fed1b8af633410a1a44e265edae796b2` — 기존 Windows OBS 방송 GUI에 네이버 카페 입력/최종 승인/기록 조회 연결.
- **제품 소스 4커밋, 신규 Python 2개·기존 Python 수정 2개.** 본 부록/전체 인수인계 2개는 제품 소스 이후 별도 append-only 커밋으로 누적. 부록 자체를 기능 개발로 계산하지 않음.

## 남은 핵심 제품 개발 / 다음 회차
- 202절은 **공식 네이버 카페 공지 기능의 실제 코드 경로 작성**이며 AISTING 전체 개발 완료 아님. 운영자 카페 토큰이 없으므로 실계정 글쓰기·실제 게시 성공/실제 방송을 확인하지 않았음.
- 여전히 미개발/미완료: 4플랫폼 수백 명 채팅 수신·SQLite 무손실/복구·AI 실제 처리량/최종 시청자 1~3초 목표, 권리 있는 한국어 GPT-SoVITS 동일 WAV→공식 Cubism 입→OBS 영상/음성의 장시간 실제 동기/인과, OBS·공식 Cubism·GPT-SoVITS 24시간 장애 후 승인 경계 내 안전 복구, 자율 게임·콘텐츠 장기 수행, 원본 기획의 나머지 미완 기능.
- 과거 실제 로컬 AI 500건 CI `39720448468` **500/500 3초 초과**, FIFO p95 2973.875초/전체 p95 2979.984초 실패, Windows CI `39722213656` 취소를 성공으로 바꾸거나 삭제하지 않음.
- **이번 실행: 테스트 NOT_RUN; CI 조회하지 않음/미확인; Windows 10/11 네이티브 EXE·GUI NOT_RUN; 실제 OBS/공식 Cubism/한국어 GPT-SoVITS/네이버 카페/4플랫폼 계정/24시간/수백 명/시청자 수신 NOT_RUN.** API 명세 검색은 실행 검증 아님. 정상 작동/게시 성공·1~3초 성능 주장 금지.
- 다음 실행: 이 AISTING 기존 대화 유지 우선, GitHub `main` HEAD 새로 조회, 기존 원본·202절까지 인수인계 확인, **남은 핵심 제품 코드 실제 개발부터** 계속, main 비강제 커밋, 기존 인수인계 원문 끝에만 append-only. 다른 예약/프로젝트/Drive/브랜치 변경·임의 모델 교체·무단 방송/계정 사용 금지.
