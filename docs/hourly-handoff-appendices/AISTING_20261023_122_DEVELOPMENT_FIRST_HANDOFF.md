# AISTING 122회차 누적 신규 개발 인수인계

## 122. 2026-10-23 — 실제 GPT-SoVITS WAV 발화·쉼 및 OBS 미터 신호 구간 연결, 음성·OBS 단계별 실제 시간 계측 신규 개발

### 시작 HEAD / 과거 사용자 지시 확인
- 최신 사용자 지시 `계속`; AISTING만 기존 `main`의 미완료 기능 **전체 누적 개발을 우선** 진행하고, 개발 완료 후 **전체 회귀검사 및 네이티브 Windows EXE/GUI·실제 OBS·로컬 모델 연동 검사 → 오류 수정 → 전체 재검증** 순서를 지킨다.
- 실제 시작 `main` HEAD `20bfbe694e4f57ce38aa8c023f7bb6aa450a648e` 재확인. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~121절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, 특히 97절 과거 원문 및 121절 부록을 조회. 기존 본문·부록/설정/캐릭터/SQLite/원래 코드 삭제·덮어쓰기 없이 이 절만 문서 뒤에 누적 추가.
- 기존 Windows CI `39722213656` 재조회 결과 `completed/cancelled`; 기존 성공했던 일부 작업이 있어도 전체 성공 아님. 실제 Ollama 500건 CI `39720448468` 재조회 결과 workflow `completed/success`이지만 합성 채팅 500/500건 전부 3초 초과. 기존 p95 전체 2,979.984초, FIFO 대기 2,973.875초, AI 처리 7.875초. 이는 500명 실제 시청자/송출/1~3초 E2E 달성 증거 아님. 모든 구실패·취소 로그 이력 보존.

### 실제 신규 소스 개발 1 — 권리 있는 WAV의 발화/쉼 패턴과 OBS 실측 미터 구간 대응
- 개발 커밋 `14c96d5a2da04eb8d540f43887c00d763c69b9c4`을 기존 main에서 `force=false` 안전 fast-forward 반영.
- 기존 `original_plan_obs.py`의 `ActualObsAudioMeters`에 `selected_all_meter_level_samples` 기본값 필드 추가, 실제 OBS `INPUTVOLUMEMETERS` 선택 입력의 양성/0레벨을 50ms 이내 동일 구간에서 한 값으로 집계하고 메모리 최근 256개에만 보관. **0레벨을 임의 생성하지 않고 실제 이벤트가 있어야만 포함**한다. 기존 positive-only 측정·UUID·입력 음량 상태 검증은 유지한다.
- 신규 `src/ai_broadcaster/voice_observed_segments.py`는 앞선 121회차에 구현한 실제 16-bit PCM WAV 50ms RMS 음량 윤곽과 **선택 OBS 임시 입력의 실제 비음성/음성 레벨 이벤트**를 대조한다. 관측하지 않은 침묵·보간 시각을 추가하지 않고 0~1초 후보 지연, 12개 이상 시간표본/발화 및 무음 각 4개 이상 등 별도 조건에서만 비교한다. 발화/쉼의 균형 일치 점수, 사용한 각각의 표본 수, 후보 지연을 메모리에서 계산한다. PCM WAV 형식 미지원·관측 부족·시간 역행·모두 발화/무음 등은 `미측정`으로 보존하며, 점수≥0.8 및 각 발화/쉼 일치율≥0.7인 경우만 **실측 구간 패턴 유사 후보**로 표시한다. 이것만으로 파형 동일성·해당 WAV 자체의 녹음/송출·화자·Cubism 입 연동을 실증한 것이 아님.
- 기존 `original_plan_voice_obs_bridge.py`의 `RealVoiceObsResult`에는 호환용 기본값 필드 `obs_wav_segment_*` 추가. 기존 사용 권리/운영자 1회 승인 확인 후 실제 합성 WAV→유일 OBS 임시 입력 생성/재생/자동 삭제 작업에서 해당 표본만 비교한다. `desktop_chat_tab.py` Windows GUI에 발화·쉼 패턴/후보 및 미측정 구분 표시. 출력 또는 송신 동작의 자동 추가 없음.

### 실제 신규 소스 개발 2 — 합성·OBS 입력 준비·관측 단계별 지연 분리
- 개발 커밋 `5b74c0857e984d24b6c23d9b5f1cc0621d0c96a8`을 기존 main에서 `force=false` 안전 fast-forward 반영.
- 승인받은 실제 1회 WAV 합성 경로의 **OBS WebSocket 연결**, **실제 로컬 GPT-SoVITS 합성**, **임시 OBS 미디어 입력 생성 및 확인**, **OBS 미터 실제 관찰**, **합성 완료→OBS 처음 관측된 양성 미터 이벤트**를 같은 Python `time.monotonic()` 실제 시각으로 분리 계측하고 `RealVoiceObsResult` 기본값 필드로 전달한다. 외부 송출 또는 최종 시청자 1~3초 측정치가 아님. 실패/OBS 실제 측정 표본 없음은 미측정. 기존 Windows GUI에 계측 각각 한국어 표시.
- 합성 경로의 보이스 학습, 권리 없는 음성, 무단 계정/OAuth, 외부 방송/녹화/채팅 발신, 저장된 캐릭터·SQLite·설정 변경은 **하지 않음**. 기존 응답토큰 길이 96 또는 keep_alive 10분을 임의 추가하지 않음.

### 안 한 것 / 남은 일 / 다음 회차
- **실제로 한 것:** AISTING GitHub 현재 main·과거 인수인계·기획·실제 원본 소스 조회, 기존 121회차 WAV→OBS 1회 승인 경로에 기능 2개 누적 개발, 신규 모듈 1파일+기존 파일 변경 및 GitHub main 안전 fast-forward 커밋 2개, 인수인계 122절 원문 뒤 추가.
- **실제로 하지 않은 것:** 신규 CI 실행, 전체 회귀검사, Windows 10/11 EXE·GUI 실제 실행, 실제 본인 라이선스 GPT-SoVITS 장비·공식 Cubism·OBS 실사용 계측, 실제 수백 명·24시간 읽기 성공, 실방송·시청자 E2E 1~3초 실증, 신규 코드 오류 수정 또는 전수 재검증. 기존 CI 실패 사실을 지우거나 mock를 실사용 실증으로 표기하지 않음.
- **다음에 해야 할 핵심 기능:** 기존 동작을 유지하며 권리 있는 한국어 GPT-SoVITS WAV→공식 Live2D Cubism **정확한 동일 발화** 립싱크→OBS 영상·음성 실제 경로 및 동일 PCM 파형 대응 구현·실증, 실제 4플랫폼 수백 건·수백 명 누락 처리, 실제 24시간 재연결/안전성, 로컬 AI FIFO·음성·영상/시청자 1~3초 지연의 원인 및 병목 개선 개발. **전체 개발 완료 후** 전수 회귀/Windows 네이티브 EXE/GUI/OBS·로컬 모델 실사용 검사→오류 수정→전체 재검증.
- 본회차 기능 개발 HEAD `5b74c0857e984d24b6c23d9b5f1cc0621d0c96a8`. 문서 반영 뒤 HEAD가 달라지므로 다음 회차는 다시 확인. **새 브랜치/force push/롤백/전면 재개발, 다른 프로젝트/Google Drive/기존 예약 변경 없음.** 모든 기존 인수인계 1~121절 및 과거 부록 보존.
