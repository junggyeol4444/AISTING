# AISTING 201절 — 2026-10-26 03:33 KST 이후 실제 핵심 제품 소스 개발

## 사용자 직접 지시 및 대상
- 이 기존 AISTING 대화에 연결된 매시간 예약을 유지하고, 다른 대화·프로젝트·예약·Drive·브랜치에 임의 접근/변경하지 않는다.
- 기존 GitHub `junggyeol4444/AISTING` **main**만 비강제 누적. 이번 실행 시작 당시 실제 main HEAD: `8688d6892b4a55d2a4c199f332e601b9a058e1a4` (200절).
- **남은 핵심 기능 소스 전체 개발 먼저 → 그 다음 전체 Windows 10/11 EXE·GUI/로컬 모델·OBS·공식 Cubism·4플랫폼 통합검증 → 발견 오류 일괄 수정 → 전체 재검증**. 이번 회차는 코드 개발과 GitHub 소스 반영만 수행. 테스트/CI/실방송 실행 안 함.
- 원본 기획, 96토큰/keep_alive 10m, 캐릭터 이름/성격/말투, 모델, 기존 사용자 SQLite, 기존 인수인계 전문 보존. 승인 없는 OAuth·방송·녹화·실제 외부 채팅/공지 발신·음성 모델 학습 금지.

## 실제 확인한 기존 자료
- main HEAD와 재귀 트리 새로 조회. `docs/AISTING_HOURLY_FULL_HANDOFF.md` 전체 602,508자, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 전체 607,276자, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`을 GitHub에서 가져와 기존 내용을 보존.
- 기존 `docs/hourly-handoff-appendices` 97·185·187~200절 중 존재하는 관련 파일(189/193의 복수 부록 포함)을 가져와 확인. 다른 모든 과거 부록 각각을 읽었다고 주장하지 않음.
- 실제 수정 대상 `approved_live_voice_output.py`, `approved_live_voice_journal.py`, `desktop_chat_tab.py` 및 기존 `approved_obs_reconnect.py`, `original_plan_obs.py`, `durable_public_chat_queue.py`, `ordered_parallel_local_ai.py`, `approved_live_scheduler.py`, `approved_live_content_agenda.py`, `approved_discord_notice.py`, `approved_local_notice_ai.py`의 기존 함수·승인 경계를 읽음.

## 이번 제품 소스 개발 1 — OBS 실제 송출 소유권 고정
1. **신규 `src/ai_broadcaster/approved_live_voice_stream_lease.py`**: 실제 승인된 한 OBS 방송에서 첫 한국어 발화 직전 `GetStreamStatus.outputDuration`(밀리초)과 실제 장면/단조 시각을 고정. 매 발화 구간 시작·합성 후·OBS 소스 생성 전·재생 요청 전·발화 종료 후 실제 출력 가동시간 연속성 확인. 송출이 종료·재시작·장면 변경·조회 불명일 때 다른 방송에 기존 음성을 자동 발화하지 않고 Lease를 상실 상태로 유지. OBS 방송/녹화 시작·종료·장면 변경 API 없음. 시청자 실제 수신/동기화 성공 증명 아님.
2. **기존 `approved_live_voice_output.py`**: 기존 권리 확인 한국어 GPT-SoVITS→공식 Windows Cubism PCM 입→OBS ffmpeg 음성 입력 경로에 실제 출력 Lease 연결. 기존 사용자 승인/원본 WAV/임시 소스 소유권 확인 유지.

## 이번 제품 소스 개발 2 — 수백 건 음성 FIFO의 Windows DPAPI 영구 보존
3. **신규 `src/ai_broadcaster/approved_live_voice_outbox.py`**: 기존 `approved_live_voice_journal.py`와 **다른** 독립 소유권 SQLite `approved_live_voice_outbox.sqlite3` (AVO1). 실제 한국어 AI 답변은 Windows **현재 사용자 계정 DPAPI**로 암호화한 후 디스크에 영구 확정, 서버 채팅 이벤트의 SHA-256 키·원문 SHA·세션 ID와 원순서 접수 번호만 별도 기록. 기존 채팅/캐릭터/설정/기억 DB 변경 없음. DPAPI 복호화·무결성 실패 시 원문으로 대체 저장하지 않음.
4. 실제 한국어 합성·OBS 소스 생성 **전에** 원래 FIFO 첫 대기 항목을 SQLite 트랜잭션으로 `시도` 확정. 강제 종료 뒤 `시도`/불명은 자동 재발화하지 않음. 앱 재시작으로 생성된 새 방송 세션은 **이전 방송 세션의 암호화된 대기 음성을 자동 송출하지 않음**. 과거 미발화/불명 건수만 로컬 GUI에서 조회 가능. 성공/중단/불명/중복 시 해당 행의 암호문 삭제, 상태·해시/시각만 유지. 동시 중복 서버 이벤트는 하나의 키로 거부, ID 없는 서로 다른 채팅은 본문·닉네임으로 임의 병합하지 않음.
5. 세션·상태·원순서 SQLite 인덱스, 20만 건 대기 보호한도, `PRAGMA synchronous=FULL`, 파일 소유권/application_id/테이블 열 검증, symlink 차단, 매 호출 DB 핸들 닫기 경로 개발. Windows가 아닌 환경은 기존 메모리 FIFO를 보존하되 실제 Windows EXE는 DPAPI 초기화 실패 시 영구 음성 기능을 임의로 평문 폴백하지 않음. **과거 방송 대기 건의 사용자 승인형 재생 재개 기능은 아직 개발하지 않았으므로 보류로 표시**.
6. **기존 `approved_live_voice_output.py`**: Windows 승인 실제 방송의 `enqueue`를 영구 암호화 대기함 접수로 연결, 작업자가 SQLite FIFO를 차례로 꺼내 기존 영구 발화 시도 장부에 claim한 뒤 기존 GPT-SoVITS/Cubism/OBS 경로 실행. `stop`은 기존 방송 자체를 중단하지 않고 새 음성 시도를 막음. 중단/불명 원문 자동 중복 재전송 없음.
7. **기존 `desktop_chat_tab.py`**: 실제 Twitch·치지직·SOOP·YouTube 로컬 AI 응답의 기존 음성 접수 경로에 영구 접수 상태/현재 세션 대기 건수/이전 방송 미처리 건수 표시. 기존 발화 기록 버튼에서 암호화 음성 대기/불명 **건수만** 조회. 새 외부 계정 로그인·방송 시작·채팅/공지 게시 없음.

## 이번 제품 소스 개발 3 — 동일 WAV의 실제 전달 순서 영구 기록
8. **신규 `src/ai_broadcaster/approved_live_voice_causal_journal.py`**: 독립 SQLite AVC1에 같은 실제 WAV SHA-256, 원래 발화 해시, 구간 번호, 실제 OBS 장면/임시 소스 UUID, 공식 Cubism PCM 입 구동 함수 반환 시각, OBS WebSocket 미디어 재생 요청 반환 시각, 재생 시간 경과/전달 불명 상태 기록. 음성 원문·WAV 바이트·채팅 본문·비밀번호·OAuth 토큰 미저장.
9. **기존 `approved_live_voice_output.py`**: 한국어 장문 분절·재분절 각 구간에서 동일 `raw` WAV를 Cubism PCM 봉투와 OBS 미디어 파일에 동시에 사용한 뒤 실제 입 시작/OBS 재생 요청의 순서를 장부에 기록. 불확실한 요청은 '전달불명'으로 남기고 무단 재시도하지 않음. 재생시간 경과는 **시청자 실제 수신·OBS 오디오 트랙 성공·입/영상 동기 실증이 아님**.
10. **기존 `desktop_chat_tab.py`**: 기존 실제 음성 기록 조회창에서 최근 10개 WAV 구간의 해시 일부, 길이, 입→OBS 요청 간격과 상태를 읽기 전용으로 표시.

## 실제 제품 소스 GitHub main 커밋 (11개)
1. `593e0c6a466b37cb30830ddd498a2fa66c714e62` — OBS 동일 출력 Lease 신규 파일.
2. `1d036b8101dc6b556c92ac987df7374e7f8f0659` — Windows DPAPI 영구 음성 FIFO 신규 파일.
3. `e1d4c151514ed030a9daeba394dc211aed71f662` — 영구 SQLite 트랜잭션 핸들 종료 구현.
4. `1c55f974b654fd53ed0d4339c5fe8a9e1692bdab` — 실제 음성 출력의 영구 FIFO/OBS Lease 연결.
5. `47e6b040e2c418a7ee3439ef281487c66a09b74e` — 영구 미처리 음성 건수 조회.
6. `d8feed394a1bba863f0819989dfaaafccf1f6e64` — Windows 실제 채팅 음성 GUI 영구 상태 연결.
7. `cc63d449c30d6e7d6c0ea1768044fbb912fc33f9` — GUI Windows 플랫폼 분기 포함.
8. `fe6c00e307e495441be92644654bf70de82a0d2a` — 동일 WAV Cubism/OBS 인과 장부 신규 파일.
9. `958c23a31203bbf4a408a668e4e5cae2aac5686b` — 실제 PCM·OBS 재생 요청 인과 장부 연결.
10. `b20bbab41101cdf86219bbaacb195c0c4837fdd0` — Windows 인과 기록 GUI 조회 연결.
11. `0ec58a72c0ac757372e7cbdfd06ba58480391c11` — 대규모 FIFO 세션·상태 인덱스.

실제 제품 소스 신규 Python 3개, 기존 Python 수정 2개. 제품 소스 최종 HEAD `0ec58a72c0ac757372e7cbdfd06ba58480391c11`은 이 부록/전체 인수인계 문서 반영 전 기준. 문서 커밋 후 실제 최종 HEAD 재조회.

## 이번 실행 검증·미완료·다음 실행 인수인계
- **제품 소스 작성 및 기존 main 누적 반영: 완료. AISTING 전체 기능 개발: 미완료.**
- **테스트 NOT_RUN, CI 조회하지 않음/결과 미확인, Windows 10/11 EXE GUI NOT_RUN, 실제 4플랫폼 계정·OBS·공식 Live2D Cubism·한국어 GPT-SoVITS·24시간·수백 명·시청자 음성 수신 NOT_RUN.** 제품 기능이 정상 작동한다고 단정하지 않는다.
- 과거 500건 실모델 CI `39720448468`에서 500/500 모두 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초 실패, Windows CI `39722213656` 취소 기록 보존. 현재 1~3초 달성/실방송 성공 주장 금지.
- **남은 실제 개발:** 수백 명 4플랫폼 공개 채팅 장시간 수신·영구 커서·AI 처리량/FIFO 백프레셔/1~3초 목표, 사용자 승인형 과거 음성 대기 재개(동일 방송 출력 확인 필수), 실제 OBS 오디오 트랙·공식 Cubism 입·WAV의 장시간 영상/음성 동기 유지, OBS/공식 Cubism/GPT-SoVITS 다운 시 24시간 승인 경계 내 자동 복구, 자율 게임·콘텐츠 장기 수행, 원본 기획의 공식 네이버 카페 공지 등. 모든 핵심 기능 개발 완료 전 검증/오류 수정 단계로 이동하지 않는다.
- **다음 시간:** 바로 이 AISTING 대화 유지 최우선. 새 대화/다른 프로젝트·예약·Drive/브랜치 조작 금지. GitHub main HEAD 재조회 → 201절까지 원본·기획·인수인계 읽고 **남은 실제 제품 소스 개발부터** 계속 → 정상 main 커밋 → 기존 두 전체 인수인계 원문 뒤에 새 절 append-only.
