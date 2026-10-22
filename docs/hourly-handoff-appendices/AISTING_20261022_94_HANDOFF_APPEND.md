## 94. 2026-10-22 — 공식 Cubism·OBS 동일 발화 시간 증거 현재 질문 범위 검증

### 계승 원문·금지 지시
- 이번 기준 HEAD `f55e9916d9ff515daa37dd600be3707ee7694d9f`. 기존 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` **1~93절 원문 전부**, `docs/hourly-handoff-appendices/` 전부, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 모든 코드·캐릭터·SQLite·운영자 설정을 유지하고 이 절만 추가한다. 원본 로드맵 승인 상태 pending 유지.
- 기존 `main`만 안전한 fast-forward; 브랜치 생성·force push·롤백·전면 재개발·다른 프로젝트·예약·Drive 변경 금지. 무단 로그인/YouTube OAuth 동의 대행·방송·녹화·채팅 발신·목소리 훈련·무권리 음성 금지. 임의 `num_predict=96`, `keep_alive=10m` 강제 설정 금지.

### 새롭게 확인한 실제 Windows / 모델 검사
- 93절 최종 HEAD `f55e9916` [전체 회귀 39707490288](https://github.com/junggyeol4444/AISTING/actions/runs/39707490288) **success**, [Windows 39707490277](https://github.com/junggyeol4444/AISTING/actions/runs/39707490277) **success**. 읽기/GUI/EXE 통합 검사를 실제 Windows Actions에서 실행. 실제 권리 있는 GPT-SoVITS WAV→Cubism 입→OBS 같은 발화 확인·24시간 방송 실증과 구분.
- **91절 실제 Ollama synthetic 500건 [39702241916](https://github.com/junggyeol4444/AISTING/actions/runs/39702241916) 최종 success는 무누락 처리 한정**. 500/500 처리, 누락·모델 실패 0, 3초 초과 **499/500**, 전체 p95 **3499.515초**, FIFO 대기 p95 **3492.297초**, AI 처리 p95 **9.5초**, 1~3초 목표 실패. 실제 Ollama 서버 내 단계별 p95: 모델 로딩 **0.124819초**, 프롬프트 평가 **8.306656초**, 답변 생성 **0.944631초**, 총 내부 처리 **9.373657초**; 각 500개 서버 제공 실측 표본. **반복 입력 문맥 평가와 직렬 FIFO 대기**가 실제 병목이라는 정량 자료이며, 사용자 설정·모델·대화기억·답변 토큰을 임의로 축소하지 않았다.
- 92절 [39704987503](https://github.com/junggyeol4444/AISTING/actions/runs/39704987503) 및 93절 [39706777993](https://github.com/junggyeol4444/AISTING/actions/runs/39706777993)은 이 기록 시점 진행 중으로 최종 수치는 미확정. 93절 이전 실모델 CI 성공/실패와 실제 플랫폼 시청자 메시지 0건은 구분.

### 이번 회차 실제 개발
- `src/ai_broadcaster/original_plan_full_pipeline.py`: 이미 사용 중인 **단일 운영자 승인 공식 AI→한국어 TTS→Cubism→OBS 읽기 전용 관찰** 경로에서 Cubism의 실제 음성 RMS·입 움직임 monotonic 시작/종료 시각을 **이번 단일 질문 요청 시작~종료 구간 내부**에서만 유효하게 인정한다. 이번 질문 이전부터 시작됐거나 질문 완료 후까지 뻗은 과거/미래 발화 입 움직임 구간은, OBS의 실제 선택 입력 오디오 미터와 우연히 시간 중첩돼도 `temporal_overlap_candidate=False`, `verified_observation=False`, 첫 Cubism/OBS 실측 지연 `None` 처리. 기존 OBS 실제 오디오 표본 시각의 정확한 중첩 검사·권리/운영자 승인·녹화/송출 차단과 질문 1회 전송 정책 유지. **같은 발화 오판 방지 강화이며 실사용 합성 성공을 새로 입증한 건 아님**.
- `tests/test_aisting_official_chat_obs_pipeline.py`: 과거 음성의 시작시각이 질문 이전인데 종료가 현재인 표본, 질문 종료 후 미래까지 이어지는 표본이 이번 발화 인증을 통과하지 않음을 확인하는 격리 회귀검사 **2개 추가**. 이 테스트는 OBS/음성 모델을 모의하므로 실실행 증거로 세지 않는다.

### 검증·미변경·차후
- 변경 반영 후 **동일 HEAD 전체 회귀 및 Windows 네이티브 EXE·GUI/OBS 실제 읽기/로컬 Ollama/4플랫폼 공개 읽기 CI**를 반드시 최종 확인하고 오류가 나면 수정 뒤 전체 재검증한다. 진행 중 상태를 성공이라 보고하지 않는다.
- 본 회차 기존 원본 프로그램 기능 삭제·캐릭터·설정·SQLite·로드맵 수정, 다른 저장소/예약/Drive/계정 접근 및 송출·녹화·채팅 송신 없음.
- 남은 핵심: 권리 있는 실제 한국어 GPT-SoVITS WAV 합성 → 공식 Live2D Cubism 립싱크 → OBS 같은 발화 오디오·영상 실측 증거(관측 중첩은 완전한 동일성/시청자 전달 증명이 아님), 4플랫폼 실제 수백 명 동시 처리·24시간 안정성, 최종 **1~3초** E2E 목표와 위 프롬프트 입력평가·FIFO 병목 **미완료**. 다음 95절 개발에서 이전 대화 원문/금지·완료·미완료를 인계하고 개선·전체 실검증 지속.
