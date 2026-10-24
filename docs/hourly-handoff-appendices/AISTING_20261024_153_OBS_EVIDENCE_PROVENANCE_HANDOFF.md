# AISTING 153회차 원문 누적 인수인계

## 153. 2026-10-24 — 실제 OBS 채택 표본의 출처와 동일 발화 관찰 후보 연결 개발

### 시작 기준·원본 보존
- 시작 `main` HEAD: `2e4e3ca27c665e4812edd3bacad105777634d75c` (152절 포함). `docs/AISTING_HOURLY_FULL_HANDOFF.md`의 1~152절 원문, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 원문, `docs/hourly-handoff-appendices/` 모든 기존 부록(특히 97절), `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 main 소스를 읽거나 원문/트리 보존을 확인했다. 기존 캐릭터·SQLite·설정·원본 파일 삭제/초기화 없음.
- 새 브랜치·force push·롤백·전면 재개발·다른 프로젝트·Drive·다른 예약 변경 없음. 실계정 OAuth 동의 대행·방송·녹화·채팅 발신·모델 훈련·권리 없는 음성 사용 없음. 모델 토큰 96 또는 keep_alive 10m 임의 설정 없음.

### 이번 회차 실제 누적 개발
- 기존 `src/ai_broadcaster/obs_consecutive_audio.py`에 `collect_obs_audio_evidence`를 추가하여 실제 채택한 OBS 양성 미터 시각·관찰창 개수·채택 창 원래 순번을 함께 반환하도록 개발했다. 기존 `collect_obs_audio_times`의 두 값 반환 계약은 래퍼로 유지했다. 새로운 OBS 음성·무음·시간 표본은 만들지 않는다.
- 기존 `src/ai_broadcaster/original_plan_full_pipeline.py`에 `_matched_obs_audio_candidates`를 추가하고 공식 GPT-SoVITS/Live2D/OBS 단일 질문 경로의 동일 발화 OBS 후보 선택을 **실제로 채택된 창**에만 귀속시켰다. 시간상 겹치더라도 경로 단절·무관측 공백·손상 뒤의 창은 앞쪽 발화의 선택 후보로 다시 합치지 않는다. 실측 표본 출처와 최종 선택된 OBS 관찰 객체가 어긋나는 위험을 줄이는 개발이며 시청자 인코더/송출 실증은 아니다.
- 기존 소스 2개 수정 코드 커밋 `04d2e5e98d88edb92c03467d1321ae2d4f96b3ce`. 신규 가상 계약검사 7건 `tests/test_aisting_obs_evidence_provenance_153.py` 작성 커밋 `51589015f2100800d1ac3b1c5a41c67f5fee6636`. 테스트는 **작성만 하고 직접 실행하지 않았다**. 이 회차의 코드 반영을 실제 방송/실모델 검증 성공으로 간주하지 않는다.

### 실제 확인한 CI와 기존 실패
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): 최종 `completed/cancelled`. 5개 작업 중 4개 성공, 공개 한국어 채팅 읽기 작업 취소. 취소 작업 로그는 조회 불가(404). 전체 성공으로 보고하지 않는다.
- 96절 실제 Ollama 500건 [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): 로그에서 실제 로컬 모델과 합성 채팅 500/500건 처리, **500건 모두 3초 초과**, 전체 p95 **2,979.984초**, FIFO 대기 p95 **2,973.875초**, AI p95 **7.875초**, `passed_three_second_local=false`. 실제 시청자 500명·24시간 방송 실증이 아니다.
- 152절 전체 회귀 [40054420230](https://github.com/junggyeol4444/AISTING/actions/runs/40054420230): 최종 `failure`. `validate` 로그 **2,655건 실행·35실패·32오류·2건 건너뜀**. Twitch AI 오류/기대 성공 불일치, FIFO 2,048건 대비 0건, 공식 OBS 동일 발화·관찰 준비 등 미해결.
- 152절 Windows CI [40054420221](https://github.com/junggyeol4444/AISTING/actions/runs/40054420221): 최종 `failure`. 실제 OBS 작업에서 Chocolatey OBS 패키지 조회 **504 Gateway Timeout**, `C:\Program Files\obs-studio\bin\64bit\obs64.exe` 미설치로 실패. Windows EXE 작업은 취소됐으며 다른 3개 읽기/모델 작업 성공만으로 Windows 통합 성공을 주장하지 않는다.
- 152절 실모델 500건 [40054343542](https://github.com/junggyeol4444/AISTING/actions/runs/40054343542): 마지막 조회 당시 `in_progress`, 최종 결과 미확정. 153절 새 CI도 아직 최종 판정하지 않았다.

### 완료·하지 않은 것·미완료·진행 중 멈춘 것·다음 인계
- **완료:** main 시작 HEAD 재확인, 96절 필수 두 CI 상태·실모델 실패 로그, 152절 전체 회귀·Windows OBS 실패 로그 확인, 원본 기획·로드맵·설정 및 누적 인수인계 보존 확인, 실제 OBS 표본 출처→후보 연결 코드 2개 누적 개발, 가상 계약검사 7건 작성, 기존 main에 새 브랜치 없이 fast-forward 커밋 2개 반영, 153절 누적 인수인계.
- **하지 않은 것:** 신규 가상 계약검사 실행/통과 확인, 전체 회귀 통과, Windows 10/11 네이티브 EXE/GUI 버튼·실제 OBS·로컬 모델 실사용 통합검사, 권리 확인된 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 실제 입→OBS 같은 발화 실증, 실제 4플랫폼 수백 명 무누락·24시간 방송·시청자 1~3초 달성. mock/가상 관찰을 실사용으로 보고하지 않는다.
- **미완료:** 기존 전체 회귀 35실패·32오류의 원인 수정과 전체 재검증, 권리 있는 실제 한국어 보이스·공식 Cubism·OBS 동일 발화 오디오/영상 실증, 실제 수백 명 4플랫폼 무누락/24시간 재연결·안전성, FIFO 대기·AI·음성·영상·시청자 E2E 1~3초 병목 해결, Windows 네이티브 EXE/GUI/OBS/로컬 모델 통합검증.
- **진행 중 멈춘 것:** 152절 실모델 500건 최종 상태, 153절 새 CI 확인, 사용자 권리 모델·실계정·공식 Cubism/OBS 환경이 필요한 실증. 구 CI 실패는 그대로 유지한다.
- **다음 시작 기준:** `junggyeol4444/AISTING/main` HEAD를 다시 조회한다. 153절 코드/검사 마지막 커밋 `51589015f2100800d1ac3b1c5a41c67f5fee6636` 위에 본 문서 인수인계 커밋이 추가된다. 기존 1~153절 전체 원문과 과거 부록, 기획·로드맵·설정·원본 코드를 그대로 보존하며 AISTING 기존 코드 전체 개발 우선→전체 회귀/Windows 실기기 검증→오류 수정/전체 재검증 순서를 지킨다. 기존 매시간 예약 중복 생성 금지.

