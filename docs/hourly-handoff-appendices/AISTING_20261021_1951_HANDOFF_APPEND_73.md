# AISTING 73절 — 2026-10-21 19:51 KST 매시간 누적 개발 인수인계 (main 원격 쓰기 차단)

## 기준 및 보존
- 프로젝트: `junggyeol4444/AISTING` 하나만 대상. 시작/종료 main HEAD: `37ae19498f845ec7a0576fd68fc829a30d9a5de0` (변경 없음).
- 원문 확인: `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` (1~72절), `docs/AISTING_HOURLY_FULL_HANDOFF.md` (1~72절), `docs/hourly-handoff-appendices/`의 과거 16개 파일 전부, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`. GitHub tree 전체 1319개 파일 목록과 핵심 소스, 실제 CI 읽음. 전체 `src/` 142개를 읽으려는 일괄 호출은 도구 호출 상한에 걸려 전체 본문을 다 읽었다고 주장하지 않음.
- 기존 1~72절, 16개 appendix 원문, 캐릭터, SQLite, 설정, 원본 로드맵 상태, 다른 프로젝트, Drive, 예약은 변경하지 않음. 새 브랜치/force push/롤백 없음. 계정 로그인, 방송 송출/녹화, 채팅 발신, 음성 무단 훈련 없음. 96토큰 및 keep_alive 10m 설정 재도입 없음.

## 직전 개발을 이어받아 이번 회차에 준비한 실제 코드
1. `scripts/aisting_real_ollama_fifo_soak.py`: 24시간 paced 수신 중에도 실제 worker 결과 큐를 128개씩 지속 회수하고 진행 집계. 이전 코드는 합성 입력 500건을 장시간 천천히 넣는 동안 응답 결과를 끝에 몰아 읽어서 중간 집계 0건과 큐 적체를 유발할 수 있었음. 원본 FIFO/단일 AI worker/메시지 보존·정책은 그대로.
2. `tests/test_aisting_real_local_fifo_soak.py`: 36건/초당 12건의 단축 paced 계약 검사 추가. 실제 Ollama·24시간 실증으로 포장하지 않음.
3. `src/ai_broadcaster/original_plan_voice_obs_bridge.py`: 임시 OBS ffmpeg 소스 CreateInput 반환 UUID와 GetInputList UUID를 비교. 재생 직전 및 삭제 직전 동일성 확인. 다른 UUID로 교체된 사용자 소스 재생/삭제 금지. 기존 임시 WAV·미터 구독 후 재생, 송출·녹화 사전 거부는 보존.
4. `tests/test_aisting_gpt_sovits_obs_integration.py`: UUID 정상 유지→재생/삭제, UUID 교체→재생·삭제 거부 회귀 2개 추가.
5. 재현 가능한 4파일 보존형 변환 스크립트 `AISTING_20261021_1951_PENDING_APPLY.py` 생성. GitHub main 각 파일 blob SHA 일치와 고유 원문 앵커를 확인한 뒤에만 diff 생성/명시적 로컬 적용이 가능. 기본 실행은 원본을 수정하지 않음. **현재 GitHub main에 미반영**.

## 이번 회차 실제 검증 및 쓰기 차단
- 생성한 패치 변환 스크립트 Python 구문 검사 성공. 신규 회귀 테스트 3개 메서드를 추출한 최소 Python 클래스 구문 검사 성공, 원문 앵커 불일치 시 중단 검증 성공. **이것은 전체 AISTING 회귀/Windows EXE/OBS/GPT-SoVITS 실제 검증이 아님**.
- GitHub `create_blob`으로 OBS UUID 회귀 테스트 코드를 반영하려고 시도했으나 **OpenAI safety checks 차단**. 이후 다른 GitHub 쓰기 경로로 우회하지 않음. 신규 main 커밋/CI 없음.
- 기존 main 회귀 [39580268467](https://github.com/junggyeol4444/AISTING/actions/runs/39580268467): success, 이번 73절 변경의 검증 아님.
- 기존 main Windows 통합 [39580268520](https://github.com/junggyeol4444/AISTING/actions/runs/39580268520): 최종 5개 job 중 **4 success, 1 failure**. Windows EXE, Twitch 공개 실제 PRIVMSG 1건, CHZZK/SOOP 공개 읽기, OBS 읽기 성공. `ollama-real-local-e2e`는 실제 로컬 모델 한글 Tk 답변 **18자 성공** 후 외부 실제 시청자 채팅 0건으로 `AssertionError: No real live viewer message arrived` 실패. 모델 로컬 생성 성공과 실제 viewer 미수신을 분리하고 CI 실패 유지.
- 실제 모델 500건 [39572382928](https://github.com/junggyeol4444/AISTING/actions/runs/39572382928): 500/500 성공·누락 0, **500/500 3초 초과**, p95 전체 2781.218초, FIFO 대기 2775.281초, AI 처리 6.078초. 실제 500명 시청자·24시간 방송·최종 1~3초 성공이 아님.

## 미완료·다음 회차 우선 작업
- 73절 패치 4파일은 안전 검사 차단으로 main 미반영, 해당 변경의 전체 회귀/Windows 네이티브 EXE/실제 OBS/GPT-SoVITS/로컬 Ollama 재검증 미실행. 기존 main HEAD가 바뀌면 패치의 SHA 및 원문 앵커 재검토. 안전 차단 우회 금지.
- 실제 권리 있는 한국어 GPT-SoVITS 참조 WAV와 합성 모델→공식 Live2D Cubism 립싱크→OBS 동일 발화 실제 음성·영상 출력 및 타이밍 실증 미완료. 소유자 승인 없는 계정/모델/방송 작업 금지.
- 4플랫폼 실제 수백 명 부하, 24시간 실제 방송 안정성/재연결, 최종 시청자 1~3초 미완료. 기존 단일 FIFO의 burst 대기 병목(수천 초) 개발 필요. 메시지 임의 건너뛰기·중복 병합·응답 길이 강제 제한 금지.
- 다음 회차는 1~72절 원문 및 73절을 함께 읽고, 실제 main과 CI를 확인한 후 소스 개발→전체 회귀→Windows 네이티브 EXE/GUI·OBS·로컬 모델·공개 채팅 검사→실패 수정 후 전체 재검증. 변경 완료/실증 수준 구분, 원문 추가 인수인계 유지.