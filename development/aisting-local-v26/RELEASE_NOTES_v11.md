# AISTING 기존 소스 로컬 수정 패키지 v11 — 공식 설정 보존 강화

**기반:** 기존 v10 패키지를 로컬 작업 폴더로 복원하여 기존 코드를 수정. 원본 전체 AISTING 프로그램을 새로 만들지 않음. 원본 GitHub에는 어떤 쓰기도 하지 않음. 설치·다운로드·학습·실제 송출·음성 재생 없음.

## 실제 변경 파일

- `payload/src/ai_broadcaster/original_plan_config_io.py` **신규**: 공식 `conf.yaml`의 안전한 백업·교체 공통 기능. 기존 원본의 UTF-8 BOM 보존, 기존 파일 바이트·inode·수정시각 검사, 고유 백업(0600) 기록 및 fsync·원본과 대조, 같은 디렉터리 임시 파일 동기화, 실패 시 임시 파일 정리, 원본 파일 권한 보존. 다른 프로세스와의 완전한 원자적 충돌 방지는 보장하지 않음.
- `payload/src/ai_broadcaster/original_plan_studio.py`: **기존** 캐릭터 공식 설정 적용 기능을 공통 보존 경로로 연결. 미저장 초안은 여전히 공식 프로젝트에 적용하지 않음.
- `payload/src/ai_broadcaster/original_plan_tts.py`: **기존** GPT-SoVITS 설정 적용 기능을 같은 보존 경로로 연결. 기존 WAV/FLAC 검사·로컬 API 설정·승인 조건 유지.
- `apply_to_existing_aisting.py`: 검증된 기존 소스의 별도 로컬 사본에 신규 모듈을 함께 적용하도록 추가. 원본 직접 패치 차단 유지.
- `build_existing_windows.ps1`: 신규 모듈 검사 및 별도 v11 출력 폴더로 변경. 실제 Windows 빌드는 수행하지 않음.
- `tests/test_v11_official_config_preservation.py`: BOM/CRLF·백업 원본 바이트·동일 설정 멱등성·변경된 원본 거부·교체 실패 원본 보호·심볼릭 링크 거부·개인 백업 권한 등 **6개 로컬 보호 검사** 추가.

## 실제 로컬 검증 및 한계

- `python -m unittest discover -s tests -p 'test_*.py' -v`: **69개 통과**.
- `xvfb-run -a python tests/gui_existing_studio_smoke.py`: Linux Tk 화면 검사 통과(실제 Windows/Live2D/AI·음성·OBS 아님).
- `python verify_local_revision.py`: 패키지 내 소스·문서·검사 파일 SHA-256 검증.
- 원본 전체 `main` 소스는 로컬에 없으므로 v11을 실제 기존 전체 프로그램에 적용한 회귀시험, Windows EXE 빌드, 실제 GPT-SoVITS 한국어 합성/재생, Live2D 움직임, 실제 채팅·OBS 송출, 자동방송은 모두 미완료.

## 다음 작업

기존 AISTING 전체 소스의 **읽기 전용 확보는 별도 승인 범위 확인 후** 진행하고, 원본을 보존한 사본에 v11 패치 적용 및 기존 설정·기억·100단계 기록 회귀 검증. Windows EXE와 실제 코어·음성·아바타·방송 기능은 원본 7부 순서대로 개발. 사용자 PC 실기기 검증 기준은 기존 `WINDOWS_REAL_DEVICE_VALIDATION_v10.md` 참조.
