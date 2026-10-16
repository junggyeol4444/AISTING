# AISTING v26 — 기존 데스크톱에서 공식 AI 실제 응답을 순차적으로 표시 (1단계)

## 실제 변경

- `payload/src/ai_broadcaster/original_plan_conversation.py`: 기존 공식 Open-LLM-VTuber `/client-ws` 대화 세션의 `ask()`에 선택적 `on_progress(kind, value)` 콜백 추가. **서버가 전송한 `audio.display_text.text`만** 실제 수신 순서대로 전달. 공식 오디오 이벤트는 기존 WAV 컨테이너 검사를 거쳐 `audio_wav`/`audio_silent`/`audio_invalid`와 바이트 수만 알림. 원본 WAV·base64 음성을 UI 이벤트로 전달/저장/재생하지 않음. callback 예외는 서버에 질문을 다시 보내는 계기로 사용하지 않음.
- `payload/src/ai_broadcaster/original_plan_studio.py`: 기존 Tk 데스크톱 대화창의 백그라운드 수신 스레드 → `queue.Queue` → Tk 메인 스레드 전달. 서버에서 도착한 문장 조각을 **도착 시점에 화면에 누적**하고, 완료 메시지에서 문장을 중복 출력하지 않음. 연결 종료/서버 오류 시 받은 부분 응답을 '미완료'라고 표시. 닫힌 창 또는 이전 generation 결과 무시. 기존 승인·캐릭터 확정·설정 저장 흐름은 변경하지 않음.
- `tests/test_v26_live_official_response_stream.py`: 새로 11개 보조 회귀 검사. 기존 테스트와 합계 **216개 통과**. 테스트 데이터는 합성 이벤트이며 실제 LLM·TTS·Live2D 실행 검증이 아님.
- `build_existing_windows.ps1`: 빌드 경로를 v26으로 분리. 기존 exe 덮어쓰기 방지 규칙 유지. Windows EXE를 실제로 빌드하지는 않음.

## 연결과 미완료

- **개발 단계:** 원본 7부의 1단계(공식 Open-LLM-VTuber의 실제 AI 대화·기본 음성·Live2D) 개발 중.
- v26에서 실시간 표시하는 텍스트는 **공식 서버가 전달한 데이터**에 기반. **이 회차에서는 실제 공식 서버에 연결/질문/재생을 하지 않았음**. 로컬 검사는 메시지 계약과 UI 전달에 대한 보조 검사.
- 이전 v25와 마찬가지로 공식 WebGL Live2D 프런트엔드는 별도 브라우저 세션이며 AISTING 내부 텍스트 대화와 동일 세션으로 동기화되지 않음. 같은 세션이라고 표시하거나 립싱크 완료라고 주장하지 않음.
- AISTING **전체 원본 `desktop.py` 및 100단계 기록 사본은 현재 작업 공간에 없음**. 따라서 실제 전체 프로그램 사본 적용, 전체 프로그램 회귀, Windows EXE 및 실제 AI/한국어 음성/Live2D/OBS 동작은 미완료.
- GitHub 쓰기·설치·외부 게시·OBS 시작·마이크·스피커 재생 없음. 기존 비활성 예약은 변경하지 않음.

## 다음 작업

1. GitHub READ ONLY 확인된 전체 기존 원본 소스를 별도 안전한 로컬 사본으로 확보하고 사본에 패치 적용. 설정/기억/100단계 기록·캐릭터 확정 저장 보존 전수 확인.
2. 1단계 공식 Live2D 프런트엔드와 AI 대화에 실제 **동일 세션** 연결이 가능한지 프런트엔드 코드까지 읽기 전용 조사 및 현 UI 아키텍처 변경(임의 유사 엔진 불가).
3. 공식 TTS 응답 → Live2D WebGL/표정/립싱크 연결을 완성하고, 추후 운영자 PC에서만 실기기 검증. 그 다음 2단계 GPT-SoVITS, 3단계 OBS/실제 방송 채팅 순서로 개발.
