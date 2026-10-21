## 75. 2026-10-21 — 73~74절 미반영 기존 코드 보존형 main 반영 시도 및 검증 인계

### 사용자 요구·원본 보존
- 대상은 `junggyeol4444/AISTING` 기존 `main` 하나뿐. 이 변경의 부모는 `37ae19498f845ec7a0576fd68fc829a30d9a5de0`이며 강제 푸시·새 브랜치·롤백·다른 저장소/예약/Drive 변경 없음.
- 원문 1~72절과 부록 16개, ORIGINAL_PLAN/ROADMAP_100/config roadmap, 기존 GUI·캐릭터·SQLite·설정은 삭제·초기화·변경하지 않음. 73·74절 이전 원문을 본 문서와 과거 부록에 그대로 추가.
- 사용자 허가 없는 계정 OAuth 로그인/채팅 발신/방송·녹화/음성 모델 훈련 금지. 토큰 길이 96 및 keep_alive 10m 강제 재도입 금지.

### 이 커밋에 포함하는 실제 소스 수정
- `scripts/aisting_real_ollama_fifo_soak.py`: 장시간 paced 입력 중 완료 결과를 주기적으로 회수·집계하며 Windows 스레드 선점으로 인한 음수 sleep 방지. 실제 로컬 AI 추론은 기존 단일 FIFO·원래 코드 그대로 호출.
- `tests/test_aisting_real_local_fifo_soak.py`: 입력이 계속되는 동안 중간 결과 처리 및 모의 입력/실제 시청자 배송 실증 구분 회귀 2건 추가.
- `src/ai_broadcaster/original_plan_voice_obs_bridge.py`: 생성된 OBS 임시 ffmpeg 소스 UUID를 확인하여 재생 직전과 삭제 직전 다른 UUID의 사용자 소스가 되었다면 재생/삭제 거부. 기존 송출·녹화 차단, 음성 사용권 검사 유지.
- `tests/test_aisting_gpt_sovits_obs_integration.py`: UUID 정상 유지, 재생 전 변경, 재생 후 변경 방어 회귀 3건 추가. 테스트 모의 클라이언트는 실제 OBS·음성 실증이 아님.
- 이 새 변경은 실제 Windows EXE/OBS/Cubism/GPT-SoVITS 사용자 모델에 대해 아직 검증 완료한 상태가 아님. GitHub Actions 실행 전이나 진행 중인 결과를 성공으로 표시하지 않음.

### 이미 입증된 구버전 실모델 결과와 미완료
- 과거 실제 Ollama synthetic 입력 500/500건 처리, 누락 0건; 3초 초과 500건, 전체 p95 2781.218초, FIFO 대기 p95 2775.281초, AI 처리 p95 6.078초. 1~3초 목표 **실패**. 이전 실증에 대한 링크: https://github.com/junggyeol4444/AISTING/actions/runs/39572382928
- 이전 Windows 통합 CI에서 외부 시청자 채팅 0건으로 검사가 실패한 상태를 그대로 둔다. 로컬 한국어 Ollama 한 문장 생성은 성공했지만 실제 시청자 송달 성공을 뜻하지 않음: https://github.com/junggyeol4444/AISTING/actions/runs/39580268520
- 권리 있는 실제 GPT-SoVITS 한국어 WAV→공식 Live2D Cubism 실제 입 움직임→OBS 동일 발화 음성·영상 출력 E2E, 실제 4플랫폼 수백 명 동시 채팅, 24시간 실운용, 최종 시청자 1~3초 지연은 아직 **미완료·미실증**.

### 다음 회차 검증 및 수정
1. 새 `main` HEAD의 전체 회귀, Windows EXE 및 네이티브 Tk GUI, OBS 읽기·임시 소스, 로컬 Ollama 실제 모델 500건/24시간 및 4플랫폼 공개 읽기 CI의 **최종 상태와 실패 로그**를 수집.
2. 실패가 코드 문제면 원본 소스 보존하면서 수정하고 동일 HEAD에서 전체 재검증. 외부 공개 채팅 미수신은 소스 실패와 따로 기록하며 실제 채팅 0건을 성공으로 표시하지 않음.
3. GPT-SoVITS→Cubism→OBS **동일 발화 영상·음성** 결합 실구현과 병목 개선 및 24시간 재연결을 계속 개발. 실제 모델·방송/녹화/계정 작업은 무단 수행하지 않는다.
4. 실제 변경 파일·검사 내역·건드리지 않은 것·남은 작업을 다음 76절에 원문 추가. 다른 저장소/예약/Drive 그대로 보존.
