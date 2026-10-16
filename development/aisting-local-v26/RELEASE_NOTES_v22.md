# AISTING 기존 프로그램 로컬 수정 v22 — 실제 공식 AI 연속 대화 세션

## 변경한 실제 코드

- `payload/src/ai_broadcaster/original_plan_conversation.py`: 공식 Open-LLM-VTuber 서버에 표준 `text-input`으로 보내고 공식 `audio.display_text` 텍스트/`conversation-chain-end`를 받는 **연속 WebSocket 세션** `OfficialConversationSession` 개발. 같은 연결을 여러 질문에서 재사용하여 서버 세션 컨텍스트가 유지될 수 있게 했다. 공식 코어의 메모리·히스토리는 코어가 관리하며, AISTING이 대화를 재구성하거나 답변을 만들어내지 않는다.
- 질문마다 **명시적 승인**을 요구하고, 이미 보낸 요청을 네트워크 실패 시 자동 재전송하지 않는다(중복 생성·처리 위험 방지). 서버 오류 발생 시 연결을 폐기하며, 신규 연결은 사용자가 다음 질문을 직접 승인해야만 실행된다.
- 창 닫기 시 **이 대화 연결만 종료**. 공식 서버와 OBS를 종료하거나 시작하지 않는다. 소리/녹음/방송 송출/외부 게시는 발생하지 않는다.
- `payload/src/ai_broadcaster/original_plan_studio.py`: 실제 공식 AI 대화 창에서 연결 재사용, 질문/응답 누적 출력, 질문 번호·세션 표시, 종료된 창의 늦은 응답 표시 차단. 오류 후 다음 질문은 새 세션으로 표시하여 모델 대화 기억의 연속성을 보장한다고 주장하지 않는다.
- `build_existing_windows.ps1`: 기존 v21 빌드 경로와 덮어쓰기 방지 원칙 유지하면서 새 v22 전용 경로 사용.
- `tests/test_v22_upstream_session_reuse.py`: 실제 AI 모델을 사용하지 않는 프로토콜 보조 검사 3개 (동일 WS 연결 2턴, 매 턴 별도 승인, 오류 시 자동 재전송 없음).
- 이전 v1~v21 수정 코드, 원본 보존 스크립트, 설정·기억·100단계 기록을 삭제하지 않았다.

## 개발과 실제 검증의 구분

- 로컬 Python 회귀 검사 총 **169개 통과**, 신규 3개 포함. 컴파일 및 ZIP 무결성 확인. 이 검사는 실제 AI 방송 기능 검증이 아니다.
- **실제 서버 질문·응답, 음성, Live2D/VRM 립싱크, 채팅, OBS, 방송 스케줄러, Windows EXE 실기기 검증 미실시**: 사용자 지시에 따라 실기기 검증은 후순위다.
- 2026-10-16 현재 컨테이너에서 원본 저장소 main ZIP의 HEAD 조회를 시도했으나 `Temporary failure in name resolution`로 실패. **원본 전체 소스 확보와 실제 적용은 미완료**. 이전 v21 역시 전체 원본이 아닌 사본 적용용 수정 패키지다.
- GitHub 쓰기/브랜치 수정/커밋/병합/푸시·프로그램/모델 다운로드 또는 설치·계정 로그인·음성 재생/녹음·실방송·외부 게시 **모두 수행하지 않음**.

## 공식 프로토콜 근거 — GitHub READ ONLY

- `Open-LLM-VTuber/src/open_llm_vtuber/websocket_handler.py` (`text-input`, `/client-ws`, 클라이언트별 ServiceContext)
- `Open-LLM-VTuber/src/open_llm_vtuber/conversations/conversation_handler.py` (text-input→conversation task)
- `Open-LLM-VTuber/src/open_llm_vtuber/conversations/conversation_utils.py` (`conversation-chain-end`)
- `Open-LLM-VTuber/src/open_llm_vtuber/utils/stream_audio.py` (`audio.display_text` 실제 텍스트)

## 다음 개발 우선순위

기존 전체 main 소스를 READ ONLY로 로컬 사본 확보 가능 여부 확인 → v22 사본 적용 및 원본 기능·설정·기억 보존 → 실제 플랫폼 선택을 반영한 채팅 입력 연결 및 공식 코어의 연속 대화 처리 → OBS와 TTS·Live2D 기능의 실제 연결 코드 → 종료/시작·공지·무인 운영 코드. 사용자가 요청한 **실기기/방송 검증은 나중에** 한다. 승인 없는 외부 동작은 금지.
