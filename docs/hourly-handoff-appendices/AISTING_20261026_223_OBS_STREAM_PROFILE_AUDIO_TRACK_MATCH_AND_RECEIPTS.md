# AISTING 223절 — 2026-10-26 OBS 활성 송출 프로필 오디오 트랙과 동일 WAV 입력 경로 연결

## 개발 기준
- 유일한 기존 저장소 `junggyeol4444/AISTING/main`, 시작 HEAD `e506b962d8716bf601fd25c3745b9a1901f03b4c` 실제 확인. 222절 부록, 기존 전체 인수인계 두 개(원본 Git blob 읽기), `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, OBS/승인 음성 실제 소스 확인.
- 원래 100단계 상태 9 completed/91 pending·운영자 최종 승인 대기, 기존 한국어 Windows 10/11 EXE/Tkinter/공식 Cubism/GPT-SoVITS/로컬 Ollama·설정·캐릭터·기억·SQLite 및 `num_predict=96`/`keep_alive=10m` 변경 금지. 219~222절 기능 재작성 대신 222절 오디오 경로 후보가 실제 OBS 프로필 선택 트랙과 교차하는지 개발.

## 실제 제품 소스 4개 파일 누적 구현
- **실제 제품 커밋 `6fc1a4e544cf737607de373137328f786bd8d2b5`**, 원래 main에 정상 비강제 expected-SHA fast-forward 반영.
- **`src/ai_broadcaster/original_plan_obs.py` 수정:** `ActualObsStreamAudioTrack` 자료형 및 `OfficialObsWebsocket.read_stream_audio_track_profile()` 추가. OBS WebSocket v5에서 현재 활성 송출 `GetStreamStatus`, 현재 프로필 `GetCurrentProfile`, 현재 출력 모드 `GetProfileParameter(Output, Mode)`, 고급 모드 `GetProfileParameter(AdvOut, TrackIndex)`를 읽기만 함. Simple 모드 트랙 1은 OBS Simple 기본 설정 후보임을 구분, Advanced는 명시된 1~6 트랙만 허용. 조회 불명/미활성/범위 밖이면 진행 금지. OBS 송출·녹화·장면·입력/트랙 설정 변경 요청 없음.
- **`src/ai_broadcaster/approved_live_voice_audio_route_watch.py` 수정:** 기존 OBS WAV 임시 입력 UUID·프로그램 장면/중첩 장면·음소거·볼륨·1~6번 활성 믹스 트랙 관측에 현재 활성 송출 프로필 선택 트랙을 연결. 선택 트랙이 WAV 입력 활성 트랙에 포함되지 않으면 발화 요청 전 차단. 재생 중에도 기존 1초 주기 관측 시 프로필 이름/모드/선택 트랙/근거 변화를 감지해 후속 발화 차단. 같은 WAV·같은 소스 소유권·기존 운영자/권리 승인 경계 유지.
- **신규 `src/ai_broadcaster/approved_live_voice_stream_track_receipts.py`:** 기존 사용자 SQLite 및 222절 AVR1 장부를 손대지 않고 `approved_live_voice_stream_track_receipts.sqlite3` AST1 독립 SQLite로 실제 WAV SHA256·승인 임시 소스 UUID·장면·프로필 이름/모드·선택 트랙·입력 활성 트랙·관측 횟수만 기록. 기존 다른 DB 침범 차단·동일 발화/구간 PK 중복 기록 금지. 원본 음성 바이트·시청자 닉네임/채팅 원문·비밀 토큰 저장하지 않음.
- **`src/ai_broadcaster/approved_live_voice_output.py` 수정:** 기존 GPT-SoVITS WAV→OBS 임시 입력→공식 Cubism 동일 WAV 입→실제 PLAYING 커서→OBS 오디오 후보 기록 다음, 실제 활성 프로필 선택 트랙 교집합 장부까지 저장한 뒤 구간 완료. 기록 실패 시 기존 재발화 차단·불명 처리 및 OBS 임시 소스 정리/공식 Cubism 원상복귀 경로 유지. 다른 OBS 소스/방송/녹화 제어 변경 없음.

## 의미와 미검증 경계
- **OBS 프로필의 선택 오디오 트랙 설정 후보를 읽어 WAV 입력 활성 믹스 트랙과 대조한 것**이지 OBS 실제 스트림 인코더에서 최종 인코딩된 오디오 패킷, 원격 플랫폼 수신, 시청자 청취 성공 증거는 아님. Simple 모드 기본 트랙 1 역시 프로필 관례를 사용한 후보이며 실제 인코더 트랙 판독이라고 주장하지 않는다.
- 전체 개발 미완료. 코드 테스트 **NOT_RUN**, 전체 통합 **NOT_RUN**, CI **미조회/미확인**, Windows 10/11 EXE·GUI **NOT_RUN**, 실제 권리 GPT-SoVITS·공식 Cubism·OBS 인코더·4플랫폼 수백 명·24시간 방송 **NOT_RUN**, 시청자 1~3초 **미확인**.
- 과거 CI `39720448468` 실제 로컬 모델 500/500 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초 실패; Windows CI `39722213656` 취소 기록 보존. 테스트나 오류 수정을 앞세우지 않고 개발 먼저 수행.
- 기존 사용자 DB·캐릭터·모델·원본 기획/100단계/이전 1~222절 인수인계 삭제·재개발/변조 없음. 브랜치 생성/삭제·force push·rollback·Drive/타 저장소·예약 조작 없음. 운영자 별도 승인 없는 실제 방송·녹화·OAuth·외부 채팅/공지·게임 조작·모델 다운로드/학습 없음.

## 다음 회차
- 224절은 최신 main HEAD/이 223절 4개 제품 소스·기존 전체 인수인계 확인 후 **남은 핵심 제품 기능을 실제 소스에 먼저 구현**: OBS 출력 오디오/영상 인과와 장시간 재생 안전, 4플랫폼 대량 FIFO·Ollama 병목·1~3초 목표, 승인형 24시간 방송·게임·자율 콘텐츠·Discord/카페 공지·장기 기억. OBS 설정만으로 실제 인코더/시청자 수신 성공이라고 주장하지 않는다.
- 개발 전체 종료 후에만 Windows EXE/실계정/OBS·공식 Cubism·권리 TTS/수백 명·24시간 전체 통합 검증→오류 일괄 수정→재검증. 기존 예약 하나와 원래 대화에서 이어 보고 우선; 다른 프로젝트·예약·Drive·무승인 실제 외부 행동 금지.
