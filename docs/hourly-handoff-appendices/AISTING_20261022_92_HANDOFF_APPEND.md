## 92. 2026-10-22 — 네 플랫폼별 무누락·FIFO 적체 계측 및 끊긴 전송 정리

### 기준/원문 보존/금지사항
- 대상은 기존 `junggyeol4444/AISTING`의 `main`만. 시작 HEAD `b91b6b6589d363641c436b61d489af8d517a73bb`. 앞선 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md`, `docs/AISTING_HOURLY_FULL_HANDOFF.md`의 **1~91절 전체 원문**, 모든 과거 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`의 pending, 모든 캐릭터/설정/SQLite와 기존 소스를 삭제·요약·변경하지 않고 이번 절만 추가.
- 다른 저장소·프로젝트·예약·Drive·계정 OAuth·Windows 개인 PC, 새 브랜치·force push·롤백·사용자 설정 변경·임의 응답 길이 96 또는 keep_alive 10m 강제 금지. 사용자 승인 없는 로그인·송출·녹화·채팅 발신·보이스 훈련·권리 없는 TTS 금지.

### 이번 회차 실제 추가 개발 소스
- `scripts/aisting_real_ollama_fifo_soak.py`: 기존 실제 Ollama→기존 Windows 채팅 AI 1-worker FIFO 부하 검사에서 **플랫폼별 시간 측정 회계**를 실제 성공/실패·뒤따르는 `twitch_ai_timing` 이벤트 순서로 결합. 각 플랫폼(Twitch, 치지직, SOOP, YouTube)의 종결 측정 건수·실제 전체 지연 p95·3초 초과 건수·모델 오류 건수와 관측된 최대 FIFO 적체 건수를 진행/최종 JSON에 추가. 최근 1024개 이내 지연 표본만 메모리 보관, 채팅 본문·시청자 식별자·모델 출력은 보고서에 저장하지 않음. 존재하지 않는 표본의 p95는 `null`, 실제 시청자 증명은 `false` 유지.
- 같은 검사에서 **시간 측정 누락·불일치·플랫폼 종결 이벤트 짝 누락을 무손실 성공으로 오판하지 않도록** `passed_no_drops` 및 `passed_three_second_local`에 타이밍 건수 일치 검증 추가. 메시지를 건너뛰거나 합치거나 모델 설정을 바꾸지 않음.
- `src/ai_broadcaster/multi_platform_session.py`: 수신기 전송 예외 뒤 1·2·4초 기존 재연결 정책 이전에 실패한 원래 수신기를 명시적으로 `stop()`하여 소켓/연결 자원을 정리. 정리 과정의 예외 원문·토큰·URL은 공개하지 않고 다른 플랫폼 정상 읽기/새 수신기 생성은 계속 진행. 전체 운영자 Stop 정책·사용자 설정은 유지.

### 이번 회차 신규/수정 회귀검사
- `tests/test_aisting_real_local_fifo_soak.py`: 기존 합성 500건 × 4플랫폼 125건씩의 처리 시간 집계와 최대 큐 적체 검증 강화; 새 합성 40건 동일 문장 중복/각 플랫폼 10건 처리·p95 회계 테스트; 시간 측정 실패를 무누락 성공으로 바꾸지 못하는 검사. 실제 모델 호출은 CI 별도, 단위검사 음성·계정·방송·유료API 호출 없음.
- `tests/test_aisting_multiplatform_session_lifecycle.py`: 끊긴 전송을 재연결 전에 정리하는지 검사; 기존 수신기 `stop()` 오류가 비밀문자열을 노출하거나 재연결을 영구 중단하지 않는지 검사. 합성 수신기이며 실제 수백 명 연결 증명 아님.
- 신규 테스트 **4개**, 기존 검사 확장 1개. `main` 반영 직후 최신 전체 회귀·Windows 네이티브 EXE/GUI·OBS/로컬 Ollama·4플랫폼 공개 읽기 CI를 실행/확인하고 실패 시 소스를 고쳐 **같은 전체 검사 재실행** 필요. 로컬 작업 환경은 외부 GitHub DNS가 해석되지 않아 기존 저장소를 직접 내려받은 로컬 실행 결과 없음. GitHub Actions 결과만 실증으로 기록할 것.

### 이전 회차 최신 확인 결과 (실제 성패 보존)
- 91절 HEAD `b91b6b6`의 전체 회귀 [39702242027](https://github.com/junggyeol4444/AISTING/actions/runs/39702242027): **총 2534개 실행, 2개 건너뜀, 실패 0, 성공**.
- 같은 HEAD Windows [39702242064](https://github.com/junggyeol4444/AISTING/actions/runs/39702242064): **5개 작업 모두 성공** (원본 Windows EXE/GUI, OBS 실읽기, Twitch 공개 읽기, 치지직·SOOP 공개 읽기, 로컬 Ollama 연동). Windows EXE artifact 두 개 생성. 공개 연결 검사 성공이 실제 시청자 메시지 수백 건 처리 성공은 아님.
- 90절 실제 로컬 Ollama+합성 FIFO 500건 [39699481047](https://github.com/junggyeol4444/AISTING/actions/runs/39699481047): **500/500 접수·완료, 누락 0, 모델 오류 0**, **3초 초과 500/500**; 전체 p95 **2676.343초**, FIFO 대기 p95 **2670.906초**, AI p95 **6.922초**. 업무상 **1~3초 목표 실패**(worklow success는 500건 완료 의미, 지연목표 충족 아님).
- 91절 [39702241916](https://github.com/junggyeol4444/AISTING/actions/runs/39702241916)은 기록 당시 진행 중. 기존 89절 [39698914387](https://github.com/junggyeol4444/AISTING/actions/runs/39698914387)도 마지막 확인에서 진행 중. 91절 신규 Ollama 서버 구간 계측의 500건 실제 p95는 최종 검증 전.

### 여전히 미완료·후속 93절 인계
- 권리 있는 실제 한국어 GPT-SoVITS WAV→공식 Cubism **실제 입 움직임**→OBS **같은 발화** 영상·오디오, 4플랫폼 실제 수백 명 무누락, **실제** 24시간 장시간 방송/재연결, 최종 시청자 **1~3초**는 미완료. synthetic 500건·OBS 읽기·Windows GUI/EXE 빌드만으로 실증 성공 주장 금지.
- 다음은 이 92절 소스의 전체 회귀와 Windows CI 실제 결과, 91/92절 실제 Ollama 500건 결과에서 **모델 로딩·프롬프트·생성 p95 vs 플랫폼별 FIFO 대기**를 비교하고 실제 코드 병목을 수정. 핵심 GPT-SoVITS·공식 Cubism·OBS 동일 발화 연결은 기존 권리/사용자 승인 게이트를 유지하고 추가 개발. 에러 수정 뒤 전체 재검증, 변경/미변경/미완료를 후속 원문 절에 추가. 원본 모든 절 유지.
