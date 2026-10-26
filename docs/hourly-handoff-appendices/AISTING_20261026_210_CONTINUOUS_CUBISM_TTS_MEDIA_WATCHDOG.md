# AISTING 210절 — 2026-10-26 기존 main 실제 승인 방송 공식 Cubism·한국어 GPT-SoVITS 연속 감시 및 안전 종료

## 시작 기준 및 원본 보호
- 실행 시작 시 실제 GitHub `junggyeol4444/AISTING` 기존 `main` HEAD: `470ad3e11903ca64ecc2cadab6311cef8b4bc352`. 이전 209절 인수인계와 원본 계획/로드맵·사용자 설정을 참고하고, 제품 코드 개발을 인수인계 문서 추가보다 먼저 진행.
- 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 1~209절 인수인계 원문 유지. 기존 캐릭터 이름·성격·말투, 등록한 GPT-SoVITS 권리·참조 파일·Ollama 모델, `num_predict=96`, `keep_alive=10m`, 사용자 SQLite/기존 DB·채팅·기록 삭제/변경하지 않음.
- 신규 브랜치·강제 push·롤백·외부 Drive·다른 저장소/예약 변경·실제 방송 실행·임의 OAuth·공지 전송·모델 훈련·권리 미확인 음성 사용 없음.

## 이번 실행의 실질 제품 개발 — 기존 main 비강제 소스 커밋 6개
1. `3ac1d91d0ed4308be5f5df4973da3f63cbb4fbe6`: 신규 `src/ai_broadcaster/approved_live_media_watchdog.py`. 운영자 승인 방송의 실제 단조 시계 기준으로 공식 Cubism·한국어 TTS 연결 상태 관측. 일시 중단과 지정 30초 이상 연속 미확인을 구별하고 회복을 별도 상태로 표시. 단독으로 OBS 송출 시작/종료·장면 변경·오디오 합성 수행하지 않음.
2. `ca8993c59f520e6adfce6a793f26b0e4bdb5fb5b`: 기존 `src/ai_broadcaster/approved_live_scheduler.py`에 `media_alive` 실제 상태 콜백 추가. 승인된 방송 송출 중 5초 간격 관찰, 30초 이상 지속 미확인 시 이전 슬롯에서 자신이 소유한 동일 OBS 출력에만 안전한 종료 시도. 별도 방송이나 장면·녹화 제어/무단 재방송 금지. 회복 이벤트·미확인 상태를 스냅샷에 보존.
3. `7e8c3de62f2ac6e2e817e85be03553dab1a4d3a8`: 기존 `src/ai_broadcaster/approved_live_slot_journal.py`에 매체 연결 지속 실패/복구 확인이라는 실제 방송 사건 종류 추가. 기존 시작/종료·OBS 장애 기록과 원본 SQLite 테이블·스키마 유지.
4. `c6f3d4ab9007323e6c5b3a69edf86a2bcd595249`: 기존 `src/ai_broadcaster/desktop_obs_tab.py`에 운영자 승인형 매체 감시 구성 연결, 사용자에게 30초 종료 유예 고지, Windows GUI 상태 표시.
5. `7f0bf9b0aa190e4ea03a45a25543d4ab6b346f5c`: 신규 `src/ai_broadcaster/approved_local_tts_listener.py`. 원래 공식 설정에서 검증된 로컬 `127.0.0.1`/`localhost`/`::1`의 GPT-SoVITS `/tts` 포트만 0.75초 이내 TCP 연결 관측. 외부 DNS·HTTP 요청·실제 음성 합성·모델 학습/설치 없음.
6. `28dfa6d40cf43bc19e7c29797721b9d34a36ab01`: 기존 `src/ai_broadcaster/desktop_obs_tab.py`의 매체 생존 콜백에 기존 공식 Live2D·페르소나/권리 한국어 설정 검사와 같은 로컬 음성 서비스 실제 수신 포트 관찰을 연결. TCP 연결만으로 합성·음성/입/OBS 동일 발화·시청자 수신 성공을 주장하지 않음.

## 현황과 미완료
- **이번 회차 제품 기능 구현 및 GitHub 기존 main 커밋: 완료. AISTING 전체 필수 기능 개발: 미완료.**
- **테스트 NOT_RUN / 통합 회귀 NOT_RUN / CI 미조회·미확인 / Windows 10·11 EXE/네이티브 GUI NOT_RUN / 실제 권리 GPT-SoVITS 한국어 WAV→공식 Live2D Cubism 입→OBS 동일 음성/영상 장시간 인과 NOT_RUN / 4플랫폼 수백 명·24시간·최종 시청자 응답 1~3초 NOT_RUN.**
- 과거 실모델 CI 39720448468: 500/500건 모두 3초 초과, FIFO p95 2973.875초, 전체 p95 2979.984초 실패. Windows CI 39722213656 취소. 원문 실패 사실 삭제·성공 표시 금지.
- 현재 로컬 포트 연결 관측은 실제 모델의 WAV 생성/시청자 수신 실증이 아니며, 사용자 승인 없이 방송을 재시작·재연결/전송하거나 타인의 기존 OBS 출력을 건드리지 않음.

## 다음 실행 개발 우선순위
- 동일한 원래 AISTING 대화에서 한국어 보고를 우선 시도, 새 대화나 중복 예약 요구/생성 금지. 매 실행 GitHub main HEAD 새로 읽고 210절 이후 원본 기획과 실제 소스 확인.
- 남은 원래 핵심 기능의 실제 소스 개발을 먼저 계속: 권리 GPT-SoVITS 동일 WAV→공식 Cubism 입→OBS 실시간 완결·장시간 복구/인과, AI 최종 1~3초 실효 응답을 위한 기존 96토큰/10분 설정 유지 선행 모델 처리 및 FIFO/백프레셔, 4플랫폼 수백 명 채팅 SQLite 전체 지속 수신·재연결, 24시간 승인형 방송·게임·콘텐츠 장기 자동 운영.
- 모든 개발 완료 이후에만 실제 Windows 10/11 EXE/GUI, 실계정 OBS·Live2D·GPT-SoVITS·4플랫폼 전과정 통합 검증 → 발견 오류 일괄 수정 → 전수 재검증. 불가한 실계정 승인·음성 권리·사용자 PC 실측은 미검증으로 정확히 보고.
