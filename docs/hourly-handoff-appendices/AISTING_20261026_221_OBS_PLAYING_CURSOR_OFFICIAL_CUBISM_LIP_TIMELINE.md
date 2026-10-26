# AISTING 221절 — 2026-10-26, OBS 실제 PLAYING 미디어 커서와 공식 Cubism 동일 WAV 입 움직임 시간축 연결

## 실제 구현 및 GitHub main

## 221절 — 2026-10-26 OBS 실제 PLAYING 커서 기반 공식 Cubism 동일 WAV 입 타임라인
- 시작 `main` HEAD `941f2470f62d965d356b24869cd4ac3bf2d4755f` 재조회. 220절 원본 부록, 기존 두 대형 인수인계 Git blob, 원래 기획/100단계, 실제 `approved_live_voice_output.py`, `approved_live_voice_playback_watch.py`, `original_plan_frontend.py`, `same_wav_cubism_driver.py`를 읽고 제품 코딩 우선 수행.
- 실제 소스 커밋 `e087fc85f3c53c623505ef8ba88631f56cab5d89`: 기존 `same_wav_cubism_driver.py` 공식 WebGL Cubism 모델 `_wavFileHandler.getRms()`에 실제 WAV RMS 제공하는 경로에 선택형 `await_obs_cursor` 추가. OBS 재생 요청 이전엔 0(입 움직임 없음), PLAYING으로 실제 관측된 OBS 미디어 커서 ms를 받으면 그 위치를 기준으로 같은 WAV RMS를 읽도록 시간축 연결. 커서 역행·장시간 미갱신 시 계속 입을 움직인 척하지 않고 0 또는 거부. 기존 수동/비동기 경로는 기본값 false로 보존. 같은 커서 수신/중단/원상복구 스크립트 추가. `original_plan_frontend.py`에 Windows 인증된 기존 네이티브 WebView2 IPC `authorized-pcm-cursor` 처리, 토큰·실제 커서·반영 횟수 확인, 기존 운영자/권리 승인 요구 보존.
- 실제 소스 커밋 `35518ed24173b6f11b0b659523549ae955445b20`: `approved_live_voice_playback_watch.py`는 기존 승인 OBS 소스의 `GetMediaInputStatus`가 실제 `OBS_MEDIA_STATE_PLAYING`일 때의 커서만 선택형 콜백으로 공식 Cubism에 전달. 커서 역행·0.8초 정지 관측 시 같은 WAV 불명/후속 자동 발화 차단, 전달한 실커서 업데이트 횟수 메모리 관측에 포함. `approved_live_voice_output.py`의 실제 GPT-SoVITS WAV→OBS ffmpeg 임시 소스 재생 요청→기존 공식 Cubism 입 구동에 이 커서 동기화 옵션 연결. 원래 OBS 송출/녹화/장면/다른 소스 변경 없음, 중단·실패 시 기존 발화 불명 처리/원래 cleanup·재발화 차단 유지.
- 이는 **OBS 미디어 재생 위치에 따른 로컬 공식 Cubism 입 타임라인의 개발**이지 시청자 실제 오디오/영상 도달이나 플랫폼 인코더 믹스 검증이 아니다. Windows IPC 지연·OBS media cursor 관측 주기·실제 lip 결과는 아직 미검증. 새 SQLite 사용자 데이터/캐릭터/설정/모델 `num_predict=96`/`keep_alive=10m`/원래 로드맵 9 completed·91 pending/기존 1~220절 기록을 삭제·수정하지 않음.
- **전체 개발 미완료. 테스트 NOT_RUN, 통합 NOT_RUN, CI 미조회·미확인, Windows 10/11 EXE GUI NOT_RUN, 권리 GPT-SoVITS→공식 Cubism→OBS 실방송·4플랫폼 수백 명·24시간 NOT_RUN, 실제 1~3초 미확인.** 과거 CI `39720448468`: 500/500 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초 실패. Windows CI `39722213656` 취소 기록 보존.
- 다음 회차는 최신 HEAD/직전 코드 확인 후 남은 원본 기능 **실제 제품 소스 개발부터**: 실제 OBS 오디오 믹스·입/음성 연속성, 4플랫폼 공개 채팅 FIFO 대량 적체/로컬 AI 병목, 승인형 24시간 방송·게임·자율 콘텐츠·공지·장기 기억. 개발 완료 전 CI/개별 오류 수정 금지. 이후에만 Windows EXE/실계정/OBS·공식 Cubism·권리 TTS/24시간 통합 검증→오류 일괄 수정→재검증. 기존 예약·동일 대화 보고 우선, 다른 프로젝트/Drive/브랜치/무승인 방송·공지·로그인·모델 학습 조작 금지.

## 기술적 범위와 미완료
- 실제 OBS `GetMediaInputStatus`의 PLAYING 상태와 `media_cursor` 값을 기존 승인 Windows 네이티브 IPC로 전달한다. 재생 요청 직후부터 무조건 움직이는 이전 Cubism 입 RMS 시간축 대신, OBS가 보고한 위치를 사용한다. 관측 사이 최대 500ms 동안 단조 시각으로 연속 보간하되 갱신이 없으면 입 RMS를 0으로 둔다. 재생 시작 전에는 0이며 커서 역행은 거부한다. 새 WebSocket 방송/녹화/다른 장면 조작 없음.
- `authorized-pcm-start`의 `obs_cursor_sync`는 기본 false이며 기존 수동 경로를 보존한다. 승인된 실제 음성 `_speak_segment`에서만 true. 커서 갱신을 위한 새 `authorized-pcm-cursor` 명령은 같은 인증된 Windows IPC를 사용하고 응답의 token/cursorMs/updates를 확인한다.
- 시간 보간·IPC 오버헤드/OBS 커서 스톨 0.8초 차단은 구현된 코드의 동작 의도이며 실제 성능/안정성 검증은 아직 하지 않았다. OBS 소스 입력 재생 성공은 시청자 전달/오디오 믹스/방송 성공을 증명하지 않는다.
- 기존 `approved_live_voice_media_receipts.sqlite3`, `approved_live_wav_sync_receipts.sqlite3`, DPAPI outbox/공개 채팅 DB 구조 및 과거 장부 행을 변경하지 않는다. 새 OBS 커서 갱신 횟수는 이번 회차에서 메모리 `LivePlaybackObservation` 필드이며 영구 시청자 수신 근거로 사용하지 않는다.

## 다음 회차
- 원래 1~221절 전체 인수인계와 원본 기획을 확인하고 제품 개발 계속. 전체 개발 완료 전 CI·테스트·오류수정 선행 금지. 원래 Windows 10/11 Tkinter EXE, 기존 모델·권리 음성·공식 Cubism·OBS·4플랫폼, 모든 사용자 승인·기록·예약 보존.
