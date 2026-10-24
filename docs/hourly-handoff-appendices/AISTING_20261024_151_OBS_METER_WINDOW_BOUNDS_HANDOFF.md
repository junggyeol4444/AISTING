# AISTING 151회차 — OBS 관찰창 경계·빈 경로

## 151. 2026-10-24 — OBS 미터 관찰창 경계 이탈 및 빈 오디오 경로 차단

### 시작 기준 및 원문 보존
- 시작 main HEAD: `967e32ebf5c02d7c6b0acfc93648b4b3eac6cb66` (150절까지 기록).
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 기존 1~150절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 기존 전체, `docs/hourly-handoff-appendices/` 모든 과거 원문(특히 97절), `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`을 유지한다.
- 기존 캐릭터·SQLite·설정·원본 소스 보존. 새 브랜치·force push·롤백·다른 프로젝트·Drive·다른 예약 변경 없음. 사용자 동의 없는 계정/OAuth·송출·녹화·채팅 발신·모델 훈련·권리 없는 음성·토큰 96·keep_alive 10m 임의 설정 없음.

### 이번 회차 실제 누적 개발
- 기존 `src/ai_broadcaster/obs_consecutive_audio.py`의 `collect_obs_input_meter_levels`에서 미터 콜백 시각이 관찰창 시작 전 또는 종료 후인데도 정상 관찰로 넘어가 뒤쪽 실제 표본과 결합할 수 있던 경로를 차단했다. 관찰창 경계 안에서 발생한 콜백만 연속 증거로 인정한다.
- `_관찰창_경로`에서 전후 경로가 동일하더라도 빈 문자열 또는 공백뿐인 문자열이면 미확정 경로로 판단한다. 기존 경로 객체 및 실제 값이 있는 문자열 경로의 비교 동작은 유지한다.
- 이미 실제 표본을 채택한 이후의 손상 관찰창은 이후 표본 결합을 중단한다. 아직 증거를 채택하지 않은 손상 관찰창은 건너뛰고 정상 창에서 시작할 수 있다. 관찰창 경계에 정확히 일치하는 실측 시각은 허용하며, 요청 조회구간 밖이라도 관찰창 안에 있는 정상 콜백은 손상으로 오인하지 않는다.
- 기존 소스 1개 수정: 코드 커밋 `d440bd9965d36f4d4af513b17669631554363e59`.
- 신규 `tests/test_aisting_obs_window_bounds_151.py`에 가상 계약검사 **9건 작성**: 테스트 커밋 `961827875c4f294917ad8e54bd9ebc7648572508`. 신규 검사 **직접 실행하지 않았으며** 실제 OBS·GPT-SoVITS·Cubism 실증 성공으로 보고하지 않는다.

### 확인한 기존 CI 실패와 미달
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): 4개 작업 성공, 한국어 공개 채팅 읽기 전용 작업 취소로 전체 **cancelled**. 취소 작업 로그는 BlobNotFound 404.
- 96절 실제 Ollama 500건 [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): **500/500 처리, 3초 초과 500/500**, 전체 p95 **2,979.984초**, FIFO 대기 p95 **2,973.875초**, AI p95 **7.875초**. 1~3초 목표 실패.
- 150절 코드 HEAD 전체 회귀 [40045977698](https://github.com/junggyeol4444/AISTING/actions/runs/40045977698): **cancelled**. Windows [40045977762](https://github.com/junggyeol4444/AISTING/actions/runs/40045977762): **cancelled**.
- 150절 실제 Ollama 500건 [40045977727](https://github.com/junggyeol4444/AISTING/actions/runs/40045977727): **500/500 처리**, 3초 초과 **497건**, 전체 p95 **1,294.343초**, FIFO 대기 p95 **1,291.421초**, AI p95 **3.015초**. 실제 시청자 500명이나 24시간 방송 실증이 아님.
- 150절 인수인계 HEAD 전체 회귀 [40046065041](https://github.com/junggyeol4444/AISTING/actions/runs/40046065041): **실패**, 2,639건 실행, **35건 실패·32건 오류·2건 건너뜀**. 실제 로그에 Twitch AI `twitch_ai_error` 대 `twitch_ai_ok`, 2,048건 FIFO 처리 예상 대비 0건, 작업자 진입 이벤트 미발생 등 기존 회귀 실패가 남아 있다.
- 150절 인수인계 HEAD Windows [40046065080](https://github.com/junggyeol4444/AISTING/actions/runs/40046065080): Windows EXE 작업 **cancelled**, 나머지 읽기 전용 4개 작업 성공. Windows 네이티브 EXE·GUI 통합 성공으로 처리하지 않는다.
- 151절 코드/테스트 커밋 이후 신규 CI는 이 기록 시점에 **확정 결과 미조회**. 다음 회차 최신 HEAD와 Actions 실행 번호를 재확인해야 한다.

### 완료·하지 않은 것·미완료·중단 및 다음 인계
- **완료:** 최신 main HEAD·96절 및 150절 CI 실패 로그 확인, 기존 OBS 실측 미터 경계·경로 공백 차단 코드 수정, 가상 계약검사 9건 작성, 기존 main fast-forward 커밋 2개 반영, 151절 누적 기록.
- **하지 않은 것:** 신규 가상 계약검사 직접 실행, 전체 회귀 통과, Windows 10/11 실제 EXE 실행·GUI 클릭·OBS·로컬 모델 통합검사, 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism 입 움직임→OBS 동일 발화 실증, 실제 4플랫폼 수백 명 무누락·24시간 안정성·시청자 1~3초 E2E 달성.
- **미완료:** 기존 전체 회귀 35실패·32오류 원인 수정과 전체 재검증, 권리 있는 실제 한국어 WAV→공식 Cubism→OBS 실증, 실제 수백 명·24시간, AI·음성·영상·시청자 1~3초 병목, Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검증.
- **진행 중 멈춘 것:** 신규 CI 최종 결과 확인, 사용자 권리 있는 음성 모델·공식 Cubism·OBS·실계정 환경에서의 실증. mock를 실사용으로 속이지 않는다.
- **다음 회차:** `junggyeol4444/AISTING/main` 최신 HEAD를 다시 확인하고 기존 1~151절 및 과거 부록 전체 원문을 유지하며 **AISTING만** 기존 코드 전체 개발을 이어간다. 개발 누적 완료 후 전체 회귀·Windows 실검사, 오류 시 수정 후 전체 재검증. 기존 매시간 예약 1개 유지·중복 생성 금지.
