# AISTING 103회차 실제 기능 개발 인수인계

## 103. 2026-10-22 17시대 — 사용자 지시대로 전체 검증 없이 AISTING 실제 기능 개발부터 누적

### 이번 사용자 최신 원문 및 실행 순서
> 내가 검증 말고 개발하라고 했지

- 사용자 명령: **남은 기능 개발을 먼저 누적 완료 → 그 후 전체 통합 검증 → 오류 수정 → 전체 재검증**. 개별 오류 수정/CI 검사를 앞세워 개발을 중단하지 않는다. 이번 103회차에는 테스트 실행, CI 수동 실행, 오류 수정은 하지 않았다. `[skip ci]`를 통해 기존 main 개발 커밋으로 인한 자동 CI를 선행하지 않도록 했다.
- 최초 확인 main HEAD는 `fa655120a69f1d1c07d580122b74ec1719eb66da`. 기존 원본 1~102절, 원래 기획·100단계 계획, 설정·캐릭터/SQLite/기존 부록/다른 프로젝트는 변경·삭제하지 않았다.

### 실제 신규 소스 개발 3단위 — 모두 기존 main fast-forward
1. `4a8631463c80f1550217c48a8793963bf4c30a88`: 기존 `original_plan_frontend.py` 공식 Live2D 창에 승인된 단일 질문과 동일 WebSocket에서 오는 **RIFF/WAVE 서버 오디오 헤더 후보의 선언 길이와 base64 복호화 예상 바이트 수 일치/불일치 건수**를 메모리 누적하는 기능을 개발. 기존 실제 WebSocket 전송 감사를 유지하고 첫 WAV 후보 도달까지의 `performance.now()` 기반 시간(초)을 기록. IPC `OfficialLipSyncEvidence`에 관측 결과와 `original_plan_full_pipeline.py`의 로컬 구간 보고를 연결. `desktop_chat_tab.py` 기존 Windows GUI에 공식 WAV·Cubism·OBS 연관 후보 상태와 첫 음성 도달 지연 표시. WAV 본문이나 모델/토큰·대화 텍스트 신규 저장/게시하지 않음. RIFF 길이 일치만으로 원래 화자·정확한 PCM 파형·시청자 방송 출력을 증명하지 않는다.
2. `44fb017b5c0041fbe796de7c1f0d28dc005f21f2`: `original_plan_obs.py` 기존 읽기 전용 OBS 프로그램 장면/음성 검사에 **관찰 전후 실제 프로그램 화면 두 번째 PNG 프레임 획득 선택 기능**과 동일 장면의 실제 영상 변화 여부 후보를 구현. `original_plan_full_pipeline.py`의 승인된 질문·동시 관측에서만 옵션 활성화, 공식 WAV 길이·Cubism 입/RMS·OBS 선택 오디오 미터 겹침·OBS 영상 변화 후보를 결합하는 신규 결과 속성 구현. 기존 Windows GUI에서 구분해서 표시. 영상 변화가 반드시 공식 아바타 입 때문에 발생한 것이라는 확증이나 실제 인코더·시청자 전달 증거가 아니며 프레임 외부 저장 없음.
3. `c340994def101383d976bdbb6c2c988ae96ec013`: `desktop_chat.py`에 기존 로컬 설정·기억·Ollama 연결 객체를 수신 세션 내에서 재사용하는 `LocalChatRunner` 신규 기능 구현. `desktop_chat_tab.py`의 기존 Twitch/치지직/SOOP/YouTube 단일 AI FIFO 워커에서 실제 `reply_function` 미주입 시 이 처리기를 선택하여 메시지별 JSON 설정·캐릭터 파싱과 HTTP opener 생성 비용의 반복을 줄이도록 연결. 메시지는 여전히 각기 독립 ID·전달 후 SQLite 기록·개별 오류 구분, 원래 단일 FIFO, 응답 본문/모델 선택, 캐릭터 선택, 생성 길이, 96토큰/keep_alive 설정을 임의로 변경하지 않는다. 재사용 기능이 수백 건에서 몇 초를 줄였는지는 아직 측정하지 않았다.

### 이번 회차 실제 한 것 / 하지 않은 것 / 이어받을 것
- **실제 한 것**: AISTING `main` HEAD 재조회, 기존 기획/누적 문서/실제 소스 읽기, 총 **3개 기능 개발 커밋**을 부모-자식 fast-forward로 반영. 신규 개발 대상 기존 소스는 `original_plan_frontend.py`, `original_plan_full_pipeline.py`, `original_plan_obs.py`, `desktop_chat_tab.py`, `desktop_chat.py` 5종. 새 브랜치 없음.
- **아직 하지 않은 것**: 새 코드 테스트, CI 수동 실행, Windows 네이티브 EXE/GUI 실기기 실행, 실제 승인된 본인 GPT-SoVITS WAV 음성·공식 Cubism 입·OBS 동일 발화 실증, 실제 수백 명 4플랫폼 무누락 실수신, 24시간 방송 및 재연결, 시청자 E2E 1~3초 실증, 테스트에서 확인된 오류 수정/전체 재검증. 실사용 완료라는 표현 금지.
- **진행 중/계속 개발**: 권리 있는 실제 한국어 WAV가 공식 Cubism 입/OBS 프로그램과 정확히 동일한 발화라는 실측 연계 강화, 4플랫폼 수백명/24시간 복구·보존, AI·음성·영상·시청자 지연 1~3초 병목 개선. 기존 102절 실제 Ollama 500/500건 완료에도 500/500건 지연 3초 초과, FIFO 대기 p95 2,973.875초 성능 실패, 과거 Windows 취소/실패 기록 모두 그대로 유지. 본 기능 개발 뒤에만 전수 검증/실패 수정/재검증.
- OAuth 동의 대행, 무단 채팅 발신/실제 방송·녹화 시작, 권리 없는 음성 학습·사용, 다른 저장소/Drive/예약 변경, 기존 소스 전면 재개발·롤백·force push 모두 하지 않았다.
- 다음 회차는 변경 가능성이 있으므로 **현재 `main` HEAD를 반드시 새로 조회**. 기준 기능 코드 HEAD는 `c340994def101383d976bdbb6c2c988ae96ec013`이며 본 원문 추가 후 HEAD가 더 전진한다. 이전 모든 1~103절과 부록·기획 원문 보존. 새 CI는 개발이 끝나기 전까지 아직 실행하지 않음.
