# AISTING 기존 소스 수정 패키지 v4 — 2026-10-15 (한국시간)

## 진행 원칙

기존 AISTING `main` 코드를 **별도 로컬 작업공간에서만** 수정하도록 준비한 v3 패키지의 후속 패치입니다. 원본 프로그램의 기존 GUI/설정/메모리/100단계 개발 도구를 제거하거나 신규 프로그램으로 대체하지 않습니다. **GitHub에는 쓰지 않았고, 실제 OBS 송출·설치·다운로드·외부 게시·음성 재생도 수행하지 않았습니다.**

## 읽기 전용으로 확인한 근거

- AISTING `main` 원본 커밋 SHA `2269205998201165e024a22d0adef576e6cac0c6`, `src/ai_broadcaster/desktop.py` Git blob SHA `a5df12a74a27a5a50657da9c968253859b98b8ed` 확인 (2026-10-15).
- 공식 Open-LLM-VTuber `run_server.py`는 `frontend/index.html`이 없으면 `git submodule update --init --recursive`를 실행하며, 실행 중 `upgrade_manager.sync_user_config()`를 호출한다는 사실을 **공식 업스트림 소스에서 확인**했습니다.
- 그러므로 v3의 `uv run --offline --no-sync`만으로는 **공식 프로그램 전체가 다운로드·설정 변경을 하지 않는다고 보장할 수 없습니다.** v3의 이 주장을 정정합니다.
- 공식 `config_templates/conf.default.yaml`에 실제 `character_config`, `tts_config`, `gpt_sovits_tts` 항목이 존재한다는 것을 확인했습니다. 이 템플릿의 존재는 로컬 음성·아바타 작동 검증이 아닙니다.

## 실제 로컬 코드 변경

1. `original_plan_studio.py`: `prepare_official_launch()`로 기존 공식 디렉터리, `frontend/index.html`, `conf.yaml`의 존재를 읽기 전용 확인합니다. 프런트엔드가 없으면 업스트림의 암묵적인 Git 서브모듈 다운로드를 유발할 수 있는 서버 실행을 **차단**합니다. 설정 파일이 없는 경우 자동 생성·수정 위험으로 실행을 차단합니다.
2. `original_plan_studio.py`: `launch_official_server()`는 `operator_authorized_side_effects=True`가 없는 호출을 거부합니다. GUI에서 현재 실행의 잠재적 설정 동기화·모델 다운로드·네트워크 영향과 유료 API 승인에 해당하지 않는다는 점을 명확히 알리고 사용자 승인을 받은 경우에만 실제 업스트림 프로세스를 실행합니다. 이는 그 프로세스에 부수 효과가 **절대 없다**는 보장은 아닙니다.
3. `original_plan_studio.py`: 저장된 캐릭터 정보를 공식 YAML에 적용할 때 프롬프트 다음의 업스트림 주석을 잘못 삭제할 가능성을 수정합니다.
4. `original_plan_obs.py`: 실제 OBS 스트림 종료 API에도 시작과 동일하게 `operator_confirmed`와 별도 `AISTING_APPROVED_OBS_OUTGOING=YES` 승인을 요구합니다. 어떤 방송도 시작·종료하지 않았습니다.
5. `tests/test_v4_upstream_safety.py`: 실제 업스트림 코드의 알려진 부작용 방지, 승인 없이 실행 불가, 기존 주석 보존, OBS 종료 보호를 확인하는 5개 **보조 단위 검사**를 추가했습니다. 이전 14개 포함 총 19개 로컬 테스트 통과. 가짜 모델/방송 동작을 합격 처리하지 않습니다.

## 엄격한 미완료 내역

- **기존 전체 원본 소스의 로컬 복원·v4 패치 실제 적용 및 통합 회귀 검사 불가:** GitHub 커넥터로 SHA와 필요한 파일은 읽기 전용 확인했지만, 전체 저장소 ZIP을 이 실행환경으로 받을 수 없었습니다. 즉, 패치는 아직 실제 기존 전체 프로그램에 적용되지 않은 로컬 코드 변경안입니다.
- **Windows EXE 빌드 및 사용자 Windows PC 실제 사용 확인 불가:** Windows 실행환경과 전체 원본 소스가 없습니다.
- **실제 Open-LLM-VTuber AI 대화/한국어 TTS/GPT-SoVITS/Live2D 실제 움직임/OBS 방송 화면과 오디오/방송 플랫폼 채팅/자동 종료·시작/자동 공지/장기 무인 운용:** 개발·검증 미완료, 단계 완료 판정하지 않습니다.
- 공식 서버를 실제로 실행한 적 없습니다. 잠재적 설정 동기화와 자동 모델 다운로드 가능성을 코드에서 표시할 뿐 자동 설치를 실행하지 않습니다.

## 다음 개발

1. 기존 GitHub `main` 전체 소스를 읽기 전용으로 내려받을 수 있는 환경 또는 사용자가 제공한 기존 원본 ZIP이 확보되면 **별도 사본**을 만든 뒤 `apply_to_existing_aisting.py --source <기존사본>`를 먼저 `--check`로 검사합니다.
2. 원본 백업·일치 확인 후 **사본에만** `--apply`하여 기존 UI 및 데이터 보존, 캐릭터 확정 저장·재실행, 정식 코어 설정 연결을 회귀 검증합니다. 사용자 파일/PC 및 GitHub 임의 변경 없음.
3. 기존 전체 프로그램의 Windows EXE를 별도 경로에 빌드하고 기획안 7부 순서에 따라 실제 엔진 연동을 지속 구현합니다. 사용자 PC 전용 실제 동작은 합격 기준·오류 수집을 넘기고 나머지 개발을 지속합니다.

**이번 v4 로컬 변경 작업은 끝났지만, 전체 AISTING 개발은 미완성입니다.**
