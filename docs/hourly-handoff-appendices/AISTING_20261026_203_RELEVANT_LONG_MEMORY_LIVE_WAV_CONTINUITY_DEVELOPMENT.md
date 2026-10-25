# AISTING 203절 — 2026-10-26 05시대 실제 핵심 제품 개발: 관련 장기 대화 기억·실제 WAV 재생 중 OBS/Cubism 연속 감시

## 이번 실행 지시와 시작 기준
- 사용자의 최신 지시: **기존 AISTING 대화 유지 우선**, 기존 매시간 예약 그대로, 다른 프로젝트·Drive·브랜치·예약 변경 금지.
- GitHub `junggyeol4444/AISTING` **main** 실제 시작 HEAD: `5fc764d3c804fe9ca12d330da9b2af3befae4933` (202절 이후). 오래된 195절 HEAD를 최신으로 간주하지 않음.
- 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 두 전체 인수인계, 97·185·187~202절 부록과 실제 변경 대상 기존 Python 파일을 읽고 원본 기능에 이어 개발함. 두 번째 전체 인수인계는 `fetch_file` 전체/범위가 빈 문자열로 반환되는 도구 문제를 확인하여, 별도 GitHub `fetch` 원문 617,374자를 가져와 **원본 전문을 보존**할 수 있도록 함.
- 원본 100단계/운영자 최종 승인 상태는 변경하지 않음. **모든 핵심 소스 개발 완료 → 전체 통합검증/Windows EXE 실사용 → 일괄 수정 → 재검증** 순서 유지. 이번 회차에는 제품 코드 개발과 기존 main 커밋만 수행, 테스트/CI 조회/실방송 없음.

## 이번 실제 제품 소스 개발 1 — 로컬 한국어 AI의 과거 관련 대화 기억
1. **기존 `src/ai_broadcaster/conversation_memory.py` 확장**: 원래 SQLite `exchanges` 테이블에서 최근 대화에 포함되지 않은 과거 메시지를 한국어·영문 키워드로 검색. SQL 바인딩·LIKE 이스케이프, 최대 8개 토큰·512개 후보, 실제 일치 점수와 시간 순서로 최대 4개 관련 과거 대화 조회. 기존 기억 DB 스키마/내용/캐릭터/보존 한도 변경 없이 **읽기 전용** 검색. 관련 기록이 없으면 창작하지 않고 빈 결과.
2. **기존 `src/ai_broadcaster/local_llm.py` 확장**: 운영자가 선택할 때만 `LocalModelConfig.max_relevant_exchanges`를 2로 설정. 일반 Ollama `generate`와 스트리밍 `generate_stream` 모두 **같은 실제 SQLite 관련 과거 대화**를 기존 최근 8개 앞에 참고 맥락으로 넣음. 과거 기록은 새 system 명령이 아니라 실제 과거 user/assistant 발화로 표시. 원래 사용자 페르소나/모델명/토큰 96/keep_alive 설정 변경 없음.
3. **기존 `src/ai_broadcaster/desktop_chat.py` 확장**: 수동 AI 질문과 기존 직렬 FIFO의 `LocalChatRunner`에서 선택한 관련 기억을 동일하게 사용.
4. **기존 `src/ai_broadcaster/ordered_parallel_local_ai.py` 확장**: 최대 4개 병렬 추론의 각 실제 Ollama 요청도 관련 과거 기억을 **이미 SQLite에 확정된 답변만** 읽어서 참고. 원래 32건 선행 한도·FIFO 결과 확정 순서·기억 저장 순서 유지.
5. **기존 `src/ai_broadcaster/desktop_chat_tab.py` 확장**: Windows GUI에 기본 꺼짐인 '관련 과거 대화 2건 참고' 선택을 추가. 수동 질문, 4플랫폼 실제 채팅의 직렬/병렬 AI 경로에 선택값 전달. 실제 계정/외부 검색·모델 다운로드 없이 기존 로컬 SQLite만 사용. 이 기능은 **최대 5000개 기존 보존 기록 범위** 내 검색이며, 별도 장기 아카이브나 무제한 기억을 구현한 것으로 주장하지 않음.

## 이번 실제 제품 소스 개발 2 — 동일 WAV 재생 중 OBS·Cubism 연속 감시
6. **신규 `src/ai_broadcaster/approved_live_voice_playback_watch.py`**: 실제 한국어 GPT-SoVITS WAV의 0.4~8초 재생 도중 약 0.4초마다 **이미 승인한 OBS 출력 가동시간·장면의 Lease, 이번 구간의 UUID로 소유권 확인된 전용 ffmpeg_source, 공식 Windows Live2D Cubism 창 생존**을 읽기 전용으로 점검. 방송이 끊기거나 관측 불명/장면 변경/다른 출력/사용자 Stop이면 이후 구간을 임의 재생하지 않고 실패를 상위 작업자에 전달. OBS 송출·녹화 시작/종료, 장면 변경, 타 소스 조작 없음.
7. **기존 `src/ai_broadcaster/approved_live_voice_output.py` 확장**: 기존 동일 WAV→공식 Cubism PCM 입→OBS 음성 입력의 실제 `trigger_media_input_action` 뒤, 기존 마지막 한 번의 재생 대기 대신 **전체 재생 구간 연속 감시**를 연결. 기존 `ApprovedVoiceCausalJournal`은 관찰 불명 시 '전달불명' 상태를 유지하고 자동 이중 발화하지 않음. 기존 고유 소스만 정리·Cubism 원상복귀하는 경로 유지.
8. 주의: OBS API 상태/공식 Cubism 창/소스 확인은 **프로그램 내부 연결 관측**이며, OBS 인코딩 트랙·실제 최종 시청자 1~3초·장시간 실제 립싱크 성공의 증명 아님.

## GitHub main 실제 제품 소스 커밋 (7개)
1. `e5d6abb84d4fb1292cc65dbf7e4cfd6e8d2ff45f` — SQLite 과거 관련 대화 안전 검색.
2. `22da18658a5eea8f69f4a07ba98c8f7903f5ab5e` — 일반/스트리밍 Ollama 관련 기억 문맥 연결.
3. `72d18463baa2e4291a6a2713b04abae0b4ea733b` — 수동/직렬 로컬 AI 기억 선택.
4. `f86438bc4aa6ee7340cbf1b978efa858112e0395` — 4개 병렬 추론 관련 기억 선택.
5. `1fc888e297170fd721d399dee55d171f0764f0dc` — Windows GUI·4플랫폼/수동 기억 선택 연결.
6. `d2631f26d3a227ffed1daf3bb97c8b69d4b7d709` — 실제 WAV 재생 연속 감시 신규 모듈.
7. `4c57f4ccdad3cd3b66f1360ecc48796de22e0a53` — 기존 한국어 WAV/Cubism/OBS 실제 출력에 감시 연결.
- **실제 제품 소스 7커밋, 신규 Python 1개, 기존 Python 수정 6개.** 제품 코드 최종 HEAD는 `4c57f4ccdad3cd3b66f1360ecc48796de22e0a53`. 본 부록과 두 전체 인수인계는 제품 소스 커밋 이후 별도 append-only 커밋이며, 제품 개발 건수에 포함하지 않는다.

## 실제 상태·남은 기능·다음 회차
- 이번 실제 개발 완료: **선택형 과거 관련 대화 검색/수동·4플랫폼 직렬·병렬 로컬 AI 문맥 연결**, **같은 WAV 재생 중 OBS·공식 Cubism·고유 음성 소스 연속 감시**. 전체 AISTING 개발 완료 아님.
- **미개발/미완료**: 4플랫폼 수백 명 전체 이벤트 무손실 수신·서버별 재연결 커서의 실사용 완성, 로컬 AI 500건 FIFO의 실제 1~3초 처리 목표를 위한 모델/음성 병목 추가 개발, GPT-SoVITS/공식 Cubism/OBS 영상·음성의 24시간 장애 후 동일 방송에서 안전한 복구, 운영자 승인형 과거 음성 대기 재개, 자율 게임/콘텐츠 장기 수행, 원본 계획의 남은 기능. 관련 과거 대화 검색은 기존 최대 5000개 범위이며 무제한 장기기억은 미개발.
- 과거 실제 500건 Ollama CI `39720448468`은 **500/500 모두 3초 초과**, FIFO p95 2973.875초/전체 p95 2979.984초 실패. Windows CI `39722213656` 취소, 기존 전체 회귀 실패 기록 보존. 성공으로 변경 금지.
- **이번 회차 수동 단위 테스트 NOT_RUN, 전체 회귀 NOT_RUN, CI 조회하지 않음/미확인, Windows 10/11 EXE GUI NOT_RUN, 실제 OBS/공식 Cubism/한국어 GPT-SoVITS/4플랫폼 계정·수백 명·24시간/최종 시청자 1~3초 NOT_RUN.** 개발 코드를 실제 방송에서 검증했다고 주장하지 않음.
- 기존 사용자 원본/SQLite/설정/캐릭터/기획/인수인계 삭제·축약·전면 재개발 없음. 새 브랜치·다른 프로젝트·예약·Drive 변경 없음. 실제 방송/계정/OAuth/채팅·공지 발신·모델 학습 없음.
- 다음 매시간 작업은 **기존 AISTING 대화 유지 최우선**, 최신 GitHub main HEAD 재조회, 203절까지의 전체 인수인계·원본 확인 후 남은 핵심 **제품 코드 개발부터** 계속. 검증·오류 수정 선행 금지. 소스 main 비강제 커밋 후 두 전체 인수인계 문서 끝에만 새 절 append.
