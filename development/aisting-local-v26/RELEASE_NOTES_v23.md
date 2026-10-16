# AISTING 기존 프로그램 수정 v23 — 1단계 음성 데이터 수신 증거 처리

## v22에서 이어 개발한 코드
- `payload/src/ai_broadcaster/original_plan_conversation.py`: 공식 Open-LLM-VTuber `audio` WebSocket 응답 중 base64 WAV를 **메모리 내부에서만** 형식 검사한다. 유효한 RIFF/WAVE+fmt+data 청크 구조만 유효 데이터로 집계하며 무음(`audio: null`), 잘못된 데이터, 유효 데이터를 구분한다. `RealConversationResult`에 WAV 수신 패킷 수/바이트 수/무음/오류 개수 필드를 추가했다. AI 응답 텍스트 추출, 명시적 승인, 연결 재사용, 자동 재전송 금지는 보존했다.
- `payload/src/ai_broadcaster/original_plan_studio.py`: 공식 실제 AI 대화 결과에 WAV 데이터 수신 현황을 표시한다. **실제 스피커 재생, WAV 파일 저장, OBS 송출 없음. 수신 데이터만으로 청취/립싱크/한국어 자연스러움 완성 판정 금지.**
- `build_existing_windows.ps1`: 향후 Windows 빌드 산출물 경로 v23 분리, 기존 EXE 불변.
- `tests/test_v23_upstream_wav_evidence.py`: WAV 형식, 무음, 잘못된 base64, WAV 헤더만 있는 무효 파일, 잘린 청크, 비 PCM, 과대 입력, 동일 세션 응답 계수 검사를 8개 추가. 실제 AI 모델/TTS/OBS 수행 **안 함**.
- `DEVELOPMENT_STAGES_ORIGINAL_PLAN_v23.md`: 사용자 원문 0~8단계 진행표 및 향후 수동 판정 조건.

## 코드 근거
기존 공식 소스 `src/open_llm_vtuber/utils/stream_audio.py`의 `prepare_audio_payload`에서 실제 TTS 출력은 WAV로 변환 후 base64 `audio` 필드로 전송된다(이전 v21/v22에서 GitHub READ ONLY 확인). 반환된 오디오 컨테이너를 조사하는 일은 *실제 한국어 음성/Live2D 동작 검증을 의미하지 않는다*.

## 실제 로컬 검증
- v22 동일 패키지에서 복원해 Python 단위/계약 검사 기준점 **169개 통과**.
- v23 Python 로컬 단위/계약 검사 **177개 통과** (신규 8개). 이 검사에 사용된 WAV는 형식 시험용 생성 데이터이며 실제 GPT-SoVITS 음성이 아니다.
- Python 구문 검사 및 패키지 SHA-256/ZIP 무결성 검사는 별도 기록.
- 기존 전체 AISTING `desktop.py`+원본 소스는 이번 로컬 개발 공간에 없음. 전체 원본에 실제 적용/Windows EXE 빌드/AI 한국어 음성 생성/Live2D/OBS/실방송 검증은 미완료.

## 외부 영향 제한
GitHub READ ONLY 원칙 유지. 이번 회차 실제 네트워크 AI 호출/설치/모델 다운로드/훈련/음성 재생/녹음/OBS 제어/외부 게시 없음. 사용자 원본 파일/기존 EXE/과거 비활성 예약은 변경하지 않음. 코드 개발과 검사는 대화의 별도 로컬 작업 디렉터리에서만 실행.
