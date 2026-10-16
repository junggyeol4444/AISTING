# AISTING v24 로컬 개발 기록 — 기존 데스크톱 소스 확장

2026-10-16 / 기존 v23의 변경 파일을 유지하면서 **원본 기획안 1단계 Live2D 선택 기능**을 추가했습니다.

## 실제 코드 변경
- **신규** `payload/src/ai_broadcaster/original_plan_avatar.py`: 공식 `model_dict.json`의 기존 Live2D 목록 및 파일 참조 검사, `conf.yaml`의 `character_config.live2d_model_name` 한 항목만 사용자 승인 후 백업·변경. 새 프로젝트/대체 모델/이미지/실행 엔진을 만들지 않음.
- **수정** `payload/src/ai_broadcaster/original_plan_studio.py`: 데스크톱 방송인 홈에 기존 Live2D 모델 선택 UI와 실제 서버 대화 결과의 초기화 모델 이름/경로 표시.
- **수정** `payload/src/ai_broadcaster/original_plan_conversation.py`: `set-model-and-conf`에서 읽은 실제 `model_url`을 결과로 전달. 단, 라이브 렌더링·립싱크 증거가 아님.
- **수정** `apply_to_existing_aisting.py`: 새 모듈을 기존 원본 사본에 적용하기 위한 모듈 목록 보완.
- **수정** `build_existing_windows.ps1`: 새 모듈 필수 검사, 기존 Windows EXE 보호 및 새 출력 경로 v24.
- **신규** `tests/test_v24_official_live2d_model_selection.py`, `tests/test_v24_official_avatar_session_metadata.py`: 합성된 로컬 설정·소켓 이벤트 보조 검사. 실제 모델 실행을 흉내내거나 검증했다고 주장하지 않음.

## 보호 조건
- 선택 목록 열기 = 오직 기존 설정/모델 파일 읽기. 서버/AI/OBS/네트워크 호출 없음.
- 선택 변경은 UI 승인 이후에만 파일 1개를 수정하고 원본 백업을 별도 생성하며 기존 문자 인코딩 BOM/CRLF/주석·캐릭터 정보 보존.
- `model_dict.json`의 `name`, `url`, `kScale` 필수 값과 Cubism model3.json 참조 파일 존재 확인. 이 검사만으로 자산의 실제 표시·표정·립싱크가 가능한지 보증하지 않음.
- 선택한 `conf.yaml`이 도중에 변경되면 저장 중단. 동일 모델은 불필요한 파일 수정 없음.
- 실행 중인 서버의 캐릭터 설정 전환은 별도 항목이며, `conf.yaml` 변경만으로 즉시 프런트엔드가 전환되었다고 주장하지 않음.
- GitHub 읽기 전용, 사용자 원본·기억·100단계 기록·기존 EXE 변경 없음. 외부 설치/다운로드/훈련/음성 재생/방송/게시 없음.

## 검사 범위
- Python `unittest discover` 191건 통과, `compileall` 구문 검사.
- 이 로컬 보조 검사는 실제 전체 원본 AISTING에 패치한 통합 검증이 아니며, 실제 LLM/TTS/Live2D/OBS 성공 증거도 아님.
- GitHub DNS 불가로 기존 전체 `main` 원본을 로컬에 가져오지 못함. Windows EXE 미제작.

## 공식 문서와 기준
- https://docs.llmvtuber.com/en/docs/user-guide/live2d/
- https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/model_dict.json
- https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/config_templates/conf.default.yaml

## 다음 개발 우선순위
1. 기존 `main` **전체 원본**의 승인된 로컬 안전 사본 확보 및 기존 파일/데이터 해시 보존.
2. v24 패치를 그 사본에 적용하고 기존 모든 기능·설정·캐릭터 복원·100단계 기록 보존 확인.
3. 공식 Live2D 프런트엔드 렌더링·실제 음성 출력 동기화 연결 코드, 사용자 선택 아바타 전환 기능 보완(임의 플러그인 설치 금지).
4. 1단계 실기기 테스트는 사용자 요청대로 이후 수행. 2단계 GPT-SoVITS, 3단계 실제 채팅/OBS, 4~7단계 순차 개발.
