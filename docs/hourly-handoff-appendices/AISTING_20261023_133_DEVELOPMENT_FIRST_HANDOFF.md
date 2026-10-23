## 133. 2026-10-23 16:30 KST — AISTING 서버 RECONNECT 누적 개발 및 GitHub main 반영

### 이번 시작 기준과 기존 사용자 지시 원문 보존
- 시작 GitHub main HEAD: `4c40d6495fbe248e0ca8b4cdbf74c13f7929f2f8`. 사용자 제시 인계 기준 `2687831af162f90f985da467aac9f90d0fd01828`은 이전 이력으로 유지하되 **최신 main을 기준으로만** 변경했다.
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~130절(기존 원문 341,676자), `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체, 97절 부록, 원본 기획 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 Twitch·다중 플랫폼 소스를 확인했다. 과거 인수인계/캐릭터/SQLite/사용자 설정은 삭제·대체하지 않았다.
- 131·132회차 ZIP에서 이전 미반영 `AISTING_131_Twitch_RECONNECT.patch`, 원래 작성된 비네트워크 테스트 3개 및 132회차 상위 재연결 테스트를 확인했다. **이전 ZIP의 원래 독립 테스트 파일은 이번 회차에도 그대로 ZIP으로 보존되며, main에는 133회차 통합 테스트로 같은 검증 경로를 포함했다.**
- 사용자 순서: **기존 기능의 전체 개발 먼저 → 전체 회귀·Windows 10/11 EXE/GUI·OBS·로컬 실모델 통합검사 → 오류 수정 → 전체 재검증.** 96토큰, keep_alive 10m 임의 설정 금지. 실증되지 않은 기능을 완료로 표시하지 않는다.

### 실제 main에 반영한 신규 코드(모두 정상 커밋, 새 브랜치·force push 없음)
1. `905ffad29befa0c8d81139808231619b18c6f7dc` — `src/ai_broadcaster/twitch_readonly.py`: 서버의 IRC `RECONNECT` 명령을 시청자 `PRIVMSG` 본문과 구별해 인식. 같은 프레임의 뒤쪽 채팅을 먼저 기존 AI 콜백에 전달하고 나서 재연결 예외를 발생시키며, 이미 있던 상위 수신기 재생성 경로를 이용한다. 131회차 작성·미반영 수정안의 실제 누적 반영.
2. `225abc4227f684083161abd4ad6274f40691f2bf` — 같은 파일: `TwitchServerReconnect(TwitchReadError)`를 추가해 서버의 명시적 명령과 일반 소켓 장애를 예외 타입으로 구분.
3. `7cf963ed9a49c83f0be96338f1c40b43c3d833ac` — `src/ai_broadcaster/multi_platform_session.py`: 명시적 Twitch `RECONNECT`일 때 일반 오류의 지수형 1~4초 대기를 생략하고 새 수신기 재생성. 일반 오류의 기존 대기·다른 플랫폼·사용자 Stop 정책은 그대로 보존. **이 변경은 1~3초 전체 시청자 응답시간 보장이나 실제 Twitch 메시지 무누락을 뜻하지 않는다.**
4. `55d28f61613d9d5c370e3e062a05149e33886c98` — `tests/test_aisting_twitch_server_reconnect_133.py`: 외부 네트워크 없는 대역에서 같은 프레임 RECONNECT 전후 채팅 순서/서버 ID, 분할 명령, 시청자 본문과 명령 구분, 새 수신기 생성, 재연결 공백 계측, 재연결 시 지수 대기 미호출을 검증하도록 테스트 코드를 추가. 131/132 테스트 범위를 포함하며 신규 테스트 실행 결과는 아직 미확인.

### CI/로그 확인 — 구 실패를 숨기지 않음
- 96절 Windows CI `39722213656`: 최종 `completed/cancelled`. OBS 공개 읽기·Twitch 공개 읽기·Windows EXE·Ollama 로컬 4개 job 성공, 한국 공개 채팅 읽기 job `119638028931` 취소. 취소 job 로그는 이번 회차에도 GitHub 404 `BlobNotFound`로 조회 불가.
- 실모델 500건 CI `39720448468`: 최종 `completed/success`, **실제 Ollama 500/500 처리, 실패 0건이나 500/500건 모두 3초 초과**. 전체 p95 2979.984초, FIFO 대기 p95 2973.875초, AI 처리 p95 7.875초. 합성 채팅이며 실제 500명/24시간/시청자 E2E 1~3초 증거 아님.
- 이번 회차 시작 직전 main `4c40d649...`의 전체 회귀 CI `39903724991`은 `completed/failure`: **2,555개 실행, 26 failures, 35 errors, 2 skipped**. 특히 `test_aisting_twitch_ai_integration`에서 실제 오류/실패. 이를 과거 성공으로 덮어쓰지 않는다. 이번 새 코드의 테스트 결과와는 별개다.
- 이번 새 커밋 `55d28f6...`에 따른 CI `39918388827`(전체 회귀) 및 `39918388805`(Windows EXE)는 조회 시 **queued**. 직전 커밋 `7cf963e...`의 실모델 500건 CI `39918357226`도 **queued**. 최종 성공/실패는 다음 회차 반드시 재조회한다. 중간 코드 커밋으로 생성된 일부 회귀·Windows 작업은 자동 취소됐으며 실패를 성공으로 바꾸어 보고하지 않는다.

### 이번 회차 하지 않은 일·미완료·다음 작업
- **하지 않음:** 이번 신규 테스트 로컬 실행, 전체 회귀의 최종 성공 확인, 새 Windows EXE 실행/GUI 클릭, 실제 개인 소유 한국어 GPT-SoVITS WAV 합성, 공식 Live2D Cubism 실제 입/OBS 동일 발화 영상·음성 실증, 4플랫폼 실제 수백 명 수신, 실제 24시간 방송, 시청자 E2E 1~3초 실증, 외부 OAuth 동의/로그인, 실제 송출·녹화·채팅 발신, 음성 모델 훈련.
- **남은 핵심:** 권리 있는 한국어 GPT-SoVITS 한 WAV→공식 Cubism 립싱크→OBS 동일 발화 오디오/영상 실증; 4플랫폼 실제 수백 명·수백 건 무누락 검증과 소켓 단절 중 서버 유실 한계; 실제 24시간 재연결/안전성; AI·음성·영상·시청자 E2E 1~3초 병목(특히 500건 FIFO 대기 p95 2973.875초) 개발·수정.
- **진행 중/다음 시작:** 현재 main HEAD와 위 신규 CI 최종 상태·실패 로그부터 다시 조회한다. 131/132 원래 독립 테스트 파일은 ZIP에서 계속 보존(이번 main에는 통합 133 테스트만 존재). 사용자 지시 범위 내 원본 기능 전체 누적 개발을 우선 이어가며, 개발 완료 후 전체 회귀→Windows 네이티브 EXE/GUI·OBS·실모델 통합→오류 수정→전체 재검증. CI 실패 26/35는 별도 미해결로 유지.
- 기존 원본 코드/기획·인수인계, 캐릭터, SQLite, 설정을 보존. 새 브랜치/force push/롤백, 다른 프로젝트/Drive/예약 변경, 계정 승인·방송/녹화/채팅 발신·모델 훈련 없음.
