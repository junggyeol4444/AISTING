# AISTING 101절 동일 공식 세션 WAV 관측 개발

## 101. 2026-10-22 — 본 개발 우선 회차 추가: 실제 공식 Live2D 단일 WebSocket WAV 헤더 이벤트와 Cubism 입 관측 연결
- 사용자 명시 순서 **남은 기능 개발부터 누적 → 전체 검증 → 오류 수정 → 전체 재검증** 변경하지 않는다. 100절 원문과 이전 1~99절, 과거 부록 및 원본 기획 전부 그대로 보존.
- 개발 시작 main `1f57daae2cc61337c17bd1fbffc4d532404c7a0a`, 소스 신규 fast-forward 커밋 `f806a56ed8b35ca8e9ebd1a573a85ea16ece6c40` (`[skip ci]`; 전체 검증·오류 수정 의도적으로 아직 하지 않음).
- `src/ai_broadcaster/original_plan_frontend.py`: 승인된 기존 질문 1건의 공식 Live2D WebView2에서 원래 React `text-input` 전송을 가로채지 않고 WebSocket 원본 전송 메서드에 일회성 감사 훅을 붙인 기존 흐름을 확장. **같은 공식 WebSocket**으로 서버에서 들어오는 `audio` 메시지의 문자열 base64 첫 12바이트가 `RIFF....WAVE` 구조인지 읽기 전용 검사하고, 헤더 후보 이벤트 건수만 기록. WAV 파일/음성 전체/개인 대화·토큰을 기록하지 않는다. 오디오 listener는 실제 입/RMS 표본 관찰이 끝날 때까지 유지하고, 이후 제거하여 기존 브라우저 전송 동작 복원. 기존 일반 수동 질문 경로는 바로 해제.
- 같은 파일의 실제 `_observe_actual_live2d_model` 결과에 `official_wav_header_events` 관찰 건수 추가, Python IPC 및 `OfficialLipSyncEvidence`로 전달. `src/ai_broadcaster/original_plan_full_pipeline.py`의 기존 지연 정보에 동일 WebSocket의 실제 서버 음성 **헤더 후보 이벤트** 수량을 명시. 이는 실제 WAV 전체 무결성 확인, 참조 음성 라이선스, Cubism/OBS 오디오 신호 정확한 화자 식별이나 인코더·시청자 E2E 증거가 아니다. 공식 실제 WAV 전송 수신을 추가로 관찰할 수 있는 개발 기능이다.
- 이번 회차 실행: 기존 코드 누적 기능 구현 및 `main` fast-forward 반영만 수행. 실 OBS/Windows GUI/TTS 실행, 실모델 측정, 전체 회귀, Windows EXE 빌드, 오류 수정·검증은 **아직 수행하지 않음**. 소스 반영을 동작 성공이라고 혼동하지 않는다.
- 다음 개발: 공식 GPT-SoVITS 합성 본문·원본 설정과 이 이벤트/실제 Cubism RMS·입 움직임·OBS 동일 발화 연결을 계속 확장. 4플랫폼 실제 수백 명 수신, 24시간 장시간 재연결, FIFO 1~3초 목표 병목의 미개발/미실증 항목까지 기존 코드 누적 개발. 사용자 권리/동의/송출 금지 및 토큰/keep_alive 임의 설정 금지, 신규 브랜치·롤백·force push/다른 프로젝트/예약 수정 금지. 개발 완료 후에 전체 회귀→실패 수정→전체 재검증. 다음 실행은 현재 main HEAD 조회부터.
