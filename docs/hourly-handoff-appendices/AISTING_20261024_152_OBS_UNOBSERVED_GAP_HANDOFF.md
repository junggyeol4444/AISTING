# AISTING 152회차 — OBS 무관측 공백 차단

## 152. 2026-10-24 — OBS 무관측 시간 공백을 동일 발화의 연속 오디오 증거로 합치지 않도록 개발

### 시작 기준·원문 보존
- 시작 `main` HEAD: `e42fda67ee93b57e107bc2e112803f02d43fc463` (151절 인수인계 포함). 기존 1~151절 전체 원문, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 원문, `docs/hourly-handoff-appendices/` 과거 원문(특히 97절), `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 원본 소스·캐릭터·SQLite·설정은 삭제·초기화하지 않았다.
- 새 브랜치·force push·롤백·전면 재개발·다른 프로젝트·Drive·다른 예약 변경 없음. 실계정 OAuth 동의 대행·채팅 발신·방송·녹화·모델 훈련·권리 없는 음성 사용 없음. 토큰 길이 96·keep_alive 10m 등 사용자 요청 없는 설정 변경 없음.

### 이번 회차 실제 누적 개발
- 기존 `src/ai_broadcaster/obs_consecutive_audio.py`의 `collect_obs_audio_times`와 `collect_obs_input_meter_levels`에 관찰창의 **연속 관측 종료 범위**를 누적하도록 개발했다. 앞쪽 실제 오디오 또는 미터 표본을 채택한 뒤 다음 관찰창 시작 시각이 앞서 확인된 관측 종료 시각보다 늦으면, 그 사이에 OBS 입력·장면·트랙이 바뀌지 않았음을 확인할 수 없으므로 뒤쪽 표본을 같은 발화로 합치지 않는다.
- 겹치는 관찰창과 종료/시작 경계가 정확히 맞닿는 관찰창은 유지한다. 겹치는 짧은 창이 들어와도 기존의 더 긴 실제 관찰 종료 범위를 축소하지 않도록 `max`로 유지한다. 정상 무음 창도 연속 관찰 범위에 포함한다. 첫 실제 표본을 얻기 전의 공백은 다음 정상 창의 첫 증거 채택을 차단하지 않는다.
- 코드 커밋 `6252a4f14f27ae3b6157fb4d541bc5f77b5f6c99`, 신규 가상 계약검사 7건 `tests/test_aisting_obs_unobserved_gap_152.py` 추가 커밋 `72ba88ed890b6735da3c5534227277be659ad604`. 시작 HEAD 대비 GitHub 비교 `ahead_by=2, behind_by=0`으로 기존 main의 fast-forward 누적을 확인했다.
- **이번 7건은 작성만 했고 직접 실행하지 않았다.** 실제 WAV·Cubism·OBS·시청자 실증으로 간주하지 않는다. 기존 실패를 숨기지 않고 개발 우선 순서를 유지한다.

### 실제 조회한 과거 CI·실패
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): 5개 작업 중 4개 성공, `korean-public-chat-readonly` 취소로 전체 취소. 취소 작업 로그 직접 재조회는 **404 BlobNotFound**.
- 96절 실제 Ollama 500건 [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): 실제 작업 로그 재조회로 500/500 처리, **500건 전부 3초 초과**, 전체 p95 **2,979.984초**, FIFO 대기 p95 **2,973.875초**, AI p95 **7.875초**, `passed_three_second_local=false` 확인. 합성 채팅+실제 로컬 모델이며 실제 시청자 500명·24시간 방송이 아니다.
- 150절 전체 회귀 [40046065041](https://github.com/junggyeol4444/AISTING/actions/runs/40046065041): 실제 `validate` 작업 로그에서 **2,639건 실행, 35실패·32오류·2건 건너뜀** 확인. Twitch AI `twitch_ai_error` 대 `twitch_ai_ok` 불일치, FIFO 2,048건 예상 대비 0건, OBS 동일 발화·관찰 준비 관련 실패가 남아 있다.
- 151절 및 152절 새 Actions 실행 번호·최종 상태는 이번 회차에 **조회 확정하지 못했다**. 최신 CI 통과를 주장하지 않는다. 다음 실행에서 현재 `main` HEAD 및 최신 Actions 실행 번호·실패 로그를 다시 확인한다.

### 완료·하지 않은 것·미완료·중단·다음 인계
- **완료:** 최신 main HEAD 확인, 원본 기획·로드맵·설정·151절까지의 누적 인수인계 및 기존 OBS 소스 확인, 96절 두 CI 작업 로그 재조회, 150절 전체 회귀 실패 로그 확인, 실제 OBS 관찰 공백 차단 코드 개발, 가상 계약검사 7건 작성, main fast-forward 반영, 152절 누적 인수인계.
- **하지 않은 것:** 신규 검사 실행/통과 판정, 전체 회귀 통과, Windows 10/11 네이티브 EXE·GUI 버튼·OBS·로컬 모델 실사용 통합검사, 권리 확인된 실제 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 입 움직임→OBS 같은 발화 실증, 4플랫폼 실제 수백 명 무누락·24시간 방송·시청자 1~3초 달성.
- **미완료:** 기존 회귀 35실패·32오류 원인 수정과 전체 재검증, 실제 권리 있는 한국어 음성·공식 Cubism·OBS 동일 발화 검증, 실제 4플랫폼 수백 명/24시간 재연결·안전성, FIFO/AI/음성/영상/시청자 1~3초 병목, Windows 네이티브 EXE/GUI 통합검증.
- **진행 중 멈춘 것:** 151·152절 신규 CI 상태 조회 및 사용자 권리 모델·실계정·공식 Cubism·OBS 실제 환경에서만 가능한 실증. mock를 실사용으로 보고하지 않는다.
- **다음 시작 기준:** `junggyeol4444/AISTING/main`의 **152절 문서 커밋을 포함한 최신 HEAD를 다시 조회**한다. 코드·검사 HEAD는 `72ba88ed890b6735da3c5534227277be659ad604`; 문서 반영 후 최종 HEAD는 별도 조회한다. 기존 1~152절 전체와 과거 부록 원문을 보존하고 AISTING 실제 개발 우선, 전체 개발 완료 후 전체 회귀·Windows 통합검사, 오류 시 수정 후 전체 재검증한다. 기존 매시간 예약은 중복 생성하지 않는다.
