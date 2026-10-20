## 28. 2026-10-20 21:30 KST 자동화 회차 — 4플랫폼 수신기·YouTube 토큰 안전 개선, GitHub 커밋 생성/브랜치 반영 차단

### 선행 확인
- GitHub `junggyeol4444/AISTING` main HEAD `0ec10097bd0ba37a23508749ca3b6bc1b893d3d5` (작업 시작·종료 시 동일), tree `7683ae131f29cced1d34049b68c4262f9989a075`.
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 원문 100,997자, 1~27절(25/26 중복 번호 포함), `docs/ORIGINAL_PLAN.txt` 19,347자, `docs/ROADMAP_100.md` 34,687자, `config/roadmap.json` 19,909자 및 최신 소스/테스트/Actions 확인. 과거 문서와 로드맵의 상태는 바꾸지 않음.
- 시작 시 최신 `main`의 Actions 39391243912, 39391243822 모두 `completed/success`. 이것은 이번 코드에 대한 CI가 아님.
- 이전 20:30 미반영 ZIP `AISTING_20261020_2030_개발패치_v4_격리12검사_인수인계.zip`을 열어 v4 변경 계획/격리 테스트와 실제 최신 원본의 앵커를 비교. 기존 소스 5파일의 수정 지점 16개 모두 원본에서 각 1회씩 확인.

### 이번 회차 실제 코드 개발
1. 기존 소스 `src/ai_broadcaster/multiplatform_readonly.py`에 YouTube 비정상 `nextPageToken` 2048자 초과를 채팅 전달 전에 거부하는 변경을 준비. 기존 메시지 ID 중복 방지/정상 FIFO 유지.
2. 새 `src/ai_broadcaster/multi_platform_session.py`: 원래 AISTING 읽기 전용 플랫폼별 reader를 동시에 실행하고, 한 직렬 callback으로 chat을 전달하는 4플랫폼 조정기. 플랫폼 식별/중복 문장 보존, Stop 후 늦은 이벤트 차단, 읽기 오류 정보에서 인증정보 제거, 플랫폼 하나 종료 오류가 나도 나머지 종료, 재실행 차단 및 3초 제한된 종료 대기. 이 모듈은 현재 main GUI에 아직 연결되지 않았으므로 사용자 화면에서 '전체' 기능이 작동한다고 주장 금지.
3. 새 `tests/test_aisting_multi_platform_session.py`: 2,000건/4플랫폼 순서 보존과 재실행/설정 거부 테스트 2개.
4. 새 `tests/test_aisting_youtube_token_length.py`: 비정상 토큰 차단과 HTTP 도중 Stop시 늦은 메시지 억제 테스트 2개.
5. 기존 GUI/Windows 실제 클릭 검사 2파일의 v4 패치 적용도 시도했으나 원본 대형 파일 내용을 포함한 GitHub 쓰기가 OpenAI safety checks에 차단됨. 기존 v4 ZIP에 미반영 수정안과 격리 테스트 12개를 보존.

### GitHub 객체 및 안전 차단 결과
- `create_blob` 성공: 새 멀티 플랫폼 조정기 SHA `fab05ccb198b6fbb0634deb9bdca347bd4cab246`, 신규 테스트 SHA `25eacf4a0d9c5d43a9e45e5d79e94aedede5900a`, YouTube 테스트 SHA `bb396314181a276b3a0d360e8a1f7877e0299e9a`.
- `create_tree` 성공: 기존 YouTube 파일 수정 포함 최초 tree `c9bc61a68da639f93c78ef112484f153035357ec`, 조정기와 신규 테스트까지 묶은 최종 tree `9894c598fd9ce7383a87a65811f9b21b917d3f0d`.
- `create_commit` 성공: **`2efc6a0627327e789e72c45e3976bec1af48b534`** (부모 `0ec10097bd0ba37a23508749ca3b6bc1b893d3d5`). GitHub 객체로 존재 확인.
- `update_ref(main, force=false, expected_sha=0ec10097...)` 두 번 시도했으나 **`This tool call was blocked by OpenAI's safety checks`**. 다른 경로인 `create_blob`/`create_tree`는 일부 성공, 기존 대형 소스의 `create_blob`/`create_tree` 쓰기는 차단. 권한/안전 차단을 우회하지 않았음.
- 따라서 **실제 main에는 이번 변경 0개**. 위 커밋은 현재 main에서 도달할 수 없는 미반영 Git 객체이므로 적용 성공/CI PASS로 주장 금지. 마지막 main HEAD `0ec10097bd0ba37a23508749ca3b6bc1b893d3d5` 재확인.

### 검사/미완료 경계
- 이전 v4 ZIP의 독립 fake reader 12개 격리 테스트를 이번 회차에서 재실행하여 **12/12 PASS (3.221s)**. 이는 새 미반영 GitHub tree의 전체 CI 또는 실제 방송/4플랫폼 실연동 증거가 아님.
- 이번 변경으로 새 GitHub Actions 실행 없음. Windows EXE/GUI 전체 회귀 및 사용자 PC 실사 검증 미수행. 과거 Actions 39391243912/39391243822는 현재 main 이전 코드에 대한 성공이며 신규 수정 검증과 구분.
- 정당한 GPT-SoVITS 모델 한국어 실제 음성 합성 → 공식 Cubism 립싱크 → OBS 동일 발화 오디오/영상 전체 실증, 소유 YouTube API 활성 라이브 인증, 100~500명·1~3초·24시간 실운용 모두 미실증.

### 다음 회차 필수
1. 이 GitHub 원문 1~27절 및 이후 추가된 절 전체, 원본 기획·100단계, 최신 main/CI부터 재확인. 이번 `28절`은 로컬 ZIP에만 있고 아직 GitHub handoff에 append되지 않음.
2. GitHub 안전 차단은 우회하지 말고 권한 내 정상 쓰기가 가능해졌는지 확인. `2efc6a...`가 아직 main 부모의 보존형 fast-forward인지 반드시 재검증; 현재 main이 바뀌었다면 절대 이전 SHA를 강제로 덮지 말고 새 HEAD를 기반으로 내용 조정.
3. v4 GUI/Windows 패치와 이번 4플랫폼 수신기/YouTube 수정 등 **여러 기능을 먼저 함께 통합 구현**하고, 한 번에 전체 회귀 + Windows EXE/실제 Tk GUI/가능한 OBS·Ollama·공개 채팅 검증. 실패 시 수정한 최신 전체 다시 검사.
4. 원본 캐릭터/SQLite/OBS/모델/계정/예약 및 타 프로젝트는 건드리지 말 것. 실제 방송/녹화/채팅 발신/무단 로그인·음성 훈련/Google Drive 연결 금지. 원본 로드맵 pending 승인 임의 변경 금지.
5. 기존 GitHub 인수인계 원문을 삭제/요약하지 말고 **추가 절만 append**, 실제 commit·CI·artifact·미실증·차단 기록을 누적. 사용자에게 성공을 꾸미지 말 것.