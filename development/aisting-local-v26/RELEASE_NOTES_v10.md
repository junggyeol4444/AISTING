# AISTING 기존 소스 로컬 수정 패키지 v10 — 실제 GPT-SoVITS 연결 설정 보강

**작업 방식:** v9 패키지를 그대로 복원한 별도 로컬 작업 공간에서 기존 수정 모듈만 변경. 기존 `main`/브랜치 쓰기, 원본 프로그램 전체 재개발, 설치/다운로드, 학습/녹음, 음성 재생/OBS 송출 없음.

## 이번에 실제 수정한 파일

- `payload/src/ai_broadcaster/original_plan_tts.py`: 이미 보유한 WAV/FLAC의 **실제 컨테이너 헤더**를 읽기 전용으로 검사. WAV의 RIFF/RF64/WAVE 및 fmt/data 청크, FLAC의 STREAMINFO 존재/기본 형식 필드 확인. 파일 확장자만 맞춘 손상된 참조 파일은 공식 설정에 기록하지 않음. 이 검사는 실제 음성 재생, 음질, 화자 권리, 모델 호환성의 증거가 아님. 또한 공식 GPT-SoVITS API URL을 사용자 선택 가능한 인자로 변경하고, 무단 외부/유료 API 사용을 막기 위해 기본적으로 명시적 로컬 `http://127.0.0.1:<포트>/tts` 또는 `localhost`/`[::1]`만 수용. 다른 호스트는 사용자 별도 의사결정 전까지 자동 연결/설정 금지.
- `payload/src/ai_broadcaster/original_plan_studio.py`: 기존 **2단계 GPT-SoVITS** 창에 로컬 API 주소 입력란 추가. WAV/FLAC 컨테이너 확인 결과와 선택한 주소를 **명시 승인 팝업에 표시**하고, 그 주소를 실제 공식 `conf.yaml`의 GPT-SoVITS 설정 변경 함수에 전달. 창 열기만으로 파일 변경/서버 접속 없음.
- `payload/src/ai_broadcaster/original_plan_readiness.py`: 기존 1단계 공식 코어 파일 준비 검사에서 GPT-SoVITS 참조 파일이 있으면 확장자만 아니라 컨테이너 헤더도 검사해 손상 가능성을 보고. 실제 모델 호출 없음.
- `tests/test_real_tts_config.py`, `tests/test_v3_readiness.py`, `tests/test_v5_official_file_inspection.py`: 가짜 `RIFF` 바이트를 유효한 음성으로 가정하던 이전 보조 검사를 고침. 테스트 내에서 Python `wave`로 실제 WAV 구조를 갖는 **무음 테스트 바이트**를 만들고, 검사만 수행(스피커 재생/학습 없음). WAV 손상 거부, 로컬 API 포트 선택, 외부 URL 거부, FLAC STREAMINFO 검사 사례 추가.
- `README_기존프로그램_수정안내.md`, `build_existing_windows.ps1`: 최신 v10 명칭/주의사항 갱신. 기존 출력 EXE 덮어쓰기 금지 유지.

## 확인한 공식 원본 근거 (READ ONLY)

- AISTING `main` 고정 커밋 `2269205998201165e024a22d0adef576e6cac0c6`, 기존 `desktop.py` blob SHA `a5df12a74a27a5a50657da9c968253859b98b8ed`.
- Open-LLM-VTuber 공식 `src/open_llm_vtuber/tts/gpt_sovits_tts.py`: `api_url`, `text_lang`, `ref_audio_path`, `prompt_lang`, `prompt_text`를 받아 실제 TTS API로 요청하는 코드 존재. `config_templates/conf.default.yaml` 기본 `http://127.0.0.1:9880/tts`와 일치. 본 회차에는 API 요청하지 않음.

## 실제 검사 증거와 한계

- `python -m unittest discover -s tests -p 'test_*.py' -q`: **63개 로컬 보조 검사 통과**. `evidence/local_unit_test_v10_ONLY_not_live_function.txt`.
- `xvfb-run -a python tests/gui_existing_studio_smoke.py`: **Linux Tk 창 검사 통과**. `evidence/linux_tk_studio_v10_UI_only_not_actual_audio.txt`.
- Python 소스 구문 검사 및 ZIP 자체 무결성 검사 별도 수행.
- 로컬 환경의 `github.com`, `api.github.com`, `codeload.github.com` DNS 조회 실패. **기존 전체 AISTING 원본 로컬 확보/원본 사본에 v10 실제 적용 미완료**. 실제 Windows EXE 빌드 미완료. 실제 AI 대화, 한국어 GPT-SoVITS 합성·재생, Live2D 움직임, OBS 송출, 실제 채팅, 자동 시작/종료 미완료.
- v10은 **기존 프로그램에 적용할 수정 패키지**이지 완성된 AISTING ZIP/EXE가 아님. 검사 63개로 원본 7부 개발 단계 완료를 주장하지 않음.

## 다음 회차 우선 작업

1. GitHub **READ ONLY**로 전체 원본 소스 확보를 다시 시도하거나, 이미 확보한 사용자 기존 원본이 있다면 `prepare_local_source_copy.py`로 별도 사본을 만든다. 외부 설치/다운로드는 사용자 승인 범위 확인 후에만 수행.
2. 사본에서 v10 실제 패치 적용/캐릭터 확정 저장·재시작·일반 저장 초안 분리/기존 설정·기억·100단계 보존 회귀 검사.
3. Windows EXE를 기존 EXE를 건드리지 않는 별도 폴더에 빌드. 실제 공식 Open-LLM-VTuber 한국어 AI 대화·GPT-SoVITS/Live2D·OBS/채팅·스케줄러를 원본 단계 순서대로 구현하고 사용자 PC 전용 검증은 합격 기준/오류 수집법을 인계.
4. GitHub 쓰기, 계정/모델/설치/송출/외부 공지는 명시 승인 전 금지. 기존 비활성 예약 유지.
