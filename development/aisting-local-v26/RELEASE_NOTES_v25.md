# AISTING v25 — 1단계 공식 Live2D 실제 화면 안전 연결

## 이번 회차의 실제 소스 변경

- 신규 `payload/src/ai_broadcaster/original_plan_frontend.py`: 기존 설치된 `Open-LLM-VTuber/frontend/index.html`, `conf.yaml`, `run_server.py`, `pyproject.toml`의 **읽기 전용 사전 검사**, 로컬 `127.0.0.1:12393/` HTTP 200 / `text/html` / 실제 HTML 본문 확인, 승인 후에만 **설치된 공식 WebGL/Live2D 프런트엔드**를 브라우저로 열 수 있는 기능.
- 수정 `original_plan_studio.py`: 기존 `실제 Live2D 화면 열기` 버튼을 명시 승인형 공식 렌더러 열기로 교체. 가짜 미리보기를 만들지 않고 기존 실행 중인 공식 서버만 사용. UI 스레드에서 브라우저 열기, 다른 스레드에서 HTTP 사전 검사. HTTP 200 확인만으로 실제 렌더링 성공이라고 주장하지 않음.
- 수정 `apply_to_existing_aisting.py`: 새 모듈을 **기존 AISTING 소스 사본**에 추가하도록 등록. 원본 `desktop.py` 삭제/재생성 없음.
- 수정 `build_existing_windows.ps1`: 새 모듈 유무 확인 및 v25만의 새 출력 경로. 기존 exe 덮어쓰기 불허.
- 신규 `tests/test_v25_official_live2d_frontend.py`: 승인 없이는 HTTP 요청/브라우저 실행을 하지 않음, 외부 URL 거부, HTTP 리다이렉트/JSON/가짜 HTML 거부, 누락된 프런트엔드 시 서버 부트스트랩 금지, 실제 UI 함수 이벤트 연결 등 **14개 로컬 보조 검사**.

## 중요한 경계

현재 AISTING은 **Windows 네이티브 Tk 데스크톱 앱**이며 HTTP 앱으로 교체하지 않음. 다만 원본 Open-LLM-VTuber의 실제 Live2D WebGL 화면은 공식 프런트엔드가 담당하므로 **추가 설치 없이 이미 준비된 로컬 브라우저**로 표시하도록 연결함. 이는 기존 AISTING AI 텍스트 대화 WebSocket과 **별도 세션**을 형성할 수 있고 두 화면의 질문/음성이 자동으로 동기화되는 것은 아님. 공식 화면이 사용자의 추가 승인 없이 자동 실행되는 것은 아님.

운영자가 버튼 승인 후 브라우저를 열 경우 프런트엔드 JS는 운영자 설정에 따라 모델 리소스 다운로드, 외부 API 호출, 음성 재생, 마이크 접근 등을 요청할 수 있음. 실제 사용자 PC에서 이 회차에 아무것도 실행하지 않음. 앱의 GUI는 사전 경고 + 명시 동의를 필수로 함.

## 실제 확인 근거와 상태

- 공식 Open-LLM-VTuber `src/open_llm_vtuber/server.py`: `frontend` 디렉터리를 마지막 catch-all StaticFiles(html=True)로 마운트, `live2d-models` 리소스 제공. Git blob SHA `7a34b7b2a7e6e29f36c92b4cd2aa0db1af6eda81` (2026-10-16 READ ONLY 확인).
- 공식 `run_server.py`: 프런트엔드가 없으면 `git submodule update --init --recursive` 실행 시도, SHA `510ca20b4ba56f075e6e3a099f55b0ba3e8649f7`. 이 코드는 호출하지 않음.
- 이전 v24 코드 및 단위검사 그대로 유지, 신규 14개 포함 Python 로컬 보조 검사 **205개 통과**. `evidence/v25_local_regression_ONLY_not_real_live2d.log` 참조.
- 실제 공식 렌더링/음성/립싱크/OBS 송출 테스트, 전체 원본 통합 패치, Windows EXE 제작은 **미완료**. HTTP 확인은 기능 완성 증거가 아님.
- GitHub READ ONLY로만 조사, 저장소 쓰기 0, 사용자 개인 파일/원격 리소스/음성 재생/게시/모델 설치/실방송 0.

## 다음 개발 구간

1. 기존 **전체** AISTING main 소스 안전한 별도 사본 확보, 원본 기획과 저장된 설정/기억/100단계 기록 전체 무결성 확인 후 이 패치 실제 적용.
2. 1단계: 원본 공식 프런트엔드와 현재 AISTING 대화 세션의 **실제 같은 세션 동기화** 가능 여부 조사 및 연결 코드 개발. 별도 WebSocket을 동기화된 것처럼 표시하지 말 것.
3. 1단계 실제 LLM 응답 → 공식 TTS 출력 → Live2D 입/표정 움직임, Windows 실행 결과는 사용자가 실기기에서 나중에 검증.
4. 이후 2단계 GPT-SoVITS 실제 한국어, 3단계 플랫폼 채팅/OBS, 4~7단계 순서대로 개발.
