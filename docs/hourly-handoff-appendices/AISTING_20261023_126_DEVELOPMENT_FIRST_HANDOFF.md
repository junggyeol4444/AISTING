# AISTING 126회차 기존 원본 보존 누적 인수인계

## 126. 2026-10-23 — 공식 Open-LLM-VTuber WebSocket 첫 실제 RIFF/WAV 응답의 선택형 3초 관찰 기능 누적 개발

### 현재 기준 / 이전 사용자 지시와 자료 확인
- 최근 사용자 지시 `계속`; AISTING 기존 main 원본의 **전체 미완료 개발 우선 → 모두 개발한 뒤 전체 회귀·Windows 네이티브 EXE/GUI·OBS·로컬 모델 실통합검사 → 오류 수정 → 전체 재검증** 순서를 유지한다. 기존 원본 개발·인수인계·캐릭터·SQLite·모델·설정·전달 큐, 모든 과거 부록 및 지침을 보존한다. 다른 프로젝트, Drive, 기존 매시간 예약은 생성·수정하지 않았다. 새 브랜치/force push/롤백/전면 재개발 및 무단 계정·OAuth 대행, 송출·녹화·채팅 발신·모델 학습·권리 없는 음성 금지. 사용자 지시 없는 `num_predict=96`과 `keep_alive=10m` 추가/변경 금지.
- 시작 실제 GitHub `main` HEAD `0c47cb44c1bd7fdc1efaac40f58185fd06daa896` 재조회. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, `docs/AISTING_HOURLY_FULL_HANDOFF.md` 원문 1~125절, `docs/AISTING_NEXT_CONVERSATION_HANDOFF.md` 원문, 97절 원본 부록, 125절 부록 및 실제 `original_plan_frontend.py`·`desktop_chat_tab.py`·로컬 AI 관련 코드 확인.

### 실제 신규 개발 및 GitHub fast-forward 반영
- 기존 125회차: 공식 React UI/WebSocket 질문 `send_to_native_live2d_session`은 **텍스트 전송만** 확인, 기존 8초 `send_to_native_live2d_session_with_observation`은 실제 PCM WAV·공식 Cubism 입/RMS 관측. 125회차 빠른 전송을 사용하면 질문이 실제 서버에서 음성으로 돌아왔는지는 전혀 확인하지 못하는 문제가 남았다.
- 126회차 신규 개발 커밋 `f4d4186ec63aec6b934642dce8930ac5384a4f74`을 **main 직접 fast-forward, force=false/expected_sha 확인**으로 반영 성공. `src/ai_broadcaster/original_plan_frontend.py`에 `OfficialFirstWavReceipt`, `send_to_native_live2d_session_with_first_wav`, `_observe_first_wav_receipt` 구현. 이미 인증된 Windows AF_PIPE와 운영자 1회 승인/동일 공식 WebView2 React 핸들러·기존 원본 `WebSocket.prototype.send` 호출을 그대로 사용한다. 승인받은 원래 텍스트를 한 번만 전송하고, **그때 붙은 동일 원본 WebSocket 메시지 리스너**에서 반환된 `type=audio` / RIFF WAV 헤더·RIFF 길이 일치의 실제 이벤트가 최대 3초 동안 들어오는지만 관찰한다. 관찰 중 연결/브라우저 오류, 메시지 형식 불일치, 응답 시간 초과는 오류·미측정으로 기록하며 **원래 질문/AI 호출은 재전송하지 않는다**. WAV 원본 음성·채팅 텍스트/계정 정보는 새 로그·파일에 저장하지 않고 작은 bool 및 실제 WAV 시작 관측 시각만 응답한다. 기존 브라우저 훅·메시지 리스너는 기존 `finally`에서 반드시 해제되는 경로를 유지한다.
- Windows 네이티브 `desktop_chat_tab.py`의 기존 빠른 공식 채팅 모드에 **운영자가 별도로 선택하는 첫 RIFF/WAV 관찰 체크박스(기본 꺼짐)** 추가. 기본 선택이 꺼져 있으면 기존 빠른 전송을 그대로 실행하여 추가 대기 시간이 없다. 운영자가 선택한 경우에만 실제 기존 FIFO 워커가 질문 1건을 `send_to_native_live2d_session_with_first_wav(...wait_seconds=3.0)`로 한 번 보내고 해당 창에서 실제 WAV 첫 헤더가 관찰됐는지를 보고한다.
- 기존 공식 텍스트 전송 성공 건수 `_twitch_official_forwarded`를 별도로 유지한다. 새 `twitch_live2d_first_wav` GUI 이벤트에서 `_twitch_official_wav_observed` / `_twitch_official_wav_unobserved`를 분리해 한국어 표시. **3초 이내 실제 WAV를 못 보았다고 모델 실패나 최종 무응답으로 단정하지 않고**, WAV 관측을 성공한 AI 답변·GPT-SoVITS 음색·Cubism 입·OBS 인코더/송출·시청자 수신으로 허위 계수하지 않는다. 전송 성공만 된 이벤트의 입력별 완료 보장은 안 된다. 원본 프로토콜에 요청-응답 식별자가 없으므로 과거 발화의 잔여 오디오가 새 관찰 창에 들어왔을 수 있으며 **특정 채팅과 특정 WAV의 인과성은 미증명**임을 UI·코드에 명시한다.
- 과거 사용자 승인·캐릭터/설정 일치·기존 저장 기능/SQLite/단일 AI FIFO·운영자 Stop/종료 안전 경로를 변경하지 않았다. 동일 공식 서버의 텍스트 입력을 두 번 보내지 않고, OBS 방송·녹화·장면·실시간 채팅 송신·AI 모델 다운로드/학습 작업을 실행하지 않는다.

### CI 진실 상태 및 실시하지 않은 작업 / 다음 이관
- 과거 [Windows CI 39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656) 최종 조회 `completed/cancelled` (예전 4작업 성공·한국 공개 채팅 작업 취소, 취소 로그 404 기록 및 과거 다른 실패 CI는 원문에 그대로 보존). 전체 성공으로 표현하지 않는다.
- 과거 [Ollama 실모델 500건 CI 39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468) 최종 조회 `completed/success`지만 **합성 채팅 500건 모두 로컬 3초 초과**, 기존 전체 p95 `2979.984초`, FIFO 대기 p95 `2973.875초`, AI 처리 p95 `7.875초`. 실제 동시 500명, 진짜 24시간, 시청자 E2E 1~3초·네 플랫폼 무누락 실증이 아니다.
- **이번 실제 수행**: 기존 main 재확인, 원본 기획/로드맵/인수인계·소스·기존 CI 재조회, 실제 공식 WebSocket 서버 audio 리스너의 첫 WAV RIFF 이벤트 응답을 선택적으로 확인하는 Windows EXE용 Python 원본 기능 구현·GitHub fast-forward 반영, GUI에서 결과 분리·오류/미관측 표시 개발, 126절 전체 인수인계 누적.
- **이번 실제 수행하지 않음**: 이번 126회차 새 코드의 CI·단위검사·전체 회귀, Windows 10/11 네이티브 EXE 빌드/실행, 사용자 라이선스 GPT-SoVITS WAV·공식 Live2D Cubism·OBS 실장비 구동, 네 플랫폼 실수백명 부하 테스트, 실제 24시간 연속 실행/재연결 성능 측정, 방송·시청자 E2E 1~3초 실측 및 오류 수정/전체 재검증. 개발 커밋만 생성·적용되었으며 검증 완료가 아니다.
- **남은 핵심 기능 개발**: 실제 각 채팅별 답변 완료와 권리 있는 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 실립싱크→OBS **같은 발화**의 PCM·영상 동기 인과 실증, 실제 4플랫폼 수백 명의 서버 채팅 전체 수집·재연결 복구, 24시간 견고한 읽기·출력 안전, 로컬 Ollama FIFO 500건/실물 AI 음성 영상 경로의 1~3초 시청자 E2E 병목 기능 개발. 전체 기능 개발 완료 후에만 사용자 지정 전수 회귀/Windows 네이티브 EXE/실제 OBS·로컬 모델 통합→오류 수정→전체 재검증 수행.
- 신규 소스 커밋 HEAD `f4d4186ec63aec6b934642dce8930ac5384a4f74`. 이 인수인계 126절 커밋 후 실제 main HEAD는 달라지므로 다음 대화/매시간 실행에서 반드시 현재 main HEAD를 다시 확인한다. 원본 1~125절 및 모든 과거 부록을 유지한다.
