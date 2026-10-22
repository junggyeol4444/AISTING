# AISTING 112~113회차 신규 기능 개발 누적 인수인계

## 112. 2026-10-23 01시대 — 공식 WAV 수신 예상 음성창 안 Cubism 입·RMS 관측 신규 개발

### 원본 및 이번 개발
- 시작 main `d6172529c653e23a825d211a8d1173c9cc575d45`, 111회차 코드/인수인계 객체 `3b8156f4336c58cb110a08daccaea147088e38af` / `8ea9a1f6d604695bfc8383689b35dda0a1628aaf` 직계 자손은 당시 main 미반영. 원본 1~111절, 과거 부록, 사용자 금지, 기획/100단계/캐릭터/SQLite/설정 보존.
- `original_plan_frontend.py`: 111회차 공식 WebSocket PCM/float WAV 헤더의 음성 길이를 이용해 브라우저 `performance.now()` 기준 수신 예상창(최대 12초 + 250ms)을 만들고, 창 안에서 실제 Cubism 입 파라미터 변화·양수 RMS·립싱크 활성 표본을 계수. IPC에 `official_pcm_mouth_window_samples` 추가. 111회차 Python에 혼입된 JS 스타일 `//` 주석은 Python 주석으로 통합.
- `original_plan_full_pipeline.py`: 기존 공식 WAV PCM 헤더·Cubism·OBS 관측 후보와 WAV 예상창 내 입·RMS 표본을 결합하는 `same_session_pcm_mouth_audio_video_candidate` 추가.
- `desktop_chat_tab.py`: Windows GUI에 해당 결합 후보/미충족을 한국어로 구분.
- WAV 예상창은 실제 재생 시각, OBS 인코더 전달, 시청자 E2E 증거가 아님. WAV 본문/음성 원본·사용자 텍스트 저장하지 않음. 운영자 승인 없는 송출·녹화·채팅 발신/훈련 없음.
- **당시 결과**: 112회차 로컬 패치 `AISTING_112_누적개발_패치.py` 작성. 당시 GitHub create_tree 요청이 안전 검사에서 차단되어 main 미반영. 이번 113회차에서 111+112 누적 소스를 다시 읽어 Git tree로 통합했으며 112 당시 미반영 기록을 삭제하거나 성공으로 소급 수정하지 않는다.

## 113. 2026-10-23 02시대 — 공식 WAV 예상 음성창 Cubism 입·OBS 오디오 미터 실제 시간 겹침 신규 개발

### 이번 회차 수행한 신규 소스 개발
- 시작 GitHub main HEAD **`d6172529c653e23a825d211a8d1173c9cc575d45`** 확인. main의 기존 1~110절, 111회차 미반영 코드·원문 커밋, 112회차 미반영 패치, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 과거 38개 부록 전체 원문 및 실제 관련 소스 확인.
- `original_plan_frontend.py`: 112회차 공식 WAV 수신 예상창 안 실제 Cubism 입 변화·RMS 동시 표본의 **첫 번째/마지막 Python monotonic 시각**을 추가 수집. IPC 수량·시간의 유효 범위와 표본 개수/시각 일관성을 검사하도록 연결. 샘플 1건은 두 시점의 지속시간으로 취급하지 않음.
- `original_plan_full_pipeline.py`: 112회차의 후보 판정에 더해 **WAV 예상창 내 입·RMS 동시 표본 2건 이상**, 실제 monotonic 시각상 입 변화 구간, 실제 OBS 선택 입력의 양수 오디오 미터 구간이 **0초보다 긴 교집합**을 가질 때에만 PCM 예상창·Cubism·OBS 동일 발화 **연관 후보**로 판정하도록 개발. 기존 더 넓은 시간 중첩 결과와 구분하며 실제 송출/인코더 증거로 승격하지 않음.
- `desktop_chat_tab.py`: Windows 네이티브 GUI에 **WAV 예상 음성창 내 Cubism 입·OBS 미터 실제 시간 중첩 후보/미충족**으로 표시.
- 이번에 기존 111회차 Git tree 위에서 112+113 소스 개발을 누적한 **Git tree `746e1ab23e1801bed442d344de7ddcb623f85e82` 생성 성공**. 변경한 기존 소스는 위 3파일만. 새 브랜치/force push/롤백/전면 재개발/다른 프로젝트·Drive·예약 변경 없음. 기존 토큰 길이·keep_alive·캐릭터·SQLite·모델 선택/단일 AI FIFO 변경 없음.

### 이전 CI 실제 최종 상태와 로그 — 성공/실패 구분 유지
- Windows CI `39722213656`: GitHub 최종 `completed/cancelled`. Windows EXE 빌드·GUI 테스트 작업 자체는 `success`였으나, 한국 공개 채팅 읽기 작업 `119638028931`이 `cancelled`되어 **워크플로 전체 성공 아님**. 해당 취소 작업의 다운로드 로그는 GitHub 저장 BlobNotFound 404로 조회 불가. 구 로그 경고 `GUI_NATIVE_CANCEL_NO_LATE_SUCCESS_PASS (SIMULATED MODEL)`은 실제 모델 증거가 아니다.
- 실제 Ollama 500건 CI `39720448468`: GitHub 최종 `completed/success`, 실제 로컬 Ollama 모델 호출 500/500건 완료·실패 0건. 하지만 **500/500건 모두 3초 초과**, 전체 지연 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, 실제 AI 처리 p95 **7.875초**, 경과 **3133.64초**. 이 500개는 합성 채팅 입력 + 실제 로컬 모델이지 실제 시청자 500명이나 24시간 방송 실증이 아니다. 이전 CI 실패·취소 기록 보존.
- 이번 113회차에는 사용자 지시대로 **신규 개발 먼저 진행**. 새 CI 실행, 전체 회귀, Windows 10/11 EXE/GUI 실사용, 실제 OBS/Cubism/한국어 GPT-SoVITS 동일 발화 승인 실행, 오류 수정/전체 재검증 **아직 수행하지 않음**.

### 남은 작업 및 다음 인수인계
- 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism 실제 입→OBS 동일 발화 **실제 통합 실증**, 4플랫폼 실제 수백 명 채팅 무누락 처리, 24시간 실제 연결·복구 안정성, AI·음성·영상·시청자 E2E 1~3초 병목 개발 및 달성 **미완료**.
- 다음 회차는 최신 GitHub main HEAD를 **다시 조회**하고 111~113 누적 소스/원문을 보존한 채 남은 신규 기능 개발부터 계속한다. 개발 전체 완료 뒤에만 전체 회귀→Windows 네이티브 EXE/GUI·OBS·실모델 통합검사→오류 수정→전체 재검증. 원본 1~113절, 과거 부록, 사용자 지시·금지·실패·미검증 사항 삭제 금지.
- **본 절 작성 시점**: 소스 Git tree 객체 생성 완료, main 반영 성공 여부는 이후 별도 실제 GitHub 응답 확인으로만 기록한다.
