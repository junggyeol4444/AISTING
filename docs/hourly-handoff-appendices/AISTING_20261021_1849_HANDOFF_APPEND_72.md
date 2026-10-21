## 72. 2026-10-21 18:49 KST — AISTING 기존 main 점검·실모델 500건 최종 결과·미반영 24시간/OBS 안전 개발 인계

### 사용자 지시와 범위
- 프로젝트는 AISTING 하나, 기존 main만 안전 fast-forward. 원본 1~71절과 과거 15개 appendix, ORIGINAL_PLAN/ROADMAP_100/config roadmap, 캐릭터·사용자 설정·SQLite 보존. 새 브랜치/force push/롤백/재개발/다른 프로젝트·예약·Drive 변경 없음.
- 계정 OAuth 대행·방송/녹화/채팅 발신·무단 음성 합성·훈련 없음. 사용자 승인 없는 96 토큰/keep_alive 10m 설정을 복구하지 않음. 모의 테스트와 실제 모델/시청자 실증 구분.

### 확인한 실제 GitHub HEAD 및 CI
- 기존 main HEAD `2837946ac303b2bf15e30e72c73966d9517db546` (이번 회차 새 commit 없음).
- 71절 전체 회귀 [39572382916](https://github.com/junggyeol4444/AISTING/actions/runs/39572382916) 성공: 2,510개 통과, 2개 skipped.
- Windows [39572383171](https://github.com/junggyeol4444/AISTING/actions/runs/39572383171): EXE 빌드, OBS 실제 읽기, CHZZK/SOOP 공개 읽기 성공; Twitch 공개 JOIN 세 채널은 확인됐으나 PRIVMSG 실제 수신 0건으로 실패, Ollama 한국어 18자와 테스트 GUI FIFO 1건은 성공했으나 실제 시청자 메시지 0건으로 해당 job 실패. 전체 3/5 성공, 2/5 실패를 유지.
- 실제 Windows 로컬 Ollama 500건 [39572382928](https://github.com/junggyeol4444/AISTING/actions/runs/39572382928) **최종 SUCCESS**, artifact `12336190383`: synthetic 입력 4플랫폼 각각 125건, accepted=500, not_accepted=0, completed=500, model_success=500, model_failure=0, unfinished=0, processing_errors=[], p95 sample=500. **3초 초과 500건, 전체 p95 2781.218초, 대기 p95 2775.281초, 모델 p95 6.078초**, `passed_no_drops=true`, `passed_three_second_local=false`. 실행 2929.094초, `completed_full_local_duration=false`. 실제 500명/24시간 송출 실증 아님.

### 이번 회차 개발 진행·미반영 사실
- 앞선 72절 후보의 `scripts/aisting_real_ollama_fifo_soak.py` blob `3b51b48a0d56ef2a65c8e42a4ece323fc732ad1b`, `tests/test_aisting_real_local_fifo_soak.py` blob `40bd258711b316b021945f0c513872f38908f928`, `src/ai_broadcaster/original_plan_voice_obs_bridge.py` blob `a663e99fac57dd5840f4d50b0ec8283cc3f8377a`를 실제 GitHub에서 재조회해 main 소스와 대조. 24시간 paced 입력 중 결과 큐를 중간 소비하는 수정, 진행 체크포인트 테스트, OBS 고유 임시 소스 UUID 검사 후보는 **여전히 main 미반영**.
- 이번 회차에 OBS 임시 소스 UUID 정상/교체 회귀 테스트 2개를 기존 테스트 파일에 누적 구현해 GitHub create_blob 쓰기를 시도했으나 **OpenAI safety checks가 차단**. blob 생성/commit/CI 실행 없음. 차단 우회하지 않음. 이 회차에서 실제 main 수정/배포/검증 완료했다고 주장하지 않음.
- 현행 main의 `src/ai_broadcaster/original_plan_voice_obs_bridge.py`는 OBS 임시 음성 입력을 이름으로만 재생·삭제. 이름 충돌·사용자 교체 시 안전성은 72절 UUID 보호 코드와 테스트를 **main에 반영해 검증해야 할 미완료** 항목.

### 다음 회차 작업 순서
1. 위 기존 1~71절 원문 및 72절, appendix 전부와 최신 main을 읽고 충돌/기존 변경 확인. 이미 main 반영된 71절을 중복 적용하지 않음.
2. 안전 검사·권한이 허용될 때만 72절 3개 미연결 Git blob의 소스/테스트를 원본 대비 검토하여 반영하고, OBS UUID 정상/교체 테스트도 추가. 안전 차단은 우회하지 않음.
3. 사용자 요구대로 핵심 소스 개발 누적 → 전체 회귀/Windows 네이티브 EXE·Tk GUI/OBS/실제 로컬 Ollama/4플랫폼 공개 읽기 → 오류 수정 후 전체 재검증. 실제 Twitch 0건/시청자 0건은 원인 구분 및 실패 기록 유지.
4. 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 립싱크→OBS 동일 발화의 실제 오디오/영상 E2E, 실제 4플랫폼 수백 명, 24시간 방송/재연결, 1~3초 지연 실증은 **미완료**. 사용자 소유 모델/참조 WAV·실기 OBS·Live2D·승인 없는 실제 송출/녹화/훈련/채팅 발신 금지.
5. 작업 시 이전 원문/SQLite/캐릭터/설정·기존 예약/다른 프로젝트 보존, 완료/미완료/실증 수준과 정확한 HEAD·CI를 추가 기록.
