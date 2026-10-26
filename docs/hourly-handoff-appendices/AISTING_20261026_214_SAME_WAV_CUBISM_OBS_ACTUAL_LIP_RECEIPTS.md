# AISTING 214절 — 2026-10-26: 동일 실제 한국어 WAV→공식 Cubism 입 변화 관측→OBS 재생 요청 연결 개발

## 현재 실행의 기준
- 실제 `junggyeol4444/AISTING/main` 시작 HEAD: `c4b6263e95e6a733001120f90ad9029d76b36012`(213절 기록 이후). 현재 HEAD는 다음 실행 때 새로 조회.
- 기존 `approved_live_voice_output.py`, `approved_live_voice_causal_journal.py`, `approved_live_voice_prefetch.py`, `approved_live_voice_stream_lease.py`, `approved_live_voice_playback_watch.py`, `same_wav_cubism_driver.py`, `original_plan_frontend.py`, `obs_live2d_frame_link.py`와 이전 인수인계/원본 계획의 목표를 확인. 원래 승인형 OBS·공식 Live2D·GPT-SoVITS 경로를 대체하거나 새 모델로 변경하지 않음.
- 사용자 승인 없는 실방송·채팅·공지 발신, OAuth·음성 모델 학습, OBS 장면/녹화/다른 사용자 방송 변경 없음. 신규 브랜치, 강제 push, 원본 코드·캐릭터·SQLite 삭제, 다른 예약/저장소/Drive 변경 없음.

## 소스 개발: 기존 main 비강제 제품 코드 5개 커밋
1. `d7682f530f7c1299f37e2d372732389663d749d6`: 신규 `src/ai_broadcaster/approved_live_voice_sync_receipts.py`. 실제 사용자 승인을 얻어 발화한 WAV 구간별로 SHA-256, 동일 OBS 임시 음성 소스 UUID, Cubism 실제 구동 콜 횟수, 양성 호출/모델 파라미터 변화 횟수·첫 변화 시각, OBS 재생 요청 시각과 입 시작 요청 사이 간격을 기존 사용자 DB와 분리된 새 SQLite에 원자 기록. 음성 원문, WAV 본문, 개인·인증 토큰 저장 없음. 같은 turn_key/part 중복 기록 금지. 공식 입변화는 실제 렌더러 매개변수 관측 후보이며 플랫폼 시청자 AV 동기화 증명이 아님.
2. `9bb656b5e67d1597373afbf072bb84c29fc4b3b9`: `src/ai_broadcaster/approved_live_voice_causal_journal.py`에 원래 같은 WAV의 실제 `mouth_started_at`→`obs_triggered_at` 단조시계 간격을 읽는 원본 보존 메서드 추가. 기존 DB 테이블/데이터 구조 삭제·변경 없음.
3. `f96a9eb327f84b0b779ff7c6d4709e51d58a85fb`: `src/ai_broadcaster/approved_live_voice_output.py`의 실제 WAV → OBS 재생 경로에서 원래 무성 구간·8초 한도·공식 Cubism 모델·소유 OBS Lease 보존. OBS 임시 소스 활성화/연속성 확인 후 공식 Cubism PCM RMS 입 구동을 시작하고 바로 동일 파일 재생 요청을 전송. 기존 다음 구간 한 개 선행 TTS 합성은 현재 OBS 재생 요청 이후 실행하도록 배치. 동일 구간 Official Cubism 종료 관측 요약을 오디오 WAV 해시·원래 인과 장부 시각과 함께 별도 SQLite에 기록하고 실패 시 미기록을 성공으로 표시하거나 자동 재발화하지 않음. 종료 소스·임시 파일 처리 보존.
4. `928ed170dc6073e69a0296f1e0c5a52f750c8fb2`: 기존 `src/ai_broadcaster/desktop_chat_tab.py` Windows GUI 상태/과거 발화 기록 조회에서 실제 Cubism 매개변수 변화, 같은 WAV·OBS 트리거 간격, 입 변화-OBS 요청 상대 시간 근삿값을 분리 표시. GUI는 실제 최종 시청자 소리·립싱크 완성으로 오인시키지 않음.
5. `132a2bc451c4e40a8ab1bc40fe10a9353080ee34`: `approved_live_voice_output.py`에서 직접 구간 호출의 임시 키도 원래 WAV 인과 기록과 새 Cubism 관측 기록이 동일 식별자를 공유하도록 강제. 사용자 캐릭터·목소리·대화·음성 FIFO와 권한 유지.

## 완료/미완료/검증 상태
- **214절 소스 5커밋 개발·기존 GitHub main 반영 완료. 전체 AISTING 100단계 원본 실제품 완성은 아님.** 실 WAV·실계정·실제 Windows 10/11 EXE·OBS·공식 Cubism의 통합 실행은 하지 않았다.
- **테스트 NOT_RUN / 전체 회귀 NOT_RUN / CI 미조회·미확인 / Windows 10·11 EXE GUI NOT_RUN / 실제 합성 WAV→Cubism 모델 입→OBS 동일 발화 장시간 연속 출력 NOT_RUN / 4플랫폼 수백 명·24시간·실제 시청자 종단간 1~3초 NOT_RUN.**
- 사용자가 요구한 원래 미완 핵심: 로컬 AI 선행 추론 FIFO/백프레셔 실효 1~3초, 4플랫폼 대규모 SQLite 채팅 전량 내구·재연결, 같은 권리 한국어 WAV→공식 Cubism 입→OBS 방송의 장시간 완결/시청자 측 시청각 정합성, 24시간 안전 복구, 게임/콘텐츠/공지·기억 장기 운영. 이름/성격/말투·사용자 설정/기존 SQLite·`num_predict=96`/`keep_alive=10m` 보존.
- 이전 실모델 CI 39720448468: 500/500 모두 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초 실패. Windows CI 39722213656 취소. 성공 표시 금지.

## 다음 시간
- 기존 같은 AISTING 대화 보고를 최우선 시도하되 게시 위치 기술 보장이라고 거짓말하지 않음. 예약 추가/비활성화·다른 대화/저장소/Drive 조작 금지.
- 다음 회 실행 시 최신 GitHub main HEAD와 214절 이후 부록·기존 원본 소스를 확인하고 **미개발 원래 핵심 제품 기능부터 계속 코딩→기존 main 정상 비강제 커밋**. 전체 개발 완료 이후만 Windows/실모델·Live2D·OBS·4플랫폼 전과정 통합 검증 → 발견 오류 일괄 수정 → 재검증.
