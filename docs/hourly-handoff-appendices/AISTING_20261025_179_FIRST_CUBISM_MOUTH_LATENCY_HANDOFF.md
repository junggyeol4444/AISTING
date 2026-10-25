## 179. 2026-10-25 — 4플랫폼 채팅 파싱→공식 Cubism 첫 입 움직임 및 WAV→입 후보 단계 지연 누적 개발

### 이번 첫 재개 기준과 보존
- 시작 당시 GitHub `junggyeol4444/AISTING` 최신 `main` HEAD **`760dc11d6b134492ceebdaad5c8afd27fc3f98f9`**를 다시 조회함. 이전 178회차 HEAD와 일치.
- `docs/AISTING_HOURLY_FULL_HANDOFF.md` 1~178절 및 `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체, 97절과 178절 부록 원문, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`과 현재 실소스(`live_runtime_metrics.py`, `desktop_chat_tab.py`, `original_plan_frontend.py`, 전 회차 검사 파일)를 조회함. 모든 과거 개별 부록의 본문을 별도 파일로 1개씩 전수 읽었다는 주장은 하지 않음. **기존 원문은 삭제하거나 재작성하지 않고 이번 절만 뒤에 누적한다.**
- 마지막 사용자 명령 "계속": 먼저 AISTING 원본의 미완료 기능 전체 누적 개발을 수행하고, 전체 개발 후 전체 회귀/Windows 네이티브 EXE·GUI·OBS/실제 로컬 모델 통합검사→오류 수정→전체 재검증. 변경 시 기존 `main`만 Blob SHA 확인 후 fast-forward로 반영. 브랜치 생성/force push/rollback/전면 재개발/다른 프로젝트·Drive·기존 예약 변경·중복 예약 추가·임의 OAuth/방송/녹화/채팅 발신·권리 없는 음성·훈련·토큰 96·keep_alive 10m 추가 금지.

### 179회차 실제 누적 개발
1. `src/ai_broadcaster/live_runtime_metrics.py`의 기존 `LiveFirstWavLatencyMetrics` 뒤에 **`LiveFirstMouthLatencyMetrics`** 추가(`b7a4d87c50a278e4e238de709ee019302b72bb41`). 이미 운영자가 선택한 공식 Live2D 관찰 결과의 실제 단조시계 입 움직임을 플랫폼별로 수집하여 파싱→공식 전송 시작 대기/공식 요청 시작→첫 입/파싱→첫 입, 실측 최근 최대 512건 p95·최대·3초 초과로 구분. 공식 같은 관찰창에 WAV 도착 monotonic 시각이 있고 요청 시작 이후이며 입 시각 이전이면 **WAV 수신→입 시각차 후보**를 별도로 계산. WAV 누락·과거 수신·입 시각 역행·입 미관측·공식 관찰 예외·파싱시각 누락은 정상 표본에서 제외하거나 구분. 채팅 본문, 음성, 닉네임, 토큰 저장 안 함.
2. `src/ai_broadcaster/desktop_chat_tab.py`(`62b086d739304938592468105eb3fae5392f98c5`): 실제 4플랫폼 단일 AI FIFO 세션별 입 지연 측정 객체 초기화. 기존 운영자 승인 **공식 느린 관찰 모드**에서만 첫 입 확인과 공식 WAV 수신 monotonic 값을 재사용, 질문당 새 음성 합성/OBS 변경/별도 메시지 전송 없음. 기존 `twitch_live2d_ok` 상태 유지. 4플랫폼 결과 이벤트 `twitch_ai_first_mouth_timing` 및 에러 이벤트를 기존 Tk GUI에서 받아 플랫폼별 통계/미검증 경고 출력. 기존 fast 모드와 Ollama 모드는 변경하지 않음.
3. `tests/test_aisting_first_mouth_candidate_latency_179.py`(`e8a049162f1d110425115a227387f1c2cfda4ed3`): 모의 monotonic 시각으로 정상 분절, 3초 경계, 초과, 입 미관측, 관찰 오류, 누락/역행, float NaN/Inf/bool, WAV 누락/과거/늦은 수신, 플랫폼 독립성/표본 상한 등 **15개 가상 계약검사 작성**. 신규 검사 실행·통과 주장 금지.
- 본 179회차 코드 개발은 **실제 사용자 PC, 권리 보유 TTS, 공식 Cubism 입과 OBS 화면/실제 오디오 인코더 동기화, 시청자 단 E2E, 실제 수백 명·24시간 연속 실증**이 아니다. 채팅→공식 WebSocket 응답에 명확한 원본 채팅 대응 ID가 없으므로 시각 근접만으로 동일 발화 인과성 확정 금지.

### 과거 CI 최종 상태 및 실패를 숨기지 않음
- 96절 Windows `39722213656`: obs-real-readonly, twitch-public-readonly, windows-exe, ollama-real-local-e2e **4개 job success**, korean-public-chat-readonly **cancelled**. 취소 작업 로그 다운로드 시 404 BlobNotFound. 전체 workflow 실사용 성공 아님.
- 96절 실제 Ollama `39720448468` 작업 성공: 실제 모델 500/500, 모델 실패 0, **500건 전부 3초 초과**, 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, 모델 p95 **7.875초**. 합성 4플랫폼 입력이지 시청자 500명 실증 아님.
- 177절 전체 회귀 `40155307503`: **36 failures, 33 errors, 2 skipped**를 Validate job 실제 로그에서 재확인. 수신기/GUI 모의 객체 계약 불일치와 OBS 후보 검사의 실패가 남음. 사용자 지시대로 전체 기능 개발 이후 전수 검사·수정·재검증 예정이므로 이번 개발을 회귀 해결로 주장하지 않음.
- 177절 Windows `40155307396`: 4개 job success, windows-exe **cancelled**. 네이티브 통합 완료 아님.
- 177절 실제 Ollama 500건 `40155307463`: 500/500, 실패 0, **500건 모두 3초 초과**, 전체 p95 **2867.219초**, FIFO 대기 p95 **2861.109초**, 모델 p95 약 **6.469초**. 1~3초 목표 미달.
- 178/179회차 최신 신규 CI의 확정된 실행 번호/전체 통과 결과는 이번 회차에서 확인되지 않음. 새 코드 자체 15건 실행하지 않음. 현재 GitHub 원격 검증 및 실제 Windows 실사용 결과 없음.

### 이번 회차 실제 완료·안 한 것·미완료·진행 중·다음 기준
- **실제 완료**: 현재 HEAD/설계·인수인계/CI 실패 로그 조회, 기존 `live_runtime_metrics.py`·`desktop_chat_tab.py` 실제 소스 2개 누적 수정, 신규 검사 15건 작성·GitHub `main`에 반영, 기존 문서 원문 유지와 본 절 append-only 인수인계.
- **실제 안 한 것**: 신규 검사 직접 실행, 전체 회귀 통과, Windows EXE 빌드/GUI 실제 클릭/OBS 실장비 검사, 권리 있는 본인 GPT-SoVITS 실제 한국어 WAV→공식 Cubism 실제 입→OBS 같은 PCM 입력 실증, 방송 송출/녹화/채팅 발신, 실제 4플랫폼 수백 명 무누락, 24시간 운영, 시청자 E2E 1~3초 달성.
- **남은 것**: 채팅-WAV-입-OBS 같은 발화 인과성/송출 출력 확인 경로 개발 및 실증, 공식 한국어 모델/GPT-SoVITS 오디오 권리 확인·실환경 통합, 4플랫폼 재연결 후 보류 채팅 실무누락과 수백 명 무누락 시험, 24시간 안정성, 실제 FIFO 적체(p95 수천 초) 및 모델 1~3초 병목 개발, 기존 36 실패·33 오류 수정 전수 검사/Windows 원본 EXE 검증.
- **진행 중 멈춘 것**: 파싱→Cubism 입 및 WAV→입 단계 후보의 실제 개발 완료, 신규 15건 검사와 전체 E2E/Windows 검증 시작 전. 과거 CI 실패·취소 미해결, 사용자 계정/모델/PC 필요한 실증 미진행.
- **다음 회차**: 문서 반영 후 변경된 `main` HEAD를 반드시 새로 확인하고, 기존 1~179절 원문과 전체 과거 부록 보존, 실제 소스 개발 누적→전체 개발 후 회귀·Windows·OBS·실제 로컬 모델 검사→수정→전체 재검증 순서 지킬 것. 다른 프로젝트나 예약은 수정·추가하지 말 것. 코드 커밋 마지막 HEAD `e8a049162f1d110425115a227387f1c2cfda4ed3`; 뒤에 문서 커밋으로 HEAD가 달라짐.
