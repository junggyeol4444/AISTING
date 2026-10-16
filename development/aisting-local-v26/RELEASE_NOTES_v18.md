# AISTING 기존 프로그램 로컬 수정안 v18 — 2026-10-16

## 실제 수정 코드
- `payload/src/ai_broadcaster/original_plan_persona_store.py`: 전용 캐릭터 확정 저장과 일반 방송 설정 저장이 동일한 OS 파일 잠금을 사용하도록 개선. 잠금 경쟁이 발생하면 기다리지 않고, 다른 설정을 덮어쓰지 않은 채 명확한 충돌 오류로 중단하는 **비차단 잠금**이다.
- Windows: `msvcrt.locking`의 1바이트 잠금. Linux/POSIX: `fcntl.flock`의 배타 잠금. 새 외부 패키지는 필요 없다.
- 잠금 파일은 `settings.json` 옆의 `.settings.json.aisting-write.lock`. 다른 프로세스가 다른 inode를 잠그는 일을 방지하기 위해 저장 후에도 이 작은 파일은 유지한다. 심볼릭 링크, 하드링크, 비정상 크기·내용, POSIX 공개 권한은 거부한다.
- 기존 설정 JSON을 다시 읽고 저장 직전 원본 바이트를 비교하며, 기존 비공개 백업·원자적 교체 기능은 유지한다.
- **한계:** 이전 AISTING의 `offline_settings.save_settings`처럼 이 잠금에 협력하지 않는 쓰기 경로까지 원자적으로 통제하지는 못한다. 실제 Windows OS 파일 잠금은 사용자 PC에서 검증해야 한다.
- `build_existing_windows.ps1`: 기존 EXE를 덮어쓰지 않는 v18 고유 출력 경로. 기존 전체 소스 사본이 없으면 실행하지 않는다.

## 이전 버전 대비 의미 있는 검증 강화
- `evidence/original_readonly/offline_settings_main_20261016.py`: GitHub `main`의 **실제 기존 `offline_settings.py`**를 읽기 전용으로 확보한 사본. Git blob SHA `769ea22a59b490d9eeb27913aa569550f3b57da3`와 바이트 단위로 일치함을 확인. **기존 전체 AISTING 소스가 아니다.**
- `tests/test_v18_actual_offline_settings_contract.py`: 위 실제 기존 설정 모듈과 v18 저장 코드를 결합해 확정 캐릭터 재읽기, 미확정 초안 격리, v05/v07 설정 마이그레이션, 외부 방송 설정 충돌, 승인되지 않은 송출 플래그 거부, 손상 파일 보호 등을 검사.
- `tests/test_v18_cross_process_settings_lock.py`: 실제 OS 파일 잠금 경쟁·해제·오류 거부·권한 및 심볼릭 링크 보호에 대한 로컬 보조 검사. 실제 Windows에서는 실행하지 못함.
- 기존 보조 검사 119개 + 신규 검사 17개 = **136개 통과**. Linux Xvfb Tk 화면 검사 통과. 두 검사는 실제 AI·음성·Live2D·OBS 작동 증거가 아니다.

## 미완료
GitHub 전체 원본 파일 로컬 복원(현재 실행 환경에서 github.com DNS 연결 실패), 기존 전체 `desktop.py`에 수정안 적용, Windows EXE 제작, 실제 사용자 설정/기억/100단계 기록 통합 회귀검사, 실제 AI 응답·GPT-SoVITS 한국어 음성·Live2D/VRM 동작·OBS/채팅/스케줄/공지 검증 모두 미완료. GitHub 쓰기·프로그램/모델 설치·음성 재생·실제 송출·외부 게시는 실행하지 않음.
