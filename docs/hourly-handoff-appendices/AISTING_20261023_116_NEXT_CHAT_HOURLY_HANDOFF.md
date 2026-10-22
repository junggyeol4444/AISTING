# AISTING 116회차 누적 개발 인수인계

기존 전체 1~114절 원문은 docs/AISTING_HOURLY_FULL_HANDOFF.md에 그대로 보존.

## 115. 2026-10-23 04시대 — 기존 114회차 뒤 미반영 신규 개발 보존
- 기존 main 8243a710f06cd1e0d5ef2cc9b53e38413e1c31f2에서 공식 WAV·Cubism·OBS 콜백시각 근접 표본 p95, OBS 다중 관측 선택, 4플랫폼 수신 큐 적체 계측을 개발 패치로 작성했으나 당시 main 반영은 안전 검사에서 차단되었다. 당시 검증·EXE 빌드 미실행. 원본 코드·캐릭터·SQLite·설정·기획/인수인계 원문 보존.

## 116. 2026-10-23 05시대 — 115회차 누적 및 4플랫폼 수신큐 대기 관측 신규 개발
- 시작 main HEAD 8243a710f06cd1e0d5ef2cc9b53e38413e1c31f2 재조회. docs/ORIGINAL_PLAN.txt, docs/ROADMAP_100.md, config/roadmap.json, 1~114절 원문 및 과거 부록을 보존한 채 기존 소스 2개에 115회차 기능과 116회차 기능 누적 개발.
- 116회차 신규 기능: 트위치·치지직·SOOP·유튜브별 네트워크 수신 후 로컬 수신 큐 대기 완료 건수, 누적·최장 대기시간, 3초 초과 건수를 메모리에서 분리 계측하고 기존 Windows GUI에 표시. 단일 AI FIFO/채팅 원본·순서·중복/SQLite/캐릭터/설정/모델 선택은 유지. 대기 중인 미완료 사건·네트워크 이전 누락·시청자 E2E를 검증했다고 주장하지 않음.
- Windows CI 39722213656: completed/cancelled. Windows 작업 success, 한국 공개 채팅 작업 cancelled, 해당 작업 로그 BlobNotFound 404. 구 GUI의 SIMULATED MODEL 로그를 실모델로 보고하지 않음.
- 실모델 500건 CI 39720448468: completed/success, 실제 로컬 Ollama+합성 채팅 500/500 처리, 실패 0, 500/500 모두 3초 초과. 전체 p95 2979.984초, FIFO 대기 p95 2973.875초, AI 처리 p95 7.875초, 경과 3133.64초. 실제 시청자 수백 명·24시간 방송 실증 아님.
- 이번 회차 전체 회귀, 신규 CI, Windows EXE/GUI 실사용, 권리 있는 GPT-SoVITS 한국어 WAV→공식 Cubism 실제 입→OBS 동일 발화 통합 실증, 실제 4플랫폼 수백 명·24시간·시청자 1~3초 E2E 실증 미수행·미완료. 모든 기능 개발을 먼저 누적 완성한 뒤 전체 회귀→Windows EXE/GUI·OBS·로컬 모델 통합검사→오류 수정→전체 재검증 순서 유지.
- 다음 회차 시작 시 main HEAD/CI 재조회 후 누적 개발 계속. 새 브랜치·force push·롤백·전면 재개발·다른 프로젝트/Drive/예약 변경, 승인 없는 OAuth·방송/녹화/채팅 발신·훈련·권리 없는 보이스, 임의 토큰 길이 96·keep_alive 10m 설정 없음. GitHub main 반영 여부는 실제 ref 재조회로만 판단.
