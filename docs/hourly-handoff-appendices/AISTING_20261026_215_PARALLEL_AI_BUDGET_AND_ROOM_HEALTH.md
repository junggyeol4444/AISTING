# AISTING 215절 — 2026-10-26: 로컬 AI FIFO 작업자·선행 대기 한도와 실제 플랫폼 입장 관측 연결

## 출발점·기존 기능 보존
- 시작 시 실제 `junggyeol4444/AISTING/main` HEAD: `f71e200f35cc345a07439ba88b484d0a57f355ad` (214절 완료 시점). 매 다음 회차 최신 HEAD는 새로 확인.
- 원본 `src/ai_broadcaster/desktop_chat_tab.py`, `src/ai_broadcaster/desktop_obs_tab.py`, `src/ai_broadcaster/ordered_parallel_local_ai.py`, `src/ai_broadcaster/multi_platform_session.py`, `src/ai_broadcaster/durable_public_chat_queue.py`, 이전 214절 부록과 원래 AISTING 미개발 목표를 기준으로 직접 소스에 누적 구현함.
- 운영자 저장 모델 이름/캐릭터·말투·성격/대화 장기기억과 SQLite 본문·기존 채팅 FIFO/공식 Live2D·권리 한국어 GPT-SoVITS·OBS 원본 유지. 기존 사용자 지정 `num_predict=96`, `keep_alive=10m` 불변.
- 새 브랜치/강제 푸시/기존 원본 파일·DB 삭제/다른 프로젝트·Drive·예약 조작·승인 없는 실제 방송/채팅 발신/공지/OAuth/음성 합성·학습 없음.

## 본 회차 실제 제품 코드 4개 GitHub main 누적 커밋
1. `a3a137c360b622512b53e131508cfe86849b6efb` — 기존 Windows `src/ai_broadcaster/desktop_chat_tab.py`에서 별도 사용자가 켜는 로컬 AI 선행 추론 모드의 작업자 1~4개, SQLite→AI 선행 창 4~512건을 정확한 정수로 사전 검증하고, 기존 `OrderedParallelLocalAI(max_workers, max_prefetch)`에 인자로 연결. 기본값 4/32 보존. 작업자 추가는 같은 Ollama 모델의 병렬 요청 수만 바꾸고 페르소나/대화 기억/완료·발화·FIFO 순서를 바꾸지 않는다. 한도 초과분 채팅은 기존 SQLite에 그대로 대기. 실제 GPU 처리량·최종 시청자 지연 개선은 테스트/실측 없이 단정하지 않는다.
2. `f3b6d617a9e7c238616932d11055bdc27c2fc0fd` — 기존 `src/ai_broadcaster/desktop_obs_tab.py` 승인형 장기 방송 채팅 상태 점검. 이전에는 세션 객체의 Stop 여부만 봐서 실제 Twitch/Chzzk/SOOP/YouTube 중 선택한 플랫폼의 JOIN/API 준비 실패를 놓칠 수 있었다. 이제 플랫폼별 채팅방 실제 준비 상태·수신 공백·종료를 확인해 잘못된 정상 판단을 줄이고 원래 승인 방송의 채팅 재연결/안전 종료 콜백으로 전달.
3. `4581a578ea03f7855b8aace346c6d9df817d8f5c` — 기존 `src/ai_broadcaster/multi_platform_session.py`에 `live_room_readiness`를 추가하여 1초 주기 예약 방송 감시가 최대 4플랫폼의 서버 입장·현재 공백·종료 상태만 잠금으로 빠르게 읽도록 구현. 기존 전체 퍼센타일·수만 건 운영 진단 정렬은 빈번한 예약 감시에서 수행하지 않음. 네트워크 중단 중 서버가 애초 보내지 않은 채팅의 복원 기능은 아님.
4. `3f719692fbc04b09e9a3e059262f718791f81560` — `desktop_obs_tab.py`에 재연결·OBS 상태와 별도로 실제 플랫폼 입장 관측 설명을 표시. 수동 승인 방송만 사용하며 Tk 위젯 갱신은 기존 GUI 이벤트 루프가 담당. 동일 방송의 원래 OBS 출력 외에는 건드리지 않음.

## 남은 핵심 개발/검증을 완료로 위장 금지
- **215절 제품 소스 코드 작성 및 원래 main 비강제 반영 완료. AISTING 전체 개발 미완료.** GitHub 기존 브랜치 보존, 과거 1~214절 전체 인수인계 원문 유지.
- 여전히 원본 개발 목표는: 로컬 모델 실제 FIFO·백프레셔와 최종 시청자 1~3초, 권리 GPT-SoVITS 한국어 실 WAV→공식 Live2D Cubism 입→OBS 동일 발화의 장시간 인과/실출력, 4플랫폼 수백 명 채팅 전량 SQLite 보존·재연결과 24시간 방송 연속성, 장기 자율 게임·콘텐츠·공지·기억의 실사용 완성. 기존 200,000건 SQLite 보호한도 및 서버 미수신 사건의 복원 한계를 정확히 표시한다.
- **테스트 NOT_RUN / 전체 통합 회귀 NOT_RUN / CI 미조회·미확인 / Windows 10·11 EXE·GUI 실사용 NOT_RUN / 실제 실계정 OBS·공식 Live2D·권리 GPT-SoVITS, 수백 명 4플랫폼·24시간·시청자 최종 1~3초 NOT_RUN.**
- 과거 모델 CI `39720448468`은 500/500 응답 3초 초과, FIFO p95 2973.875초 및 전체 p95 2979.984초 실패. Windows CI `39722213656` 취소. 성공으로 고쳐 쓰지 말 것.

## 다음 회차 실행 지시
- 새로운 회차는 항상 **GitHub main 최신 HEAD 새로 조회 → 215절 이후 부록 및 현재 소스와 기존 원본 요구 확인 → 미완 핵심 제품 소스 실제 구현 → 비강제 main 누적 커밋 → 원문 보존 append-only 인수인계**.
- 전체 필수 개발이 끝난 뒤에만 실기기 Windows EXE, 로컬 모델·공식 Live2D·OBS·4플랫폼·수백 명/24시간 종단간 통합 검증 → 발견한 오류를 한꺼번에 수정 → 재검증. 이번 215절은 이 검증을 수행하지 않았다.
- 같은 원래 AISTING 대화의 작업 흐름 유지 우선. 별도 예약 생성/삭제·다른 프로젝트·브랜치·Drive/무승인 외부 발신 없음. 게시 위치를 기술적으로 보장한다는 거짓 주장 금지.
