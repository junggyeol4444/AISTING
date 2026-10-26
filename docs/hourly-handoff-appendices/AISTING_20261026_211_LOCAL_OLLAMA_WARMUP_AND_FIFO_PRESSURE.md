# AISTING 211절 — 2026-10-26 기존 Ollama 모델 선행 적재와 4플랫폼 AI FIFO 선행 추론 병목 실시간 표시

## 이번 실행 현재 상태 및 원본 보존
- 개발 시작 직전 `junggyeol4444/AISTING/main` HEAD `e562e46f8ccbc3bcffb6adf02f0fd1f755ccbd45`를 직접 확인했다. 과거 210절 부록, 원래 기획/로드맵의 게임·방송·1~3초 응답 목표 및 원본 `ordered_parallel_local_ai.py`, `desktop_chat_tab.py`, `local_llm.py`를 확인하여 기존 코드 위에 실제 개발했다. 인수인계의 1~210절 기존 원문을 유지한다.
- 사용자 캐릭터 이름/성격/말투, SQLite 채팅·기억·권리 확인 음성, 기존 방송/계정·승인, OBS 설정 및 로컬 모델 이름은 유지한다. 사용자 지시의 Ollama 최대 생성 `num_predict=96` 및 `keep_alive=10m`를 임의 변경하지 않았다. 신규 브랜치 생성/삭제, 강제 push, 다른 프로젝트·Drive·다른 예약 조작 없음.
- 운영자 승인 없이 외부 OAuth·실제 방송/녹화/채팅·공지 발신, 음성 합성/훈련·모델 다운로드/교체·임의 모델 생성 없음.

## 실제 제품 개발 — 소스 코드 5커밋, 기존 main 비강제 반영
1. `6c40b73d3932cd52bfefc416347127d4581d5c93`: 신규 `src/ai_broadcaster/approved_local_model_residency.py`. 기존 사용자가 이미 설치해 선택한 Ollama 모델만 `127.0.0.1:11434/api/generate` 빈 프롬프트·`keep_alive=10m`로 선행 적재 요청. 명시 승인·경로 제한·HTTP 응답 크기/형식/선택 모델 동일성 확인. 모델 설치/다운로드·텍스트 생성·합성·방송 없음.
2. `6854f31e498f410c84e0bef38a3f8230ec67c8b4`: 기존 `src/ai_broadcaster/desktop_chat_tab.py`에 모델 선행 적재 버튼·운영자 개별 확인창·GUI 비차단 로컬 작업자·준비 결과/실패 상태 표시. 기본 자동 연결/적재 없음. 기존 메시지 송신과 음성·OBS 동작 영향 없음.
3. `e4571f3b697af472b468dfdf219c8bec11c025fc`: 기존 `src/ai_broadcaster/local_llm.py`의 정상 로컬 Ollama 답변 생성 및 생성 스트리밍에 사용자 기존 `num_predict=96`, `keep_alive=10m`를 명시. 모델 이름·기억·페르소나와 다른 옵션 변경/추가 없음.
4. `69cc1b6d6ab0af778a79c3a11030d3feaad42f4c`: 기존 `src/ai_broadcaster/ordered_parallel_local_ai.py`에 실제 모델 선행 추론의 대기·진행 중·완성 후 FIFO 대기·선두 순번 완료 여부/현재 경과시간을 텍스트·닉네임 저장 없이 읽는 `ParallelInferencePressure`/ `pressure_snapshot` 추가. 기존 원본 SQLite→전역 순번·기억 확정/ACK 순서 보존; 선행 추론 창 32건/최대 512 및 4작업자 원래 제한 보존.
5. `8b5150c46cf55bbd33ed3876954e56ce02d59db2`: 기존 `src/ai_broadcaster/desktop_chat_tab.py` GUI 상태에 실제 선행 추론 실행중·대기·완료 FIFO 보류 건수, 맨 앞 시퀀스가 완료되지 않아 뒤 결과가 묶이는 head-of-line 상태와 경과시간 추가. 자동 메시지 폐기·임의 재정렬·선행 발화 없음.

## 미완료/미검증을 명확하게 기록
- **211절 코드 구현·기존 main 비강제 커밋 완료. AISTING 필수 기능 전체 개발 미완료.** 모델 적재 성공은 첫 생성 응답 1~3초 달성이 아니며, FIFO 압박 표시는 병목 진단일 뿐 응답 지연의 해결 증명이 아니다.
- **테스트 NOT_RUN / 전체 회귀 NOT_RUN / CI 미조회·미확인 / Windows 10·11 EXE GUI NOT_RUN / 실제 권리 GPT-SoVITS WAV→공식 Cubism 입→OBS 동일 발화·수백 명 4플랫폼·24시간 정상 방송·시청자 최종 1~3초 NOT_RUN.**
- 과거 500건 실모델 CI 39720448468: 500/500 3초 초과, FIFO p95 2973.875초, 전체 p95 2979.984초 실패; Windows CI 39722213656 취소를 그대로 유지. 실제 모델·시청자 E2E 목표는 실패/미실증 상태.

## 다음 시간 이어서 실제 개발
- 현재 최신 GitHub main HEAD/211절 이후 인수인계/기존 소스부터 확인하고 **원본의 미완 핵심 코드 구현을 먼저 계속**한다. 4플랫폼 수백 명 채팅 전체 SQLite 내구·재연결, AI 최종 1~3초를 위한 선행 추론·FIFO 처리량, 권리 있는 실제 한국어 WAV→공식 Cubism 입→OBS의 시간·소유권·음성/영상 인과와 24시간 복구, 사용자가 승인한 자율 게임·콘텐츠·장기 기억.
- 모든 기능 개발을 마친 뒤에만 전체 Windows/EXE·실제 모델·공식 Live2D·OBS·4플랫폼/장기 운영 검증 → 발견 오류 일괄 수정 → 재검증. 미실증 성능을 달성이라고 주장하지 않는다.
- 예약은 중복 생성·비활성화하지 않고 다른 예약/프로젝트/브랜치 조작 금지. 원래 AISTING 채팅에서 예약 결과를 이어 쓰는 것을 우선 시도하되 게시 위치를 기술적으로 보장한다고 거짓 주장하지 않는다.
