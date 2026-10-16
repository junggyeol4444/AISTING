# AISTING 기존 소스 수정 패키지 v9 — 2026-10-15 (KST)

## 이번 회차 실제 변경

- `fetch_existing_main_snapshot_readonly.py` **신규 작성**. 기존 AISTING GitHub `main`의 확인된 커밋 `2269205998201165e024a22d0adef576e6cac0c6`을 기준으로, 전체 원본을 **새 로컬 경로에만** 보존하는 소스 확보 도구. GitHub 공개 `codeload.github.com`에 HTTPS **GET만** 사용하며 GitHub 쓰기·로그인·설치·모델/플러그인 다운로드·송출을 실행하지 않는다. 기본 실행은 조회 안내만 출력하며 **네트워크 요청도 하지 않는다**. 실제 소스 수신은 명시적인 `--fetch` 옵션이 있을 때만 시도한다.
- `--fetch`의 보호: 고정 커밋 ZIP 루트 확인, 필수 원본 파일 7종 존재 확인, 원본 `desktop.py` Git blob SHA `a5df12a74a27a5a50657da9c968253859b98b8ed` 대조, ZIP 경로 이동(`..`)·심볼릭 링크·특수 파일·Windows 파일 이름 충돌·기존 대상 덮어쓰기 차단, 크기/파일 수 상한, ZIP CRC 및 추출 크기 확인, 실패 시 불완전한 새 사본 제거, 파일별 SHA-256과 아카이브 SHA-256 및 고정 커밋 기록.
- `tests/test_v9_readonly_source_snapshot.py` **신규 작성**: 작은 임시 소스 ZIP으로 파일 바이트 보존·원본 보호·필수 파일 누락·SHA 불일치·경로 이동·심볼릭 링크·대소문자 충돌·잘못된 커밋·파일/디렉터리 충돌을 보조 검사. **실제 AISTING 전체 원본을 내려받아 시험한 것은 아니다.**
- `build_existing_windows.ps1`: 새 빌드 결과물 폴더 표기를 `dist-local-revision-v9-*`로 변경하여 이전 v8 결과물을 덮어쓰지 않도록 유지. 실제 Windows 빌드는 미수행.
- `README_기존프로그램_수정안내.md`에 소스 확보 및 기존 사본 패치 절차와 승인 경계 추가. 기존 v8 코드·기능·설정·기억·100단계 기록은 삭제하지 않았다.

## 실제 조회 및 검증 증거

- GitHub 커넥터 **READ ONLY**로 `main`의 현재 참조 커밋 `2269205998201165e024a22d0adef576e6cac0c6`을 확인하고, 해당 커밋의 트리 1,112개 항목 / 파일 1,103개 / GitHub API 표시 합계 8,142,093바이트 및 `desktop.py` 원본 blob SHA를 재확인했다. GitHub 파일을 쓰거나 커밋하지 않았다.
- 로컬 `/mnt/data`에 v8 패키지가 실제 존재함을 확인하고 압축 해제한 후 수정했다. v9 보조 단위/보호 검사 **60개 통과**(`python -m unittest discover -s tests -p 'test_*.py' -q`), Linux Xvfb 실제 Tk UI 레이아웃 검사 통과. ZIP 무결성 및 v9 패키지 SHA-256 검사는 별도 수행한다.
- **전체 소스 실제 확보 실패/미완료**: 이 실행 환경의 `api.github.com`과 `raw.githubusercontent.com` DNS 해석이 실패했다. 따라서 고정 커밋 원본 ZIP을 이 로컬 환경으로 실제 다운로드·복원하지 않았으며, `--fetch`도 실행하지 않았다. GitHub 커넥터의 읽기 전용 트리 조회는 로컬 파일 복원이 아니다.

## 실제 미완료

- 기존 AISTING 전체 원본에 v9 패치를 적용한 통합 회귀, 기존 사용자 데이터/캐릭터 확정 저장·재시작 통합 확인, Windows EXE 실제 빌드.
- 공식 Open-LLM-VTuber 실서버 AI 대화, GPT-SoVITS 한국어 음성·립싱크, Live2D/VRM 움직임, OBS 실제 화면/오디오 및 플랫폼 채팅, 방송 자동 종료/시작, 자동 공지, 장시간 운영.
- 60개 검사는 안전한 코드와 파일 처리에 대한 **보조 검사**이며 실제 기능 검증 또는 원본 7부 단계 완료 증거가 아니다.

## 다음 실행의 우선순위

1. 이전 패키지와 인계 파일 실재 재확인. GitHub **READ ONLY** 원본을 로컬에 받을 수 있는 환경에서 고정 커밋/원본 SHA를 확인하고 `--fetch`는 사용자 승인 범위 내에서만 실행. 원본 전체가 없으면 새 프로그램을 임의로 만들지 않는다.
2. 원본 전체 확보 후 `prepare_local_source_copy.py`로 **별도 검증 사본**을 생성. 기존 설정/기억/100단계 기록의 SHA를 보존하고 그 사본에만 v9의 `apply_to_existing_aisting.py` 적용·회귀 검사.
3. 공식 코어 실제 연결·GPT-SoVITS/Live2D·OBS/실제 채팅 코드를 원본 기획안 순서대로 계속 수정하고, 가능한 Windows EXE를 제작. 실기기 전용 검증은 확인법/합격 기준/오류 수집법으로 인계하되 다른 개발은 멈추지 않는다.

**이번 v9 로컬 코드 작업 구간은 끝났습니다. AISTING 전체 프로젝트는 아직 미완성입니다.**
