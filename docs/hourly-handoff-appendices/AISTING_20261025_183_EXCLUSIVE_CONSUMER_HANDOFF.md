# AISTING 183절 전체 누적 개발 부록 — 2026-10-25

이 파일은 기존 `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~183절,
`docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 과거 모든 부록,
`docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`,
`config/roadmap.json`의 원문을 대체하거나 삭제하지 않는다.

## 마지막 사용자 명령과 순서
- 원문: "개발 하라고". 기존 "개발부터 다 끝내라"에 따라 **남은 전체 기능 개발 우선 → 전체 회귀검사와 실제 Windows 10/11 EXE/GUI/OBS/실제 음성·Live2D·4플랫폼 통합검사 → 오류 수정 → 전체 재검증**.
- AISTING 외 프로젝트·Drive·예약 건드리지 않음. 새 브랜치, 강제 푸시, 롤백, 전면 재개발, 다른 설정/캐릭터/기존 SQLite 데이터 변경, 임의 96토큰/keep_alive 10m, 권리 없는 음성/훈련, 계정·OAuth 대행, 방송·녹화·채팅 발신 금지.

## 이번 실제 개발과 커밋
1. 시작 main `4b6ade235f987a25090b73f8e4ab570c4ccf8170` 재확인.
2. `src/ai_broadcaster/durable_public_chat_queue.py`: SQLite 원본 스키마 변경 없이 다른 프로세스의 중복 AI 소비자 실행을 막는 단독 운영체제 잠금 메서드 2개 개발. OS 잠금은 별도 잠금파일에 유지, 중복 시 fail-closed. 최초 커밋 `073e8412f5ef1082f4eede80d68be7126885985f`.
3. `src/ai_broadcaster/desktop_chat_tab.py`: 승인된 수신 시작 전에 단독 잠금 확보, 실패 시 연결 중단, 이전 AI 작업자 종료 확인 후 해제 경로 연결. 커밋 `e36bfa89b8b1b3ee3d60e7f95c0fc713b573d3c8`.
4. `tests/test_aisting_exclusive_consumer_183.py`: 서로 다른 창의 같은 DB 경합, 작업 종료 후 재연결, 미확인 채팅 원본 보존, 별도 DB 경로와 잘못된 잠금 경로 4개 계약검사 **작성만 완료**. 커밋 `132d83f5a7ff3fd8874144325e5694d3e443d38c`.
5. Windows 잠금 파일을 명확한 1바이트로 초기화하는 개발 정밀화 `b5a490c1421b1b8de8ec4d0a6e42e45a6a9581a6`. 해당 개발 코드는 **실행·검증되지 않음**.
6. 기존 전체·다음대화 원문 1~182절 보존, 두 인수인계 문서에 183절 추가(커밋 `c1036def7027a12c9934a2bf9b3a001b07976e66`, `7b7b97a637c33741b689cbf081664e03e4b7ccb8`).

## 아직 하지 않은 것 / 실패·미완료 보존
- 본 회차 새 검사나 전체 회귀, Windows EXE/GUI·OBS·실제 모델 실행 **하지 않음**. 테스트 mock을 실제 성공이라 보고하지 않음.
- 과거 CI Windows `39722213656` 최종 cancelled (4작업 성공·한국 채팅 작업 취소). 실제 Ollama `39720448468`은 500/500 처리해도 전체 p95 2979.984초, FIFO 대기 p95 2973.875초, 500건 모두 3초 목표 미달. 177절 전체 회귀 36 failures/33 errors 미해결.
- 실제 권리 있는 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 실제 입→OBS 동일 발화 오디오/영상 인과관계와 시청자 E2E 증명 미완료.
- 실제 4플랫폼 수백 명·수백 건 무누락, 24시간 재연결/안전성, 사용자 1~3초 지연 미완료.
- 기존 181~183절 영속 큐·복구/단독 잠금 기능의 실기기/동시 인스턴스 검증도 미실행.
- 모든 원본 파일·캐릭터·말투·SQLite 사용자 데이터·설정·기획/인수인계 원문 보존. 다른 저장소·예약·Drive·브랜치·계정·방송·녹화·채팅 발신 미수행.

## 다음 진행
실제 현재 main HEAD 및 CI 다시 확인 → AISTING 기존 코드 전체 필수 미완료 기능 개발을 계속 누적 완료 → 전체 회귀/실제 Windows 네이티브 GUI/OBS·한국어 GPT-SoVITS/공식 Live2D/4플랫폼·24시간 실증 → 오류 수정 → 전체 재검증. 사용자 지시를 수정하거나 임의 기본값 추가하지 말 것.
