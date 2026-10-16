# AISTING 기존 프로그램 로컬 수정 v16 — 확정 캐릭터 저장 보존

**기존 v15 수정 패키지에만 추가한 로컬 변경**입니다. AISTING 전체 원본 소스/Windows EXE는 포함하지 않습니다. GitHub 쓰기, 설치, 모델 다운로드·학습, 로그인, 송출, 스피커 재생, 외부 게시는 실행하지 않았습니다.

## 코드 변경

- `payload/src/ai_broadcaster/original_plan_persona_store.py` 추가. 전용 **캐릭터 확정·저장** 동작에서만 이름·말투·성격을 저장합니다. 기존 `offline_settings.load_settings()`와 `validate_settings()`를 호출하여 저장 직전 디스크의 유효한 최신 설정을 읽고, 방송 플랫폼·콘텐츠·아바타·음성 등 **비캐릭터 필드**를 보존합니다. 기존 파일이 있으면 제한된 권한의 고유 백업을 만들고 바이트 무결성을 확인한 뒤 임시 파일을 원자적으로 교체합니다. 파일 변경/링크/손상 시 덮어쓰지 않습니다.
- `apply_to_existing_aisting.py`: 기존 `desktop.py`의 `_save_character_identity`에 주입하는 저장 로직을 새 헬퍼로 교체. 일반 **방송 설정 저장**은 기존과 같이 확정 캐릭터 값을 보존하며 미저장 초안을 적용하지 않습니다. 새 모듈은 **기존 원본의 검증된 사본**에만 추가됩니다.
- `build_existing_windows.ps1`: 새 모듈 검사 및 v16 전용 출력 경로로 갱신. 기존 EXE 덮어쓰기 금지 유지.
- `tests/test_v16_committed_persona_persistence.py`: 파일 보존·재읽기·백업·손상 거부·링크 거부·실패 시 원본 유지 등 **보조 단위검사 8개** 추가.

## 검증과 한계

- v15 패키지 복원 및 v15 기존 단위검사 103개 통과 확인.
- v16 로컬 보조 단위검사 총 **111개 통과**. 테스트는 원본 `offline_settings.py` 전체가 없는 상황이므로 저장소 인터페이스에 맞춘 **제한된 테스트용 설정 검증기**를 사용합니다. 따라서 **실제 기존 AISTING에 적용한 통합 검증이 아닙니다**.
- Linux 가상 디스플레이 Tk 창 생성 검사 통과. 실제 Windows EXE/LLM/TTS/Live2D/OBS/방송 기능 확인이 아닙니다.
- GitHub 커넥터 **READ ONLY**로 고정 커밋 `2269205998201165e024a22d0adef576e6cac0c6`의 기존 `offline_settings.py` 및 원본 기획 7부를 확인했습니다. `offline_settings.py` blob SHA `769ea22a59b490d9eeb27913aa569550f3b57da3`.
- 이 실행 환경에서 `git ls-remote`와 DNS 조회 실패. **기존 전체 원본 소스 확보, 실제 패치 적용, Windows EXE 제작, 실제 한국어 AI 대화·음성·Live2D·OBS/채팅/스케줄 검증 미완료**.

## 다음 작업

기존 전체 원본을 **읽기 전용**으로 확보한 후, 별도 검증된 로컬 사본에만 패치를 적용합니다. 기존 `offline_settings.py` 실제 구현을 사용해 전용 확정 저장 → 종료/재시작 복원 → 일반 방송 설정 저장 시 미저장 초안 격리 → 사용자 데이터/100단계 기록 전수 보존을 검증합니다. Windows PC 실기기 검증은 별도 문서 참고. 원본 7부의 실제 AI+TTS+Live2D 1단계, GPT-SoVITS 2단계 이후 순서대로 개발하되 실동작 증거 없이는 완료로 판정하지 않습니다.
