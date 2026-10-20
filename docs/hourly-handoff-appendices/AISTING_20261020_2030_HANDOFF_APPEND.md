## 28. 2026-10-20 20:27 KST 예약 연속 실행 — 기존 4플랫폼 동시수신 미반영 패치 v4 보완·격리검증, GitHub 쓰기 차단 기록

### ① 원본과 사용자 지시 준수
- GitHub `junggyeol4444/AISTING` 기존 `main` HEAD **`0ec10097bd0ba37a23508749ca3b6bc1b893d3d5`** (시작/종료 재조회 동일). `docs/AISTING_HOURLY_FULL_HANDOFF.md` 100,997자/792줄 **전체**와 원본 `docs/ORIGINAL_PLAN.txt` 19,347자, `docs/ROADMAP_100.md` 34,687자, `config/roadmap.json` 19,909자, 최신 주요 소스/테스트/Windows GUI 스크립트, 최근 Actions 읽기 완료. 기존 handoff의 **1~27절(중복 25/26 번호 포함) 원문 보존**. 사용자의 원래 요구는 다중 플랫폼 중복 포함 전 메시지 수신·단일 AI FIFO·Windows EXE·캐릭터/SQLite 보존이며 독자적 새 프로그램 개발 금지.
- 이전 17:30, 18:30, 19:30 예약 산출물(특히 `AISTING_20261020_1930_개발패치_9개검사_인수인계.zip`)을 실제 열어 확인하고, 기존 5파일 **미적용 패치**를 기반으로 추가 개발. 원본 사용자 설정/SQLite/모델/OBS/방송 계정/다른 프로젝트/예약은 수정하지 않음.

### ② 이번 묶음 개발 산출물 (로컬 준비, GitHub 적용 전)
- 신규 **`AISTING_20261020_2030_pending_batch_v4.py`**: 기존 `main` 클린 체크아웃에서 `--apply`를 실행할 때만 정확히 5개 기존 파일에 누적 패치를 적용하는 보존형 스크립트. 기본 실행은 변경 없는 dry-run. 기존 메인/캐릭터/SQLite 삭제나 새 브랜치 생성/force push 없음.
  1. `src/ai_broadcaster/multiplatform_readonly.py`: `MultiPlatformReadOnlySession` 추가, 4개 기존 읽기 전용 수신기를 **하나의 직렬 GUI/AI FIFO**로 연결, 별개 채팅 중복 보존/플랫폼 ID 확인/채널 전체 사전 검증/오류 격리/Stop 후 늦은 채팅 폐기/동시 재시작 거부. 이번 v4에서 `stop()`과 각 리더 스레드 시작을 **동일 잠금**으로 동기화해 Stop 이후 새로운 수신 스레드 시작 경합을 방지, 중지된 비정상 네트워크 리더가 종료되지 않아도 코디네이터가 최대 3초 추가 대기 후 해제되도록 개선, `ready/connected` 상태 문자열에 서버가 보낸 비밀 URL/토큰이 섞이지 않도록 상태 일반화. YouTube 페이지 토큰 최대 2,048자 사전 차단. **실제 YouTube 인증/라이브 수신은 검증하지 못함.**
  2. `src/ai_broadcaster/desktop_chat_tab.py`: 기존 4플랫폼 선택에 `전체`를 추가, 방송 설정에서 선택한 플랫폼의 개별 채널 2줄 입력, 기존 Ollama/공식 Live2D 한 세션 AI 응답 FIFO와 연결. 이번 v4는 확장 입력란을 **기존 공개채팅 줄과 YouTube 키 줄 사이**에 삽입해 기존 대화창 맨 위로 밀리지 않도록 조정, 저장 플랫폼 식별자 사전 검증. 중복 메시지 필터/인위적 응답 지연/무단 채팅 게시 없음.
  3. `tests/test_aisting_multiplatform_readonly.py`: 네 플랫폼 중복 채팅, 오류 격리, 비밀 키 보호, 재실행 거부, 제한 시간/채널 입력 거부, 4개 플랫폼 500건씩 **2,000건 순서 보존**, Stop 중 늦은 이벤트 차단, 한 리더 Stop 실패 시 나머지 Stop, YouTube 토큰 크기 제한 테스트를 포함하도록 증강.
  4. `tests/test_aisting_twitch_ai_integration.py`: 네 플랫폼 중복 한국어 문장을 기존 단일 Ollama AI 응답 FIFO가 전부 순서대로 처리하고 플랫폼 이름을 올바르게 기록하는 테스트 추가.
  5. `scripts/gui_official_pipeline_click_windows.py`: **실제 Windows 네이티브 Tk** GUI의 `전체` 선택·4개 채널 입력란 노출/숨김, 비어 있는 채널 상태에서 연결 버튼을 눌러도 네트워크 수신기가 생성되지 않는지 확인하는 검증 코드 추가. **이 테스트 코드를 실제 Windows runner에서 실행한 것은 아님.**
- 이 파일들은 `AISTING_20261020_2030_개발패치_v4_격리12검사_인수인계.zip`에 포함. 기존 19:30 v3 패치도 백업으로 유지.

### ③ 검증 결과와 GitHub 접근 경계
- 최신 GitHub `main` 5파일에 필요한 **16개 핵심 문자열 앵커가 각각 정확히 1회 존재함을 GitHub 읽기 연결로 확인**. 단, 이는 실제 패치 실행이나 전체 테스트가 아님.
- Python 문법: v4 패치 스크립트 `py_compile` 성공, 삽입할 `MULTI_SESSION`, `UNIT_TESTS`, `AI_TEST` AST 파싱 성공.
- **로컬 격리 모의 수신기 테스트 12개 전부 통과**. 실제 4개 플랫폼 각 500건, 합계 2,000건의 모의 이벤트 FIFO 보존; 중지/오류 격리/비밀 토큰 상태 출력 방지/재시작 경합/비정상 Stop 3초 제한 확인. **실제 저장소 전체 회귀, Windows EXE, GUI, OBS, GPT-SoVITS, YouTube API 인증 테스트는 0건.** 격리 테스트를 제품 성공으로 표기 금지.
- GitHub `create_blob` **짧은 비실행 중간 설명 문자열**은 blob SHA `01cde23c7ffc08f6cb2f88ad48bb054cc8025167` 생성에 성공. 그러나 실제 2파일 소스 묶음으로 `create_blob`/적용을 요청한 후 `This tool call was blocked by OpenAI's safety checks`를 받음. 권한 거부를 우회하지 않았으며 **main 코드 커밋 0건, 새 CI 0건, 새 EXE 0건, 원격 인수인계 갱신 0건**. 위 blob은 Git 트리/브랜치에 연결되지 않아 main 코드 변경을 의미하지 않음. 원격 저장소 HEAD와 최근 CI 상태 재조회로 변경 없음 확인.
- 기존 `main` 기준 최근 CI `39391243912`/`39391243822` 모두 성공이지만 **이번 v4의 테스트가 아니므로 신규 기능 검증에 사용 금지**.
- 셸 raw GitHub DNS 접근 실패, 웹 캐시 미스, GitHub 읽기 connector는 정상. 권한/안전 검사 차단 우회·Drive 연결/새 브랜치/강제푸시 금지.

### ④ 미완료와 다음 예약 회차의 우선순위
1. GitHub 안전·권한 내 허용된 기존 `main` 경로에서 실제 v4 묶음 5파일 적용을 **검증할 수 있을 때만** 실행. 중간 소규모 CI 반복 금지: 복수 기능 개발 후 전량 회귀 + Windows EXE/GUI + 가능한 실제 Ollama/OBS/공개 채팅 검사; 실패 시 수정 후 전량 재검증. 안전 차단을 임의로 우회하지 말 것.
2. 실제 소유 GPT-SoVITS 모델/한국어 참조 음성으로 공식 Open-LLM-VTuber/Cubism 입 움직임과 OBS 같은 발화 영상·음성 전체 E2E **미실증**. 실제 사용자 YouTube API 키/활성 방송 인증 채팅, 4플랫폼 수백명 1~3초, 24시간 실운용 **미실증**. 데이터·권리·장비 없으면 가짜 성공 만들지 않기.
3. 원본 기획 100단계 `pending`을 CI PASS만으로 임의 완료 처리하지 말 것. 기존 캐릭터 이름·성격·말투, SQLite 기억, 방송/OBS 설정, 다른 프로젝트 예약 유지.
4. 원격 쓰기 가능해지면 본 기존 `docs/AISTING_HOURLY_FULL_HANDOFF.md` **1~27절 원문을 하나도 삭제·요약하지 말고 28절로 이 내용 추가**. 이후 실제 변경/검증/EXE/오류 수정 내역을 후속 절에 누적. 이전 예약 대화와 실제 결과 출력 라우팅은 확인되지 않으면 단정 금지.