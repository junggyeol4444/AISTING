# AISTING 178절 개별 누적 인수인계

## 178. 2026-10-25 12:34 KST — 4플랫폼 채팅 파싱→공식 첫 WAV 수신 후보 지연 누적 개발

### 원문 보존·작업 범위
- 97절 기준 원본 커밋 2687831af162f90f985da467aac9f90d0fd01828, 전체 1~177절 및 과거 모든 개별 부록을 삭제·대체하지 않는다.
- 사용자 지시 순서: 기존 AISTING 개발 우선 누적 완료 → 전체 회귀/Windows EXE·GUI·OBS·로컬 모델 통합검사 → 오류 수정 → 전체 재검증. 다른 프로젝트/Drive/예약/브랜치/캐릭터/SQLite/설정/원본 기획 변경 금지.
- 무단 계정·OAuth·방송·녹화·채팅 발신·모델 학습·권리 없는 음성 사용 없음. 임의 토큰 96 및 keep_alive 10m 변경 없음.

### 실제 조회한 GitHub main 및 CI
- 회차 시작 main HEAD: f03bfe440d98cd00491ff888aa1d82ca2bed3cd2 (177절).
- 96절 Windows 39722213656: obs-real-readonly, twitch-public-readonly, windows-exe, ollama-real-local-e2e 4개 완료/성공. korean-public-chat-readonly 1개 완료/취소. 취소 작업 로그 404 BlobNotFound로 확보 실패. 전체 Windows 실기기/GUI 검증 통과가 아니다.
- 96절 실제 Ollama 500건 39720448468: 완료/성공(작업 실행 성공), 500건 전부 3초 초과. 전체 p95 2979.984초, FIFO 대기 p95 2973.875초, 모델 p95 7.875초. 시청자 1~3초 달성 아님.
- 176절 전체 회귀 40150966420: 완료/실패(36 failures, 33 errors, 2 skipped). Windows 40150966393: 4개 성공, windows-exe 취소. 실제 모델 500건 40150966416: 완료/성공(500건 모두 3초 초과), 전체 p95 3425.172초, FIFO 대기 p95 3417.844초, AI p95 7.484초.
- 177절 전체 회귀 40155307503: 완료/실패(36 failures, 33 errors, 2 skipped). Windows 40155307396: 4개 성공, windows-exe 취소. 실제 모델 500건 40155307463: 완료/성공(500건 모두 3초 초과), 전체 p95 2867.219초, FIFO 대기 p95 2861.109초, AI p95 6.469초.
- 177절 Windows EXE 취소 작업 로그에는 '_live_queue_wait_tracker' 속성이 없는 SimpleNamespace 오류와 종료 취소가 보인다. 이번 회차는 사용자 지시대로 누적 개발 우선이므로 회귀 오류 수정/통과를 주장하지 않는다.

### 실제 누적 개발
1. src/ai_broadcaster/live_runtime_metrics.py: LiveFirstWavLatencyMetrics 추가. 플랫폼별 실제 단조시각(파싱·AI FIFO 수용·공식 WebSocket 전송 시작)과 기존 공식 첫 WAV 수신 후보 시간차를 결합하여 파싱→전송 대기, 전송→첫 WAV 후보, 파싱→첫 WAV 후보의 최근 512건 p95·최장·3초 초과를 구분. 미관측/시각 누락/비정상/전송 오류를 성공 표본에서 제외. 본문·닉네임·인증정보·음성 미저장.
2. src/ai_broadcaster/desktop_chat_tab.py: 기존 운영자 승인 공식 빠른 전송+첫 WAV 관찰 옵션에서만 실제 첫 WAV 후보 계측 사건을 전송하고 플랫폼별 GUI 상태에 표시. 새 네트워크 호출·재전송·음성 재생·OBS 변경 없음. 기존 로컬 Ollama/공식 Cubism/SQLite/캐릭터/4플랫폼 FIFO 경로 유지.
3. tests/test_aisting_first_wav_candidate_latency_178.py: 가상 시각 기반 계약검사 14건 작성. 실행하지 않았고 성공을 주장하지 않는다.
- 중요한 한계: 공식 WebSocket 응답에는 원본 채팅과 WAV를 1:1 대응시키는 식별자가 없어 이전 발화의 WAV 후보가 포함될 수 있다. 이는 실제 동일 발화 GPT-SoVITS WAV→공식 Cubism 입→OBS 출력·시청자 응답 지연의 증거가 아니다.

### 실제로 한 것·안 한 것·남은 것·중단 위치·다음
- 한 것: 최신 main HEAD 재확인, 원본 기획·100단계 로드맵·config/roadmap.json·기존 1~177절 인수인계와 실제 소스 조회, 96·176·177절 CI 및 실패 로그 확인, 코드 2개 수정·가상 검사 14건 작성·178절 원문 추가.
- 안 한 것: 신규 검사 직접 실행, 전체 회귀 통과, Windows 사용자 PC EXE 실행·GUI 버튼 검증, 실제 권리 있는 한국어 GPT-SoVITS WAV 합성→공식 Live2D Cubism 입→OBS 동일 발화 실증, 실제 수백 명 4플랫폼 무누락, 24시간 실방송, 시청자 E2E 1~3초 달성. 무단 외부 계정 작업 없음.
- 남은 것: 기존 개발 전체 완성, WAV-채팅 인과성/입/OBS 실제 결합, FIFO 및 모델 대기 병목 해소, 실제 수백 명/24시간 검증, 기존 회귀 36실패·33오류 포함 전체 검사→수정→재검증. 첫 WAV 후보 계측은 실제 시청자 지연이나 공식 모델 사용권을 입증하지 않는다.
- 진행 중 멈춘 위치: 파싱→공식 WAV 수신 후보 로컬 지연 측정 코드 및 14건 계약검사 작성 후 전체 회귀/Windows/실모델 통합 검증 전.
- 다음: main HEAD와 178절 CI를 다시 확인하고 기존 AISTING 코드 누적 개발을 계속한다. 모든 과거 인수인계 원문 보존. 새 브랜치/force push/롤백/다른 프로젝트/예약 변경 금지.
