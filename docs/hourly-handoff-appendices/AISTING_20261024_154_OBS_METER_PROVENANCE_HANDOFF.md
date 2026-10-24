# AISTING 154회차 원문 누적 인수인계

## 154. 2026-10-24 — 실제 채택 OBS 관찰창에 한정한 공식 WAV·OBS 미터 출처 결합 개발

### 원문·시작 HEAD·금지사항 보존
- 시작 main HEAD: `ff8c63c5b6f98ea8192f2ae481d8ca7099e8e335` (153절 전체 포함). 1~153절 전체 원문과 과거 부록(특히 97절), `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 기존 소스의 현 상태를 확인했다. 원본 문서는 삭제·요약 대체·재작성하지 않고 끝에 이 절을 추가한다.
- 새 브랜치·force push·롤백·전면 재개발·다른 프로젝트·Drive·다른 예약 변경 없음. 캐릭터·SQLite·설정·기획·원본 소스 삭제/초기화 없음. 계정/OAuth 동의 대행, 방송·녹화·채팅 발신, 무단 모델 훈련·권리 없는 음성 사용 없음. 토큰 길이 96 또는 keep_alive 10m 임의 변경 없음.

### 이번 회차 실제 누적 개발
- 기존 `src/ai_broadcaster/obs_consecutive_audio.py`의 `collect_obs_input_meter_levels`에 선택적 `accepted_window_indices` 인수를 추가했다. 공식 WAV와 OBS 입력 미터 음량 상관을 계산할 때, 실제 선택 오디오 양성 표본이 채택된 OBS 관찰창의 **원래 순번**만 사용한다. 이전·이후 다른 경로의 미터 레벨을 섞지 않고, 기존 경로·시간 연속성 검사 및 실측값만 보존한다. 인수가 없는 기존 호출 계약은 그대로 유지한다. 빈 순번·중복·역순·불량 순번은 거절한다.
- 기존 `src/ai_broadcaster/original_plan_full_pipeline.py`에 `_matched_obs_audio_evidence`를 추가해 기존 채택 표본·후보와 함께 채택 창 순번을 반환한다. 기존 `_matched_obs_audio_candidates`의 3개 반환값 계약은 래퍼로 유지한다. 실제 승인 단일 질문 경로에서 공식 PCM16 WAV와 OBS 미터 상관 계산에 **같은 채택 창 순번**을 전달하도록 연결했다. 별도 음성 합성·재생·방송·녹화·채팅 발신을 시작하지 않는다.
- 가상 객체 계약검사 `tests/test_aisting_obs_meter_provenance_154.py` 7건 작성: 기존 호출 호환, 첫 채택 전 다른 경로 제외, 경로 변경 후 복귀 제외, 정상 연속 두 창 유지, 미채택 시 미터 대체 금지, 잘못된 순번 거절, 기존 3개 반환값 호환. **작성만 했으며 직접 실행·통과 확인하지 않았다.** 이는 실OBS·실모델·시청자 실증이 아니다.
- 코드 개발 커밋: `02933d1cdb42495ede568d0dc0441c3c6fb2df25`. 기존 main을 단일 부모로 하여 force 없이 fast-forward 갱신. 변경은 기존 소스 2개와 신규 가상 계약검사 1개로 한정한다.

### 실제 확인한 기존 CI 및 실패 내용
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): `completed/cancelled`. 작업 5개 중 4개 성공·공개 한국어 채팅 읽기 1개 취소. 취소된 작업의 로그가 없어 전체 성공으로 취급하지 않는다.
- 96절 실제 Ollama 500건 [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): `completed/success`이지만 합성 채팅 500/500건 **모두 3초 초과**, 전체 p95 2,979.984초, FIFO 대기 p95 2,973.875초, AI 처리 p95 7.875초. 실제 수백 명 시청자·24시간 방송이나 1~3초 달성의 증거가 아니다.
- 153절 전체 회귀 [40059160672](https://github.com/junggyeol4444/AISTING/actions/runs/40059160672): `completed/failure`. 2,662건 실행, **36건 실패·31건 오류·2건 건너뜀**. Twitch AI/FIFO/OBS 관련 기존 실패가 여전히 존재한다. 구 CI 실패를 숨기거나 신규 코드로 해결됐다고 보고하지 않는다.
- 153절 Windows EXE [40059160706](https://github.com/junggyeol4444/AISTING/actions/runs/40059160706): `completed/cancelled`. Windows 네이티브 EXE/GUI·OBS 통합 성공 미확인.
- 152절 실제 Ollama 500건 [40054343542](https://github.com/junggyeol4444/AISTING/actions/runs/40054343542): `completed/success`. 상세 지연 수치는 이번 회차 별도 로그 재집계하지 않았다. 153절 실모델 [40059089187](https://github.com/junggyeol4444/AISTING/actions/runs/40059089187)은 마지막 조회 당시 `in_progress`였다.
- 154절 코드 HEAD `02933d1c` 신규 CI: [전체 회귀 40063169941](https://github.com/junggyeol4444/AISTING/actions/runs/40063169941), [Windows EXE 40063169930](https://github.com/junggyeol4444/AISTING/actions/runs/40063169930), [실제 Ollama 500건 40063169931](https://github.com/junggyeol4444/AISTING/actions/runs/40063169931) 모두 마지막 조회 당시 `queued`. 신규 검사 실행·성공 또는 실기기 검증 성공으로 보고하지 않는다.

### 완료·하지 않은 것·남은 것·진행 중 멈춘 것·다음 인계
- **완료:** 최신 main HEAD 및 원본 기획·로드맵·설정·인수인계 확인, 필수 96절 CI 로그 확인, 153절 실패·취소 확인, 채택 OBS 오디오 창→공식 WAV·OBS 미터 출처를 실제 기존 파이프라인에 연결한 소스 2개 누적 개발, 신규 가상 계약검사 7건 작성, main 안전 fast-forward 코드 반영, 154절 원문 누적 인수인계.
- **하지 않은 것:** 신규 검사 직접 실행/통과 확인, 전체 회귀 통과, Windows 10/11 EXE/GUI 버튼·실제 OBS·로컬 모델 통합검증, 권리 확인된 실제 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 입 움직임→OBS 동일 발화 실증, 실제 4플랫폼 수백 명 무누락·24시간 방송·시청자 1~3초 달성. 가상 객체를 실사용으로 속이지 않는다.
- **미완료:** 기존 회귀 36실패·31오류 원인 수정/전체 재검증, 실제 권리 보유 보이스·공식 Cubism·OBS 동일 발화 오디오/영상 실증, 4플랫폼 실제 수백 명 무누락, 24시간 재연결/안전성, FIFO·AI·음성·영상·시청자 E2E 1~3초 병목, Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검증.
- **진행 중 멈춘 것:** 153절 실제 Ollama 500건 완료 여부/최종 로그, 154절 3개 신규 CI 최종 상태, 실제 권리 모델·계정·공식 Cubism/OBS 환경이 필요한 실증. 구 버전 CI 실패는 그대로 남긴다.
- **다음 시작 기준:** `junggyeol4444/AISTING/main` 최신 HEAD를 다시 확인하고 154절 인수인계 커밋의 실제 HEAD 및 신규 CI를 확인한다. 기존 1~154절 전체 원문·모든 부록·기획·로드맵·설정·캐릭터·SQLite·소스를 보존하고 AISTING 기존 코드 전체 개발 우선→전체 회귀/Windows 실검증→오류 수정·전체 재검증 순서를 유지한다. 기존 매시간 예약을 새로 만들거나 다른 예약을 수정하지 않는다.

