# AISTING 74절 — 2026-10-21 20:17 KST 이후 누적 개발 인수인계

## 1. 프로젝트·기준·읽은 원문
- 대상 저장소 **오직** `junggyeol4444/AISTING`; 원격 `main` HEAD `37ae19498f845ec7a0576fd68fc829a30d9a5de0`. 74회차 GitHub 커밋 없음. 73절도 원격 미반영.
- GitHub `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체(1~72절 포함, 172094자), `docs/AISTING_HOURLY_FULL_HANDOFF.md` 전체(1~72절 포함, 166967자), `docs/hourly-handoff-appendices/` 16개 원문 전체(합계 56777자), `docs/ORIGINAL_PLAN.txt`(19347자), `docs/ROADMAP_100.md`(34687자), `config/roadmap.json`(19909자) 조회.
- 현재 GitHub tree 1344개 경로 확인. 73절 대상 프로덕션 2개/테스트 2개 전체를 조회해 blob SHA 및 소스 수정 앵커 13곳을 대조함. 로컬 FIFO 지연 측정/동시 플랫폼 세션 관련 소스 일부도 조회했으나, **1344개 전 파일 전체 본문을 읽지는 않았음**. 조회하지 않은 파일까지 읽었다고 주장하지 말 것.
- `docs/ORIGINAL_PLAN.txt`, 기존 100단계 상태(`pending`), 원래 네이티브 Windows EXE/Tk UI, 단일 AI FIFO, 캐릭터·SQLite·설정 보존 요구 유지.

## 2. 73절에서 이어받아 이번 회차 개발한 코드 (로컬 패치, main 미반영)
- 산출물 `AISTING_20261021_2017_PENDING_APPLY_74.py`: **기존 73절 4개 파일 변환을 전부 포함**하는 보존형 갱신 코드. 지정한 기존 main 소스와 Git blob SHA 및 정확히 1회 나오는 원문 앵커가 일치해야만 패치를 생성함. 실행 기본값은 읽기 전용이며 명시적인 `--apply`가 없으면 원본을 쓰지 않음.
- `scripts/aisting_real_ollama_fifo_soak.py`: 24시간 paced 합성 입력 중에도 OBS와 무관한 **실제 로컬 AI worker 결과 큐를 주기적으로 회수**, 중간 처리 진행 체크포인트에 반영하는 73절 개선을 보존. 추가로 매우 짧은 sleep 잔여 시간을 연속 monotonic 호출 사이에 음수가 되지 않게 `max(0.0, ...)`로 보강하여 Windows 선점 타이밍에서 발생할 수 있는 `ValueError` 후보를 수정.
- `src/ai_broadcaster/original_plan_voice_obs_bridge.py`: 실제 GPT-SoVITS 음성의 임시 OBS `ffmpeg_source`에 대해 CreateInput 반환 `input_uuid`와 GetInputList의 `inputUuid`를 교차 확인하고, 재생과 정리 직전에 UUID 일치 여부를 확인하도록 하는 73절 소스 변경안을 보존. 사용자 소스가 같은 이름으로 교체됐으면 재생 또는 삭제하지 않고 실패로 남김. 예전 주입 테스트 더블과의 동작 조건은 그대로 유지.
- `tests/test_aisting_real_local_fifo_soak.py`: paced 입력 중 중간 완료 결과 관찰 테스트 및 **로컬 성공을 시청자 실증으로 오인하지 않는 검사** 추가 후보.
- `tests/test_aisting_gpt_sovits_obs_integration.py`: UUID 생성·재생·정리 성공, 재생 전에 UUID 변경되어 재생·삭제 거부, **재생 이후 UUID가 변경되면 삭제 거부**의 테스트 추가 후보. 테스트의 mock은 실제 OBS 또는 라이선스 보이스 실증이 아님.
- 새 사용자 설정, 모델 파라미터, 음성·캐릭터, 정책, 토큰 생성 길이, keep_alive 값, 방송 자동 실행, 외부 계정 코드는 추가·변경하지 않음.

## 3. 이번 로컬 코드 검사 (증빙 구분)
- 앞선 73절 소스/테스트 blob SHA가 여전히 원격 main에서 각각 일치:
  - `scripts/aisting_real_ollama_fifo_soak.py`: `0b1b17039fcecb2f468e2b0c8fd1a173efd589b7`
  - `tests/test_aisting_real_local_fifo_soak.py`: `bc574fa3a8746212f5ff33452c679086cead8d24`
  - `src/ai_broadcaster/original_plan_voice_obs_bridge.py`: `9878f7c80a42b30d961d176ccc5b995079a2c29e`
  - `tests/test_aisting_gpt_sovits_obs_integration.py`: `88d7e7fe91e40cd1ec15563b60e82018bb13e0af`
- 73절 기존 앵커 13곳이 최신 main에서 각각 1회 존재하는 것을 GitHub 실파일과 대조.
- 74절 생성 코드 및 자가 검사 코드 `py_compile` 통과. 작성한 테스트를 처음 실행할 때 **패치 생성기의 신규 테스트 문자열 참조 오류(`NameError`)와 격리 검증기의 변수 참조 오류**가 발생하여 각각 수정하고 전량 재검사함.
- `AISTING_20261021_2017_PATCH_SELFTEST_74.py` 전체 **5개 통과**: 원본 앵커 중복 중단, 기존 24h 소스 교체와 sleep 하한, 실제 AI 결과 집계 함수, OBS UUID 정상·교체·중복·누락 동작, 신규 회귀 테스트 문법.
- **검증하지 못한 것:** 현행 1344개 소스 전체 회귀, 새 74절 패치를 실제 원본 4개에 적용해 실행한 결과, 실제 Windows EXE/Tk GUI, 진짜 GPU Ollama/OBS/Live2D/GPT-SoVITS/외부 플랫폼. 새로운 74절 실제 CI는 없음. 자가 검사 5개를 메인 테스트 5개 통과나 최종 Windows 실증으로 포장 금지.

## 4. CI의 실제 현재 상태 — 성공과 실패 그대로 유지
- 기존 main `37ae1949` 전체 회귀 [39580268467](https://github.com/junggyeol4444/AISTING/actions/runs/39580268467): `success` (이번 미반영 코드 테스트 아님).
- 동일 HEAD Windows 통합 [39580268520](https://github.com/junggyeol4444/AISTING/actions/runs/39580268520): `failure`, jobs 5개 중 4개 success(`windows-exe`, `twitch-public-readonly`, `korean-public-chat-readonly`, `obs-real-readonly`), 1개 failure(`ollama-real-local-e2e`). 이전 증빙의 실제 로컬 한국어 Ollama 생성 성공과 외부 시청자 채팅 0건 실패를 분리해서 그대로 유지.
- 이전 HEAD `2837946a` 실제 로컬 모델 부하 [39572382928](https://github.com/junggyeol4444/AISTING/actions/runs/39572382928): synthetic 4플랫폼 총 500건 모두 접수/500건 모델 처리, 누락 0건. 3초 초과 **500/500건**, 총 p95 **2781.218초**, FIFO 대기 p95 **2775.281초**, AI 계산 p95 **6.078초**. 이는 실제 500명 시청자·24시간 송출·최종 1~3초 실증 아님.

## 5. 원격 미반영 이유·변경하지 않은 것
- 직전 73절에서 GitHub 쓰기가 안전 검사에 의해 차단되었으며, **이번 74절은 우회성 원격 쓰기 시도를 하지 않음**. GitHub main을 갱신했다고 주장하지 않음. 이 회차는 격리된 `/mnt/data` 내 코드·테스트·결과·인수인계 파일만 작성.
- GitHub의 원래 1~72절 원문, 과거 16개 appendix, 기획안·로드맵, 캐릭터·말투, SQLite 데이터, 사용자 설정, 기존 main 코드, 다른 저장소·프로젝트·예약·Drive **전부 미변경**.
- 새 브랜치·force push·롤백·파일 삭제·무단 OAuth 로그인·실제 방송·녹화·채팅 발신·무단 모델 훈련·사용권 없는 음성 합성 **없음**.

## 6. 다음 회차의 정확한 이어받을 위치
1. 현재 GitHub main HEAD 및 원본 1~72절, 본 73~74절, appendix, 원본 기획·100단계, 주요 실제 소스 재조회. 73~74 절간 중복 적용 방지.
2. **`AISTING_20261021_2017_PENDING_APPLY_74.py`가 73절 누적 전부 포함한 최신 미반영 4파일 패치**임을 확인. 원격 변경이 있으면 SHA·원문 일치를 먼저 재검토. 안전검사가 허용하는 일반 절차에서만 기존 main fast-forward 반영하고, 차단된 쓰기를 우회하지 않음.
3. 다수 핵심 소스 수정 누적 후 같은 HEAD로 전체 회귀 → 실제 Windows 네이티브 EXE·Tk GUI / OBS / 로컬 Ollama / 4플랫폼 실제 읽기 검사 → 실패 원인 수정 후 전량 재검증. `ollama-real-local-e2e` 실제 시청자 0건은 외부 환경과 소스 오류를 구별하고 실패 보존.
4. 권리 확인된 한국어 GPT-SoVITS 실제 WAV → **공식 Live2D Cubism** 실제 입 움직임 → OBS 동일 발화 오디오·영상, 4플랫폼 실제 수백 명, 실제 24시간 안전성·재연결 및 최종 시청자 1~3초는 아직 **개발·실증 미완료**. 사용자 계정·장비·실제 방송에 대한 무단 조작 없이 계속 코드·테스트 우선 보완.
5. 다음 새 절은 원문 삭제나 기존 완료상태 재해석 없이 추가. 실제 변경된 커밋/검사/실패/수정/유지/미완료를 누적.