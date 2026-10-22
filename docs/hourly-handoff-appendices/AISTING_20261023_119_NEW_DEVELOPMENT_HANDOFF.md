# AISTING 119회차 신규 개발 인수인계

## 119. 2026-10-23 — 신규 개발: OBS 실제 영상 획득 경계와 공식 WAV·Cubism·오디오의 시간 결합

### 이번 회차 실제 개발
- 118회차 반영 직후 `main` HEAD `29ab17c1573995f7611419cebf368b989b122d41`에서 시작. 기존 `original_plan_obs.py`의 운영자 승인 읽기 전용 `inspect_program_media`에 두 실제 OBS 영상 프레임 획득 API 호출의 시간 경계를 추가. 첫 프레임 API 완료 시각, 음성 미터 관측 후 두 번째 프레임 API 시작 시각을 **Windows 공유 monotonic 시계 기준**으로 보관. PNG 외부 저장, 실제 방송·녹화·장면 변경 없음.
- 새 `ActualObsProgramMediaObservation.observed_video_brackets_audio_candidate`로 동일 프로그램 장면 두 프레임 변화가 실제 확인됐을 때, **첫 영상 취득 완료 후**이면서 **다음 영상 취득 시작 전**에 선택 OBS 입력의 첫·마지막 양성 오디오 표본이 실제로 위치하는지를 검사하는 기능 개발. 시간 역행/0초/NaN 등은 후보 처리하지 않는다.
- 기존 `original_plan_full_pipeline.py`에서 공식 실제 WAV+PCM 헤더 후보·Cubism 입/RMS 근접 표본+OBS 미터와 영상 시간 경계를 연결한 `same_session_observed_video_audio_timing_candidate` 판정 추가. 기존 네이티브 `desktop_chat_tab.py`의 운영자 승인 통합 검사 결과에 한국어로 별도 표시.
- 신규 개발 코드 커밋 `3ff4bbdc3b5723d74ffccf7c851c13e1a898f66c`을 `main`에 **fast-forward, force=false** 반영 성공. 총 119회차에서 수정한 소스: `original_plan_obs.py`, `original_plan_full_pipeline.py`, `desktop_chat_tab.py`. 이전 캐릭터, SQLite, 설정, 기획, 인수인계, 계정/모델 선택은 변경하지 않음.
- 이 값은 **두 프레임 획득 API 호출 경계에 걸친 관찰 후보**이다. 개별 이미지가 캡처된 정확한 렌더 시간, 바뀐 영상이 Cubism 입 때문인지, 동일 WAV 파형이 인코더·시청자에게 전달됐는지까지 확정하지 않는다.

### 과거 CI 실패 보존 및 실제 하지 않은 작업
- [Windows CI 39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656) = 전체 completed/cancelled. 이전 기록은 Windows EXE, OBS readonly, Twitch 공개 채팅, 실 Ollama 로컬 작업 성공, 한국어 공개 채팅 작업 취소. 취소된 작업을 성공이라고 보고하지 않음. 이전 404 로그 접근 불가 내용 보존.
- [실모델 500건 CI 39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468) = workflow completed/success이나 실제 Ollama에 합성 채팅 500/500건 모두 3초 초과. 전체 p95 2,979.984초, FIFO 대기 p95 2,973.875초, AI 처리 p95 7.875초. 실제 시청자 500명, 24시간 정상 송출, 1~3초 E2E 달성 증거 **없음**.
- 이번 대화 실제 수행: GitHub main HEAD/두 CI 재조회, 기존 계획 및 1~117절/117차 부록 읽기, 118차 미반영 ZIP·추가절 점검, 117 미반영 fast-forward, 118회차 신규 기능 2파일, 119회차 신규 기능 3파일 실제 main fast-forward 반영. **이번 턴에 새 CI 실행, 전체 회귀, 실제 Windows EXE/GUI, 본인 권리 확인 GPT-SoVITS 로컬 WAV→실 Cubism·OBS 직접 운영·실증, 실제 수백 명 4플랫폼, 24시간 장기 시험, 시청자 E2E 지연 검증, 오류 수정은 하지 않았음.** 승인 없는 OAuth/송출·녹화·채팅 발신·모델 훈련·권리 없는 보이스 없음.
- 원래 1~117절 원문과 다른 프로젝트/Drive/예약 일절 변경하지 않음. 새로운 브랜치·force push·롤백·전면 재개발 없음. 토큰 생성 길이 96·keep_alive 10m를 강제로 설정하지 않음. 기존 패치 ZIP과 인수인계 자료는 별도 보존.
- 다음 실행에서 **현재 실제 main HEAD부터 재조회**하고 이전 1~119절과 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 모든 과거 부록을 확인. 4플랫폼 실수신 수백 명·24시간 복구, 실제 한국어 WAV→공식 Live2D 입→OBS 동일 파형 실증, 로컬 대기 병목 1~3초 개선의 미완료 기능을 **개발부터** 진행하고, 전체 기능 개발 완료 뒤 전수 회귀·Windows 네이티브 EXE/GUI·OBS/모델 실사용 검사, 오류 수정, 전체 재검증 순서를 지킬 것.
- 119 기능 커밋 기준 HEAD `3ff4bbdc3b5723d74ffccf7c851c13e1a898f66c`; 이 문서 반영 시 새로운 실제 HEAD로 전진하므로 재조회 필수. 이번 신규 개발 기능 CI **미실행**.

