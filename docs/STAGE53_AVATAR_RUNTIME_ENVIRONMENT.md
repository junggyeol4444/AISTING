# v53 / 원본 052 아바타 실행 환경 설정 — 로컬 후보 초안

## 작업 범위

최신 누적 v52의 51단계 아바타 모델 준비표와 기존 2D Tk 샘플을 보존하며,
원본 100단계 계획의 **052 아바타 실행 환경 설정**을 위한 수동 구성·검증 UI를 추가했습니다.

- `아바타 실행 환경 준비` 탭에서는 **현재 사용자가 선택한 아바타 종류**(미정/2D/3D)와 호환되는 **렌더러 후보만** 인정합니다.
  - 미정: 렌더러 미정만 허용
  - 2D: 미정 / 이미 앱에 존재하는 Tk 2D 샘플 / 외부 Live2D 후보(미연결)
  - 3D: 미정 / 외부 VRM 후보(미연결)
- 내장 샘플의 배경은 기존 `남색 스튜디오`/`초록색 배경` 중 선택하며, 외부 후보에는 배경 설정을 전달하지 않습니다.
- 모델 실행 파일·경로·모델/라이선스 파일·GPU·드라이버·설치 정보를 탐색하지 않으며 실제 PC 사양·프로세스·외부 서버도 확인하지 않습니다.
- 별도 JSON `avatar_runtime_environment_draft.json`에 **사용자 확인 후에만** 후보 설정을 기록합니다. 수동 불러오기·2회 확인 삭제 지원. 선택한 종류와 저장 내용이 불일치하면 거부하며, 선택 변경 시 화면 초안을 초기화합니다.
- 저장 형식은 고정 필드만 허용합니다. `pc_inspected`, `model_accessed`, `software_installed`, `external_process_launched`, `renderer_connected`, `license_verified`, `streaming_authorized`, `final_approval`은 모두 `false`이며 조작된 기록의 로드를 거부합니다. 심볼릭 링크 및 과대·손상·알 수 없는 필드도 거부합니다.
- 기존 방송 설정, 사용자 아바타 선택, 51단계 모델 준비표, SQLite, 원본 기획안은 수정하지 않습니다.

## 수행하지 않은 작업

Live2D / VTube Studio / VRM 설치, 실제 모델 렌더링/불러오기, OS·GPU 확인, 아바타 립싱크, OBS 송출, 인터넷·GitHub 접속, 사용자의 PC 정보 수집 및 자동 승인 **모두 없음**.
설정 초안을 저장했다고 렌더러가 준비되었거나 설치·라이선스 검증이 끝난 것은 아닙니다.
현재 2D 내장 Tk 샘플은 **기존 샘플 미리보기**이지 승인된 정식 아바타 모델이 아닙니다.

## 승인 및 진행 상태

원본 052의 **코드 작업 범위**에 도달했지만 실제 Windows PC/EXE/2D·3D 외부 렌더러 적합성은 검증하지 않았습니다.
10단계 전체 최종 승인과 11단계 이후 PC 실기기 정보 접근은 사용자 승인 대기입니다.
다음 작업 원본 053 `캐릭터 화면 표시`에서는 기존 내장 2D 렌더러 기능과 신규 요구사항을 비교한 후 미구현 부분부터 개발합니다.

## 시험 방법

```
PYTHONPATH=src python -m unittest discover -s tests -q
xvfb-run -a python scripts/gui_avatar_runtime_environment_smoke.py
```

Linux Xvfb GUI 시험은 실제 Windows PC 검증이 아닙니다. 실행 결과는 `logs/STAGE53_FINAL_VALIDATION.txt` 참조.
