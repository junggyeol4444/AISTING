# v45 / 원본 로드맵 044 — 한국어 음성 합성 환경 구성 초안

## 구현 범위

- 기존 `offline_tts.py`에 이미 있는 Windows System.Speech 기능을 재사용할 준비를 하는 비실행 구성 화면 `한국어 TTS 환경 준비` 추가.
- 현재 `방송 설정`의 음성 확보 방식(`undecided/windows_system/own_recording/consented_recording/licensed_recording`)과 Windows 음성 프로필(선택 음성 이름, 속도, 음량)만 메모리에서 읽고 `ko-KR` 구성 후보를 보여줌.
- Windows 방식: 기존 엔진을 후보로 **표시만** 하며 설치된 음성 존재 여부·장치·OS 정보는 자동 조회하지 않는다. 이름 미선택이면 실행 가능 판정 불가.
- 녹음/동의/라이선스 방식: `future_local_tts_unconfigured` 후보로 표시. 엔진은 실제로 설치하거나 연동하지 않음. 미정 방식도 유효.
- 확인 후 별도 `korean_synthesis_environment_draft.json` 파일에만 원자적으로 저장, 수동 불러오기, 2회 확인 후 삭제. 음성 확보 방식/음성 이름/속도/음량 변경 시 이전 기록 불일치로 재사용 거부.
- 저장 기록에는 `pc_probed/audio_accessed/model_installed/training_authorized/broadcast_authorized/environment_verified` 값 모두 `false` 고정, 임의 조작 및 미승인 외부 엔진 거부. 로드 시 자동 적용 없음.
- 기존 플랫폼·콘텐츠·캐릭터·음성·아바타 선택, 기존 41~43단계 권리/자료/품질 기록, SQLite 기억, 전체 기획안 및 사용자 승인 대기 상태 보존.

## 검증 범위/한계

코드 정합성·로컬 파일 저장·사용자 확인·설정 불일치 차단·GUI 네비게이션·기존 화면 회귀를 검사한다. 새로운 외부 모듈·설치·계정·유료/클라우드 API·GitHub 사용 없음.

**미검증/대기:** Windows 실기기의 한국어 음성 설치 및 재생, EXE 빌드, 로컬 클로닝 TTS 엔진, 실제 목소리 자료와 라이선스, AI 음성 생성 품질, 마이크·오디오 장치 정보, 실제 OBS 방송. 010단계 최종 운영자 승인도 완료 처리하지 않음. 이번 코드는 로드맵 044의 **오프라인 구성 초안 작업**이며 실제 한국어 음성 합성 환경 검증 완료가 아니다.

## 테스트

- `PYTHONPATH=src python -m unittest discover -s tests -q`
- `xvfb-run -a python scripts/gui_synthesis_environment_smoke.py` (Linux 가상화면)
- Windows 사용자의 명시적 수동 실행/승인 전에는 OS 정보 자동 수집·음성 목록 조회·재생하지 않음.
