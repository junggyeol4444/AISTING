## 91. 2026-10-22 — Ollama 서버 실제 추론 단계별 병목 계측 개발

### 이전 원본 및 개발 조건
- 본 회차 시작 HEAD `2f9df1b32a2febdcdc70ec923752783086aef6a8`. 기존 문서 1~90절과 과거 부록 전체, 원본 기획/로드맵/roadmap pending, 다른 소스·캐릭터·SQLite·설정 원문을 삭제·축약하지 않음.
- 오직 AISTING 기존 `main`만 안전한 fast-forward. 브랜치 생성·강제 푸시·롤백·다른 프로젝트·예약·Drive/계정 조작·방송 송출/녹화·채팅 발신·사용권 없는 훈련/보이스 사용 없음. 무단 `num_predict=96`·`keep_alive=10m` 설정 없음.

### 실제로 추가한 소스 코드
- `src/ai_broadcaster/local_llm.py`: 기존 Ollama `/api/chat` 단일 모델 요청과 원래 캐릭터·전체 응답을 **변경하지 않고**, 응답에 실제 존재하는 `load_duration`, `prompt_eval_duration`, `eval_duration`, `total_duration` 나노초 메타데이터만 초 단위로 기록. 음수·문자열·누락·부정확 타입은 제외하고 표본 없음(`None`) 처리. 채팅 원문/모델 답변/사용자 정보 기록 안 함.
- `src/ai_broadcaster/desktop_chat.py`: 기존 `ChatResult`에 옵션 서버 타이밍 필드 추가. 기존 모의 생성기에 필드가 없어도 호환되도록 `getattr(..., None)` 사용. SQLite 메모리·답변 내용 변경 없음.
- `src/ai_broadcaster/desktop_chat_tab.py`: 기존 네이티브 Tk 공개 채팅 AI 처리 결과에 실제 모델 로딩·입력 처리·답변 생성 시간만 최초 3회·25건마다 한국어로 출력. 채팅 중복이나 처리 순서 변경 없음. 로컬 서버 내부 측정이며 방송 인코더/시청자 E2E가 아님을 명시.
- `scripts/aisting_real_ollama_fifo_soak.py`: 실제 FIFO 경로의 `twitch_ai_ok` 이벤트에서 성공 응답의 서버 실측 숫자만 메모리 bounded(최근 1024개) 수집, 진행/최종 JSON에 각 구간 p95와 유효 표본 수 추가. 없는 Ollama 메타데이터는 `null`; synthetic 테스트만으로 실제 서버 값 생성 금지. 기존 500건 무누락 판정·AI 단일 FIFO·실제 부하 p95 및 3초 초과 검사 변경 없음.

### 신규 회귀검사
- `tests/test_local_llm.py`: 로컬 테스트 서버의 실제 Ollama형 나노초 필드 정규화, 누락/잘못된 단계 값 미측정 처리, 모델 요청에 임의 `options`/`keep_alive` 추가 금지 2건.
- `tests/test_aisting_local_chat_saved_character.py`: 기존 원본 ChatPipeline을 통한 서버 계측 전달·네트워크 없음 검증 1건.
- `tests/test_aisting_real_local_fifo_soak.py`: 실제 작업자 이벤트 통로를 통한 bounded 단계 p95/표본 수·민감 정보 미포함, Ollama 제공 수치가 없을 때 `null` 검증 2건.
- 총 신규 5개 테스트는 모델/OBS 실사용 증거가 아닌 계약 검사. 실제 Windows CI가 완료되기 전 성공이라 기록하지 않음.

### 직전 검증 결과 및 실패 유지
- 이전 코드 HEAD `2f9df1b3` [전체 CI 39699481118](https://github.com/junggyeol4444/AISTING/actions/runs/39699481118) **성공: 총 2529건 실행·2개 건너뜀·실패 0**.
- 이전 HEAD [Windows CI 39699481040](https://github.com/junggyeol4444/AISTING/actions/runs/39699481040) **5개 job 모두 성공**: Windows EXE/Tk GUI, OBS 읽기, Twitch 공개 읽기, 치지직·SOOP 공개 읽기, 로컬 Ollama 통합. 위 결과는 **이번 신규 수정본의 검증이 아님**.
- [90절 실제 Windows Ollama synthetic 500건 39699481047](https://github.com/junggyeol4444/AISTING/actions/runs/39699481047), [89절 실제 500건 39698914387](https://github.com/junggyeol4444/AISTING/actions/runs/39698914387)은 기록 당시 진행 중. 과거 완료된 88절 [39695199416](https://github.com/junggyeol4444/AISTING/actions/runs/39695199416): 500건 무누락 처리 성공, p95 1939.547초 / FIFO 대기 p95 1935.688초 / AI p95 5.016초, 3초 초과 499건으로 **실시간 목표 실패**.
- 실제 권리 있는 한국어 GPT-SoVITS WAV→공식 Cubism 입/음성→OBS 동일 발화 출력 및 시청자 청취, 실제 4플랫폼 수백 명·24시간 안정성·최종 시청자 1~3초는 **미완료**. 표본 없이 성공 선언 금지.

### 다음 회차 이어받기
- 바로 이 코드가 반영된 `main`의 전체 회귀와 네이티브 Windows EXE/GUI·OBS·로컬 Ollama·4플랫폼 검사를 최종 확인. 실패 시 원인 수정 후 전체 재검증하고 인수인계 92절 추가.
- 실제 Ollama 응답 메타데이터가 있는 500건 실행에서 로딩·입력 평가·토큰 생성 시간 p95를 기존 FIFO 대기와 비교, 모델/토큰 옵션 임의 변경 없이 병목 수정. 권리 확인된 실제 한국어 GPT-SoVITS→공식 Live2D→OBS 같은 발화 실증은 별도 사용자 승인 없이 송출/녹화/계정 작업하지 말 것.
