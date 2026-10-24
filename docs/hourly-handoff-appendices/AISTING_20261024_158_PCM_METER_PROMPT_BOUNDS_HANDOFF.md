## 158. 2026-10-24 — 공식 WAV·Cubism 입 구간과 OBS 미터 비교 시간의 교집합 보존

### 시작 HEAD 및 사용자 원문 보존
- 시작 `main`: `7d7f029c2a33f703797e87ec8bb09ddee382e746`. 1~157절 전체 인수인계와 과거 부록·기획·로드맵·SQLite·설정·캐릭터를 삭제·축약·초기화하지 않는다.
- 사용자 지시 순서: 기존 AISTING 개발 우선 → 전체 회귀 및 Windows 네이티브 EXE·GUI·OBS·로컬 모델 통합검증 → 오류 수정·전체 재검증. 다른 프로젝트·브랜치·Drive·예약은 변경하지 않는다.

### 이번 회차 실제 개발
- `src/ai_broadcaster/original_plan_full_pipeline.py`의 공식 WAV→OBS 음량 비교 경로에 `_current_prompt_pcm_meter_bounds`를 추가했다. 공식 WAV 수신·질문·Cubism 입 움직임의 실제 monotonic 시간 교집합과 기존 0.2초 근접 허용 범위 안의 OBS 미터만 비교 대상으로 수집한다.
- 기존에는 채택된 OBS 관찰창 안에만 있으면 입 움직임이 끝난 뒤의 다른 입력 소리도 WAV 상관 후보로 들어갈 수 있었다. 이제 WAV 수신 전·질문 종료 뒤·입 움직임에서 0.2초 이상 떨어진 미터는 비교 대상에서 제외한다. 기존 WAV 비교의 12초 상한, 0~3초 후보 지연, OBS 관찰창 출처 필터는 유지한다.
- `tests/test_aisting_current_prompt_meter_bounds_158.py`에 가상 시간·미터 계약검사 10건을 작성했다. **작성은 실제 GPT-SoVITS·공식 Cubism·OBS 실증 또는 테스트 통과가 아니다.**
- 기존 원본 소스/문서/설정/캐릭터/SQLite 변경·삭제 없음. 새 브랜치·force push·롤백 없음. OBS 송출·녹화·채팅 발신·OAuth 동의·권리 없는 음성·모델 훈련·임의 토큰/keep_alive 변경 없음.

### 기존 CI 실측과 실패 기록
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): 전체 `completed/cancelled`; 개별 windows-exe 작업 성공을 전체 성공으로 보고하지 않는다.
- 96절 실제 Ollama 500건 [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): 500/500, 실패 0, **3초 초과 500건**, 전체 p95 2,979.984초, FIFO p95 2,973.875초, AI p95 7.875초.
- 157회차 전체 회귀 [40074935603](https://github.com/junggyeol4444/AISTING/actions/runs/40074935603): **2,692건, 실패 36·오류 31·건너뜀 2**로 실패. 기존 Twitch FIFO/종료 및 공식 OBS 경로 실패가 계속 남아 있다.
- 157회차 Windows [40074935568](https://github.com/junggyeol4444/AISTING/actions/runs/40074935568): 조회 시 `in_progress`, windows-exe 작업 진행 중. 완료·실기기 성공으로 단정하지 않는다.
- 157회차 실제 Ollama 500건 [40074799643](https://github.com/junggyeol4444/AISTING/actions/runs/40074799643): 500/500·실패 0, **3초 초과 497건**, 전체 p95 1,159.766초, FIFO p95 1,157.235초, AI p95 2.625초. 실제 시청자 500명 실증 아님. **1~3초 E2E 목표 미달**.

### 완료·안 한 것·미완료·진행 중 멈춘 것·다음 인계
- **실제 완료:** 공식 WAV/입/질문/OBS 미터 비교 범위 누적 개발, 가상 계약검사 10건 작성, 과거 원문 뒤 158절 추가.
- **안 한 것:** 신규 테스트 직접 실행, 전체 회귀 통과, 실제 Windows 10/11 GUI·OBS·권리 확인 한국어 GPT-SoVITS·공식 Cubism 동일 발화 실증, 실제 4플랫폼 수백 명, 실제 24시간 재연결, 시청자 1~3초 달성.
- **미완료:** 기존 36 실패·31 오류, Windows EXE 완료 확인, 음성·입·OBS 실측, 4플랫폼 무누락, 24시간 안정성, FIFO 장기 대기 병목, Windows 통합검증·수정 후 전체 재검증.
- **진행 중 멈춘 것:** 신규 코드 CI 완료/실패 로그 확인, Windows/실모델/실계정 환경이 필요한 검증.
- **다음 회차:** 반드시 현재 main HEAD와 158회차 신규 CI를 재조회한다. 1~158절 원문과 과거 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 main 소스를 기준으로 개발 우선 진행하고 전체 검증·수정을 이어간다. 기존 예약 유지, 새 예약 생성 금지.
