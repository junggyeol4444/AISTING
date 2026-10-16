# AISTING 기존 프로그램 로컬 수정안 v19 — 2026-10-16

## 실제 개발 범위
- **기존 원본 `src/ai_broadcaster/offline_settings.py`의 `save_settings` 저장 경로**를 새로 수정하도록 패치 생성기 확장. GitHub `main`의 실제 파일 Git blob SHA `769ea22a59b490d9eeb27913aa569550f3b57da3`와 정확히 일치할 때만 변경한다. 원본 파일 전체를 교체하는 것이 아니라 `save_settings` 함수 하나만 수정하고 다른 함수·마이그레이션·검증기는 그대로 보존한다.
- 기존 일반 저장 호출도 `original_plan_persona_store.save_broadcast_without_persona`를 사용하도록 연결: 전용 캐릭터 확정 저장과 같은 OS 잠금/백업/원자적 교체 경로를 사용하고, 저장되지 않은 캐릭터 초안(형식 오류가 있는 초안 포함)은 일반 저장에서 적용하지 않는다. 이미 확정된 캐릭터는 디스크의 최신 값을 보존한다.
- `payload/src/ai_broadcaster/original_plan_persona_store.py`: 일반 방송 설정 저장이 무관한 미확정 캐릭터 초안을 검증하려다 실패하던 경우를 수정. 방송 설정의 다른 필드는 기존 실제 설정 검증기로 검사한다.
- `apply_to_existing_aisting.py`: `desktop.py`와 `offline_settings.py`의 두 원본 SHA 확인, 두 개의 비공개 백업, 두 파일의 별도 임시 파일 준비, 순차 교체 중 실패 시 앞서 바뀐 파일을 백업 내용으로 복원하는 경로 추가. 검증된 **기존 전체 프로그램 사본**에서만 쓰기 가능. `--apply` 없이 기본 읽기 전용.
- `audit_local_patch_preservation.py`: 두 원본 파일과 각각의 백업을 검사하고 나머지 기존 파일·기억·100단계 기록의 원래 SHA-256을 비교하도록 확장.
- `build_existing_windows.ps1`: 두 원본 백업과 전수 감사 요구, v19 전용 출력 폴더 사용. Windows EXE는 이번 환경에서 만들지 않음.

## 검증 범위와 실제 증거
- `evidence/original_readonly/offline_settings_main_20261016.py`: **GitHub main의 실제 설정 모듈 사본**, blob SHA 일치. `desktop.py` 전체 원본은 아직 로컬에 없음.
- `tests/test_v19_original_settings_writer_integration.py`: 원본 설정 모듈에서 기존 저장 함수만 수정한 결과를 실제 `load_settings`/`validate_settings`와 결합. 저장/재읽기, 레거시 데이터, 초안 격리, 잠금 충돌, 비공개 백업, 손상 파일 거부 확인.
- `tests/test_v19_two_existing_files_preservation.py`: 실제 `offline_settings.py`와 **테스트용 desktop.py**를 이용한 패치/감사/부분 실패 복원 검사. 실제 기존 desktop.py 통합 검증은 아님.
- 기존 테스트의 합성 소스 사본에 **실제 원본 offline_settings.py**를 포함하도록 수정해 v19의 강화된 원본 SHA 검사를 반영.
- Python 보조 검사 **153개 통과**, Linux Xvfb Tk UI 표시 검사 통과. 실제 LLM, 음성 합성, Live2D/VRM, OBS/플랫폼 채팅/방송 검증은 전혀 아님.

## 미완료 및 안전 제한
- 기존 전체 AISTING `main` 소스는 현재 로컬에 없음. `desktop.py` 실제 패치 적용, Windows EXE 빌드, 사용자 PC 재시작 복원 및 원본 전체 회귀 시험은 **미완료**.
- GitHub READ ONLY로 원본 일부를 확인했으나 로컬 컨테이너의 github.com DNS 문제로 전체 소스 다운로드는 실패. GitHub에 커밋/푸시/PR/브랜치 변경하지 않음.
- `offline_settings.save_settings`의 기존 호출은 현재 기준 설정을 읽은 뒤 잠금 안에서 다른 방송 설정의 변경을 다시 검사한다. 단, 호출자에게 저장 전 화면의 버전 정보가 전달되지 않으므로 오래된 GUI의 비캐릭터 값 덮어쓰기를 **완전히 판별하지는 못한다**. 전용 캐릭터 확정/방송 설정 UI 경로는 기존 충돌 검사 유지.
- 기존 프로그램의 다른 비표준 파일 직접 쓰기 경로, Windows 실제 잠금 동작, Windows 파일 권한/ACL, 외부 프로세스 경쟁은 아직 검증하지 못했다.
- 사용자 승인 없는 설치·다운로드(기존 원본 확인용 조회 외), 모델 학습·녹음, 음성 재생, 실제 방송/외부 게시 수행하지 않음.
