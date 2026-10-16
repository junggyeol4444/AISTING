# AISTING v12 — 기존 전체 파일 보존 확인 강화 (로컬 수정 패키지)

이 ZIP은 기존 AISTING을 대체하는 신규 프로젝트나 완성된 방송 프로그램이 **아닙니다**. v11을 기반으로 기존 소스의 **검증된 별도 사본**을 안전하게 수정하기 위한 패치입니다. GitHub 쓰기, 설치, 모델 실행, 실제 방송은 수행하지 않았습니다.

## 이번 회차 실제 코드 변경

- `prepare_local_source_copy.py`: 기존 AISTING 전체 파일의 상대 경로별 SHA-256을 `.aisting_local_copy_provenance.json`의 `original_all_sha256`에 기록. 기존의 필수 7개 파일 확인과 전체 파일 개수 기록은 유지.
- `apply_to_existing_aisting.py`: 패치 적용 **직전**에 전체 사본 파일의 SHA-256과 파일 목록을 다시 검사. 기존 기억 DB, 설정, 과거 모듈 등 7개 필수 파일 이외의 파일도 수정/누락/추가/심볼릭 링크를 감지하면 적용 중단. 오래된 사본 기록(v11 이하에 전체 해시 없음)은 안전하게 거부하고 v12 복사 도구로 새 사본 생성 필요.
- `apply_to_existing_aisting.py`: 기본 읽기 전용 검사에서도 사본 기록이 있으면 전체 해시 검사를 수행. 원본 저장소의 기본 검사에서는 코드 위치만 확인하고 `--apply`는 차단됨을 명시.
- `tests/test_v12_full_copy_integrity.py`: 전체 파일 해시 기록, 미변경 사본 적용, 비필수 기억 DB 변조/모듈 삭제/추가 파일/옛 기록/경로 탈출/심볼릭 링크/읽기 전용 사전 검사에 대한 보조 단위 검사 추가.
- `tests/gui_existing_studio_smoke.py`: 과거 v8 증거 이미지를 덮어쓰지 않고 v12 별도 UI 검사 이미지 저장.

## 로컬 검증 (실제 기능 검증 아님)

- `python -m unittest discover -s tests -p 'test_*.py' -v`: **78개 통과** (합성 파일 사본 및 설정 형식 검사 포함).
- `xvfb-run -a python tests/gui_existing_studio_smoke.py`: **Tk 위젯 표시 검사 통과** (실제 AISTING 전체 앱이나 Live2D 모델 구동 아님).
- Python 구문 검사 및 ZIP/패키지 SHA-256 검사는 `MANIFEST.json`, `verify_local_revision.py`로 재확인 가능.
- GitHub READ ONLY에서 `main` 커밋 `2269205998201165e024a22d0adef576e6cac0c6` 및 기존 `desktop.py` Git blob SHA `a5df12a74a27a5a50657da9c968253859b98b8ed` 확인.
- 로컬 컨테이너 `github.com`/`api.github.com` DNS 해석 실패. **기존 원본 전체 다운로드 및 실제 적용은 수행하지 못함.**

## 실제 Windows 원본 적용 준비 (사용자 승인 후에만 수행)

기존 원본을 보존하고, 기존 원본 폴더 및 새 사본 경로를 사용자가 직접 지정한다. 예시:

```powershell
python prepare_local_source_copy.py --source "C:\\AISTING-original" --destination "C:\\AISTING-local-copy-v12"
python prepare_local_source_copy.py --source "C:\\AISTING-original" --destination "C:\\AISTING-local-copy-v12" --copy
python apply_to_existing_aisting.py --source "C:\\AISTING-local-copy-v12"
python apply_to_existing_aisting.py --source "C:\\AISTING-local-copy-v12" --apply
```

실제 경로는 사용자 PC 상황에 따라 달라진다. 첫 번째와 세 번째 명령은 읽기 전용이며, 두 번째와 네 번째는 명시적 로컬 파일 쓰기 작업이다. **이 회차에서는 위 명령을 사용자 PC에 실행하지 않았다.** 기존 프로그램 사용자 데이터 및 방송 설정은 원본에서 변경하지 않는다.

## 한계 및 다음 작업

현재 전체 원본이 로컬에 없으므로 원본 프로그램에 패치 적용한 회귀 테스트, 실제 Windows EXE 제작, 저장된 캐릭터의 전체 앱 재실행 검증, 실제 LLM/한국어 GPT-SoVITS/Live2D/OBS/실시간 채팅/자동 방송 검증은 **모두 미완료**다. 다음 회차에는 GitHub READ ONLY 원본 확보 가능 여부를 먼저 확인하고, 승인된 별도 사본에 v12를 실제 적용하여 기존 설정·기억·100단계 기록 보존을 검사해야 한다. 실제 실기기 검증은 `WINDOWS_REAL_DEVICE_VALIDATION_v10.md`를 참고하되 최신 수정 내용은 위 절차를 따른다.

전체 해시 기록은 우발적 변경 감지용이지 공격자가 사본 기록과 파일을 함께 위조하는 상황을 방어하는 서명 기술이 아니다. 기존 파일 내용이나 해시는 보고서에 직접 노출하지 않는다.
