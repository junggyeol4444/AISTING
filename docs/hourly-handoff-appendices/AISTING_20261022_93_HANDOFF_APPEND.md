## 93. 2026-10-22 — 실제 공식 AI·Cubism·OBS 관찰 중 방송·녹화·장면 변경 즉시 불합격

### 원문·지시·작업 범위
- 시작 원격 `main` HEAD `d2949af4023503bda5b6e70e9c578ed8fdeb2521`. 오직 AISTING, 기존 main 안전 fast-forward만 허용. 1~92절 원문과 docs/hourly-handoff-appendices 전체, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 원본 소스·캐릭터·SQLite·설정 전부 보존·삭제 금지.
- 새 브랜치·force push·롤백·다른 저장소/프로젝트·예약·Drive·YouTube OAuth 사용자 계정 조작·자동 로그인·송출·녹화·채팅 발신·권리 없는 음성 학습/복제 금지. 미승인 `num_predict=96`·`keep_alive=10m` 재도입 금지.

### 이번 회차 실제 개발
- `src/ai_broadcaster/original_plan_full_pipeline.py`: 운영자가 권리를 확인한 단일 공식 AI→GPT-SoVITS→Cubism 동시 OBS **읽기 전용** 검증의 관찰 스레드가 OBS 사전 연결에서 방송 중이 아님을 확인한 뒤에도, **매 OBS 프로그램 영상/오디오 미터 관찰 앞뒤** OBS 실제 송출 상태·현재 장면·녹화 상태를 재확인하도록 보강. OBS 상태를 확인할 수 없거나 녹화/송출 또는 장면 변경이 감지되면 해당 표본을 신뢰하지 않고 별도 오류를 기록, 정상 동일 발화 동시 증거 성공을 반환하지 않음. OBS 상태 조회 자체만 실행하며 프로그램 장면/소스·녹화/송출 설정을 바꾸지 않음.
- `tests/test_aisting_official_chat_obs_pipeline.py`: 관찰 도중 모의 OBS 녹화 시작·장면 변경을 주입하여 기존에 정상 증빙으로 잘못 인정할 수 있는 경로의 불합격 회귀 2개 추가. 모두 합성/모의 외부 영상·음성 테스트이므로 **실제 한국어 WAV·Cubism 입·OBS 동일 발화 증명으로 주장 금지**.

### 이어받은 실제 CI/실패 판정
- 92절 소스 수정·문서 반영 HEAD `d2949af4` [전체 CI 39705830573](https://github.com/junggyeol4444/AISTING/actions/runs/39705830573) 성공, [Windows 통합 39705830684](https://github.com/junggyeol4444/AISTING/actions/runs/39705830684) 성공. 과거 92절 첫 실패는 원본 기대값 `platform_model_failures=={}` 오류였고 재검증으로 해소; 실패 기록도 문서에 보존.
- 새로 최종 확인한 89절 실제 Windows Ollama synthetic 500건 [39698914387](https://github.com/junggyeol4444/AISTING/actions/runs/39698914387): 접수·완료 500/500, 누락·모델 실패 0, 전체 p95 **4027.484초**, FIFO 대기 p95 **4019.125초**, AI 처리 p95 **11.172초**, 3초 초과 **500/500**. **1~3초 목표 명백한 실패**. workflow 성공은 무누락 의미일 뿐 실시간 처리/실제 수백 명 검증 아님.
- 91절 실모델 500건 [39702241916](https://github.com/junggyeol4444/AISTING/actions/runs/39702241916), 92절 [39704987503](https://github.com/junggyeol4444/AISTING/actions/runs/39704987503)은 본 문서 준비 때 진행 중: 최종 AI 단계/플랫폼별 지연값 **미확정**. 실사용 24시간 방송도 미진행.

### 수정 후 검증·건드리지 않은 것
- 이 93절 소스 적용 뒤 신규 테스트를 포함한 전체 회귀, 네이티브 Windows EXE/GUI, 로컬 Ollama·OBS 실제 읽기·Twitch/치지직/SOOP 공개 읽기 CI를 반드시 확인한다. 전체 통과 전 성공으로 단정하지 않음. 외부 방송/음성 모델/실제 로그인·채팅 발신/녹화는 수행하지 않음.
- 사용자 설정·캐릭터·음성 모델·SQLite·기존 파일·기획 원문·로드맵 pending·다른 프로젝트·예약·Drive·GitHub 타 브랜치 전부 미변경.

### 남은 핵심 목표 / 다음 회차
- 권리가 있는 실제 한국어 GPT-SoVITS WAV → 공식 Live2D Cubism **실제 입 움직임** → OBS **같은 발화** 오디오·영상 실증, 플랫폼 네 개에서 실제 시청자 수백 건 무누락, 24시간 안전성·재연결, 최종 1~3초 시청자 응답 모두 **미완료**. 실측된 FIFO 장시간 대기 병목을 유지되는 실제 모델/캐릭터/설정 위에서 수정·증명해야 한다.
- 다음 회차는 93절 HEAD 최신 회귀/Windows CI 결과와 신규 실제 Ollama 500건 최종 단계 p95·플랫폼별 FIFO 지연을 대조, 실제 로컬 모델·OBS·Cubism/WAV 검증의 누락을 계속 개발. 무엇을 확인하지 못했는지 명시하고 94절 인수인계에 원문 append.
