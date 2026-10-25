# AISTING 185절 개발 별도 인수인계 — 2026-10-25

이 부록은 기존 본문 1~185절과 전체 원본 인수인계 및 과거 모든 부록을 대체하거나 삭제하지 않습니다.

## 이번 사용자 명령 원문
개발 하라고 그리고 main에 올리고

## 지시 유지
AISTING 기존 소스 남은 기능 전체 개발 우선 → 개발 완료 후 전체 회귀 및 Windows 10/11 네이티브 EXE/GUI·GPT-SoVITS·Live2D·OBS·4플랫폼 실제 통합검사 → 오류 수정 → 전체 재검증. 새로운 브랜치·force push·rollback·전면 재개발, 타 프로젝트·Drive·기존 예약 변경, 무단 OAuth·방송·녹화·채팅 발신·모델훈련·권리 없는 보이스, 임의 기본 모델·96토큰/keep_alive 변경 금지. 모든 기존 원본 코드·사용자 페르소나·말투·SQLite 대화 기억·설정/기획/인수인계 원문 유지.

## 실제 개발 및 main 반영
시작 GitHub main HEAD a11c5a2205d06d90e6a3c4343184810e47bae156 확인. 기존 src/ai_broadcaster/obs_live2d_frame_link.py에 실제 OBS 별도 WebSocket에서 OFFLINE/녹화 꺼짐/정확한 공식 Live2D 창 capture 제목/프로그램 scene 확인 후 최대 33 PNG를 조회하고 SHA-256·실제 monotonic 시각만 일시 보관하는 OfficialProgramFrameSampler 추가. PNG/개인화면 원본 기록·파일 저장 없음. 시작 전 기준프레임과 실제 WAV 재생 중 프레임들을 분리해 관찰하며, 입력 캡처 대상 변경이나 장면 변경 시 실제 성공으로 표시하지 않음. OBS 전용 연결 종료도 추가.

기존 original_plan_voice_obs_bridge.py에 승인된 권리 있는 한국어 GPT-SoVITS 동일 WAV→공식 Cubism 입 구동 및 OBS 임시 ffmpeg_source 음량미터 경로와 이 별도 프로그램 영상 관찰기를 병행 연결. 이전 동기식 2회 PNG 조회 때문에 OBS 미터 수신이 늦어질 수 있던 경로를 분리했다. 화면 변화 후보·입 실제 RMS/파라미터·선택 OBS 미터 시각의 근접만 관찰하고, 인코더·시청자 동일 발화 송출 성공이나 실제 입 픽셀 인과성은 단정하지 않는다. 기존 사용자가 선택한 OBS 소스를 변경하지 않으며 자체 임시 source만 사용·정리, Cubism 원래 getRms 복원 유지.

기존 desktop_chat_tab.py의 Windows GUI 일회 승인 문구에 공식 OBS 프로그램 화면 최대 33프레임의 실제 일시 조회·원본 미저장·SHA만 보관을 구체적으로 표시. 공식 창 캡처 시작/종료 확인 내용도 포함. 기존 음성 미터만 단독 확인하는 경로와 무단 방송/녹화 발신 금지 유지.

기존 durable_public_chat_queue.py의 pending_public_chat에 (platform,channel,sequence) 복합 인덱스를 비파괴 추가해 4플랫폼 보류 채팅 범위 스캔을 줄이고, append마다 반복하는 전체 행 COUNT 대신 이미 DB commit 후 갱신되는 단독 소비자 인스턴스 self._pending 캐시로 200,000 미처리 보호한도를 확인하도록 개선. 채팅 메시지 내용 필터·드롭/합치기 없음. 다른 대화 기억 SQLite나 사용자 설정·캐릭터 파일 건드리지 않음.

추가 계약검사 tests/test_aisting_official_obs_frame_sampler_186.py (5개) 작성. 실제 OBS/권리 음성/실계정이 아닌 가상 인터페이스와 순수 시각 로직의 계약 검사이며 이번 회차 실행/통과 주장하지 않는다.

개발 실제 commit: 246bc241218c1a7fddeda45316c04b2fa5c78238, d4ffa3ee221d2372d014f8a7823257fd85ee8467, 07cd6e9d223e18bc8187d209892d815f0a79e666, d18b299b276f2b7ee70ae835ef657a674eaed029, 345bf9e3a0bc552515fcb5ceb9b5ac1159288924, 96f92dc5c380552f1fa473734df04497b4e8234f, fbf306c418ad608a83dce25e917968cc70183168.

## 검증을 성공으로 보고하지 않는 이유
이 회차 신규 계약검사는 작성만 했고 실제 Windows EXE/GUI·OBS/로컬 GPT-SoVITS·공식 Cubism 실통합 실행은 하지 않았다. 최신 검사 run 40171227129, Windows EXE run 40171227075는 마지막 확인 시 queued. 구 Real 500 chat run 40171113703 queued; 구 345bf9 CI 40171113716/40171113728 cancelled. 이전 실모델 500건 run 39720448468은 전체 처리되었으나 전부 3초 목표 초과, 전체 p95 2979.984초·FIFO 대기 p95 2973.875초; 이전 전체 회귀 36 failures/33 errors도 미해결. 실제 4플랫폼 수백 명 무누락·24시간·시청자 1~3초 및 OBS 인코더 출력을 검증하지 않았다.

## 한 것 / 안 한 것 / 미완료·하다가 만 것
실제 한 것: 위 코드 변경·main 커밋, 기존 1~184절 및 원문 보존한 새 185절 전체/다음 대화 인수인계 누적, 별도 이 부록 작성.
안 한 것: 테스트 통과 주장, Windows 실기기 버튼 실행, 실계정 방송·녹화·OAuth·채팅 발신, 모델 설치/훈련, 실제 음성/Live2D/OBS 인코더/시청자 1~3초 실증, 타 프로젝트·예약·Drive 변경.
남은 것: AISTING 기존 소스의 나머지 실사용 요구사항 개발, 500건 FIFO 실측 수천 초 대기와 실제 1~3초 E2E 병목 개선, 장기 24시간 4플랫폼 재연결/무누락, 권리 있는 실제 GPT-SoVITS→공식 Cubism 입→OBS 동발화 영상·오디오 출력 실증. 모든 기능 개발 완료 뒤 전체 회귀/Windows 네이티브 EXE·GUI/실장비 검사→오류 수정→전체 재검증 필요.
진행 중 멈춘 것: 185절 코드와 검사 코드 작성/소스 main 반영 후 전체 기능 개발은 아직 끝나지 않았고 검증/수정 단계로 전환하지 않았다. 다음 실행은 새 main HEAD·CI 상태 재조회부터 시작하고 기존 모든 원본/절/부록을 보존해야 한다.
