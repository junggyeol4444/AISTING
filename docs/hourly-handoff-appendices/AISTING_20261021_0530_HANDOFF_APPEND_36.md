## 36. 2026-10-21 05:30 KST — 기존 4플랫폼/Windows Tk GUI 통합 v12 묶음 개발, GitHub 안전 차단 및 검증 한계

### ① 원본 및 최신 원격 읽기
- 원본 저장소 `junggyeol4444/AISTING`, `main`만 사용. GitHub 커넥터에서 `docs/AISTING_HOURLY_FULL_HANDOFF.md` **1~27절 원문**(100,997자), `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 최신 코드/테스트/Windows GUI 스크립트, Actions 조회 성공. 이전 ZIP의 **28~35절 인수인계 추가분**도 이어받아 이번 ZIP에 원문 그대로 동봉.
- 원격 `main` HEAD `2efc6a0627327e789e72c45e3976bec1af48b534`(2026-10-21 05:30 KST 확인), base tree `9894c598fd9ce7383a87a65811f9b21b917d3f0d`.
- 실제 원격 5파일 blob SHA: `src/ai_broadcaster/multi_platform_session.py`=`fab05ccb198b6fbb0634deb9bdca347bd4cab246`; `src/ai_broadcaster/desktop_chat_tab.py`=`bdfd0512ad0043a35d1925db17b148cc46159440`; `tests/test_aisting_multiplatform_readonly.py`=`d92b63ceb096031402ed240d3e68b44c2c71abdc`; `tests/test_aisting_twitch_ai_integration.py`=`013fefad57c339b24f9420632434ded6436046ca`; `scripts/gui_official_pipeline_click_windows.py`=`eb0ca326428994b795b7f2b5693cf903d137a14e`.
- `main` 마지막 CI: 전체 회귀 `https://github.com/junggyeol4444/AISTING/actions/runs/39439480014`, Windows 통합 `https://github.com/junggyeol4444/AISTING/actions/runs/39439480139` 둘 다 `completed/success`, 코드 SHA **2efc6a0**. 이는 **이번 v12 미반영 코드의 검증이 아니다**.

### ② 실제 작업: 복수 기능 일괄 수정안
- 기존 v11의 **4플랫폼 GUI 선택/각 채널 입력 → 단일 AI FIFO**, 수신기 4개 Stop 병렬 처리 및 공통 종료 제한, 사용자 계정/토큰이 포함된 예외의 GUI 노출 차단, Windows 네이티브 GUI 선택 검사를 전부 보존.
- `AISTING_20261021_0530_pending_batch_v12.py` 추가 수정: 저장된 플랫폼 설정 로드가 `ValueError/OSError/KeyError/TypeError/RuntimeError`를 발생시켜도 예외 메시지의 비밀정보를 GUI에 표시하지 않고 연결을 거부. 읽기 전용 수신기 생성 중 발생한 `OSError/RuntimeError`도 기존 `ValueError/TypeError`와 함께 비밀정보를 표시하지 않고 거부. 기존 캐릭터/SQLite/기타 사용자 설정 수정 없음.
- 이 v12는 **기존 5개 소스/테스트 파일에 적용하는 보존형 오프라인 패치**. 새 독립 프로그램/브랜치/HTML 대체가 아니다. 기본 dry-run; 실제 `main` SHA와 clean checkout 확인 후에만 `--apply` 가능하도록 기존 보호 유지.

### ③ GitHub 쓰기 시도 및 차단 — 절대 반영 성공으로 주장 금지
- GitHub 커넥터로 최신 5파일을 읽고, 정확한 소스 anchor 1회씩 일치하는지 검증한 후 GUI/Stop/오류 차단/테스트/Windows GUI 등 5파일 묶음 변경 내용을 구성.
- `create_blob` 두 개 성공: `multi_platform_session.py` 신규 미참조 blob `44fe275eb2f5a22a50782787d22cb6fe6e8a6029`; `desktop_chat_tab.py` 신규 미참조 blob `57f03a642875ecd250d35fddb720af0ff1d97ae3`.
- 세 번째 `tests/test_aisting_multiplatform_readonly.py` blob 생성에서 **"This tool call was blocked by OpenAI's safety checks"** 발생. 안전 차단을 우회하지 않고 쓰기 중단. `create_tree`, `create_commit`, `update_ref` **미실행**. 위 두 blob은 브랜치에 연결되지 않았으며 **`main`은 변경되지 않음**. 이전에 준비한 원격 5파일 내용과 이번 v12 오프라인 스크립트는 완전히 동일한 빌드로 검증된 것이 아니므로 혼동 금지.
- 별도 컨테이너 `git ls-remote`는 DNS `Could not resolve host: github.com`으로 실패. GitHub connector 읽기는 성공했으므로 저장소가 없는 것이 아님. 안전 차단을 다른 호출로 우회하지 않음.

### ④ 실제 실행한 검증과 미실행 구분
- 기존 v11 격리 모의 테스트 **17개 통과, 실패 0**, 4개 플랫폼 2,000건 FIFO/중복, 전역 Stop 3초, 차단된 stop() 병렬 0.5초, 비밀정보 노출 방지 등. 새 v12 패치에 대해 동일 격리 테스트 **17개 재실행 PASS** (`AISTING_20261021_0530_offline_tests_v12.log`).
- v12 패치 스크립트 `python -m py_compile` 통과. v12의 추가 GUI 오류 처리 2개 경로는 **Windows 네이티브 Tk 실기 검증 미실행**. 모의 테스트 통과를 새 코드의 전체 회귀 성공으로 주장하지 않는다.
- 최신 전체 main 회귀, 새 Windows EXE 빌드/GUI 클릭, 실제 Ollama/OBS/4플랫폼 공개 연동 검사는 **v12에 대해 미실행**(원격 미반영, Windows 실행 환경 없음).
- 실제 권리 확인 GPT-SoVITS 한국어 합성 → 공식 Cubism 해당 발화 립싱크 → OBS 같은 발화 오디오/영상, YouTube 소유 API 인증 수신, 100~500명·1~3초·24시간 실운용은 **계속 미실증**. 임의 음성 모델 훈련·실방송·녹화·채팅 발신·계정 로그인/외부 자료 전송 없음.

### ⑤ 다음 회차 최우선
1. 기존 1~27절과 28~36절 전체, 원본 기획/로드맵/현재 main을 확인. 다른 프로젝트/비활성 예약 건드리지 않음.
2. 안전 정책/권한이 허용되는 범위에서만 기존 5파일 v12 **복수 기능 일괄 반영** 가능성 확인. 원격 HEAD가 변했으면 기존 소스와 병합 검토 후 수정, 강제 푸시/브랜치 생성 금지. 차단을 무단 우회하지 말 것.
3. 일괄 구현 완료 후 전체 회귀+Windows EXE/실제 Tk GUI+가능한 공개 읽기/OBS/Ollama를 한꺼번에 실행하고, 오류 수정 뒤 최신 전체 재검증. 결과/커밋/CI/artifact와 미실증을 구분.
4. 원본 1~27절 및 28~36절을 삭제/축약하지 말고 새 절을 누적. 실제 음성/YouTube/Windows 사용권한 없으면 실증 미완료 유지.