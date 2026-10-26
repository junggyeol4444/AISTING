# AISTING 220절 — 2026-10-26, 로컬 AI→Windows 영구 음성 FIFO 선접수 후 채팅 ACK

## 실제 원본 제품 개발
- 시작 `main` HEAD: `7a56252e120108e8b7c6f384b0015bdbd20b9ed5`. 기존 원본 기획, 100단계 로드맵, 전체 누적 인수인계 두 파일(Git blob 원문), 219절, 공개 채팅 SQLite/4플랫폼 AI FIFO/Windows GUI/GPT-SoVITS·공식 Cubism·OBS 실제 음성 소스를 확인한 뒤 제품 코딩부터 진행.
- 제품 코드 단일 정상 비강제 커밋: `397f14b86943dbe9cde1b5f385c4ea7b508d015a`.
- `src/ai_broadcaster/durable_public_chat_queue.py`: 기존 채팅 보류/서버 이벤트 ID/장애/219절 접수·완료 영구 원장 보존. 독립 `public_chat_voice_handoff_identity` 단일 행에 공개 채팅 DB 생애 고유 UUID 추가. `voice_handoff_nonce(sequence)`로 실제 미처리 채팅 원본 존재·DB 소유권·UUID 형식을 확인하고 원래 SQLite sequence마다 재시작에 안정적인 32자 nonce 반환. 채팅 원문/닉네임/AI 답변은 새 표에 저장하지 않음. DB 파일을 그대로 이동해도 고유 ID 유지.
- `src/ai_broadcaster/approved_live_voice_output.py`: 기존 운영자 승인 실제 GPT-SoVITS→동일 WAV 공식 Cubism/OBS 음성 작업자의 `enqueue`에 선택형 `durable_nonce` 연결. 실제 서버 event_id가 있으면 원래 서버 ID 기반 turn_key 유지, 없는 별도 채팅은 DB UUID+sequence nonce로 구분. 재시작 중복 요청은 기존 Windows DPAPI SQLite outbox UNIQUE turn_key에서 차단. 기존 수동/비내구 발화의 무작위 nonce·권리 승인·원래 음성 기능 보존.
- `src/ai_broadcaster/desktop_chat_tab.py`: 기존 선택된 4플랫폼 로컬 Ollama AI 처리 후 **GUI 결과 큐보다 먼저** 같은 운영자가 승인한 Windows DPAPI 음성 영구 outbox에 답변을 접수하고, 성공한 경우에만 공개 채팅 SQLite 완료 ACK. 영구 음성 접수 불가/Windows 대기함 없음/중지 시 ACK 금지 및 기존 FIFO 중단/장애 기록. Tk GUI는 전달받은 영구 접수 seq를 표시하고 같은 AI 답변을 다시 enqueue하지 않음. 과거 단독 GUI·기본 Windows 음성 경로 보존.
- 원본 한국어 Windows 10/11 x64 Tkinter EXE, 캐릭터·설정·사용자 SQLite·기존 모델 `num_predict=96`/`keep_alive=10m`, 기존 로드맵 9 completed/91 pending 보존. 다른 프로젝트/Drive/브랜치/예약/원본 삭제·force push·무승인 외부 방송/채팅/공지/OAuth/모델 학습 없음.

## 중단·재시작 및 사실 구분
- 2개 독립 SQLite를 하나의 원자 트랜잭션으로 주장하지 않는다. 대신 **음성 outbox 영구 접수 → 채팅 ACK** 순서와 안정적인 동일 채팅 발화 키를 사용. 둘 사이 비정상 종료 시 원본 채팅은 남지만 음성 outbox는 같은 turn_key 중복 요청을 거부한다. 기존 음성 '시도/불명/완료'는 다른 방송에 자동 재발화하지 않음.
- 영구 접수는 **음성 실제 재생/OBS 믹스/시청자 수신 성공이 아니다**. 서버가 보내지 않은 채팅은 복원할 수 없으며 로컬 AI 응답 1~3초도 증명하지 않는다.
- **전체 제품 개발 미완료. 테스트 NOT_RUN / 통합 NOT_RUN / CI 미조회·미확인 / Windows 10·11 EXE GUI NOT_RUN / 실제 권리 GPT-SoVITS WAV→공식 Cubism→OBS·4플랫폼 수백 명·24시간 NOT_RUN / 시청자 최종 1~3초 미확인.** 과거 실모델 CI `39720448468` 500/500 3초 초과, FIFO p95 2973.875초/전체 p95 2979.984초 실패; Windows CI `39722213656` 취소 기록 유지.

## 다음 221절 이후
- 매 실행 최신 `main` HEAD 및 실제 제품 소스 재조회, 기존 1~220절 인수인계 원문 보존. **핵심 미개발 제품 기능 코딩부터** 계속: OBS 실제 음성 믹스/출력 경로와 같은 WAV 공식 Cubism 장시간 동기, 4플랫폼 수백 명·FIFO 적체/로컬 Ollama 처리량, 운영자 승인 24시간 방송/게임·자율 콘텐츠·공지·장기 기억/안전 종료.
- 모든 개발이 끝난 후에만 Windows 10/11 EXE·GUI·실계정·권리 모델·OBS/공식 Cubism·수백 명/24시간 통합 검증→오류 일괄 수정→전체 재검증. 기존 AISTING 예약/원래 대화 연속성 우선, 채팅 게시 위치 보장 허위 주장 금지.
