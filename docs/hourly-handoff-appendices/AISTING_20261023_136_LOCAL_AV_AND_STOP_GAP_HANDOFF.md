## 136. 2026-10-23 19:27 KST — 공식 WAV·Cubism·OBS 로컬 지연 및 4플랫폼 중지 후 공백 동결 누적 개발

### 기존 원문과 시작 기준
- 시작 GitHub `junggyeol4444/AISTING/main` HEAD: `920baa6ff7fbd156dba986b737b2a830e129c556`(135절 문서 반영). 사용자 원문 1~97절 및 최신 135절, 기존 두 전체 인수인계 문서, 모든 기존 개별 부록은 수정·삭제·축약·교체하지 않는다. 이번 136절만 맨 뒤에 추가한다.
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`의 사용자 승인 대기 단계 및 원본 기획 유지. 기존 소스·캐릭터·SQLite·설정·모델·사용자 데이터와 GUI 동작, 실제 계정 권한·음성 사용권의 경계 유지. AISTING 외 저장소·Drive·예약·브랜치 변경 없음.

### 실제 누적 개발 및 GitHub 반영
- 실제 코드 커밋: `a5e3b5062658a5d2a81b738eaa0351df81ceb4e3`, 시작 HEAD의 단일 부모에서 기존 `main`을 `force=false` 및 `expected_sha` 일치로 fast-forward 갱신. 신규 브랜치/롤백/전면 재개발 없음.
- `src/ai_broadcaster/official_media_stage_timing.py`: 기존 승인된 단일 질문의 실제 monotonic 관측값에서 질문→OBS 선택 입력 첫 오디오, 질문→공식 Cubism 첫 입, **둘 모두 첫 신호가 관측된 시점의 로컬 경과**를 별도 산출. 둘 중 하나가 없거나 서로 다른 발화면 수치를 만들지 않고 `미측정`으로 남긴다. 로컬 3초 초과 여부 및 관측된 단일 최장 구간(질문→WAV, WAV→입, WAV→OBS)을 기존 GUI 지연 문구에 누적 표시한다. 두 후반 구간은 병렬이므로 인과관계나 시청자 E2E 병목을 추정하지 않는다.
- `src/ai_broadcaster/multi_platform_session.py`: 실제 읽기 전송 장애 중 사용자가 Stop을 누른 뒤에도 `reconnect_snapshot()`의 `관측공백초`가 영구 증가하고 `현재공백`이 계속 참으로 남는 상태 오류를 보완. 종료 시각에서 공백 시간을 동결하고 Stop 이후 현재 연결 공백 표시를 종료한다. 채팅 내용·ID·FIFO·기존 4플랫폼 재연결 정책은 변경하지 않았다.
- `tests/test_aisting_local_av_and_stop_gap_136.py` 신규 작성: 실제 측정 입력을 모사한 단위 시각으로 로컬 오디오/입 첫 신호 병렬 계산, 3초 초과와 최장 구간, OBS 동일 발화 미확인 시 미측정, 중지 이후 공백 동결을 검증하는 4건. **모의 단위검사 코드 작성은 실제 음성/OBS/수백 명/24시간 검증 성공이 아니다.**

### 기존 CI 최종 조회 및 실패 원문 보존
- 96절 Windows `39722213656`: `completed/cancelled`, 4개 job success·한국 공개 채팅 읽기 job cancelled. 성공으로 격상하지 않는다.
- 96절 실제 Ollama 500건 `39720448468`: `completed/success`, 합성 채팅 실제 로컬 모델 500/500 처리·실패 0이지만 **500/500건 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI 처리 p95 **7.875초**. 실제 시청자 500명이나 24시간 송출은 미검증.
- 135절 최종 문서 HEAD `920baa6...` 전체 회귀 `39933022177`: `completed/failure`, **26 failures·35 errors·2 skipped**. job `120345695503` 실제 로그에서 `_update_platform_health`, `_live_queue_wait_tracker`, `_live_ingress_lock` 없는 테스트 객체 오류, `transport_activity` 예상 차이, Twitch AI 이벤트 오류 등 확인. **미수정·전체 재검증 미통과**.
- 같은 HEAD Windows `39933022245`: 본 회차 조회 시 `in_progress`, `windows-exe` job `120345696255` 진행 중, OBS 읽기·Ollama 로컬·한국 공개 채팅·Twitch 공개 읽기 4개 job success. Windows 전체 통과 미확정.
- 135절 코드 `ae95b656...` 전체 회귀 `39932935581` 및 Windows `39932935705`: 후속 main 갱신으로 `completed/cancelled`; 실모델 500건 `39932935571`은 조회 시 `in_progress`, 최종 수치 미확정.
- 136절 **코드 커밋** CI 첫 조회: 전체 회귀 `39939631366` queued, Windows EXE `39939631472` pending, 실제 Ollama 500건 `39939631387` queued. 문서 추가 커밋으로 기존 push CI가 취소될 수 있으므로 최종 결과는 **문서 커밋 이후 최신 HEAD의 CI를 재조회**해야 한다. CI 미완료를 통과로 기록하지 않는다.

### 이번 회차 하지 않은 일·미완료·다음 재개
- 이번 회차는 **실제 소스 개발 및 4건의 단위검사 코드 작성, GitHub main 반영**을 완료. 신규 단위검사 실제 실행/Windows EXE 실제 버튼 조작/OBS 방송 출력/권리 확인된 한국어 GPT-SoVITS WAV 합성/공식 Cubism 실제 모델 립싱크·OBS 동일 발화 실증/실제 수백 명 4플랫폼 무누락/실제 24시간 운영/시청자 1~3초 E2E 달성은 **수행 또는 확인하지 않았다**. 모의 표본을 실제 시청각 증거로 주장하지 않는다.
- 남은 작업: 기존 공식 WAV→Cubism→OBS 동일 발화 출력 및 시간/음량 실증, 4플랫폼 실제 수백 건·수백 명 무누락과 24시간 재연결/안전성, 500건 FIFO 적체·AI/음성/영상 지연 병목 실질 개선, **전체 소스 개발 완성 후 전체 회귀·Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검사 → 오류 수정 → 전체 재검증**. 기존 26 failures·35 errors는 해결했다고 주장하지 않는다.
- 다음 회차: **그 시점의 main HEAD를 다시 확인**하고 본 1~136절 및 기존 개별 부록 원문, 원본 계획/로드맵과 실제 main 소스를 이어 읽는다. `39939631366`, `39939631472`, `39939631387`, `39933022245`, `39932935571`의 최종 상태/실패 로그부터 조회한다. 사용자 동의 없는 OAuth·계정 접근·방송/녹화·채팅 발신·모델 훈련·권리 없는 보이스·토큰 길이 96/keep_alive 10m 설정 변경 금지. 기존 매시간 예약은 중복 생성하거나 변경하지 않는다.
