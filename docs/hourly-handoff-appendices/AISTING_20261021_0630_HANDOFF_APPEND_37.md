## 37. 2026-10-21 06:30 KST — 기존 4플랫폼 Windows GUI 통합 v13 묶음 개발, GitHub 안전 차단, 검증 수준 분리

### ① 선행 원본 확인 및 기준선
- 원본 GitHub `junggyeol4444/AISTING`, 오직 `main`. 커넥터에서 `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~27절(100,997자), `docs/ORIGINAL_PLAN.txt`(19,347자), `docs/ROADMAP_100.md`(34,687자), `config/roadmap.json`(19,909자)을 읽고 절별 요구사항과 검증 경계를 확인했다. 이전 회차 ZIP의 28~36절 원문을 이번 ZIP에 함께 보존했다.
- 시작 및 종료 확인 `main` HEAD **`2efc6a0627327e789e72c45e3976bec1af48b534`**, 기준 트리 `9894c598fd9ce7383a87a65811f9b21b917d3f0d`. 원격 5파일을 재조회했고 blob SHA는 이전 36절과 일치했다.
- 기존 최신 실제 `main` CI만 성공: 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39439480014 (`completed/success`, 이전 회차 기록상 2,425개/2 skipped), Windows https://github.com/junggyeol4444/AISTING/actions/runs/39439480139 (`completed/success`, 5 jobs: windows-exe, ollama-real-local-e2e, obs-real-readonly, twitch-public-readonly, korean-public-chat-readonly). 이전 HEAD에서 생성된 ZIP artifact `AISTING-Windows-EXE-integrated` ID `12273505006`, 19,746,042 bytes, ZIP digest `sha256:6d1100d1bea4efc08c0e3d01719c56a7fd7562ee33c18aec8a3e8fd6ce558cb3`, 만료 2026-11-19T14:29:55Z. **이번 v13 검증이 아님**.

### ② 개발한 복수 기능 묶음 — 원본 소스용 미반영 v13
- `AISTING_20261021_0630_pending_batch_v13.py`: 기존 5파일을 보존형으로 수정하도록 만든 v12 누적 패치를 확장. 대상 `src/ai_broadcaster/multi_platform_session.py`, `src/ai_broadcaster/desktop_chat_tab.py`, `tests/test_aisting_multiplatform_readonly.py`, `tests/test_aisting_twitch_ai_integration.py`, `scripts/gui_official_pipeline_click_windows.py`.
- 기존 4플랫폼 동시 수신→한 AI FIFO, 동일 채팅 전부 유지, 플랫폼별 순서, 공통 3초 수신 종료, 병렬 0.5초 소켓 닫기, 토큰/비밀정보 오류 메시지 차단, Windows GUI `전체`/4채널 선택·연결 검사를 그대로 포함.
- v13 신규 ① **중복 Stop 호출 시 중복 종료 스레드 생성 방지** (`_stop.is_set()`이면 조기 반환). ② **저장된 플랫폼 목록의 비정상 자료형·중복·미지원 코드에 대한 네트워크 생성 전 차단. 구현 중 중첩 리스트(`[[]]`)에 `set()`을 먼저 호출하면 TypeError가 나는 결함을 발견해, **항목 자료형을 먼저 검사한 후에만 set() 중복 검사**하도록 수정하고 `[[]]`도 계획 회귀 사례에 포함**. ③ **실제 Windows 1280×768 Tk 창에서 4플랫폼 채널 입력란을 표시한 상태에서도 기존 공식 AI·Live2D·OBS 검사 버튼이 화면 안에 남는지 검사 추가**. ④ 기존 단일 AI FIFO 중복 메시지/4플랫폼/설정 오류 차단/Stop 재진입 회귀검사 강화.
- `AISTING_20261021_0630_offline_tests_v13.py`: 모의 reader 격리 환경에서 Stop 재호출·Stop 이전/이후 실행 방지 검사 2개 추가. 실제 외부 API/음성/OBS/계정 로그인/방송/녹화 없음. 기존 캐릭터·SQLite·원본 설정 변경 없음.

### ③ GitHub 쓰기 시도 및 차단
- GitHub connector `fetch_file`, `fetch_blob`, Git ref/commit/tree 조회 성공. 기존 v11 미참조 blob `44fe275eb2f5a22a50782787d22cb6fe6e8a6029`, `57f03a642875ecd250d35fddb720af0ff1d97ae3`의 실제 내용 확인. 특히 두 번째 GUI blob은 **v12 추가 오류 차단이 아직 없는 v11 수준**으로 확인했으므로 v12 구현 완료라고 잘못 취급하지 않았다.
- 기존 원격 5파일에서 정확한 문자열 앵커를 검사하고, 4플랫폼 GUI·FIFO·Windows Tk 통합 테스트와 오류 차단을 포함한 **5파일 묶음 Git 트리**를 합법 GitHub `create_tree`로 한 번 구성 요청. 응답 **`This tool call was blocked by OpenAI's safety checks. Please double check what you are sending.`**. 차단을 우회하지 않고 원격 쓰기 중단. `create_commit`, `update_ref`, GitHub handoff 원문 갱신 **미실행**. 실제 `main` HEAD 변화 없음. 생성된 트리/커밋/CI/artifact 없음.
- 컨테이너 직접 git 접속은 `Could not resolve host: github.com`으로 실패. GitHub connector 읽기는 정상, 따라서 저장소 접근 전체가 불가능하다는 주장은 하지 않는다. 다른 프로젝트나 예약 변경 없음.

### ④ 검증 및 정확한 미검증
- 기존 v12 격리 테스트 **17/17 PASS**를 직접 재실행. 신규 v13 격리 테스트 **19/19 PASS, 실패 0** (이 19개는 `MULTI_SESSION`의 독립 격리 모의 버전 테스트이며 원격 `main` 전체 테스트가 아님).
- v13 패치 스크립트/격리 테스트 `py_compile` PASS, 내부 다중 수신 세션 코드/신규 회귀 테스트 조각 `ast.parse` PASS. 5개 파일 실제 원본에 패치를 적용해 최신 전체 회귀를 돌리거나 Windows EXE/Tk 버튼을 실기 실행한 **결과는 없다**. 원격 차단 때문에 v13 통합 CI **미실행**. 이전 `main` CI 성공을 v13 성공으로 전용하지 않는다.
- 실제 사용자 권리 확인 GPT-SoVITS 한국어 음성→공식 Live2D/Cubism 실제 립싱크→OBS 동일 발화 오디오/영상 Windows E2E, 실제 소유 YouTube API 인증 활성 라이브 채팅, 4플랫폼 동시 100~500명·1~3초·24시간 운영은 계속 **미실증**. 사용자 계정/PC/음성 자산/방송/채팅 발신 무단 접근 없음.

### ⑤ 다음 회차 반드시 이어서
1. 이 문서 1~27절 원문, 별도 ZIP 28~37절 원문, 원본 기획/로드맵/최신 `main` 확인. GitHub 차단을 권한 없는 방식으로 우회하지 않는다.
2. 원격 권한이 허용되면 v13 **5개 파일 묶음**을 실제 기존 `main`에 fast-forward 반영하고, 필요시 충돌을 병합. 새 브랜치·force push·원본 설정/SQLite 파괴 금지.
3. 그 후 **최신 전체 회귀 + Windows 네이티브 EXE/GUI + 가능한 실제 OBS/Ollama/공개 채팅** 일괄 검증. 오류 발견 시 수정 후 동일 최신 코드로 전체 재검증. 4플랫폼 입력란으로 기존 버튼이 가려지면 Windows 실제 GUI 증빙에 따라 레이아웃 수정.
4. 실모델/권리/Windows 장비가 없으면 TTS→Cubism→OBS 동일 발화, 실제 YouTube 인증 및 24시간 고부하 운영은 미실증으로 남긴다. 새 코드 커밋·CI·artifact·검증 수준을 정확히 기록하고 기존 인수인계 원문 삭제 없이 38절을 추가한다. 다른 프로젝트/기존 예약 건드리지 않는다.