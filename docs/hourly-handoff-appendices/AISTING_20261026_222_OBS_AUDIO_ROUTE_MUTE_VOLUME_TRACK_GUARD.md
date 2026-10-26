# AISTING 222절 — 2026-10-26 OBS 실제 WAV 오디오 경로/음소거/볼륨/트랙 후보 읽기·재생 중 보호

## 개발 기준과 시작점
- 기존 `junggyeol4444/AISTING/main` 시작 HEAD `c38d71f105e8d5045068c578af708a37d769e1f1` 확인. 221절 부록, 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 실제 `approved_live_voice_output.py`, `approved_live_voice_playback_watch.py`, `original_plan_obs.py`, `approved_live_voice_media_receipts.py`, `approved_live_voice_stream_lease.py` 등을 읽고 222절 핵심 소스를 먼저 구현했다.
- 두 전체 인수인계 `docs/AISTING_HOURLY_FULL_HANDOFF.md` 및 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`는 GitHub `fetch_file` 대용량 응답이 비어 실제 blob SHA `1455d66b9716a5620064ef3f2d2c920fe13211b6` 및 `23065edb74b8e1f162f774de69041663a819e500`로 전체 원문을 읽어 끝에만 덧붙인다.
- 원본 기획의 모든 채팅 응답·인위적 딜레이 금지·운영자 승인/권리 보호·Windows EXE·로컬 모델 설정 `num_predict=96`/`keep_alive=10m`·기존 OBS/Live2D 기능 불변.

## 실제 제품 개발 커밋
- `b879394305adbf7c776530cde0e1ee74f209c52b`: 기존 main에 **4개 제품 소스 파일**을 한 번의 정상 비강제 fast-forward 커밋으로 반영.
- **신규 `src/ai_broadcaster/approved_live_voice_audio_route_watch.py`**: OBS v5 기존 `OfficialObsWebsocket.read_program_audio_route`를 사용하여 실제 임시 WAV 입력 UUID와 현재 프로그램 장면의 활성 scene-item/중첩 scene/global input, `GetInputAudioMonitorType`, `GetInputAudioTracks` 1~6, `GetInputMute`, `GetInputVolume`을 읽기 전용으로 확인. 음소거/볼륨 0/출력 후보 트랙 없음/UUID 상실/관측 도중 scene identity·트랙 변동 시 다음 음성 진행 차단. 모든 조회는 기존 승인 OBS 입력에 한정하며 다른 OBS 소스/장면/송출/녹화를 변경하지 않음.
- **신규 `src/ai_broadcaster/approved_live_voice_audio_route_receipts.py`**: 기존 WAV/립싱크/OBS 미디어 SQLite와 분리된 `approved_live_voice_audio_route_receipts.sqlite3`에 `AVR1` 응용 ID, 동일 WAV SHA256·구간·실제 소스 UUID·활성 경로/트랙 후보·관측 수·최저 볼륨을 영구 보존. 사용자 채팅 본문/닉네임·WAV 원본/인증 비밀은 기록하지 않으며 기존 SQLite 표/기록을 수정하지 않음. 기존 파일과 타 DB의 잘못된 응용 ID/테이블을 침범하지 않음.
- **수정 `src/ai_broadcaster/approved_live_voice_playback_watch.py`**: 기존 OBS PLAYING/커서/Live2D 생존·방송 Lease 주기 관측에 선택형 `audio_route_check` 콜백 추가. 약 1초 간격 및 마지막에 OBS 실제 오디오 경로가 유지되는지 조회하며 새 OBS 쓰기/출력 명령 없음. 관측 불명/경로 변경 시 기존 불명·후속 자동 재발화 금지 흐름으로 예외 전달. 기존 선택형 기본 None 보존.
- **수정 `src/ai_broadcaster/approved_live_voice_output.py`**: 기존 운영자·권리 승인된 동일 GPT-SoVITS WAV→OBS ffmpeg 임시 입력 활성화 뒤 재생 요청 **전에** 실제 scene UUID/track/mute/volume을 조회. 동일 WAV 재생 도중 주기 관측하고, 기존 미디어 커서 영구 장부 다음에 OBS 오디오 경로 후보 장부를 기록한 후에만 구간 완료. 실패 시 기존 시도/불명 보존·중복 발화 차단·기존 임시 소스 정리 및 Cubism 원상복귀 유지.

## 확인되지 않은 것
- 이 기능의 `enabled_tracks`는 **OBS 입력에 활성화된 오디오 트랙 후보**일 뿐, 실제 스트리밍 인코더가 어느 트랙을 선택했는지/최종 시청자가 들었는지 확인하지 않는다. OBS ffmpeg 소스가 PLAYING·커서 진행·mute 해제·양수 volume이어도 실제 방송 음성 수신/오디오 인코딩 PASS로 주장하지 않는다.
- 전체 개발 미완료. **코드 테스트 NOT_RUN / 전체 통합 NOT_RUN / CI 미조회·미확인 / Windows 10/11 EXE GUI NOT_RUN / 실계정 4플랫폼·수백 명·24시간 NOT_RUN / 권리 GPT-SoVITS·공식 Cubism·OBS 실제 동일 WAV 출력 NOT_RUN / 실제 시청자 응답 1~3초 미확인.**
- 과거 실모델 CI `39720448468` 500/500건 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초 실패; Windows CI `39722213656` 취소 사실 그대로 유지.
- 원본 100단계 완료 9/pending 91·운영자 승인 상태·캐릭터·사용자 SQLite/설정·선택 모델·기존 1~221절 코드/인수인계 변경/삭제하지 않음. 새 브랜치·force push·rollback·Drive/다른 저장소/예약 변경·무승인 OAuth·방송/녹화·외부 채팅/공지·게임 조작/모델 학습/다운로드 없음.

## 다음 개발
- 223절은 최신 main HEAD 및 이번 실제 4개 소스와 전체 원본 인수인계를 읽고 **제품 개발부터** 이어갈 것. 남은 실제 스트림 인코더 오디오 트랙 확인·OBS 프로그램/실제 출력의 영상/오디오 인과, 4플랫폼 대량 FIFO·로컬 Ollama 병목, 승인형 24시간 방송/게임/콘텐츠/공지·장기 기억의 미완 기능 개발. 이미 구현한 219~222절 기능을 다시 이름만 바꿔 개발하지 않는다.
- 전체 핵심 기능 구현이 모두 끝난 뒤에만 Windows EXE/실계정·수백 명·24시간/OBS·공식 Cubism·권리 TTS·실제 1~3초 전체 통합 검증→오류 일괄 수정→재검증. 기존 예약은 그대로 유지하고 원래 대화에 결과 보고 최우선. 실제 사용자 PC/실방송 성공을 허위 주장하지 않는다.
