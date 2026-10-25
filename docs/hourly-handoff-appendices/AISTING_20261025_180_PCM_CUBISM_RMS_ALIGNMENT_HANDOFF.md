## 180. 2026-10-25 — 공식 WAV PCM↔Cubism 렌더러 RMS 시각 정렬 후보 누적 개발

### 이번 시작 원본·지시 확인
- 시작 `main` HEAD: `92af08ec879dbf55cfa1c33a7cd865ae2c59f3da` (179절 최종 HEAD와 일치). 매번 HEAD 재조회.
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~179절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체, 97절 원문 부록 및 179절 부록, 현재 `original_plan_frontend.py`·`desktop_chat_tab.py`·기존 지연 소스를 읽음. 개별 과거 부록 전부를 이번 회차에서 1개씩 전수 열람했다고 주장하지 않음. 과거 원문·기존 코드·캐릭터·SQLite·설정·로드맵은 삭제·재작성하지 않음.
- 원문 사용자 지시: AISTING **기존 코드 전체 개발 우선**, 이후 전체 회귀 및 Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검사, 오류 수정, 전체 재검증. 오직 기존 main에 안전한 fast-forward만 허용. 새 브랜치/force push/rollback/전면 재개발, 다른 프로젝트·Drive·기존 예약 변경/중복 예약, 계정·OAuth 대행, 방송/녹화/채팅 발신, 모델 훈련/권리 없는 음성, 요청 없는 토큰 길이 96·keep_alive 10m 금지. 한국어로 기록.

### 실제 누적 개발
1. **`src/ai_broadcaster/live_pcm_cubism_alignment.py` 신규 작성** (`a0662ccb3e6c9242eefd91d7bdcf271702dffc73`): 기존 공식 WebSocket에서 이미 관찰한 첫 WAV PCM16 50ms RMS 윤곽과 동일 공식 Live2D 렌더러의 WAV 수신 후 상대시간 RMS 표본을 메모리에서 비교. 0~1초의 후보 지연을 50ms 간격으로 대조하고 최소 8개 실제 관측·양측 변동이 있어야 Pearson 상관 후보를 계산. 모의 음성/추가 서버 요청/실제 녹음·녹화·원본 WAV 보관 없음. 결측·시각 역행·무음·잘못된 값은 성공 후보에서 제외. 상관 점수는 **동일 발화 인과관계, 권리, OBS 출력, 시청자 수신 증명이 아니며 후보값일 뿐**.
2. **`src/ai_broadcaster/desktop_chat_tab.py` 기존 소스 누적 수정** (`33136f059df27da6ef06dc98139db7c3bcb6e839`): 운영자가 기존 공식 느린 관찰을 명시 선택한 경우, 추가 질문·음성 전송 없이 기존 `twitch_live2d_ok` 결과의 WAV PCM·렌더러 RMS를 비교. 4플랫폼별 최근 최대 512건의 후보 통계 분리. GUI에서 상관 후보, 지연 후보, Cubism 입·RMS 동시 관찰 여부와 미검증 경고 표시. 기존 단일 AI FIFO, 로컬 모델·캐릭터·SQLite·설정 및 fast 모드 유지.
3. **`tests/test_aisting_pcm_cubism_alignment_180.py` 신규 작성** (`470dfac9c82a9b9eccbcb1226e7501c280dcc2e6`): 정상 합성 수치 정렬, 입 표본 미확인, 표본 부족, 무음, 변화 없는 렌더러, NaN/Inf/음량 범위, 역행 시각, 원본 불변, 플랫폼 독립/최근 표본 한도, 후보 미충족 등 **14개 가상 계약검사 작성**. 실행하지 않았으므로 통과 주장하지 않음.

### 이전 CI 실패와 확인 범위
- 96절 Windows `39722213656`: 4개 작업 success, korean-public-chat-readonly 취소. 과거 취소 작업 로그는 BlobNotFound(404)로 미확보. **Windows 전체 통과 아님**.
- 96절 실제 Ollama 500건 `39720448468`: 500건 처리, 전부 3초 초과. 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI p95 **7.875초**. 실제 시청자 수백 명 실증 아님.
- 177절 전체 회귀 `40155307503`: 36 failures, 33 errors, 2 skipped. 177절 Windows `40155307396`: 4 success/EXE cancelled. 실제 모델 `40155307463`: 500건 모두 3초 초과, 전체 p95 **2867.219초**, FIFO p95 **2861.109초**, AI p95 약 **6.469초**.
- 위 workflow의 최종 job status를 이번 회차 재조회함. 신규 180회차 계약검사·전체 회귀·Windows EXE/GUI·OBS 실사용·실제 모델 500건은 **직접 실행하지 않았으며 신규 CI 최종 결과 미확인**. mock 수치와 실제 실사용 구별 유지.

### 이번 회차 한 것 / 안 한 것 / 남은 것 / 진행 중 멈춘 것
- **실제 완료**: 최신 HEAD 확인, 기획·원문·실제 소스 및 과거 CI job 결과 확인, PCM↔Cubism RMS 시각 후보 계산기와 플랫폼별 GUI 연결을 기존 main에 반영, 신규 가상 계약검사 14건 작성, 기존 원문 뒤에 180절 누적 인수인계.
- **실제 안 한 것**: 신규 검사 실행/통과, Windows 네이티브 EXE/GUI 버튼·OBS 실제 통합, 본인 권리 있는 GPT-SoVITS 한국어 WAV·공식 Cubism 입·OBS 동일 발화 실증, 실제 4플랫폼 수백 명·24시간 재연결·무누락, 실제 시청자 E2E 1~3초, 방송·녹화·채팅 발신·OAuth 대행.
- **남은 것**: 실제 WAV와 Cubism 렌더러 및 OBS 오디오/영상의 동일 발화 인과관계 확인 경로, 실제 음성 권리 확인·운영자 설정과 통합, 4플랫폼 실사용 무누락/24시간 안정성, 실제 Ollama 단일 FIFO 대기 수천 초 병목, 기존 36 failures·33 errors 전수 수정과 Windows 네이티브 실사용 회귀/재검증. 현재 후보 상관값만으로 목표 달성 아님.
- **진행 중 멈춘 것**: PCM↔Cubism RMS 정렬 후보 개발과 14개 가상 검사 작성까지 완료, 실제 검사·실장비 통합/OBS·동일 발화 검증 착수 전. 이전 CI 실패·취소 미해결.
- **다음 회차**: 현재 main HEAD 다시 확인하고 1~180절 및 과거 모든 원문 보존, 실제 소스 개발 우선 누적. 이후 전체 회귀→Windows 네이티브 EXE/GUI·OBS·실모델 검사→오류 수정→전체 재검증. 새로운 브랜치·force push·롤백·다른 프로젝트·Drive·기존 예약 변경·중복 예약 금지. 코드 마지막 커밋 `470dfac9c82a9b9eccbcb1226e7501c280dcc2e6`, 문서 커밋 이후 HEAD 갱신됨.
