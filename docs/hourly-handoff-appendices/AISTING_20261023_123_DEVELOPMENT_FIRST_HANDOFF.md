# AISTING 123회차 신규 개발·기존 원문 보존 누적 인수인계

## 123. 2026-10-23 — 공식 같은 WebSocket의 실제 PCM16 WAV 음량과 Live2D 렌더러 RMS·OBS 실제 미터 시각 연관 기능 누적 개발

### 사용자 최신 요구 / 원본 보존 및 시작점
- 최신 사용자 지시: **"계속"**. AISTING만 기존 원본 `main`에서 전체 미완료 **실제 기능 개발을 먼저 진행한 후** 전체 회귀검사·Windows 네이티브 EXE/GUI/OBS/실제 로컬 모델 통합검사 → 오류 수정 → 전체 재검증. 이번 회차는 기능 개발 및 안전한 main 반영과 원문 보존 인수인계만 수행했다.
- 실제 시작 `main` HEAD `5023be2a0d049b2f003156cff44ea4a94b09f940` 확인. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 과거 1~122절 `docs/AISTING_HOURLY_FULL_HANDOFF.md`, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 특히 97절·122절 원문 부록과 원래 123회차 개발 대상 소스 조회. 기존 원문/부록은 삭제·덮어쓰기 없이 뒤에만 123절 추가.

### 이번 회차 실제 새로운 소스 개발 및 main 반영 (3커밋)
1. 기능 개발 커밋 `33e8ee7f801f81e027aed0e00fe8d33c12023e93` `main` fast-forward 성공. 기존 `original_plan_frontend.py`의 운영자가 1회 승인해 **기존 공식 Live2D WebView2의 원래 React/동일 WebSocket**으로 보낸 질문에서 서버로부터 실제 받은 audio WAV를 원래 이벤트 그대로 처리한다. RIFF 길이·PCM 헤더 검증이 성공한 **최초 16비트 PCM WAV(1~2ch, 데이터 최대 2MB)**에 대해서만 브라우저 메모리에서 원본 데이터를 임시 디코딩하고 50ms RMS 표본 최대 160개를 계산한다. 첫 수신의 브라우저 performance.now() 시점을 Python monotonic 시각으로 읽기 지연만큼 보정해 기존 `OfficialLipSyncEvidence`에 `official_pcm_first_wav_rms_envelope`, `official_pcm_first_wav_received_monotonic`을 추가. 원래 사용자 발화/실제 WAV·화자/음성 파일은 별도 저장하지 않고 수치 표본만 기존 IPC 반환에 포함. 지원하지 않는 WAV 형식/너무 큰 파일은 미측정.
2. 기능 개발 커밋 `e8d194012ff747f07604f5130040f710c254f393` `main` fast-forward 성공. 기존 `obs_consecutive_audio.py`에 `collect_obs_input_meter_levels` 추가: OBS의 **같은 사용자가 선택한 오디오 입력**에서 실제 양성·무음 레벨 50ms 표본을 여섯 연속 실관측 구간으로 합치되, 안정적인 OBS 장면·입력 경로 후보만 포함하고 시간 중복·역행·불일치를 제외. 신규 `official_ws_wav_obs_match.py`에서 공식 동일 WS PCM16 WAV의 50ms RMS 음량 배열과 OBS 입력의 실제 50ms 레벨 콜백을 0~3초 후보 지연 범위에서 상관계수로 비교한다. WAV/OBS 레벨 각각 실제 변화와 대응 표본이 12개 이상인 경우만 스코어 계산하며 원본 음성은 복사해 보존하거나 로그에 기록하지 않는다. `original_plan_full_pipeline.py` `OfficialChatObsEvidence` 및 네이티브 `desktop_chat_tab.py`에 실제 관측값·후보 지연·상관도 표시; 유효 입/RMS 근접 표본 두 쌍 조건과 상관 ≥0.85인 경우에도 **단순 음량 패턴 유사 후보**로만 표시.
3. 기능 개발 커밋 `5c27c467d2b57669f7bce266a8dbf8c2f467d697` `main` fast-forward 성공. 첫 WAV RMS 표본 출력 수치를 소수 4자리로 한정해 기존 Windows 인증 파이프 최대 4096바이트 응답의 폭증을 줄인다. 같은 실관측 창에서 공식 Live2D 렌더러 `wav.getRms()` 값을 실제 80ms 주기 샘플로 수집하고, 첫 공식 WS WAV 수신 시점 이후 상대시각·RMS 최대 100쌍만 보관/검증한다. 기존 `OfficialChatObsEvidence`에서 공식 동일 WAV RMS 음량 윤곽과 실제 Live2D 렌더러 RMS 시계열을 별도로 상관 비교하고, `desktop_chat_tab.py` GUI에 WAV·OBS 미터와 WAV·Live2D RMS 후보를 독립 표시한다. 원래 Cubism 실제 입 움직임·Canvas·Renderer 활성 조건을 유지한다.
- 세 개발 커밋 모두 기존 `main` 예상 HEAD를 새로 조회한 뒤 `force=false`로만 진전시켰다. 기존 모델·캐릭터·SQLite/기획/각종 채팅 저장 경로를 임의 변경하지 않음.

### 정확한 증거 범위 / 과거 CI 결과 및 미완료
- **이번에 실제 한 것:** 이전 기획/인수인계·코드 확인, 실제 기존 공식 WAV·Live2D·OBS 계측 경로 신규 소스 개발 3건, 커밋 3개 main 반영 성공, 이 123절과 새 부록 누적 문서화.
- **이번에 안 한 것:** 신규 CI, 전체 회귀 테스트, Windows EXE 빌드·GUI/OBS/GPT-SoVITS/Live2D 실제 장비 작동검증, 권리 확인 음성으로 본인 환경 재생, 실수백 명 수신, 24시간 재연결, 로컬 AI·음성·영상/시청자 E2E 1~3초 성능 실증, 코드 실행 후 오류 수정·전체 재검증. 관찰 **후보**와 실제 성공/무누락/실시청자 도달은 구별한다.
- 기존 Windows CI `39722213656`: 재조회 결과 workflow `completed/cancelled` (과거 네 작업 성공/한국 공개 채팅 작업 취소). 과거 취소·실패 로그(접근 불가 404 포함) 감추지 않음. 기존 실 Ollama 500건 CI `39720448468`: 재조회 결과 workflow `completed/success`지만 **합성 이벤트 500건 전부 3초 초과**, 전체 p95 `2979.984`초, FIFO 대기 p95 `2973.875`초, 모델 p95 `7.875`초. 실제 시청자 500명이 아니며 실제 1~3초 E2E 미달.
- 신규 비교값은 첫 PCM WAV의 **음량 외형**과 OBS 미터/렌더러 RMS 관측의 상관일 뿐 **같은 PCM 파형이 Cubism·OBS 인코더·시청자에 실제 전달됐음, 시청자 체감 지연, 입 움직임의 직접 음원 동일성이나 음성 사용 권리를 자동 검증하지 않는다**. GUI가 해당 한계를 명시하도록 작성했다.
- 남은 핵심 기능: 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism 실입 움직임→OBS 동일 발화 영상·음성의 확정 인과 관계 및 현장 실증, 4플랫폼 실제 수백 명/수백 건 완전 무누락 수신, 실제 24시간 재연결·안전, AI·음성·영상·시청자 1~3초 병목 전체 개발. 개발 완료 후 전체 회귀→Windows 네이티브 EXE/GUI·OBS·모델 통합검사→오류 수정→전체 재검증을 수행.
- 사용자 승인 없는 방송·녹화·채팅 발신·OAuth 대행·모델 훈련·권리 없는 보이스, 새 브랜치/force push/롤백/전면 재개발/다른 프로젝트·Drive·기존 예약 수정 없음. 토큰 수 96 또는 keep_alive 10m 임의 설정 없음.
- 이번 기능 개발 HEAD `5c27c467d2b57669f7bce266a8dbf8c2f467d697`. 본 인수인계 커밋 뒤에는 다른 HEAD이므로 매번 최신 `main`을 다시 확인한다. 이전 1~122절 및 모든 원본 부록 보존.
