## 90. 2026-10-22 — AI·Cubism·OBS 실측 지연 Windows GUI 표시 통합

### 기존 실패·완료·진행 상태
- 시작 `main` HEAD `25fbf12f495f85b40434115fcbd5c2e752419738`. 기존 누적 원문 1~89절·21개 과거 부록·원본 기획·100단계 pending·사용자 설정·캐릭터·SQLite 전체 보존.
- 89절 전체 CI [39698914434](https://github.com/junggyeol4444/AISTING/actions/runs/39698914434): 2,528개 실행, 2개 건너뜀, 실패 0 **성공**.
- 89절 Windows [39698914414](https://github.com/junggyeol4444/AISTING/actions/runs/39698914414): `windows-exe`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly`, `ollama-real-local-e2e` **모두 success**. 네이티브 Windows EXE/Tk GUI 검사도 통과. 실제 한국어 TTS→Cubism→OBS 같은 발화와 방송/녹화를 실제로 실행했다는 뜻 아님.
- 88절 완료된 실제 로컬 Ollama synthetic [39695199416](https://github.com/junggyeol4444/AISTING/actions/runs/39695199416): 500/500 접수·완료, 누락 0, 모델 실패 0, 3초 초과 499/500, 전체 p95 1939.547초, FIFO 대기 p95 1935.688초, AI 처리 p95 5.016초, **1~3초 목표 실패**. 실제 외부 시청자 500명 부하는 아님.
- 89절 실제 500건 [39698914387](https://github.com/junggyeol4444/AISTING/actions/runs/39698914387) 기록 시점 **in_progress**; 최종 latency/성공 판정 없음.

### 이번 90절 실제 추가 개발
- `src/ai_broadcaster/original_plan_full_pipeline.py`: 공식 실측 지연 세 구간을 한국어·초 단위로 표시하는 `OfficialChatObsEvidence.latency_summary_ko` 읽기 전용 속성. 실제 monotonic 시간 자료만 소수 3자리로, 표본이 없을 때는 `미측정`, 최종 시청자 구간은 `별도 미검증`. 기존 AI·WAV·OBS 사용권, 송출/녹화 금지, 질문 중복 발송 방지 유지.
- `src/ai_broadcaster/desktop_chat_tab.py`: 기존 Windows Tk GUI의 공식 AI→Cubism→OBS 검사 결과 문자열에 위 실측 지표 표시. 사용자 설정/저장 파일 변경 없음; 실행·사용권 검증을 통과하고 사용자가 해당 버튼을 눌러야만 측정함. 새 자동 질문·녹화·방송 기능 없음.
- `tests/test_aisting_official_chat_obs_pipeline.py`: 측정 2개와 OBS 표본 없는 경우 `미측정`, 시청자 E2E 허위 성공 금지를 확인하는 한국어 GUI 표기 계약 검사 1개 추가. 테스트의 가짜 OBS/음성은 실사용 검증 아님.

### 미변경·남은 개발·다음 위치
- 다른 저장소/예약/Drive/새 브랜치/force push/롤백/원본 코드 삭제 없음; 사용자 데이터·캐릭터·SQLite·설정·OBS 방송/녹화/채팅 송신·계정 로그인·무단 음성 모델 훈련 없음. 응답 길이 96, keep_alive 10m 임의 강제 없음.
- 아직 미실증: 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism 실제 입 움직임→OBS 동일 발화 오디오·영상, 4플랫폼 수백 명 실제 동시 채팅, 실제 24시간 방송과 재연결, 최종 시청자 응답 1~3초. 기존 FIFO p95 지연은 실패 그대로 유지.
- 다음: 본 회차 `main` HEAD 전체 회귀 및 Windows EXE·GUI·OBS·실모델 CI 최종 상태 확인, 오류 수정 후 전체 재검증. 실모델 500건 최종 로그와 AI/입/RMS/OBS 구간별 지연 측정 및 소스 병목 개발. 확인 못 한 실증은 성공으로 쓰지 않음. 후속 91절 원문 추가.
