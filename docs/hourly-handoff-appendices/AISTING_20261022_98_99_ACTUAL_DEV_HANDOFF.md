# AISTING 98~99회차 실제 누적 개발 부록

1~97절 및 모든 과거 원문은 기존 경로에 보존한다.

## 98. 2026-10-22 — OBS·Cubism 0초 구간 동일 발화 오판 정정 (실제 소스 반영)
- 기존 사용자 원문 1~97절과 모든 과거 부록·기획·캐릭터·SQLite·설정은 그대로 보존한다. 기준 시작 main HEAD `2687831af162f90f985da467aac9f90d0fd01828`.
- 이전 대화에서 수정 패치를 만들었지만 main 반영하지 못했던 사실을 보존한다. 이번 실제 개발에서는 `src/ai_broadcaster/original_plan_full_pipeline.py`에서 OBS 양의 오디오 구간과 공식 Cubism 양의 입 움직임 구간을 각각 `first < last`로 요구하도록 변경. `tests/test_aisting_official_chat_obs_pipeline.py`에 두 종류 0초 표본을 각각 확인하는 테스트 추가.
- 실제 main fast-forward 반영 커밋: `ca35c1e2de9e7f9b713e2f9f4a898a65c019aa0b`; 소스·테스트만 변경. [해당 전체 회귀](https://github.com/junggyeol4444/AISTING/actions/runs/39730236947) success, [동일 HEAD Windows CI](https://github.com/junggyeol4444/AISTING/actions/runs/39730236939) success (2026-10-22 이번 회차 확인). [500건 Windows 실제 모델 부하](https://github.com/junggyeol4444/AISTING/actions/runs/39730236935)는 이 문서 작성 시점 진행 중.
- 이 코드 수정과 자동 검사만으로 실제 한국어 GPT-SoVITS WAV, 공식 Cubism 실제 입, OBS 동일 음성·영상, 실제 방송·시청자 E2E가 성공했다고 주장하지 않는다.

## 99. 2026-10-22 — GPT-SoVITS→OBS 음량 피크·음소거·입력 경로 판정 분리 (실제 소스 반영)
- `src/ai_broadcaster/original_plan_voice_obs_bridge.py`의 `verify_gpt_sovits_to_obs`에서 단순 `selected_signal`의 raw 피크를 실제 사용 가능한 출력 증거로 취급하던 부분을 `meters.usable_output_candidate` 판정으로 변경. OBS 입력 음소거, 유효 음량, 선택된 입력, 경로 변경 여부를 함께 검사하여 실제 음량 피크가 있어도 음소거/경로가 변경된 경우 성공 처리하지 않음. 기존 승인·권리 검사/송출·녹화 금지/임시 소스 생성 및 UUID 안전 삭제 동작은 그대로 보존.
- `tests/test_aisting_gpt_sovits_obs_integration.py`의 기존 6개 성공 모의 OBS 반환에 사용가능한 후보 여부를 명시하고, muted·route-changed 두 가지 거절 회귀 케이스 추가. 모의 검사는 실제 OBS 실행 증거가 아님.
- 기존 main을 변경 후 fast-forward로 반영한 커밋 `cde0c2d35ce4d6d076d4d53867d34ae1ba7b7640`. [전체 회귀 CI 39730548163](https://github.com/junggyeol4444/AISTING/actions/runs/39730548163) success. [Windows EXE·OBS·Twitch·4플랫폼·로컬 모델 CI 39730547939](https://github.com/junggyeol4444/AISTING/actions/runs/39730547939) 및 [실제 Ollama 500건 Windows 부하 CI 39730547798](https://github.com/junggyeol4444/AISTING/actions/runs/39730547798)는 기록 시점 아직 in_progress. 최종 결과를 추정·은폐하지 않고 다음 회차 조회한다.
- 이전 확인 [Windows 39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656)은 cancelled, [Ollama 500건 39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468)은 500건 500건 처리되었어도 3초 초과 500건이고 총 p95 2,979.984초, FIFO 대기 p95 2,973.875초: 1~3초 목표 미달. 구 CI 실패 이력과 실제 수치 모두 유지.
- 실제 수행: 위 두 코드·테스트 수정, main HEAD 매 변경 직전 대조, 신규 누적 코드 커밋, GitHub Actions 결과 조회. 실제로 하지 않은 것: 사용자 PC 조작, 본인 OAuth 동의, 실제 계정 로그인, OBS 송출/녹화/채팅 발신, 권리 없는 모델/음성 학습, 실제 GPT-SoVITS/WAV 소유 환경 실행, 진짜 시청자 수백 명·24시간 방송, Windows 10/11 사용자 PC 실행 확인, 시청자 E2E 1~3초 달성. 타 프로젝트, Drive, 예약, 다른 브랜치/롤백/force push, 모델 토큰·keep_alive·SQLite·캐릭터·사용자 설정 변경 없음.
- 진행 중 멈춘 것/다음 개발: 사용자 권리 확인된 한국어 WAV→공식 Live2D Cubism 실제 입→OBS 같은 발화 음성·영상의 운영자 승인 실증, 실제 4플랫폼 실수신 수백 건 무누락/24시간 장애 재연결/시청자 E2E 1~3초 병목 개발. 기존 FIFO 메시지 원본·순서·중복을 임의 폐기하거나 토큰 96/keep_alive 10m를 무단 도입하지 않는다. 자동 CI 결과는 재조회하고 실패 로그가 있으면 코드 수정 후 전체 재검증. `main`의 새 실제 HEAD를 항상 다시 확인할 것.
