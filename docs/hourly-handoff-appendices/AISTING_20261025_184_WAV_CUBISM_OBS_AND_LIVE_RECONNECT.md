# AISTING 184절 원문 보존 추가 인계 — 2026-10-25

이 부록은 docs/AISTING_HOURLY_FULL_HANDOFF.md의 1~184절, docs/AISTING_NEXT_CONVERSATION_HANDOFF.md, 과거 모든 hourly-handoff-appendices, docs/ORIGINAL_PLAN.txt, docs/ROADMAP_100.md, config/roadmap.json의 원본을 대신하지 않는다.

## 마지막 사용자 지시 (원문)
개발 다 안했잖아
다 하라고

기존 개발 지시: AISTING만 모든 남은 기능 코드 개발 우선 누적 완성 → 그 후 전체 회귀검사와 Windows 10/11 네이티브 EXE·GUI·OBS·실모델·4플랫폼/24시간 통합검사 → 오류 수정 → 전체 재검증.

## 이번 회차 실제 main 반영
시작 HEAD 79d201faadacfc2bbb4b05e08896c25f58a3bc4a 확인. 기존 main 원본, 사용자 페르소나·설정·SQLite 기억, 과거 기획안·전 절 및 모든 부록 삭제 없음. 브랜치 추가, force push, 롤백, 다른 레포/예약·Drive 작업 없음.

- 신규 same_wav_cubism_driver.py, 원본 original_plan_frontend.py, original_plan_voice_obs_bridge.py, desktop_chat_tab.py 수정: 한국어 GPT-SoVITS 한 실제 WAV의 16비트 PCM 50ms RMS를 공식 Live2D Cubism 렌더러의 현재 _wavFileHandler.getRms 경로와 OBS 자체 임시 media input으로 공유하는 승인형 단일 WAV 결합 코드 추가. 실제 입 변화 시각·관찰값, OBS 현재 프로그램 이미지 한 프레임·선택 입력 미터의 실측 후보 및 시간 중첩 분리 보고. 원래 Cubism 입 훅 복원·임시 OBS 입력 제거, 방송/녹화 중 실행 차단, 기존 캐릭터·음성 권리·사용자 승인 확인. 사용자는 GUI 새 버튼으로만 1회 선택 가능. 인코더/시청자 수신 실제 증명은 아직 없음.
- durable_public_chat_queue.py: 이미 복구한 행 뒤에서 신규 seq를 이어 읽는 커서, 성공 서버 ID를 pending 행 삭제와 같은 SQLite 트랜잭션으로 확정하는 추가 테이블. 원본 pending 데이터와 사용자 메인 대화기억 DB 불변.
- desktop_chat_tab.py: 보류 채팅을 수시간 복구하는 동안에도 4플랫폼 수신기를 열고 신규 메시지는 영속 DB에 우선 저장 후 기존 seq 순서대로 AI FIFO에 전달. 원자 모드 전환·Stop과 오류시 보류 데이터 유지.
- multi_platform_session.py: 영속 DB에 저장한 메시지 건수와 실제 AI FIFO 등록 건수를 구별 계측, 미등록 건수를 화면에 표시할 수 있는 읽기용 상태 필드.
- 변경 커밋: ae72dadf, 2cb8fe9f, 25b1488c, 2c3b61ca, f72e5a71, d6bfe5b9, 19adedd5, 72da4f6d, 23bd3ddf, 09ea9f16, 97b0a5a4, 3a169faa, 09c55b78, a73f95d5, edafe5e6.
- 테스트 파일 작성만 완료: test_aisting_same_wav_cubism_obs_184.py(7개), test_aisting_live_recovery_during_receive_184.py(4개), test_aisting_confirmed_server_events_185.py(5개), test_aisting_sqlite_deferred_accounting_185.py(4개). 코드 커밋 cc905c62, 9ff335db, e9393a76, 512dc82b. 새 테스트는 실행하지 않았으며 통과 주장 금지.

## 실패·미완료·진행 중
- 구 Windows CI 39722213656 최종 cancelled, 4개 job success/한국 공개 채팅 job 취소. 구 500건 Ollama CI 39720448468은 실모델 500/500 처리했어도 500/500 모두 3초 초과, 전체 p95 2979.984초, FIFO p95 2973.875초, AI p95 7.875초. 177절 전체 회귀 40155307503 36 failures/33 errors/2 skipped 미해결. 최신 512dc82 기준 전체 회귀 40169810575 및 Windows EXE 40169810560은 마지막 확인 시 queued; 구버전 일부 CI는 cancelled.
- 이번 회차 미수행: 신규 기능 검사 실행·전체 회귀·Windows EXE/GUI 버튼 실기기 실행, 권리 있는 실제 한국어 GPT-SoVITS 모델 사용, 실제 공식 Cubism/OBS 인코더 송출 확인, 4플랫폼 수백 명 무누락 실계정 시험, 24시간 운영·1~3초 시청자 E2E 실측, 계정/OAuth 대행·녹화·방송 송출·채팅 발신/모델 훈련.
- 남은 필수 개발: 장기 자율 운영/방송 안전성 누락 구현 확인, 실제 동일 음원 화면·소리 인과성과 장기간 4플랫폼 재연결/순서 처리, 단일 FIFO 실제 Ollama 500건 1~3초 불가능한 적체·음성·영상 병목 구조 개발. 외부 모델·사용 권리·운영자 실제 승인 없으면 실증 성공 주장 금지.
- 본 회차 완료 구간은 코드 및 계약검사 작성/소스 main 반영, 전체 완성 검증 전. 처음부터 새 프로젝트 재개발 금지. 사용자 요청 없는 임의 토큰 96·keep_alive 10m 설정 금지.

## 다음 실행 순서
현재 main HEAD와 실제 CI 최종 결과 확인 → 기존 본문 1~184절 및 모든 부록 원문 읽고 AISTING 기존 코드에서 필수 남은 기능 전체 개발 계속 → 모든 개발 완료 후 회귀/Windows 네이티브 GUI·OBS·실모델·4플랫폼 통합검사 → 오류 수정 및 전체 재검증. 타 프로젝트·예약·Drive·브랜치·계정/방송/설정 무단 변경 금지.
