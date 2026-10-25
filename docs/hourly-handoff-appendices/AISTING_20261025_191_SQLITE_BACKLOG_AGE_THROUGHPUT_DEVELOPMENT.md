# AISTING 191절 — 2026-10-25 18:35 KST 기존 main 실제 누적 개발

## 사용자 원문 지시 유지
- 기존 AISTING 대화와 기존 매시간 예약을 유지하고, 다른 프로젝트·예약·Drive·브랜치를 건드리지 않는다.
- 기존 GitHub `junggyeol4444/AISTING`의 main 원본을 보존한다. 기존 원본 기획, 페르소나/캐릭터, SQLite 대화, 모델, 96토큰 및 keep_alive 10m 설정, 1~190절과 모든 부록을 삭제·축약·덮어쓰지 않는다.
- 모든 미완료 실제 소스 **개발을 먼저 완료**하고, 그다음 전체 통합 회귀/Windows 10·11 EXE·GUI/실 OBS·공식 Live2D·권리 있는 GPT-SoVITS·4플랫폼/24시간 검증, 이후 오류 일괄 수정 및 전체 재검증을 수행한다. 이번 절은 개발 단계이며 수동 검증으로 전환하지 않는다.
- 무단 OAuth 동의·실제 송출·녹화·채팅 발신·공지 게시·음성 훈련을 하지 않는다.

## 확인한 기존 상태
- 이 회차 시작 main HEAD: `cf62e69b5ebad0d81f56dfc9405be831ffc95b1b`. 직전 190절 문서 커밋.
- 기존 docs/AISTING_HOURLY_FULL_HANDOFF.md, docs/AISTING_NEXT_CONVERSATION_HANDOFF.md, docs/ORIGINAL_PLAN.txt, docs/ROADMAP_100.md, config/roadmap.json 및 docs/hourly-handoff-appendices의 117개 원문을 GitHub에서 조회했다. 수정 대상 src/ai_broadcaster/durable_public_chat_queue.py, desktop_chat_tab.py와 연결된 공개 채팅·복구 경로를 확인했다. 전체 저장소 모든 파일 내용을 읽었다는 주장은 하지 않는다.
- 공식 원본 100단계 기록은 완료 9, pending 91이며 실사용 기능 완성률과 다르다.

## 실제 기존 main 코드 개발 및 커밋
- `src/ai_broadcaster/durable_public_chat_queue.py`: 기존 SQLite `pending_public_chat.created_at` UTC 값과 각 플랫폼 최저 미처리 sequence를 결합하여 **4플랫폼별 최장 미처리 채팅의 실제 저장 경과 시간**을 유지한다. 앱 재시작 때 기존 원본 행에서 시작점을 복원하고, 새 채팅 커밋/AI 완료 확인 커밋 뒤에만 최저 sequence를 갱신한다. 사용자 메시지·닉네임·기존 테이블/열·설정 변경 없음.
- 같은 기존 파일에 **이번 프로세스 실제 SQLite 성공 커밋 기준 60초 이동창의 플랫폼별 접수율·AI 완료 확인율·순증률·최근 완료율 기준 예상 미처리 소진 시간**을 추가했다. 재시작 전 과거 속도를 임의 복원하지 않고, 처리율 0이면 소진 추정을 하지 않는다. 소진 추정은 실측 완료율의 단순 비율이지 1~3초 달성이나 서버 무누락의 증거가 아니다.
- `src/ai_broadcaster/desktop_chat_tab.py`: 기존 Windows Tk 4플랫폼 운영 상태 창에 플랫폼별 최장 미처리 초, 이번 실행 접수/완료 건수, 초당 접수/완료·순증, 추정 소진 시간을 기존 5초 주기 읽기 전용 표시와 연결했다. 별도 DB 전체 COUNT 반복·원본 채팅 로그·자동 송출/채팅 발신 없음.
- 실제 코드 커밋: `ba76faa95b482ca2008085827fb39ed7c6088023` (시작 `cf62e69b5ebad0d81f56dfc9405be831ffc95b1b`의 자식, main fast-forward). 변경 소스는 위 2개 파일뿐. 이 문서 반영 커밋 후 최신 HEAD는 다음 실행에서 반드시 다시 조회한다.

## 실제 검사와 기존 실패의 보존
- 이번 회차 수동 단위 테스트, 전체 통합검증, Windows 10/11 네이티브 EXE·GUI, OBS·실 GPT-SoVITS·공식 Cubism·4플랫폼 실계정·24시간·시청자 1~3초 검사: **NOT_RUN / 미실증**. 코딩·push 자체를 성공 판정하지 않는다.
- 개발 HEAD `ba76faa9`의 자동 트리거 [Windows EXE run 40181511360](https://github.com/junggyeol4444/AISTING/actions/runs/40181511360), [REAL 500 Chat run 40181511540](https://github.com/junggyeol4444/AISTING/actions/runs/40181511540)는 2026-10-25 18:39 KST 조회 시 **queued**, PASS 아님. 이전 `cf62e69b`의 validation 40178468085 및 Windows 40178468081은 **cancelled**.
- 과거 실제 Ollama 500건 39720448468: **500/500 모두 3초 초과**, FIFO p95 2973.875초 / 전체 p95 2979.984초 실패. 이전 전체 회귀 36 failures/33 errors 및 Windows 39722213656 cancelled 이력 보존.

## 한 것 / 하지 않은 것 / 남은 것 / 중단 위치
- **실제 완료**: 기존 SQLite 보류 채팅의 플랫폼별 최장 체류 시간 추적, 이번 실행 접수·완료 처리율/적체 순증/소진 추정, Windows 운영자 상태 창 연결, 실제 main 코드 커밋.
- **하지 않은 것**: 수동 테스트 및 PASS 선언, 실계정 OAuth·방송·녹화·채팅 발신, 모델/음성 훈련, 원본 설정·캐릭터/대화 DB 변경, 타 프로젝트·브랜치·Drive·예약 조작.
- **남은 개발**: 기존 실모델 단일 FIFO 500건 대기 수천 초 병목과 1~3초 실제 시청자 E2E, 권리 있는 한국어 GPT-SoVITS WAV→공식 Cubism 입→OBS 동일 발화 실제 영상/음성 인과성, 수백 명 4플랫폼 무누락/24시간 운영 및 게임 자율 행위·공식 네이버 카페 게시 등 원본 계획의 남은 실사용 코드. 이번 개발은 **운용 가시성 개선이지 병목 해소 완료가 아니다**.
- **진행 중**: 전체 개발 미완료. 다음 실행은 이 대화·기존 예약을 유지하고 최신 main HEAD/CI와 원본 전체 인수인계를 재조회한 뒤 기존 소스 개발부터 계속한다. 개발 전부 완료 후에만 통합검증→일괄 수정→전체 재검증.

