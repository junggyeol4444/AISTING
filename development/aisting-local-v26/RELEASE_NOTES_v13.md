# AISTING v13 — 기존 프로그램 사본의 패치 후 전수 보존 감사

기존 v12 로컬 수정 패키지 위에 **읽기 전용 사후 감사 코드**를 추가했다. 새로운 AISTING 프로젝트나 가짜 AI 엔진은 만들지 않았다.

## 실제 변경 파일

- `audit_local_patch_preservation.py` (신규): 검증된 로컬 사본에 패치를 적용한 **뒤** 전체 파일 목록/해시를 원본 복제 시점 기록과 비교한다. 변경을 허용하는 파일은 정확히 수정된 `desktop.py`, 기존 `desktop.py`의 바이트 동일 백업 1개, 패키지의 공식 연결 모듈 6개뿐이다. 기존 설정·기억·100단계 파일 및 나머지 기존 소스가 바뀌거나 누락/추가되면 감사 실패. 검사 중 파일은 수정하지 않는다.
- `tests/test_v13_post_patch_preservation.py` (신규): 실제 프로그램이 아닌 **합성 파일 사본**에서 패치 후 통과, 기억 DB/100단계 기록 변경, 수정 모듈·desktop.py·백업 변조, 추가/삭제/링크 파일 거부 등을 검증한다.
- `build_existing_windows.ps1`: PyInstaller 실행 **전에** 위 보존 감사를 수행하고, 감사가 실패하면 EXE 빌드를 시작하지 않는다. 기존 EXE 보호 및 새 출력 폴더 정책 유지.
- `README_기존프로그램_수정안내.md`: 사본 적용 후 읽기 전용 감사 실행 절차 추가.

## 실행 방법 (원본이 이미 있는 사용자 PC에서만, 로컬 사본에 적용한 다음)

```powershell
# 검증된 별도 사본을 준비하고 명시적으로 패치 적용한 다음:
python audit_local_patch_preservation.py --source "D:\AISTING_local_copy"
# 통과 시에만 (이미 설치된 Python/PyInstaller로) 빌드 가능:
.\build_existing_windows.ps1 -ExistingProject "D:\AISTING_local_copy"
```

위 명령은 **이 회차에서 사용자 PC에 실행하지 않았다.** 사후 감사는 패치 적용 후 새 파일이 생기거나 기억 DB가 바뀌어도 실패한다. 이미 실행하여 상태가 바뀐 사본은 원본에서 새 사본을 다시 만드는 것이 안전하다. 원본 소스/설정/개인정보는 ZIP에 넣지 않는다.

## 증거와 한계

- 기존 v12 ZIP이 로컬에 실제 존재해 복원했다. 전체 원본 `desktop.py` 및 원본 프로그램 전체는 **현재 로컬에 없음**.
- GitHub 연결 도구로 읽기 전용으로 기존 커밋 `2269205998201165e024a22d0adef576e6cac0c6`의 `desktop.py` Git blob SHA `a5df12a74a27a5a50657da9c968253859b98b8ed`, `offline_settings.py`를 확인했다. 저장소 수정 없음.
- 로컬 단위검사 88개 통과 (v12 78개 + v13 신규 10개). 이 검사는 **합성 사본·코드의 보존 로직**만 확인한 것이며 기존 전체 소스에 패치를 적용한 통합 검증이 아니다.
- Windows EXE, 실제 한국어 LLM 응답, GPT-SoVITS 음성, Live2D 움직임, OBS 송출, 실제 플랫폼 채팅, 자동 방송은 **모두 미완료/미검증**이다.
