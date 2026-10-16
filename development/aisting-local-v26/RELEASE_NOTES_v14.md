# AISTING 기존 프로그램 로컬 수정 패키지 v14 — 원본 사본 복제 경로 강화

2026-10-16 (KST). **전체 기존 AISTING 프로그램이 아니며, Windows EXE·실제 방송 검증본이 아닙니다.** v13 패키지 전체를 보존하고 아래의 기존 프로그램 사본 보호 코드를 수정했습니다.

## 실제 수정

- `prepare_local_source_copy.py`: 기존 `shutil.copytree` 전체 트리 순회 대신, 먼저 검사한 **정확한 원본 파일/디렉터리 목록**만 별도 로컬 사본에 생성합니다. 파일을 1MiB 블록으로 복사하며 SHA-256을 동시에 검사합니다. POSIX에서는 디렉터리별 `O_NOFOLLOW`와 `dir_fd`를 사용해 **검사와 복사 사이에 삽입된 심볼릭 링크**를 따라가지 않도록 했습니다. Windows에서는 경로 구성 요소를 확인하고 전체 트리를 재검사하지만, POSIX와 동등한 원자적 경로 열기 보증은 아닙니다.
- `prepare_local_source_copy.py`: **빈 폴더까지 포함한 원본 폴더 목록**을 사본 출처 기록에 저장합니다. 복사 전후 원본 및 사본의 파일·폴더를 재검사하고, 다르면 새로 만든 사본을 폐기합니다. 읽기 전용 폴더 때문에 폐기가 실패하지 않도록 정리 절차도 보강했습니다. 기존 사용자 설정·기억·100단계 파일을 삭제하거나 바꾸지 않습니다.
- `apply_to_existing_aisting.py`: 패치 직전 파일뿐 아니라 **원본 디렉터리 구조**도 대조합니다. v13 이하의 사본 기록에는 폴더 목록이 없으므로 쓰기 전에 중단합니다. 원본에서 v14 도구로 새 사본을 만들어야 합니다.
- `audit_local_patch_preservation.py`: 패치 후 기존 빈 폴더의 추가·삭제를 포함한 구조 변경을 탐지합니다. 정상 결과에 보존된 디렉터리 수를 표시합니다.
- `tests/test_v14_exact_source_copy.py`: 합성 파일 사본에서 폴더 보존·사전/사후 변조·링크 교체·출처 기록 검사를 8개 추가했습니다. 과거 `copytree` 호출을 가정하던 v6 테스트 1개를 새 복제 함수 기준으로 갱신했습니다.
- `build_existing_windows.ps1`: v14 전용 별도 빌드 폴더 명칭과 패치 안내 문구로 갱신했습니다. Windows에서 **실제 빌드하지 않았습니다**.

## 실제 확인과 한계

- 이전 v13 패키지 ZIP 60개 엔트리를 로컬 작업 공간에 복원했습니다. `desktop.py` 원본 전체는 이 패키지에 없습니다.
- GitHub **READ ONLY**로 고정 원본 커밋 `2269205998201165e024a22d0adef576e6cac0c6`의 `desktop.py` blob SHA `a5df12a74a27a5a50657da9c968253859b98b8ed`와 `docs/ORIGINAL_PLAN.txt` 존재를 확인했습니다. GitHub 쓰기 없음.
- `python -m unittest discover -s tests -p 'test*.py' -q`: **96개 로컬 보조 검사 통과**. 실제 기존 원본 전체에 패치를 적용한 검사는 아닙니다.
- `xvfb-run -a python tests/gui_existing_studio_smoke.py`: Linux Tk 레이아웃 확인 통과. **실제 Live2D/LLM/TTS/OBS 작동 검증이 아닙니다.**
- Python 구문 검사, 패키지 SHA-256 및 ZIP 무결성 검사를 수행했습니다. 세부 로그는 `evidence/` 참조.

## 반드시 남겨야 할 미완료

기존 전체 AISTING 원본 로컬 확보, 검증된 **전체 원본 사본**에 실제 v14 패치 적용, 캐릭터 확정 저장/재실행 복원과 기존 설정·기억·100단계 파일 보존의 통합 검사, Windows EXE 제작, 공식 AI 한국어 응답·GPT-SoVITS 음성·Live2D/VRM·OBS/플랫폼 채팅·무인 방송 실제 동작은 모두 미완료입니다. v14의 96개 보조 검사를 실제 방송 성공으로 표현하지 않습니다.

## 사용자 PC 실기기 확인 인계 (승인 전 실행하지 않음)

기존 AISTING 원본을 안전하게 보관한 뒤 v14 `prepare_local_source_copy.py`의 읽기 전용 검사와 별도 `--copy`로 새 사본을 생성합니다. 성공 기준은 필수 파일과 전체 SHA-256, 빈 폴더 목록이 사본 기록과 일치하는 것입니다. `apply_to_existing_aisting.py`를 먼저 `--apply` 없이 검사하고, 별도 승인 후 **사본에만** 적용합니다. 적용 후 `audit_local_patch_preservation.py --source <사본>`으로 기존 파일·폴더가 보존되었는지 확인합니다. 실패하면 로그의 오류 문구·경로·원본/사본 파일 수만 전달하고 설정값·API 키·기억 DB 원문은 공유하지 않습니다. 실제 AI/음성/아바타/OBS 합격 기준은 `WINDOWS_REAL_DEVICE_VALIDATION_v10.md`를 참고하되, 이 회차에는 해당 검증을 수행하지 않았습니다.
