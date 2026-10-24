# AISTING 150회차 — OBS 손상 오디오 관찰창 연속성 차단

## 150. 2026-10-24 — OBS 손상 오디오 관찰창을 정상 무음으로 오인한 연속 증거 결합 차단

### 시작 기준과 원문 보존
- 시작 `junggyeol4444/AISTING/main` HEAD: `39c4c7a563c706e59f160e6d222de4b7311f01a5` (149회차).
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 기존 1~149절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 기존 전체, `docs/hourly-handoff-appendices/` 과거 원문(특히 97절), `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 코드·캐릭터·SQLite·설정을 유지하고 150절만 뒤에 추가한다.
- 사용자 지정 모델·토큰·keep_alive 변경, 신규 브랜치·강제 갱신·롤백·전면 재개발·다른 프로젝트·Drive·다른 예약 변경·무단 계정/OAuth 동의·방송·녹화·채팅 발신·모델 훈련·권리 없는 보이스 사용 없음.

### 이번 회차 실제 누적 개발
- 기존 `src/ai_broadcaster/obs_consecutive_audio.py`의 두 실측 수집 함수에서, 앞쪽 OBS 실제 오디오/미터 표본이 이미 채택된 뒤 중간 관찰창의 오디오 객체가 누락되거나 신호 메타데이터가 일부만 존재·시각 역행·범위 이탈하는 경우 뒤쪽 표본을 같은 발화로 이어 붙이지 않도록 변경했다.
- OBS 입력 미터 관찰에서 중간창 레벨 자료의 형식 오류·값 오류·시간 역행 역시 이후 표본 결합을 중단한다.
- 실제 정상 무음(첫·마지막 신호 시각 없음, 표본 빈 튜플; 미터 빈 튜플) 구간은 기존처럼 연속성을 유지한다. 메타데이터는 정상이지만 해당 입 움직임 밖에 있는 소리는 손상으로 오인하지 않고 후보에서만 제외한다. 관측 전 손상 창은 이후 첫 정상 관측을 막지 않는다. 표본 보간이나 가짜 OBS·음성 출력은 추가하지 않았다.
- 신규 `tests/test_aisting_obs_corrupt_window_150.py` 가상 계약검사 8건 작성. **직접 실행하지 않았으며 실제 WAV/Cubism/OBS 실증이 아니다.**
- 기존 main의 단일 부모로 코드 커밋 `e59306e039caf48cadcc4987c2fc4a5bf0328473` 생성, GitHub 비교 `ahead_by=1, behind_by=0` 확인 후 `force=false`, `expected_sha=39c4c7a...` 조건으로 fast-forward 반영했다. 기존 소스 1개 수정, 신규 테스트 1개 추가.

### CI 및 과거 실패를 숨기지 않은 확인
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): **completed/cancelled**. 5개 작업 중 4개 성공, 공개 한국어 채팅 읽기 전용 작업 취소. 취소 작업 로그는 과거 조회에서 404 BlobNotFound; 전체 통과가 아니다.
- 96절 실제 Ollama 500건 CI [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): **completed/success**. 500/500 처리·모델 실패 0이나 **3초 초과 500/500**, 로컬 전체 p95 **2,979.984초**, FIFO 대기 p95 **2,973.875초**, AI p95 **7.875초**. 실제 시청자 500명/24시간/1~3초 달성 증거 아님.
- 148회차 전체 회귀 [40034588786](https://github.com/junggyeol4444/AISTING/actions/runs/40034588786): **failure**. 2,625건 중 35건 실패·32건 오류·2건 건너뜀. Windows [40034588842](https://github.com/junggyeol4444/AISTING/actions/runs/40034588842): **cancelled**. 실제 Ollama 500건 [40034487419](https://github.com/junggyeol4444/AISTING/actions/runs/40034487419): **success**이나 500/500 3초 초과, 전체 p95 2,756.000초, FIFO 대기 p95 2,750.140초.
- 149회차 코드 HEAD CI: 전체 회귀 [40040228377](https://github.com/junggyeol4444/AISTING/actions/runs/40040228377) **cancelled**, Windows [40040228280](https://github.com/junggyeol4444/AISTING/actions/runs/40040228280) **cancelled**, 실제 Ollama 500건 [40040228154](https://github.com/junggyeol4444/AISTING/actions/runs/40040228154) **success**이나 500/500 3초 초과, 전체 p95 **2,718.375초**, FIFO 대기 p95 **2,712.578초**, AI p95 **5.938초**.
- 149회차 최종 인수인계 HEAD 전체 회귀 [40040291861](https://github.com/junggyeol4444/AISTING/actions/runs/40040291861): **failure**. 2,631건 실행, 35건 실패·32건 오류·2건 건너뜀. 기존 Twitch AI 처리 계약의 `twitch_ai_error` 대 `twitch_ai_ok`, FIFO 2,048건 예상 대비 0건 처리 등 미수정 실패. Windows [40040291779](https://github.com/junggyeol4444/AISTING/actions/runs/40040291779): **cancelled**.
- 150회차 코드 HEAD `e59306e039caf48cadcc4987c2fc4a5bf0328473`의 신규 CI: 전체 회귀 [40045977698](https://github.com/junggyeol4444/AISTING/actions/runs/40045977698), Windows [40045977762](https://github.com/junggyeol4444/AISTING/actions/runs/40045977762), 실제 Ollama 500건 [40045977727](https://github.com/junggyeol4444/AISTING/actions/runs/40045977727) — 기록 시 **queued**, 통과 주장 금지. 인수인계 문서 커밋 이후 별도 CI가 생성될 수 있으므로 다음 회차 최신 HEAD 및 모든 신규 run 확인.

### 완료·미완료·진행 중 멈춘 것·다음 회차 인계
- **완료:** 최신 main HEAD·96절 Windows/실모델 로그·148~149회차 CI 상태 확인, 기존 OBS 오디오·미터 수집 경로 손상창 연속성 차단 실제 코드 개발, 가상 계약검사 8건 작성, 안전한 fast-forward 코드 반영, 150절 인수인계 누적.
- **하지 않은 것:** 신규 가상 검사 직접 실행, 전체 회귀 성공 확인, Windows 10/11 실제 EXE·GUI 버튼·OBS·로컬 모델 실사용 통합검증, 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism 입 움직임→OBS 같은 발화 영상·음성 실증, 실제 4플랫폼 수백 명 무누락·24시간 방송·시청자 1~3초 E2E 실증. 실계정 동의·채팅 발신·송출·녹화·모델 훈련은 실행하지 않았다.
- **미완료:** 기존 회귀 35실패·32오류 원인 수정과 전체 재검증, 권리 있는 한국어 WAV→공식 Cubism→OBS 동일 발화 실증, 실제 4플랫폼 수백 명·24시간 안정성, 1~3초 응답 병목 해소, Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검증.
- **진행 중 멈춘 것:** 150회차 CI 결과 확정 대기, 실제 사용자 권리 모델·공식 Cubism·OBS·실계정 환경이 필요한 실증. 모의 검사와 실제 방송 증거는 구별한다.
- **다음 회차 시작:** `junggyeol4444/AISTING/main`의 **이 150절을 포함하는 최신 HEAD**를 다시 확인한다. 코드 HEAD는 `e59306e039caf48cadcc4987c2fc4a5bf0328473`; 문서 반영 HEAD는 이 절을 포함한 main 커밋이다. 위 CI 최종 상태/실패 로그를 확인하고 기존 1~150절 및 모든 과거 원문을 보존하여 **AISTING만** 실제 누적 개발을 우선 계속한다. 전체 개발 후 전체 회귀·Windows 실검증, 오류 시 수정 후 전체 재검증. 기존 매시간 예약 1개 유지·중복 생성 금지.
