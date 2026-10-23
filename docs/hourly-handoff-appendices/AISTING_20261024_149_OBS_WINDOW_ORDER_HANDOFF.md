# AISTING 149회차 — OBS 연속 관찰창 시간 역행 차단

## 149. 2026-10-24 — 같은 경로라도 과거 시각으로 되돌아간 OBS 관찰창의 오디오 증거 결합 차단

### 시작 HEAD와 원문·사용자 지시 보존
- 시작 GitHub `junggyeol4444/AISTING/main` HEAD: `951a1f1067eb70bf7d777dbeab030e89f5a15324` (148회차).
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 기존 1~148절과 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체 및 `docs/hourly-handoff-appendices/`의 기존 모든 과거 원문, 특히 97절 원문을 삭제·요약 대체하지 않고 뒤에 149절만 추가한다.
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 main 실제 소스와 캐릭터·SQLite·설정·모델 선택을 보존한다. 사용자 지시 없는 토큰 길이 96, keep_alive 10m, 새 기능, 모델 교체를 하지 않았다.
- 새 브랜치·force push·롤백·전면 재개발·다른 프로젝트/Drive/다른 예약 변경·무단 OAuth·계정 동의·송출·녹화·채팅 발신·모델 훈련·권리 없는 음성 사용을 하지 않았다.

### 실제 누적 개발
- 기존 `src/ai_broadcaster/obs_consecutive_audio.py`의 `collect_obs_audio_times`와 `collect_obs_input_meter_levels`에 **관찰창 시작 시각의 순서 검증**을 누적 추가했다.
- 동일 OBS 입력·장면·트랙 경로라도 뒤에 온 관찰창의 시작 시각이 앞서 확정된 창의 시작 시각보다 과거로 역행하면, 그 창과 그 뒤의 표본을 같은 발화의 시간순 오디오 증거로 결합하지 않는다.
- 정상적으로 시작 시각이 증가하는 겹친 관찰창은 유지하며, 이미 실측한 표본만 중복 제거한다. 무음 관찰창도 시작 시각 연속성 검증에 포함한다. 첫 유효 표본을 확보하기 전의 불명확한 창은 이후 정상 표본 수집을 막지 않는다.
- `tests/test_aisting_obs_window_order_149.py` 신규 가상 계약검사 6건 작성: 정상 겹침, 시간 역행 시 오디오 차단, 시간 역행 시 미터 차단, 무음 중간창 이후 역행 오디오/미터 차단, 첫 유효 표본 이전 불명확한 창 처리.
- **실제 코드 커밋:** `4c3e53e63504ab0e47efd8f77a23891d47df6770`. 기존 main `951a1f1067eb70bf7d777dbeab030e89f5a15324`의 단일 부모로 커밋하고 `force=false` 및 예상 HEAD 일치 조건으로 fast-forward 갱신했다. 기존 소스 1개 수정, 신규 테스트 1개 추가.
- 신규 가상 계약검사 6건은 **작성했으나 직접 실행하지 않았다**. 실제 Windows/OBS/Cubism/WAV 출력 성공이라고 주장하지 않는다.

### CI 실제 상태·실패 기록
- 96절 Windows CI `39722213656`: **completed/cancelled**. 5개 작업 중 4개 성공, `korean-public-chat-readonly` 취소. 해당 취소 작업 로그 `119638028931` 재조회는 **404 BlobNotFound**. 전체 통과 아님.
- 96절 실제 Ollama 500건 CI `39720448468`: **completed/success**. 실제 모델로 합성 채팅 500/500 처리, 모델 실패 0, **500건 모두 3초 초과**, 로컬 전체 p95 **2,979.984초**, FIFO 대기 p95 **2,973.875초**, AI p95 **7.875초**. 실제 시청자 500명·24시간·1~3초 검증 성공 아님.
- 148회차 최종 HEAD 전체 회귀 `40034588786`: **completed/failure**. 실제 로그 **2,625건 실행, 35건 실패·32건 오류·2건 건너뜀**. 예: 기존 Twitch AI 통합 계약검사의 `twitch_ai_error` 대 `twitch_ai_ok` 불일치 및 FIFO 2,048건 예상 대비 0건 처리. 구 버전 실패를 숨기지 않는다.
- 148회차 Windows CI `40034588842`: 마지막 조회 시 **in_progress**, 4개 작업 성공·`windows-exe` 진행 중. 148회차 코드 HEAD 실제 Ollama 500건 `40034487419`: 마지막 조회 시 **in_progress**.
- 149회차 **코드 HEAD** `4c3e53e63504ab0e47efd8f77a23891d47df6770`의 신규 CI: 전체 회귀 `40040228377` **queued**, Windows EXE `40040228280` **pending**, 실제 Ollama 500건 `40040228154` **queued** (2026-10-24 08:30 KST 전후 확인). 이후 문서 인수인계 커밋의 CI는 다음 실행에서 별도로 확인한다.

### 완료·하지 않은 것·남은 것·중단 상태·다음 인계
- **이번 회차 완료:** 현재 main HEAD 및 96절 CI/실제 실패 로그 재확인, 148회차 실패 CI 로그 확인, OBS 실제 소스의 관찰창 시간 역행 방지 개발, 신규 가상 계약검사 6건 작성, 기존 main fast-forward 코드 반영, 기존 인수인계 원문 뒤에 149절 추가.
- **하지 않은 것:** 신규 검사 실행·통과 판정, 전체 회귀 성공, Windows 10/11 실기기 EXE 실행→GUI 버튼→OBS 실증, 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 실제 입→OBS 동일 발화 오디오/영상 출력 실증, 실제 4플랫폼 수백 명·24시간 방송, 실계정 OAuth 동의·송출·녹화·채팅 발신·모델 훈련.
- **미완료:** 기존 전체 회귀 35실패·32오류의 원인 수정 후 전체 재검증, 실제 권리 있는 WAV·공식 Cubism·OBS 동시 출력 실증, 4플랫폼 실제 수백 명 무누락, 실제 24시간 재연결/안전성, 시청자 1~3초 E2E 달성, Windows 네이티브 EXE/GUI·OBS·로컬 모델 전체 통합검사.
- **진행 중 멈춘 것:** 148·149회차 CI 최종 결과 확인, 권리 있는 한국어 음성 모델 및 사용자 Windows OBS/Cubism/실계정 환경이 필요한 실증. 무단 외부 동작은 하지 않는다.
- **다음 회차:** GitHub 현재 main HEAD를 새로 확인하고 96절 및 148·149회차 CI 최종 상태·실패 로그를 확인한다. 기존 1~149절·모든 과거 부록·기획·로드맵·설정·기존 실제 소스를 그대로 보존하고 AISTING 전체 누적 개발 우선, 이후 전체 회귀 및 Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검사, 실패 시 수정 후 전체 재검증한다. 다음 시작 기준은 **이 149절을 포함한 main 최신 HEAD**이며, 코드 HEAD는 위 `4c3e53e...`이다. 매시간 예약 1개 유지·중복 생성 금지.
