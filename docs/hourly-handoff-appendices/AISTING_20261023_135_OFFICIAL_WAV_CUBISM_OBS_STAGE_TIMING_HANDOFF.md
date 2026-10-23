## 135. 2026-10-23 18:33 KST — 공식 WAV→Cubism 입→OBS 단계별 관측 지연 누적 개발

### 시작 상태와 원문 보존
- 실제 시작 main HEAD: `8bd4a8b9c206db1209a221fa98ca7a3d95559c13`(134절). 기존 1~134절과 1~97절 원문, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 과거 `docs/hourly-handoff-appendices/` 전체, 특히 97절 개별 원문을 수정·삭제·요약 대체하지 않았다.
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 현재 main의 공식 AI/음성/Cubism/OBS 코드와 실제 4플랫폼 FIFO 소스를 읽고 AISTING만 개발했다. 사용자 설정·캐릭터·SQLite·기존 모델 설정은 변경하지 않았다.

### 실제 개발 완료·main 반영
- 코드 커밋 `ae95b6564f05a8d56b956a7b9d13acf93ecad734`를 기존 main에서 **force=false·expected_sha 일치 fast-forward**로 반영. 신규 브랜치·롤백·재개발 없음.
- `src/ai_broadcaster/official_media_stage_timing.py` 추가: 이미 승인된 공식 단일 질문에서 **실제로 관측된 monotonic 시각**만으로 질문→공식 WAV 최초 수신, WAV→Cubism 최초 입, WAV→OBS 최초 입력 미터, OBS 첫 입력−Cubism 첫 입의 네 구간을 독립 측정. 서로 다른 질문·역행 시각·미확인 중첩은 **미측정**으로 보존. OBS가 입보다 먼저 관측된 경우 음수 부호를 보존. 음성 원본·채팅·계정 정보 저장 없음.
- `src/ai_broadcaster/original_plan_full_pipeline.py` 기존 공식 Live2D/OBS 단일 질문 관측 경로에 새 계측을 **누적 연결**하고 Windows GUI에 기존 `latency_summary_ko`로 표기. OBS 방송/녹화·장면 변경 사전 차단과 기존 음성 권리·운영자 승인 검사, WAV/OBS 상관 비교, 모델·설정·발화 순서는 그대로 유지. 새 계측은 **실제 WAV/OBS 재생 또는 시청자 1~3초 달성 증명이 아님**.
- `tests/test_aisting_official_media_stage_timing_135.py`에 단위 검사 5건 작성. 동일 계산 로직의 별도 로컬 단위 검사 5건 통과했지만 **GitHub main 통합 회귀·Windows 네이티브 EXE·실제 GPT-SoVITS/공식 Cubism/OBS 검사 성공은 아직 미확인**. 단위 모의 시각을 실제 방송 증거로 보고하지 않는다.

### CI 최종 조회·실패 로그 원문 보존
- 96절 Windows `39722213656`: `completed/cancelled`; 4개 job 성공, 한국 공개 채팅 읽기 job 취소. 96절 실모델 `39720448468`: `completed/success`, 합성 채팅 실제 Ollama 500/500 처리·오류 0건이지만 **500/500건 모두 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI p95 **7.875초**. 실제 500명·24시간 송출 증거 아님.
- 134절 HEAD `8bd4a8b9...` 전체 회귀 `39925361868`: `completed/failure`, **2564 tests, 26 failures, 35 errors, 2 skipped**. 실제 job 로그 `120320291806` 조회. 기존 Twitch AI 통합 실패, YouTube `transport_activity` 이벤트와 테스트 기대 불일치 등 존재. **수정/전체 재검증 완료로 보고하지 않음**.
- 같은 HEAD Windows `39925361862`: 조회 시 `in_progress`; OBS 읽기·Ollama 로컬·한국 공개 채팅·Twitch 공개 읽기 4개 job 성공, `windows-exe` job `120320291736` 실행 중. 성공 확정 아님.
- 134절 코드 커밋의 실제 Ollama 500건 `39925270479`: `completed/success`, 500/500 처리·오류 0건, **498/500건 3초 초과**. 전체 p95 **1268.281초**, FIFO 대기 p95 **1265.609초**, AI p95 **2.860초**. 1~3초 목표 미달. 이 수치는 이전 96절 결과를 대체하지 않으며 하드웨어/실행 조건이 다른 검사끼리 동일 성능이라고 단정하지 않는다.
- 새 135절 코드 HEAD `ae95b656...` CI 최초 조회: 전체 회귀 `39932935581` queued, Windows EXE `39932935705` pending, 실제 Ollama 500건 `39932935571` queued. **최종 성공/실패 미확인**. 다음 회차에서 반드시 로그까지 재조회.

### 이번 회차 하지 않은 일·작업 중 중단·남은 것
- 하지 않음: 권리 확인된 본인 실제 한국어 GPT-SoVITS WAV 합성 실행, 공식 Cubism 실제 모델의 입 움직임과 OBS 동일 발화 영상·음성 출력 실증, Windows 10/11 EXE 직접 실행·버튼 조작, 4플랫폼 실제 수백 명·수백 건 무누락 확인, 실제 24시간 운영, 시청자 E2E 1~3초 달성. 무단 계정/OAuth·방송·녹화·채팅 발신·모델 훈련·권리 없는 보이스 사용 없음.
- 진행 중/미완료: 기존 26 failures·35 errors 전체 회귀, Windows CI 실행 중 job, 135절 신규 CI 3건, 131/132 원래 독립 테스트 ZIP 중 main 미반영 부분, 실제 WAV→공식 Cubism→OBS 동일 발화 검증, 실제 4플랫폼 수백 명·24시간 안전 재연결, 1~3초 E2E 병목(500건 FIFO 대기). **실제 소스 전체 개발 우선 → 전체 회귀·Windows EXE/GUI·OBS·로컬 모델 통합 → 오류 수정 → 전체 재검증** 순서를 유지한다.
- 다음 시작: **반드시 그 시점의 main HEAD를 재조회**하고 본 135절까지 모든 과거 원문·부록을 보존한다. `39932935581`, `39932935705`, `39932935571`, `39925361862` 최종 상태·실패 로그부터 확인하고 기존 AISTING 누적 개발을 계속한다. 현재 반영 확인된 개발 코드 HEAD는 `ae95b6564f05a8d56b956a7b9d13acf93ecad734`이며, 인수인계 문서 추가 커밋이 그 뒤에 올 수 있으므로 이를 최신 HEAD로 고정해 추정하지 않는다. 새 예약 생성·다른 예약 변경·다른 프로젝트/Drive 접근 없음.
