# AISTING 218절 — 2026-10-26 실제 OBS 미디어 재생 상태·커서 진행과 동일 한국어 WAV 연결

## 시작점 / 원본 보존
- 최신 `junggyeol4444/AISTING/main` 시작 HEAD: `9e6dfb9fdaaab3862f2dc2090decc4cacc14c244`. 217절 원본·최신 인계, 원본 기획, 방송·음성 제품 모듈의 실제 소스 확인.
- 기존 Windows Tkinter AISTING.exe, 공식 Open-LLM-VTuber/Live2D Cubism, 권리 확보 한국어 GPT-SoVITS, 사용자 선택 로컬 Ollama/캐릭터/개인 SQLite 및 원본 방송 기록을 보존. `num_predict=96`, `keep_alive=10m`, 100단계 상태를 변경하지 않음.
- OBS WebSocket 5 GetMediaInputStatus는 OBS_MEDIA_STATE_PLAYING 등 실제 미디어 상태와 재생 커서(ms)를 제공하는 읽기 전용 API. 재생 명령 수락·OBS 송출 중만으로 WAV가 실제 재생됐다는 기록을 남기지 않도록 구현.

## 실제 제품 개발 4개 소스, 기존 main 비강제 커밋
1. `d0aaa0e0f2d24c352e9e2ec52c0b1d8815d1dee2`: 신규 `src/ai_broadcaster/approved_live_voice_media_receipts.py`. 별도 로컬 SQLite `approved_live_voice_media_receipts.sqlite3`에 원래 승인 발화 식별자·구간·동일 WAV SHA-256·OBS 임시 입력 UUID·실제 재생 상태·PLAYING 표본 수·커서 전진 표본·최초 관측 상대시각·마지막 커서·재생 종료 관측을 영구 기록. 원본 음성/게임/대화 장부 불변. WAV 원문·시청자·계정/OAuth/참조 음성은 저장하지 않음. 다른 DB 앱 ID/테이블 사용 차단 및 중복 구간 덮어쓰기 금지.
2. `1606104d21e6f408fc3ebd5aa1d9e81e2a56ec77`: 기존 `approved_live_voice_playback_watch.py`에서 같은 OBS 임시 미디어 입력의 `PLAYING` 상태와 실제 커서 증가를 재생 시간 동안 주기적으로 읽고 보고. 요청만 성공했거나 상태 불명/커서 미전진이면 다음 발화 완료로 확정하지 않도록 실패하며 원래 송출/녹화/장면에는 간섭하지 않음. 기존 OBS 송출/장면/소스 UUID/공식 Cubism 생존 감시 계속 유지.
3. `ddcc933bdb12bfeb9995dd3341be947e17e8b481`: 기존 `approved_live_voice_output.py`에서 `get_media_input_status(name)` 실제 응답을 기존 임시 입력 소유권 검사 후 받아 현재 동일 한국어 WAV→공식 PCM 입→OBS 재생 중 감시기로 연결. WAV 해시·UUID·구간 식별자가 일치하는 SQLite 실제 재생 관측 성공 이후에만 기존 인과 완료 처리. 관측/기록 실패는 해당 음성 전달 불명 상태로 기존 영구 outbox 경로에 남기며 임의 재전송 금지.
4. `b9a49e2f8c50e17ce68e50bfd586db3f16b18321`: 기존 `desktop_chat_tab.py` Windows GUI의 실제 방송 음성 상태·운영자 수동 기록 조회에 각 OBS 미디어 상태·PLAYING 표본·커서 진행·첫 재생 관측/커서 정보 추가. 실제 시청자 인코딩/수신을 의미한다고 표시하지 않음.

## 정확한 상태/남은 기능
- **218절 소스 구현 및 GitHub main 반영 완료, 전체 AISTING 개발은 미완료.**
- 테스트 `NOT_RUN` / 통합 `NOT_RUN` / CI 이번 회차 미조회·미확인 / Windows 10/11 EXE·GUI 실제 실행 `NOT_RUN` / 진짜 OBS·GPT-SoVITS WAV·공식 Cubism 실제 재생 `NOT_RUN` / 4플랫폼 실계정·수백 명·24시간·시청자 최종 1~3초 `NOT_RUN`. 실제 OBS 연동/미디어 믹서/시청자 스트림 성공 주장 금지.
- 과거 성능 CI `39720448468`: 500/500 3초 초과, FIFO p95 2973.875초, 전체 p95 2979.984초 실패. Windows CI `39722213656` 취소 기록 유지.
- 남은 핵심: 4플랫폼 대량 채팅 SQLite/FIFO/서버 재연결 지속 운영, 로컬 Ollama 1~3초 실효, 실제 한국어 WAV/공식 Cubism/OBS 장시간 입·오디오 A/V 실출력의 동기, 승인된 24시간 방송 시작/종료/장애 복구·게임·자율 콘텐츠·장기 기억·공지 운영 완성. 원격 서버가 미전송한 채팅이나 시청자 송출은 확인 없이 성공 표시 금지.
- 다음 회차 **모든 남은 실제 제품 기능을 먼저 구현→전체 개발 완료 후 전체 Windows EXE/실계정/OBS·Cubism·모델 통합 검증→발견 오류 일괄 수정→전체 재검증**. 문서/CI/오류 수정만으로 회차 종료 금지. 기존 main에서만 비강제 반영. 새 브랜치·force push·원본 삭제·다른 저장소/Drive/예약 조작·무승인 방송/공지/채팅 발신/OAuth/학습 금지.
- 기존 'AISTING 매시간 개발·인수인계' 예약 변경/중복 생성 금지. 기존 대화 결과 게시를 우선하되 강제 보장하지 않고 GitHub 누적 인수인계 유지.
