# AISTING 기존 프로그램 로컬 수정안 v20 — 2026-10-16

## 이번에 수정한 실제 코드

`payload/src/ai_broadcaster/original_plan_studio.py`의 세 동작을 수정했습니다. (1) 캐릭터 정보 새로 고침은 실제 기존 `offline_settings.load_settings()`에서 저장된 확정값을 다시 읽고, 사용자 화면의 저장하지 않은 캐릭터 초안은 사용하지 않습니다. (2) 공식 `conf.yaml` 비교도 현재 디스크의 확정값을 사용합니다. (3) 공식 `conf.yaml` 적용은 운영자 확인 전후로 확정 캐릭터를 각각 읽고, 그 사이 값이 달라졌다면 파일을 변경하지 않고 재확인을 요청합니다. 기존 방송 설정 편집값은 보존합니다. 설정 파일 누락/손상/검사 도중 변경은 명시적으로 실패 표시합니다.

이 작업은 **기존 AISTING에 추가하는 v19 패치 모듈의 버그 수정**입니다. 별도 프로젝트를 만들거나 공식 LLM/TTS/Live2D를 모방하지 않았습니다. `build_existing_windows.ps1`의 새 빌드 출력 이름을 v20으로 변경하여 과거 산출물 덮어쓰기를 피합니다.

## 증거의 한계

- `tests/test_v20_disk_confirmed_persona_only.py`: GitHub `main`의 실제 `offline_settings.py` SHA 일치 원본에 v19 저장 함수 수정안을 결합한 상태에서 확정값 재읽기, 다른 창 확정값, 미확정 초안 배제, 누락/손상 파일, 승인 대기 중 값 변경, 파일 읽는 도중 변경을 검사합니다. **테스트용 공식 설정 적용 함수는 호출 기록으로만 검사**하므로 실제 공식 코어 동작 증거는 아닙니다.
- `evidence/local_unit_test_v20_ONLY_not_live_function.txt`: 이전 회귀를 포함한 로컬 Python 보조 검사 결과.
- `evidence/linux_tk_studio_v20_UI_only_not_real_ai.txt`: Xvfb에서 실제 Tk 위젯 생성 및 미확정 상태 문구 확인. 실제 AI/Live2D/음성 검증 아님.
- `evidence/github_readonly_baseline_v20.txt`: 원본 일부의 GitHub 읽기 전용 SHA 확인과 전체 소스 미확보 기록.
- **미완료**: 전체 `desktop.py` 원본 확보 및 전체 기존 소스 사본에 패치 적용, 원본 100단계/기억 전수 회귀, Windows EXE 빌드, 실제 LLM/한국어 GPT-SoVITS/Live2D·VRM/플랫폼 채팅/OBS/스케줄러/공지 검증.

## 안전

GitHub 쓰기·브랜치 변경 없음. 사용자 PC 파일 변경, 모델 설치·학습·다운로드, 계정 연결, 마이크·스피커, 방송 송출, 외부 공지 수행하지 않았습니다. 본 패키지는 기존 원본을 대체하는 완성 프로그램이 아닙니다.
