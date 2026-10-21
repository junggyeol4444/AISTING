## 88. 2026-10-22 — Windows 보고서 동시 저장 장애 원인 코드 수정 및 재검증

### 이어받은 원문·제약
- 사용자 지시: 오직 AISTING 기존 main만 안전한 fast-forward. 기존 1~76절 원문과 전체 GitHub 부록, 별도 77~87절 전체 원문 보존. ORIGINAL_PLAN.txt, ROADMAP_100.md, config/roadmap.json pending, 기존 코드/캐릭터/SQLite/설정 유지. 다른 프로젝트·예약·Drive/브랜치/롤백/force push 변경 금지.
- 무단 로그인/본인 YouTube OAuth 동의 대행·방송/녹화/채팅 발신/사용권 없는 음성 모델 훈련/합성 없음. 임의 토큰 수 96·keep_alive 10m 재도입 없음. 한국어 진행·검사 보고.

### 실제 실패와 수정 내용
- 원본 HEAD `ebcb65d66513140494efb8f12176aaa97a8d6771`.
- 해당 HEAD Windows [39689925538](https://github.com/junggyeol4444/AISTING/actions/runs/39689925538) workflow **failure**: windows-exe job의 2,524개 회귀 가운데 `test_parallel_checkpoint_writers_leave_only_complete_json`에서 Windows `PermissionError` 8건 발생. 그 외 OBS 실제 읽기·Twitch 공개 읽기·CHZZK/SOOP 공개 읽기·실제 로컬 Ollama job 4개는 success. Linux 전체 [39689925469](https://github.com/junggyeol4444/AISTING/actions/runs/39689925469)는 2,524개 통과, 2개 skipped.
- `scripts/aisting_real_ollama_fifo_soak.py`: 기존 고유 임시파일·`fsync`·원자적 `os.replace` 유지. 동일 프로세스 여러 쓰기의 `threading.Lock` 직렬화, 외부 잠금 `PermissionError`에만 최대 8회 제한 재시도, 마지막까지 잠기면 그대로 예외 전파 및 기존 완전한 JSON 보존, 임시파일 삭제. AI 답변 길이/모델/사용자 데이터는 변경하지 않음.
- `tests/test_aisting_real_local_fifo_soak.py`: 일시 잠금 뒤 정상 교체 및 영구 잠금 8회 실패에서 기존 보고서 무결성 유지 회귀 2건 추가. 기존 12-thread 병렬 보고서 검사와 실제 FIFO 처리 검사도 유지.
- 위 코드가 GitHub `main`에 반영되면 **동일 수정 HEAD**의 전체 회귀/Windows EXE·GUI·OBS·로컬 Ollama/4플랫폼 읽기 검사를 다시 확인해야 한다. 실행 중 또는 과거 CI 성공을 새 코드 검증 성공으로 바꾸지 말 것.

### 아직 미완료
- [39689925496](https://github.com/junggyeol4444/AISTING/actions/runs/39689925496) Windows 실제 Ollama synthetic 500건은 이 문서 작성 당시 진행 중으로 최종 집계·p95 미확정. 과거 500/500 성공 사례도 전체 p95 5970.765초, AI p95 15.984초로 **1~3초 목표 실패**.
- 권리 있는 실제 GPT-SoVITS 한국어 WAV→공식 Live2D Cubism 입 파라미터→OBS 동일 발화 오디오/영상, 실제 수백 명 4플랫폼 메시지 전부 처리, 실제 24시간 방송·재연결과 최종 시청자 1~3초는 **여전히 미실증**. 외부 실제 채팅 0건과 소스 버그는 별도 구분.

### 다음 회차
- 이번 수정 커밋에서 전체 회귀·Windows EXE/GUI/OBS/로컬 Ollama/4플랫폼 CI 최종 결론과 발생 오류, 신규 500건 실행 결과를 확인하고, 문제가 있으면 코드를 수정해 전체 재검증.
- 기존 AISTING 원본 코드에서 GPT-SoVITS→Cubism→OBS 동일 발화 증거 및 재연결·지연시간 개선을 계속 개발. 테스트용 synthetic과 실제 시청자 실증은 분리해 보고. 기존 캐릭터·SQLite·설정·원본 기획/문서/다른 저장소·예약/Drive 변경 금지.
