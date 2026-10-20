# AISTING 누적 인수인계 28절 추가 초안 — 2026-10-20 19:30 KST

**중요:** 기존 GitHub `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~27절 전체를 삭제·축약·대체하지 말고 **이 절만 뒤에 추가**한다. 이번 회차 GitHub 쓰기 안전 차단으로 이 절을 원격에 커밋하지 못했다. 다음 회차에서 원본을 먼저 확인하고 중복/충돌 없이 누적할 것.

## 28. 2026-10-20 19:30 KST — 4플랫폼 기존 패치 보강·오프라인 검증·원격 반영 대기

### ① 원본/기준선 확인
- 저장소: `junggyeol4444/AISTING`, **기존 `main`만 사용**. 이번 회차 처음과 마지막에 확인한 HEAD: `0ec10097bd0ba37a23508749ca3b6bc1b893d3d5`.
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 기존 **1~27절 원문**, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`을 GitHub에서 확인. 원본 100단계 pending 및 사용자 승인 미완료는 임의로 변경하지 않음.
- 마지막 실제 기능 코드 커밋 `a5c074f3c5ef1ce3e955c80d0dd8b9929a6fe2ed`. **그 코드의** 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39388635212 = 2,421 tests, skipped 2, 실패 0. **그 코드의** Windows 5 jobs PASS https://github.com/junggyeol4444/AISTING/actions/runs/39388635145, EXE artifact ID `12248437439`, ZIP SHA-256 `8dfae3480593e34d489f61fd4e11faf38312824074ecdebc964cd9ec3fe91f97`. 현재 HEAD 문서 변경 후 Actions 39391243912/39391243822도 성공이지만 **이번 미반영 패치에 대한 검증이 아니다**.

### ② 여러 기능 먼저 묶음 개발 — 현재는 로컬 패치
- 18:30 회차 보존 ZIP `AISTING_20261020_1830_개발패치_검증_인수인계.zip`의 기존 5파일 묶음을 읽고 **v3 패치**로 확장. `AISTING_20261020_1930_pending_batch_v3.py`는 기본 dry-run, 기존 clean `main` checkout에만 `--apply`를 허용하는 패치 도구. 임의로 사용자 설정/SQLite/OBS/Live2D/음성 모델을 수정하지 않음.
- 대상 5파일: `src/ai_broadcaster/multiplatform_readonly.py`, `src/ai_broadcaster/desktop_chat_tab.py`, `tests/test_aisting_multiplatform_readonly.py`, `tests/test_aisting_twitch_ai_integration.py`, `scripts/gui_official_pipeline_click_windows.py`.
- 묶음 기능: Twitch/CHZZK/SOOP/YouTube의 운영자 선택 1~4개 읽기 전용 채팅을 독립 리더로 실행, **기존 단일 GUI/AI FIFO**에 전 메시지(동일 문장도 개별 이벤트) 전달, 오류 플랫폼 격리, 전체 Stop, YouTube API 키 비노출, YouTube 비정상 페이지 토큰 2,048자 초과 사전 차단. 네이티브 Tk `전체` 선택과 4개 채널 입력, 선택 해제 시 필드 숨김, 기존 AI·캐릭터/SQLite 보존, Windows 실제 Tk 검사 코드 포함.
- **이번 v3 추가 개발:** 동일 세션 객체가 한 번 종료된 뒤 `run()`을 다시 호출해 과거 이벤트를 재처리하는 위험을 차단하는 `_started_once` 상태; `max_seconds` 음수/NaN/무한/문자/불리언을 리더 실행 전에 거부, 0초는 외부 접속 시작하지 않음. 한 리더의 Stop 예외가 다른 리더의 Stop을 막지 않음.

### ③ 이번 회차 검증 결과와 한계
- GitHub connector `fetch`/`fetch_file`로 실제 5개 원본 파일 재조회, 기존 v2/v3 패치의 각 교체 앵커가 최신 main에서 **각각 정확히 1회** 발견됨. 새 기능 `MultiPlatformReadOnlySession`은 아직 main에 존재하지 않음.
- v3 패치 Python `py_compile` PASS, 다중 리더 클래스/추가 회귀 테스트 조각 Python AST PASS.
- `AISTING_20261020_1930_offline_patch_test_v3.py`: **격리 오프라인 테스트 9개 PASS**, 실패 0. 3플랫폼 동일 문장 각 50개 총 150개, 4플랫폼 각 500개 총 2,000개 **모의** FIFO 이벤트(각 플랫폼 순서/누락 없음), 한 플랫폼 예외와 API 키 은닉, 잘못된 설정/시간 거부, Stop-before-run/Stop-during-run, 한 리더 Stop 예외 후 다른 리더 정상 종료, 실행 중 이중 run/종료 후 재실행 차단을 검사.
- 이 결과는 **fake reader/격리 로컬 테스트**. GitHub 최신 소스에 실제 적용·전체 회귀·Windows EXE 빌드·실제 GUI 버튼·Ollama/OBS/실제 공개 채팅 연동 검증을 하지 못함. 기존 CI PASS를 이번 v3 패치의 PASS로 표시 금지.
- 원격 GitHub 코드 5파일의 한 번에 fast-forward 커밋 시도 및 본 인수인계 문서 append 시도는 **OpenAI 도구 안전 검사에서 차단**. 실제 `main` 코드/문서 변경 **없음**. container의 `git ls-remote`는 DNS에서 github.com 해석 불가. 안전/권한 거부를 무단 우회하지 않음. 새 브랜치/force push/롤백/외부 드라이브 없음.

### ④ 최우선 미완료 및 다음 회차
1. 다음 회차에 본 GitHub 문서 1~27절과 이후 절 **전부 원문**, 원본 기획·로드맵, 최신 main/Actions, 이 로컬 ZIP을 읽고 이전 변경과 충돌 여부부터 확인. 원격 쓰기가 정당하게 허용될 때 **v3의 복수 기능을 한 묶음으로** 기존 main에 반영.
2. 전체 코드 묶음 개발 완료 후 **최신 전체 회귀 + Windows x64 EXE 빌드·실제 Tk GUI 클릭 + 가능한 Ollama/OBS/공개 채팅 통합** 한꺼번에 검증, 오류 수정 시 수정된 최신 코드 **전체 재검증**. 안전 검사/권한 거부 무단 우회 금지.
3. 권리 확보한 실제 GPT-SoVITS 한국어 참조 음성 합성 → 공식 Open-LLM-VTuber/Live2D Cubism 해당 발화 입 움직임 → OBS 동일 발화 오디오·영상, 실제 소유 YouTube API 활성 방송 채팅 인증 수신, 4플랫폼 실제 100~500명·1~3초·24시간 안정 운용은 **여전히 미실증/미완료**. 실제 사용자 모델·계정·Windows PC에 무단 접근/학습/송출/녹화/채팅 발신 금지.
4. 기존 캐릭터 이름/말투/성격·SQLite/설정/원본 기획/100단계 pending 보존, Google Drive 및 외부 드라이브 연결 요구 금지. 다른 프로젝트 예약·비활성 과거 예약 변경 금지.