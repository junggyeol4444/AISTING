# AISTING 기존 프로그램 수정 패키지 v21 — 실제 Open-LLM-VTuber 대화 코드 개발

## 사용자가 요청한 우선순위
- 실제 AISTING 개발 코드를 계속 작성한다. 사용자 PC 실기기 통합 검증은 나중에 시행한다.
- AISTING 원본을 새로 만들지 않으며, 기존 `desktop.py`를 보존한 별도 사본에 수정할 수 있는 패키지 형태를 유지한다.
- GitHub에서 개발/커밋/수정하지 않는다.

## 이번 회차 실제 신규 기능
1. `payload/src/ai_broadcaster/original_plan_conversation.py` **신규 추가**.
   - 오직 이미 실행 중인 로컬 공식 Open-LLM-VTuber 서버 `127.0.0.1:12393/client-ws`에 표준 WebSocket Upgrade/텍스트 입력.
   - 공식 `set-model-and-conf` 초기화가 올바르게 수신된 다음 `{'type':'text-input','text':...}` 전송.
   - 공식 응답의 `type='audio'` + `display_text.text` 문장만 받아 순서대로 결합하며 `control` + `conversation-chain-end`로 종료 판단.
   - **오디오 바이트/base64는 재생/저장/OBS 전달하지 않음.** 인공 대화 응답/가짜 LLM 엔진 없음.
   - 응답 없음, 서버 오류, 제한 시간, 잘못된 WS 프레임은 미완료 오류로 처리.
   - Python 표준 라이브러리만 사용. 파일 접근·네트워크 접근은 함수 실행 전까지 없음.
2. `payload/src/ai_broadcaster/original_plan_studio.py` 변경.
   - 기존 방송인 홈에 **'1단계 · 실제 AI 텍스트 대화'** 버튼 및 대화 창 추가.
   - 질문 입력, 매 질문별 명시적 승인, 워커 스레드 기반 비차단 동작, 공식 서버의 실제 응답만 텍스트 표시.
   - 현재 공식 설정이 외부/유료 LLM API를 참조할 수 있음, 상위 코어가 기록/TTS 데이터를 생성할 수 있음을 분명히 안내.
   - 앱에서 스피커/녹음/송출은 하지 않음. 음성/Live2D가 동작했다고 표시하지 않음.
3. `apply_to_existing_aisting.py`: 기존 원본 사본 적용 시 신규 모듈 포함.
4. `build_existing_windows.ps1`: 신규 모듈 확인, v21 고유 빌드 경로 (기존 EXE 보호).
5. `tests/test_v21_real_official_conversation_contract.py`: 승인 없으면 연결하지 않음, 입력 한도, 공식 메시지 텍스트 추출, WebSocket 클라이언트 마스킹/UTF-8, 무단 재생·송출 코드 부재 등 **작은 보조 검사 5개** 작성.

## READ ONLY 공식 프로토콜 근거
- https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/src/open_llm_vtuber/websocket_handler.py (blob `41368a6f6ba4ab82defb59df8be4b96fd2f6bfb7`)
- https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/src/open_llm_vtuber/conversations/conversation_handler.py (blob `02780b486bcb13783bf9a3b04b2dcbb5d182665f`)
- https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/src/open_llm_vtuber/conversations/conversation_utils.py (blob `02286e95138060cdae5fdb81de8f94d4c1902566`)
- https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/blob/main/src/open_llm_vtuber/utils/stream_audio.py (blob `c8ae52b3ba3ee8d9fd71ac7783a1db7901daf1c3`)

## 검증 증거와 정확한 제한
- 이번 회차 새 프로토콜 보조 검사 5개 통과, 기존 패치 코드 보조 검사 5개 통과, Python 구문 검사 통과.
- **실제 공식 서버에 질문을 전송하지 않았으며 진짜 모델 출력/한국어 TTS/Live2D/OBS 작동은 아직 미검증.** 사용자의 지시대로 실기기 검증은 후순위.
- 기존 `main` 전체 소스는 로컬에 확보하지 못했으며 전체 AISTING에 패치를 적용하지 않았다. Windows EXE 미제작.
- 새 코드의 네트워크 호출은 사용자가 버튼과 승인 절차를 거칠 때만 발생. 이 회차 외부 API 사용/모델 실행/소리 출력 없음.

## 다음 우선 개발
- 공식 AI 응답의 실시간 이벤트/턴 관리를 기존 방송 기능에 확대하되 원본 사용자 설정과 캐릭터 확정 저장을 반드시 우선한다.
- 음성·Live2D/VRM과 실제 플랫폼 채팅(사용자가 선택한 플랫폼)·OBS 연결 구현을 순차적으로 확장한다. 실방송/외부 게시/설치는 승인 없이 실행하지 않는다.
- 전체 원본을 확보할 수 있으면 기존 개발 코드 보존한 사본에 이 변경을 실제 적용. 실제 Windows 사용자 PC 통합 확인은 추후 검증 항목으로 남긴다.
