# AISTING 매시간 개발·검증 — 전체 누적 인수인계 (원래 대화 유지 우선)

> **중요**: 이 문서는 원래 AISTING ChatGPT 대화가 길이/플랫폼 제한으로 유지되지 않을 때 작업을 잃지 않기 위한 **실제 GitHub main 상의 영구 인수인계**다. 예약 작업은 가능한 한 **예약을 만든 원래 대화에서 계속**하고, 임의로 새 대화를 만들지 않는다. 단, ChatGPT 플랫폼의 예약 결과 채팅 배치를 도구가 강제로 결정할 수 있다고 약속해서는 안 된다. 다른 대화로 표시되는 경우 이 문서를 먼저 읽고 현재 GitHub main을 검증한 뒤 누적 작업을 이어간다.

## 1. 예약 및 대화 유지 (사용자 최우선 요구)

- **프로젝트**: AISTING (별도의 AIWACK, AI NOVEL, MYVOCAL과 절대 혼동하지 말 것).
- **원래 대화**: 사용자가 `예약을 걸어 이 대화에서 계속 진행가능하게`라고 요청한 이 AISTING 대화. 현재 채팅이 가능한 동안 이 대화 우선. 대화가 너무 길거나 플랫폼 때문에 실제로 불가한 경우에만 다음 대화로 인수인계.
- **반복**: 2026-10-19 17:14 Asia/Seoul 첫 실행, 이후 정확히 매 1시간. 다른 프로젝트의 예약 건드리지 말 것.
- **PC 전원 OFF**: 사용자 Windows PC가 꺼져 있어도 GitHub 클라우드에서 실제로 가능한 코드 수정·Actions 빌드·검사는 진행. 사용자 로컬 화면·마우스·GPU·OBS·GPT-SoVITS 실행을 했다고 거짓말하지 않는다.
- **다른 대화에서 실행됐을 때 의무 순서**: ① 이 문서 및 원본 기획·로드맵 읽기 → ② 새 GitHub main HEAD/변경 커밋/CI 확인 → ③ 진행 중인 작업과 충돌 여부 확인 → ④ 원래 기획대로 기존 앱 이어서 개발 → ⑤ 최신 증빙과 본 인수인계 갱신 → ⑥ 대화 이전이 불가피한 경우 왜 그런지 보고. 파일이 없거나 누락되면 GitHub 이력과 원본 자료로 복원. 사용자에게 재설명 요구 금지.
- **각 실행 종료**: 가능하면 이 문서를 누적 갱신. 완료/진행/미완료, SHA, 파일 목록, run URLs, EXE artifact 및 검증 수준, 다음 구체적 복수 작업을 기록한다. 문서 커밋 자체가 main HEAD를 변경하는 점에 주의해 기준 SHA와 문서 커밋 SHA를 혼동하지 말 것.

## 2. 현재 GitHub 기준 (2026-10-19, 문서 최초 생성 이전 확인)

- **저장소**: https://github.com/junggyeol4444/AISTING
- **브랜치**: `main` 단 하나. 과거 dev 및 v105 테스트 브랜치는 삭제됨. 되살리거나 새 브랜치를 임의로 만들지 않는다.
- **최신 코드 기준 HEAD**: `191ab786b5b50833fea188174184fa6a98209465` (문서 생성 직전 검증; **다음 실행마다 현재 HEAD 재조회 필수**).
- **문서/기획 원본**:
  - `docs/ORIGINAL_PLAN.txt` (약 740줄, 기존 사용자 사업/방송 기획)
  - `docs/ROADMAP_100.md` (100단계)
  - `config/roadmap.json` (확인 당시 9 completed / 91 pending; 010단계 사용자 최종 승인 대기. 개발 코드 존재와 사용자 승인·실제품 완료는 구분)
  - `docs/STATUS.md` (과거 오프라인 버전 진척 누적 문서; 일부 구버전 상태 문구가 존재함. 실제 최신 코드·Actions보다 오래된 설명을 현재 사실로 취급하지 말 것).
  - `.github/workflows/build-windows.yml` (기존 네이티브 Windows CI; main push 동작 유지).
- **기존 브랜치 소스 이력 보존**: 과거 테스트 브랜치의 차이 나는 파일 51개는 `branch-snapshots/test-v105-windows-validation-20261015/`에 별도 보존되어 있음. 현재 실행 소스 대신 이 스냅샷을 덮어쓰지 말 것.
- **금지**: 다른 브랜치 삭제/생성, main 강제 푸시·원복, 과거 소스가 최신 소스를 덮어쓰기, 기존 사용자 설정/SQLite 임의 파괴.

## 3. 사용자 변경 불가능 요구 — 원래 프로그램 유지

- **Windows 10/11 x64용 기존 네이티브 `AISTING.exe`**, Tk GUI와 기존 source/build entrypoint를 **그대로 누적 수정**. 새 EXE를 다른 이름의 프로젝트로 재개발하지 말고 웹/HTML 앱으로 대체하지 말 것. 공식 Live2D WebView2는 기존 네이티브 앱 내부의 공식 화면 부분이며, 별도 브라우저 기반 프로그램으로 바꾸는 것이 아님.
- 캐릭터 이름/말투/성격은 **캐릭터 생성 때 1회 입력·저장** 후 지속 사용. 매 실행 재입력 금지. 저장한 캐릭터·기억·설정·SQLite·개인 자료 보존. 아직 승인하지 않은 draft를 최종 데이터로 자동 전환 금지.
- 기존 Open-LLM-VTuber 서버를 이용한 AI 캐릭터, 공식 Live2D 실제 아바타/립싱크, 권리가 확인된 GPT-SoVITS 한국어 음성, OBS 영상/오디오 실제 출력, Chzzk/SOOP/Twitch/YouTube 사용자 선택 방송 플랫폼의 읽기 전용 채팅 수신.
- 채팅은 **0~5명부터 수백명까지, 원칙적으로 모든 수신 메시지(반복/중복 포함)를 도착순 FIFO 응답**. 임의 누락/선별/무시/중복 제거 금지. 초기에는 전 메시지 응답 목표; 사용자 요청 없는 선택적 응답 정책 추가 금지. 사용자에게 음성·Live2D·OBS 실제 방송이 검증됐다고 과장 금지.
- 여러 실질적 오류 및 기능을 **한 묶음으로 동시에 개발/수정/검증**. 사소한 한 항목만 작업하고 매회 멈추지 말 것.
- 앱에서 자동 방송/공지를 원하는 장기 기획과 달리, 사용자가 승인하지 않은 외부 계정 로그인, 공지 게시, 채팅 송신, 실제 OBS 방송 시작/녹화, 유료 API 결제, 외부 자산 다운로드, 권리 없는 타인 음성 학습을 **검증을 핑계로 임의 실행 금지**.
- 코드를 실제 GitHub main에 안전하게 반영하고 GitHub Actions에서 **Windows EXE 빌드, 실제 GUI 생성·종료, 전체 회귀검사, 가능한 현장 공개 읽기 전용 OBS/Ollama/채팅 검증**을 확인할 것.  Linux 단위검사를 Windows 실사용자 검증이라고 주장 금지.
- **실사용자 단계 검증만 완성의 근거**: 사용자가 EXE 실행→버튼·캐릭터·채팅→실제 AI→한국어 TTS→실제 Live2D 입→OBS 화면/음성까지. 단위/모의검사와 Windows Actions 자체검사는 이 전체 사용자 흐름을 입증하지 않음.

## 4. 개발 누적 완료/수정된 범위 (실제 기능 전체 성공 주장 아님)

다음은 2026-10-19 이전/당일 기존 main에 누적 반영된 대표 항목. **다음 실행에는 실제 소스에서 재확인**:

1. 기존 Tk Windows 데스크톱 UI, 캐릭터 저장/SQLite 기억/로컬 Ollama 응답 및 GUI 회귀검사 유지.
2. CHZZK/SOOP/Twitch 공개 실제 채팅 읽기 전용 프로토콜. SOOP 채팅방 JOIN 승인, 장시간 PING, 0005 메시지 원문/중복 보존, 송수신 상태 진단. 시청자 많은 공개 방송 검증에서 실제 0005 메시지 수신 확인.
3. YouTube `liveChatId` 직접 입력 + 공식 생방송 영상 11자리 ID/HTTPS youtube.com/watch, youtube.com/live, youtu.be 주소로 YouTube Data API `videos.list liveStreamingDetails.activeLiveChatId` 조회 후 `liveChat/messages` 페이징. API 키는 메모리에서만, 오류에 비밀 값 노출 금지. 영상 ID 조회/응답 형식 단위검사 완료; **실제 소유한 키/실방송 수신은 미실증**.
4. 플랫폼별 모든 수신 중복 채팅 FIFO 처리 및 로컬 Ollama 또는 단일 공식 Live2D 세션 전달(서로 중복 호출 금지), 연결 재시작 시 이전 세션 이벤트 무시, 읽기 중지 시 대기 중인 AI 요청·늦은 응답 차단, 채팅 원문 공백 보존.
5. 대량 채팅 GUI 처리 128건 단위 이벤트 배치, 큐 순서/중복 보존 회귀검사(현재 코드에서 재검증할 것).
6. 권리확인된 GPT-SoVITS의 일회성 실제 WAV→OBS 미디어 소스 검사 코드(실제 모델 실행은 별도). OBS 송출/녹화 중 금지, 합성 사이 장면/송출/녹화 상태 반복 확인, 임시 소스 정리 및 RPC 응답 유실 시 정리검사, 무한 looping 금지.
7. 공식 Open-LLM-VTuber Live2D Windows WebView2 child 및 인증 IPC 입력/입 움직임 RMS·mouth 신호 관찰 코드, 임의 숫자를 실제 립싱크라고 위조하지 않는 검증 조건. 실제 공식 모델에서 관찰값을 읽어 입 움직임이 증명될 때만 성공 표기.
8. 과거 테스트/개발 브랜치 이력 보존 + 실제 코드 main 고정, main에 GitHub Windows Actions 빌드 지원.

## 5. 마지막 확인된 자동 검증 — 정확한 증빙

**코드 기준 SHA**: `191ab786b5b50833fea188174184fa6a98209465`

- 전체 회귀검사: https://github.com/junggyeol4444/AISTING/actions/runs/39215378365 → **success**. 실제 로그: `Ran 2331 tests`, `OK (skipped=2)` (즉 실행된 2,331개 가운데 2개 건너뜀; 전부 실제 기능 완성 의미 아님).
- Windows 5개 Actions 작업: https://github.com/junggyeol4444/AISTING/actions/runs/39215378267 → **success**, 각각 `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly` 성공.
- 2026-10-19 위 검사에서 실제 공개 읽기 전용 수신 결과: 치지직 126건, SOOP 44건 (개별 실행 상황에 따라 메시지 수 달라짐). Twitch 공개 읽기와 로컬 Ollama/OBS 검사도 통과. **이 채팅 각각에 대해 AI가 말하고 공식 Live2D 입을 움직였다는 결과는 아니다**.
- Windows Actions 생성 EXE ZIP artifact: `AISTING-Windows-EXE-integrated`, artifact ID `12169686284`, 약 19,606,989 bytes, GitHub artifact digest `sha256:f595adc1623d627e36e42f8b2cc91c294a65d82b975907927612738df535296a`, 당시 만료예정 `2026-11-18T07:22:30Z`. 모든 링크/해시는 다음 실행 시 최신 run으로 갱신.
- 마지막 Windows EXE는 실제 disposable Windows runner에서 빌드·자가검사·Tk GUI 생성/종료 확인. 사용자 Windows PC 실사용 테스트 **아님**.
- 이전 실패 기록이 있어도 최신 커밋에서 성공했다고 확인됐을 때만 성공 표기. 최신 코드 변경 이후 옛 실행의 success를 새 버전의 검증으로 재사용 금지.

## 6. 반드시 남겨둘 미완료·미검증

1. 사용자 키/채팅방을 이용한 실제 YouTube 생방송 채팅 수신·페이징·초당 메시지 검증.
2. 실제 사용 승인된 참조 한국어 음성 + 로컬 GPT-SoVITS 모델로 **실제 한국어 WAV 생성**, 언어/음색 품질 및 파일/재생/오디오 장치 확인.
3. 사용자 공식 Live2D 모델의 실제 Cubism 입 움직임(실제 오디오 RMS와 입 파라미터 동시 변화를 측정), 장시간 오디오 연결, 입/말 동기.
4. 채팅(각 플랫폼)→지속 캐릭터 메모리 포함 실제 AI→한국어 음성→Live2D 영상→OBS 오디오·영상 출력까지 한 사용자 EXE 작업 흐름의 실제 검증. OBS가 켜져 있다고 실제 방송 송출 성공이라는 뜻은 아님.
5. 방송 시작/종료/중단 재개·에러 복원·장시간 24h 안정성, 실제 수백명 동시 채팅 큐/메모리/지연, 사용자가 원하는 반응 시간(1~3초)을 실측하기 전까지 미완료.
6. 앱 `config/roadmap.json` 공식 010 승인과 011~100 원본 단계는 별도 사용자 승인 없는 한 `pending` 유지. 실제 완료 증빙 전 완료율 임의 계산 금지.

## 7. 다음 예약 실행에서 묶어서 해야 할 실제 작업

1. `git/ref/heads/main`과 최근 커밋 비교, 오늘 문서 이외 추가 코드 변경이 있었는지 확인. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 실제 src/tests/GitHub Actions 읽기.
2. 위 미실증 기능(YouTube 종료/재접속/중복, Live2D IPC 안정성 및 실제 관찰, GPT-SoVITS WAV/OBS 정리·장면/녹화 상태, FIFO chat→AI 중지/복원/고부하)을 적어도 2~3개 함께 코드/회귀 개선. 로그인이나 사용자의 PC 필요 작업은 실제 실행하지 않은 것으로 따로 분류.
3. GitHub main에 안전하게 단일 또는 소수 의미 있는 묶음 커밋 반영(강제 푸시/브랜치 생성 금지), 전체 회귀 통과 및 Windows native EXE+Tk GUI 검사, 가능한 실제 공개 채팅과 읽기 전용 연결 검사 모두 확인. 실패 수정 후 동일 main에서 재검증.
4. 매 작업마다 완료/진행/불가 항목 분리해 보고. 본 인계 문서 내용을 누적 갱신하고 다음 실행에 필요한 실수 없는 명시적 경로·SHA·artifact/run 상태를 남김.
5. **원래 대화 우선**, 다른 대화로 결과가 표시되면 원래 대화가 아닌 플랫폼 한계를 고지하고 이 문서에 근거해 연속 개발; 사용자에게 파일·지시를 다시 달라고 하지 말 것.

## 8. 주의: 이 문서와 예약의 한계

예약은 ChatGPT 플랫폼의 반복 요청 기능이다. 프롬프트에 '원래 대화에만 표시'를 명시했더라도 플랫폼의 대상 대화 선택·컨텍스트 제한·실행 시간·외부 권한을 기술적으로 보장할 수 없다. 그래서 **실제 GitHub main 인수인계 문서**를 영구 단일 복원 지점으로 유지한다. 문서에 적힌 과거 SHA가 후속 docs 수정으로 이동했으면 **실제 원격 main HEAD를 권위 있는 최신 소스로** 취급하고, 날짜/코드/CI 기록을 대조한다. 기록을 읽지 못하면 모른다고 밝힌다.

## 9. 2026-10-19 추가 묶음 개발 및 실 Windows 검증 — 515f952d

- **코드 변경 기준 `main` 커밋**: `515f952dd4061ba9f1b0691337ae524134113948` (이 인수인계 문서를 갱신하는 추가 docs 커밋은 별도; 후속 회차는 반드시 새 `main` HEAD를 재조회).
- **실제 변경된 실행 소스**: `src/ai_broadcaster/desktop_chat_tab.py` 및 `src/ai_broadcaster/multiplatform_readonly.py`. **검증 파일**: `tests/test_aisting_twitch_ai_integration.py`, `tests/test_aisting_multiplatform_readonly.py`. 이전 파일을 지우거나 기존 전체 앱을 바꾸지 않았다.
- **채팅 수신 종료 후 AI 결과 유실 수정**: 사용자가 Stop을 누른 것이 아니라 서버 EOF/연결 오류/유튜브 방송 종료로 수신만 종료한 때에는 이미 GUI에 접수한 채팅이 AI 큐에 남아 있는 한 기존 세션을 유지한다. 원래 FIFO 수신 순서와 중복 텍스트를 보존하고, 단일 AI worker가 처리 완료 마커 `twitch_ai_finished`를 보내야만 GUI 연결 버튼을 복구한다. `twitch_finished`와 `twitch_ai_finished`는 서로 다른 이벤트다. 실제 사용자 Stop은 즉시 `_stop`을 세워 나머지 요청을 처리하지 않고, 이미 reader EOF 후 AI drain 중에 Stop을 눌러도 버튼과 상태를 복구한다. 세션 교체 후 오래된 AI 결과는 표시·카운트·발화 금지.
- **치지직 초반 채팅 보존**: `ChzzkReadOnlySession.run()`이 실제 인증 ACK `10100`을 기다리는 동안 도착한 정상 채팅 `93101/15101` 전체를 임시 FIFO에 보관하고, 채팅방 승인 후 `ready` 이벤트 다음에 정확히 1회씩 전달한다. 승인 전 임의로 사용자에게 실연결 완료를 표시하지 않으며, 운영자 Stop 중 소켓 예외는 자연스러운 종료로 처리한다. 타인 채팅 송신 없음.
- **유튜브 API 개선**: 무효한 `pollingIntervalMillis`는 채팅 이벤트를 전달하기 전에 차단해 같은 과거 페이지가 재연결 시 반복 처리되지 않도록 함. 0초로 지정한 검사에서는 외부 API 요청을 호출하지 않는다. API 키는 기존처럼 RAM에서만 사용하고 오류에서 노출하지 않음. 실제 사용 키의 YouTube 채팅 수신은 여전히 미실증.
- **GitHub 전체 회귀검사**: https://github.com/junggyeol4444/AISTING/actions/runs/39217707352 → `completed/success`, 2,337개 실행, 2개 skip, 실패 0. 새 테스트: 수신 종료 전후 미처리 AI 결과 3건 및 중복 FIFO 카운트/상태, EOF 후 Stop, worker 완료 마커, 인증 전 CHZZK 메시지, 잘못된 YouTube polling 및 0초 요청 방지. 단위검사는 실제 모델·립싱크 시청각 전 구간의 증거가 아님.
- **같은 코드 SHA의 실제 GitHub Windows 통합 검사**: https://github.com/junggyeol4444/AISTING/actions/runs/39217707329 → `completed/success`, `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly` **5개 job 모두 success**. 실행 로그의 공개 읽기 전용 실제 치지직 `203`건, SOOP `37`건(실제 SOOP 채팅방 JOIN ACK 확인·WebSocket 프레임 2,254건). OBS 검사/EXE 실행·자가검사/Tk GUI 생성·종료 확인은 실사용 방송 출력과 다름.
- **Windows Actions 산출물**: `AISTING-Windows-EXE-integrated`, artifact ID `12170052488`, 19,613,938 bytes, GitHub artifact digest `sha256:fb093189543b980a974a730f6536704342e0c1651061379ecc0090984a37a3a1`, 만료 `2026-11-18T07:44:06Z`. 접근은 위 Windows Actions 링크의 Artifacts에서 한다. 로컬 임시 sandbox 경로를 검증 없이 제시하지 않는다.
- **한계/반드시 미완료 유지**: YouTube 실제 채팅 키/실방송, 사용자 권리 확보된 GPT-SoVITS 한국어 WAV·음색, 공식 Live2D 실제 Cubism mouth-RMS 동기화, OBS 오디오·영상 전 구간 및 방송 직전 사용자 흐름, 장시간 및 100~500명 구간 동작과 1~3초 지연 실측은 검증하지 않았다. 로컬 사용자의 PC 전원이 꺼져 있을 때 이 기기에서 실제 음성·화면이 실행됐다고 주장하지 않는다. 원본 100단계 승인/보류 및 캐릭터/SQLite/사용자 데이터 유지.
- **다음 회차 구체적 우선 묶음**: (1) 채팅 서버 비정상 종료·중지·재연결 경계에서 AI 큐/GUI 상태 실사용 E2E 보강, (2) 원본 공식 Live2D IPC와 GPT-SoVITS 실제 WAV·OBS 상태/임시 소스 정리/검사 과정을 추가 감사 및 코드 결함 수정, (3) YouTube API 실제 실방송 소유키가 없으면 사실대로 불가로 남기되 관련 예외·페이징·Stop 및 비밀값 보호 회귀 보강, (4) main 최신 SHA 기준 Windows EXE/전 GUI 회귀 및 실제 공개 읽기 검사를 한꺼번에 수행하고 본 문서 갱신. 새 브랜치/앱을 만들지 않는다.
- **대화 유지 규칙**: 이 예약이 생성된 원래 AISTING 대화를 최우선으로 진행한다. 다른 대화가 불가피할 때는 본 문서를 첫 단계로 정독하고 최신 `main`을 읽어 누락 없이 인수받는다. 다른 대화에 게시됐다는 사실이나 원래 맥락을 이용할 수 없다는 한계를 숨기지 않는다.


## 10. 2026-10-20 08시 이후 실제 main 개발 재개 — Twitch 코드·회귀 테스트 반영

**원래 예약 생성 대화 유지가 최우선**. 본 인수인계는 같은 AISTING 대화에서의 연속 작업 기록이며 다른 대화로 옮기는 요청이 아니다. 플랫폼이 다른 대화를 선택할 때만 본 문서에서 복원한다. 기존 매시간 예약 시간과 다른 프로젝트 예약은 변경하지 않았다.

### 실제 원격 코드 변경 (기존 네이티브 Windows 소스 유지)

- 원격 저장소: `junggyeol4444/AISTING`, 브랜치: `main`만 사용. 새 브랜치 생성·삭제, 강제 푸시, 초기화·재개발 없음.
- 직전 실제 코드 SHA: `e6653ad82fef906abdee5001153544964940b00a`.
- **수정 코드 커밋**: `c6f110219ce8a4d0158694f54a686083667b1f0f` — `src/ai_broadcaster/twitch_readonly.py`. 이전 로컬 준비 패치의 주요 오류를 원본 소스에 적용: 중복 run 차단, Stop/네트워크 핸드셰이크·IRC 명령 송신 경합, 대량 메시지 프레임의 반복 스캔 개선, 다른 채널 JOIN 366 응답 거부, viewer 텍스트에 포함된 NOTICE/366 오인 방지, PING 응답 및 소켓 닫기 오류 처리. 
- **회귀검사 추가 커밋**: `9f3ac2352ad374be1a727cb70986537186982393` — `tests/test_aisting_twitch_regression_20261020.py`. 10,000건 중복 포함 FIFO, JOIN 오인, 일반 채팅의 로그인 거부 문구 오인, 동시 실행, 무효 제한시간, 종료 소켓 예외 검증 6개. 사용자 PC나 계정에 접속하지 않는 메모리 소켓 테스트.
- 위 코드는 2026-10-20 08시 현재 실제 GitHub main에서 반영된 커밋이다. 과거 08:10 로컬 후보 패치는 전체 코드와 동일한지 반드시 파일/해시 비교 후 처리하고 **중복 적용 금지**. 반영하지 않은 과거 후보 테스트는 완료로 주장하지 않는다.

### Actions·실제 검증 범위

- 첫 소스 수정 기준 GitHub 회귀검사 https://github.com/junggyeol4444/AISTING/actions/runs/39343342935 : `completed/success` 확인.
- **최신 회귀검사** https://github.com/junggyeol4444/AISTING/actions/runs/39343436381 : `completed/success` 확인. 실제 실행 테스트 수는 작업 로그를 보고 확정할 것.
- **최신 Windows EXE·공개 읽기 전용 통합검사** https://github.com/junggyeol4444/AISTING/actions/runs/39343436352 : 문서 작성 시 `in_progress`. `windows-exe`, `obs-real-readonly`, `ollama-real-local-e2e` 작업 진행 중; Twitch/치지직/SOOP 공개 읽기 전용 잡은 `success` 확인. **전체 PASS 또는 새 EXE Artifact/해시를 결과가 나올 때까지 확정하지 말 것.**
- 이전 최종 성공 산출물 (구 코드 e6653ad 기준): Windows https://github.com/junggyeol4444/AISTING/actions/runs/39325998387; artifact `AISTING-Windows-EXE-integrated`, ID `12222486498`, GitHub artifact ZIP SHA-256 `e5255fae9b28693bedbd1d58af990720ee81ee5dfee529ad6ee6f5975f19b4d3`. **새 코드의 산출물이 아님**.

### 사용자 원래 기획·자료와 금지사항 재확인

- 위 문서 1~9절의 **사용자 원문 기획** `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 우선. 기존 AISTING.exe/Tk·캐릭터 1회 저장·SQLite·설정·사용자 파일 변경/파괴 금지. 중복 메시지 포함 모든 채팅 FIFO. 공식 Open-LLM-VTuber·Live2D, 권리 확보된 GPT-SoVITS 실제 한국어 음성, OBS 출력 목표. 원본 승인 단계 임의 completed 변경 금지.
- 사용자 요청 없는 계정 로그인·유료 API·실제 방송/녹화 시작·채팅 게시·외부 송신·사용자 PC 제어·모델/음성 무단 다운로드·권리 없는 학습·새 웹 앱/프로젝트 금지.

### 반드시 계속 미검증으로 남길 항목

1. 소유/동의 확인된 YouTube API 키와 실제 라이브 채팅 수신·페이지 커서 실증은 아직 안 됨.
2. 승인된 한국어 음성 참조 파일과 GPT-SoVITS 실제 모델 추론, 한국어 실제 WAV·음성 품질 실증은 아직 안 됨.
3. 공식 Live2D 모델에서 실제 WAV RMS와 Cubism 입 움직임을 같은 세션에서 확인하고 OBS 출력까지 엮는 사용자 버튼 흐름은 아직 안 됨.
4. 전체 EXE→저장 캐릭터→공개 채팅→AI→한국어 합성→공식 입 동기→OBS 음성+영상 실제 출력, 24시간 연속/수백명 부하·지연 실측은 아직 안 됨. Windows CI 빌드/OBS 읽기 검사와 혼동 금지.
5. 08:10 로컬 Twitch 42개 검사 후보 ZIP은 이전 대화의 별도 자료이며, 이번 main에 전부 업로드한 것으로 주장 금지.

### 다음 실행에서 묶어 처리할 작업 (복수 작업)

1. `main` 최신 HEAD/Docs SHA/CI 최신 결과를 다시 확인하고 위 Windows run이 최종 success인지, 실제 EXE artifact ID·해시를 교체 기록.
2. 남아 있는 Twitch 오프라인 후보와 이번 main 코드를 비교하여 누락된 수신/재접속·Stop 관련 필수 회귀만 선별 반영. 이전 파일을 무조건 중복 덮어쓰기 금지.
3. `original_plan_tts.py`, `original_plan_frontend.py`, `original_plan_voice_obs_bridge.py`, `desktop_chat_tab.py` 실사용 사용자 흐름의 연결 결함을 실제 소스 수정·테스트하는 묶음 작업. 인증·승인·실제 파일·모델이 없는 기능은 미실증으로 분류.
4. 기존 설정/SQLite/캐릭터 보존과 Stop/GUI 확인을 포함해 실제 Windows Actions 재검증 후 본 문서에 **최종 docs 커밋 SHA**, 소스 SHA, CI 링크, 새로운 EXE artifact 및 남은 일을 갱신.

### 최종 확인 업데이트 — 2026-10-20 08시 이후 검증 완료

- 소스/6개 신규 검사 커밋 `9f3ac2352ad374be1a727cb70986537186982393`: 전체 회귀검사 https://github.com/junggyeol4444/AISTING/actions/runs/39343436381 `completed/success`; 실제 로그 `Ran 2347 tests`, `OK (skipped=2)`, 실패 0.
- 동일 코드 Windows 통합검사 https://github.com/junggyeol4444/AISTING/actions/runs/39343436352 `completed/success`, 다섯 job 모두 success. 빌드/GUI, 실제 로컬 Ollama, OBS 읽기 전용, Twitch 공개 읽기, 치지직·SOOP 공개 읽기. **사용자 계정의 YouTube 채팅 또는 GPT-SoVITS·Live2D 실제 입·OBS 송출까지 검증한 결과가 아니다.**
- 문서 갱신 커밋 `f52fc64e986c7d8f58955d434cdc6ecf8a53a5f9`를 기준으로 실행된 전체 회귀검사 https://github.com/junggyeol4444/AISTING/actions/runs/39343746818 `completed/success`, Windows https://github.com/junggyeol4444/AISTING/actions/runs/39343746794 `completed/success`. 동일 코드에 docs만 추가. Windows 5개 job 성공.
- **최신 Windows artifact**: `AISTING-Windows-EXE-integrated`, ID `12229534865`, 19,619,595바이트, GitHub artifact **ZIP** SHA-256 `9c80f299705cd8b9eaedb0edf1567f4473bbbf07458d9a5660671ac44113ec19`, 만료 예정 2026-11-18. EXE 자체 SHA-256과 혼동 금지. 페이지 https://github.com/junggyeol4444/AISTING/actions/runs/39343746794
- 기재된 코드 수정은 실제 `main` 반영 완료. **핵심 미실증 항목**: 사용자 YouTube 실제 인증 채팅, 승인된 모델/권리 확인 WAV 기반 GPT-SoVITS, 공식 Cubism 실제 오디오-입 동기, AI→한국어 음성→Live2D→OBS 전체 실출력, 장시간 실사용. 사용자가 제공하지 않은 계정/실물 모델/Windows PC를 이 회차에서 실행하지 않았다. 원본 기획 승인·SQLite/캐릭터 자료는 변경하지 않았다.
- 최신 `main` HEAD는 문서 업데이트로 다시 이동하므로 다음 실행에서 GitHub `branches/main` 확인 필수. 원래 예약 대화 유지 희망, 불가피하면 본 문서와 누적 코드/CI를 먼저 읽고 이관 사유 명시. 매시간 예약은 변경하지 않음.

## 11. 2026-10-20 08시 이후 실제 YouTube 채팅 누락 수정·전체 검증

- 사용자 지시대로 기존 Windows x64 네이티브 AISTING.exe/Tk UI의 누적 src를 수정. 다른 브랜치/재개발/강제푸시/사용자 파일·SQLite·캐릭터 변경 없음. 원래 예약 대화 우선·매시간 예약 그대로.
- **실제 YouTube 수신 코드 커밋** `ad665d5ff971cc264e41a9e5da8e23264f814654`: `src/ai_broadcaster/multiplatform_readonly.py`의 `parse_youtube_page`에 공식 YouTube `memberMilestoneChatEvent` 포함. 기존 채팅/슈퍼챗/슈퍼스티커 동작 보존. 공식 Google API 설명은 해당 항목을 '사용자가 전송한 멤버십 기념 채팅'으로 명시한다. 정상 메시지 순서·중복을 제거하지 않음. 계정 인증이나 YouTube API 요청은 실제 실행하지 않음.
- **신규 검사 커밋** `e7bdff5ef33568c2597a74b5793351735c1b8900`: `tests/test_aisting_youtube_member_chat_20261020.py` 추가. 멤버십 기념 메시지 + 일반 채팅 + 중복의 FIFO, 채팅 종료 이벤트와 실제 시청자 채팅 구분 2개.
- **최종 실행 코드 SHA** `e7bdff5ef33568c2597a74b5793351735c1b8900`. GitHub 전체 회귀검사 https://github.com/junggyeol4444/AISTING/actions/runs/39344244993 **completed/success**. 실제 로그 `Ran 2349 tests`, `OK (skipped=2)`, 실패 0. 테스트는 오프라인·단위 위주이며 실제 사용자 음성·모델 성공 근거가 아니다.
- 같은 SHA의 Windows 통합검사 https://github.com/junggyeol4444/AISTING/actions/runs/39344244950 **completed/success**. `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly` 5개 작업 모두 success. 사용자의 로컬 실사용 전체 연결 테스트가 아니다.
- 새 Windows Artifact `AISTING-Windows-EXE-integrated`, ID `12230730515`, 19,620,228바이트. GitHub Artifact ZIP SHA-256 `c3f9bbf77c549fa7e255e45fdb0720678ad8e3fead24488843f10949ae1dd198`. **이 해시는 EXE 자체가 아니라 Actions ZIP artifact의 해시**. Windows run 페이지의 Artifacts에서 다운로드.
- 아직 미실증: 실제 사용자 YouTube API 키/채팅방 수신·키 보안 확인, 권리 확보 한국어 GPT-SoVITS 실제 음성, 공식 Live2D 실제 오디오↔입 파라미터 동기, GPT 한국어 음성→Live2D→OBS 영상/오디오 송출 전 전체 사용자 흐름, 사용자 실제 Windows PC UI 체험, 24시간/수백명 지연 실측. 모델·인증·권리 있는 자료가 없어 실제 성공으로 주장하지 않는다.
- 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 본 문서 1~10절의 사용자 필수·금지사항은 계속 유효. 공식 단계 임의 완료 처리 금지.
- 다음 실행: **main HEAD/CI/진행 중 job 재조회** → 누락된 Twitch 누적 후보와 현재 main 세부 비교(중복 적용 금지) → 공식 GPT-SoVITS/Live2D/OBS 실제 연결 코드의 누락·오류 함께 개선 → 원래 Tk 실행흐름/저장자료 보존 Windows 실행 검증 → 새로운 artifact/해시 및 전체 인수인계 재갱신. 실제 자료·실행 환경 없는 검증은 명시적으로 미실증 유지.
- 문서 업데이트 자체가 main SHA를 변경한다. 현재 실제 소스 기준 SHA와 문서 커밋 SHA를 구분하여 다음 회차에서 반드시 최신 HEAD 재확인.

## 12. 2026-10-20 사용자 항의 후 핵심 실연결 개발 — 공식 Live2D + OBS 동시 관찰 모듈

**사용자 피드백**: "최신 SHA를 굳이 왜 보며, 남은 실제 개발을 왜 안 하느냐". SHA는 내부 버전 충돌 방지용 식별값이지 기능 개발 성과가 아니다. 앞으로 매 실행 SHA 조회에 시간을 과소비하거나 반복 오프라인 채팅 검사를 핵심 기능 완성으로 포장하지 말 것. 미완료인 한국어 TTS·Live2D·OBS 실제 연결을 최우선으로 할 것.

### 기존 원본 기획/금지사항 그대로 유지

`docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 Tk 네이티브 Windows EXE, 저장된 캐릭터 이름·말투·성격, SQLite·설정 및 다른 사용자 자산 보존. 새 브랜치·강제푸시·원본 원복·대체 웹앱/HTML앱·유료 API·권리 없는 음성·계정 로그인·채팅 게시·사용자 PC 접속·실제 방송/녹화 시작 금지. 모든 채팅 FIFO/중복 보존. 예약 매시간 변경 금지, 원래 대화가 가능하면 원래 대화에서 이어가고 플랫폼이 다른 대화로 표시하면 본 GitHub 문서로 인수인계.

### 이번에 실제 main에 반영된 코드와 검증

- `aa96cf6841bfe4aeca3ed185176857867ac1e1e3`: `src/ai_broadcaster/original_plan_full_pipeline.py` 신규 모듈. 기존 Open-LLM-VTuber Live2D 동일 세션 질문/실제 RMS·입 동기 읽기와 OBS 실제 프로그램 화면/선택된 음성 입력 경로·미터를 **동시에** 검사하는 구현. 호출 시 운영자의 해당 실행 승인 + 음성 사용 권리 확인 필요; 기존 OBS input / 장면 경로를 먼저 읽고, 송출 중이면 실행 거부; 방송 시작/녹화/소스 생성/외부 채팅 전송/음성 훈련 없음. OBS 후보 미터와 립싱크가 확인되어도 실제 방송 인코더/시청자 전송을 증명하는 것은 아니라는 엄격한 판정. 질문 중복 자동 재전송 없음.
- `c979099b0d18a3ff22e539e19fdf2832d1d320a8`: `tests/test_aisting_official_chat_obs_pipeline.py` 신규 6개 검사. 권리 및 명시 승인 누락 차단, 기존 공식 세션 단일 질문/OBS 읽기 전용 1회, OBS 경로 미확인 시 질문 중단, 립싱크 신호 없을 때 미검증, OBS 미터 경로 불안정 시 미검증, 전송 중 오류 시 중복 재시도 방지.
- **최신 실행 소스 검증 URL**: https://github.com/junggyeol4444/AISTING/actions/runs/39346093869, 상태 `completed/success`, 실제 로그 `Ran 2355 tests`, `OK (skipped=2)` (실패 0). 이 결과는 단위/오프라인 검사; 실제 모델을 실행한 E2E의 증거가 아님.
- 같은 소스 Windows 워크플로: https://github.com/junggyeol4444/AISTING/actions/runs/39346094191, `completed/success`. 기존 실제 Windows EXE/GUI, Ollama 로컬 추론, OBS 읽기 전용, Twitch, 한국 플랫폼 공개 채팅 체크 job 5개 모두 성공. **이번 신규 동시 관찰 모듈의 Windows GUI 버튼 실행은 하지 않았다.**
- 새 빌드 artifact: `AISTING-Windows-EXE-integrated`, artifact ID `12230613210`, size `19,618,995` bytes, Artifact **ZIP** SHA-256 `b7dcd9a5345be996d747d64b4b16fbce76ab22f37e5c659745875b7ebbe33046`. 실행 EXE 자체 해시가 아님.
- **중요: 미완료**: 기존 `src/ai_broadcaster/original_plan_studio.py`의 실제 Tk GUI 버튼으로 위 동시 관찰 모듈을 연결하려는 파일 수정은 GitHub 안전 검사에서 차단됨. **새 모듈은 main에 존재하지만 기존 프로그램 GUI에서 원클릭으로 실행하는 연결은 아직 반영되지 않았음.** 이 사항을 숨기거나 GUI 실사용 성공으로 표시하면 안 된다. 거대한 소스 파일의 변경 요청이 차단됐으며, 우회·브랜치·강제푸시는 하지 않았음. 작은 GUI 변경을 허용 가능한 정상 도구로 다시 수행할 수 있을 때 실제 클릭→검증 이벤트의 연결을 완성할 것.
- **여전히 실제 미실증**: 사용자 소유 키를 사용하는 YouTube 실제 라이브 채팅, 권리 확인된 GPT-SoVITS 한국어 실제 모델·음질, 공식 Cubism/오디오 동기 실제 세션, OBS 전체 프로그램 영상·음성의 연속 출력 및 사용자 EXE 버튼, 실방송 전 최종 검수, 24시간 안정성과 100~500명 부하. 외부 모델/승인된 자산을 임의 설치·다운로드·훈련·로그인하지 말 것. 녹화 및 방송 시작 금지.

### 바로 다음 회차에서 해야 할 묶음 작업

1. 원본 GUI `OriginalPlanStudio._open_real_ai_chat`에 **승인 시에만** 동시 관찰을 실행하는 버튼·OBS 기존 입력 이름/비밀번호 RAM 입력·결과 이벤트와 fail-closed 처리 연결. 기존 GUI 크기/화면 동선을 유지하고 승인·캐릭터·SQLite 게이트를 그대로 적용. 이번 회차 GUI 수정 시도가 **차단돼 미완료**였음을 기준으로 이어서 완성할 것.
2. 실제 GPT-SoVITS TTS 구성/실제 WAV→기존 Live2D 동일 세션→OBS 프로그램 미디어 확인의 기능상 누락/레이스/실패 처리 동시 보강. 필요한 모델/자산/동의 없으면 통과로 주장 금지.
3. YouTube 실제 인증 연결은 사용자 소유 키 없이 실행 불가로 남기되 페이징, 중복, 종료 및 멤버십 메시지 보존의 기존 main 코드를 감사/수정하고, 네 플랫폼 FIFO 처리 및 캐릭터 재시작 지속성도 함께 확인.
4. 기존 GUI EXE Windows 빌드·실제 화면/버튼 사용자 경로·회귀 워크플로 검증, 오류 재수정, 원격 `docs/AISTING_HOURLY_FULL_HANDOFF.md`와 결과/아티팩트/남은 일의 누적 갱신. 기존 성공한 공개 읽기 검사만 되풀이하면서 핵심 기능 작업을 뒤로 미루지 말 것.

GitHub repo `junggyeol4444/AISTING` main 고정. 이번 코드 기준 커밋 `c979099b0d18a3ff22e539e19fdf2832d1d320a8`; 인수인계 문서 커밋 이후 실제 HEAD는 다시 달라지므로 다음 실행에서 내부적으로 확인만 하고 개발에 집중. 원래 AISTING 예약 생성 대화를 유지, 대화가 플랫폼 제한으로 불가할 때 반드시 본 문서를 우선 읽을 것.

## 13. 2026-10-20 현 회차 — 실제 네이티브 Tk 버튼 연결 및 OBS 상태 경합 수정

### 사용자가 지시한 우선순위 및 준수사항
- SHA 조회·해시 반복·Twitch 단위검사만으로 시간을 쓰지 않고 **남은 실사용 기능 개발**을 진행하라는 지시. SHA는 기존 main/문서 원복과 중복 수정을 막기 위해 내부에서만 확인한다.
- 기존 Windows 10/11 x64 AISTING.exe / Tk GUI / 원본 100단계 설계 / 기존 Live2D + GPT-SoVITS + OBS 연결 코드 / 네 플랫폼 모든 채팅 중복 포함 FIFO / 저장 캐릭터 / SQLite / 설정 무손실 보존.
- 브랜치 생성/삭제·강제 푸시·새 앱/웹/HTML 대체·실제 방송/녹화 시작·채팅 게시·사용자 PC 연결·계정 로그인·유료 API·권리 없는 음성 훈련 금지. 실제 Live2D·음성·OBS 전체 사용 확인 없으면 통과라고 주장 금지.
- 원래 예약 생성 대화에서 가능한 한 계속 작업하고, 불가피한 대화 이동 시 본 문서와 GitHub main, 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`를 먼저 읽고 모든 정보를 넘길 것. 기존 매시간 예약·다른 프로젝트 예약은 변경·종료하지 않음.

### 실제 반영된 이번 코드/테스트 커밋 (원본 보존)
1. `8bbe07cc39d17b4d57ea67b619d4719fd7262a8c`: `src/ai_broadcaster/desktop_chat_tab.py`. AISTING 기존 네이티브 로컬 채팅 탭에 **승인 후 실제 공식 AI·Live2D·OBS 동시 검사 버튼**, OBS 음성 입력/암호 메모리 입력 및 실측 결과 UI 연결. 원래 공식 Live2D 창/실제 캐릭터 설정 정합성·디스크 확정 캐릭터 재확인 후에만 한 번의 질문을 기존 공식 세션에 보냄. 기존 앱의 대화·목소리·설정 보존.
2. `b0b462b1ccad1bd583de5809e43f91a97cd0122c`: `tests/test_aisting_gui_official_full_pipeline.py` 신규 7개 네이티브 UI callback 검사. 운영자 승인 취소/저장된 캐릭터 미확정/실제 모니터링 실행/오류 후 암호 비노출/증거 부족 시 성공 금지 등.
3. `6a5cd2ceb2d1f70a1651b0dced42b6b793c55140`: 위 GUI mock 회귀 fixture의 결함(가짜 Tk 객체에 `_poll` 없음) 수정. 그 전 run https://github.com/junggyeol4444/AISTING/actions/runs/39347778512 에서 이 fixture 오류 1건 발생, 후속 run https://github.com/junggyeol4444/AISTING/actions/runs/39347868199 `completed/success`로 해결. 오류를 숨기지 않는다.
4. `3e4f9167ee74a9db1523b433669661d9d35bea79` 및 `ad73f74719ee5c01691d2cbfea1033dcd3649718`: `src/ai_broadcaster/original_plan_full_pipeline.py`, `tests/test_aisting_official_chat_obs_pipeline.py`. OBS에서 방송/녹화가 진행 중이면 공식 AI 음성 요청 전 단계적으로 거부, 녹화 상태 확인 실패 시 fail-closed, 검증 전후 장면/녹화 상태 재확인. 신규 세 테스트.
5. `e9fc0cb913c3ddc1afab8cb45cf61e62d8fe0f5a`, `38f2e2e0128e57ff63c35009f9a52567c6480d83`, `4e57b8ecc166129278098d496e52e812b64c6252`: 위 동시 모니터링 연결은 OBS 별도 read-only WebSocket 사용(OBS 요청/응답 클라이언트 쓰레드 충돌 방지), 모니터 독립 연결 실패 시 prompt 차단, 2개 테스트 추가.
6. `59513623d77bc817b1915a96098b84ff8a9410f1`, `3f9145ae3e921c01ccf80f101ad8faaf7dce0664`: `src/ai_broadcaster/desktop_chat_tab.py`, `tests/test_aisting_gui_official_full_pipeline.py`. 수동 AI·Live2D·OBS 승인 검사 도중 다른 네 플랫폼 공개 채팅 수신이 자동 시작돼 동일 세션에 끼어들지 않도록 차단하고 테스트 추가.

### 검증·CI·윈도우 EXE
- 최신 회귀검사 (마지막 코드 커밋 기준): https://github.com/junggyeol4444/AISTING/actions/runs/39348615210 — `completed/success`. 실제 실행 `Ran 2368 tests`, `OK (skipped=2)`, 실패 0.
- 같은 코드 Windows EXE 통합 빌드·실 GUI/읽기 전용 실제 공개 채팅·로컬 Ollama/OBS 검사: https://github.com/junggyeol4444/AISTING/actions/runs/39348615319 — **본 문서 작성 전 마지막 조회는 pending**. 반드시 최종 상태·잡·Artifact ID/ZIP 해시를 다시 읽고 완료로 기록할 것. 이전 성공 artifact와 혼동 금지.
- 직전 원본 Tk 연결/녹화 검사 전 검증은 https://github.com/junggyeol4444/AISTING/actions/runs/39348178031 (성공). 최신 코드 Windows 성공 증거로 대체 금지.
- 신규 코드가 빌드 성공해도 실제 사용자 설치 Windows에서 권리 확인된 GPT-SoVITS 합성 WAV·공식 Cubism 동기 렌더/OBS 프로그램 영상·음성 전체 관찰을 직접 했다는 뜻은 아님.

### 그대로 남은 실증·기능
- 실제 운영자 YouTube Data API 키/활성 라이브 채팅 인증 수신, 플랫폼 실시간 복수 채널·100~500명 지연·장시간 운용.
- 권리 확보된 한국어 GPT-SoVITS 모델/참조 음성으로 합성 실제 재생, 공식 Live2D Cubism 실제 RMS·입 변화의 음성 동기화, OBS 프로그램 화면과 동일 입력 음성의 실행 환경 실측. **이번 회차는 운영자의 설치 모델/마이크/OBS에 접근하지 않았음**. GUI 버튼에 연결된 Python 코드는 실제 모델이 없으면 fail로 표시하며 가짜 PASS 없음.
- 신규 승인형 Tk GUI 버튼의 Windows CI는 GUI 생성/종료 검증 중심. 사용자가 버튼→모델→출력까지 동작하는 실기기 E2E **미검증**. OBS output encoder/시청자 전달을 증명하지 않음.
- 공식 server 설정이 외부/유료 AI로 향하지 않는지 사용자 확인 필요. 별도 계정 로그인을 시도하거나 모델을 무단 다운받지 말 것.

### 다음 회차 구체적 복수 작업
1. 신규 `main`의 Windows run `39348615319` 최종 jobs/실제 EXE artifact/해시 검증, 실패면 원인 코드 수정·전량 회귀.
2. Tk 연동 화면 1366x768 레이아웃/실제 버튼 클릭에 따른 상태 확인·닫기/중단/재진입, 확정 캐릭터→공식 설정 및 SQLite 무손실 지속성 검증.
3. 공식 AI 세션의 느린 GPT-SoVITS 음성/립싱크에 비해 OBS 미터 관찰이 너무 일찍 끝날 수 있는 타이밍 결함을 개선하고 실제 샘플 구간이 겹친 경우만 검증 표시. GPU/모델 없는 검사로 실음성 통과 주장 금지.
4. YouTube 활성 실채팅 키가 확보되지 않으면 미실증 유지, 페이징·중복·시스템 이벤트를 실제 공식 API 문서에 맞춰 점검. 네 플랫폼 FIFO 실제 수신 경로 및 긴 시간 큐·중단/재시작 검증.
5. 현 회차 최신 코드/원본 기획/각 Windows CI·Artifact 등 본 GitHub 인수인계에 누적 갱신. 예약 주기는 그대로 유지.

문서 갱신 시 GitHub HEAD는 다시 이동하므로 다음 회차에서 반드시 원격 최신 소스로 작업하되 사용자에게 SHA 자체를 성과로 강조하지 말 것.

## 14. 2026-10-20 — Windows 실제 OBS 화면 재검증 성공 및 최신 완성 경계

### 기존 명령과 작업 기준
이 대화에서 사용자는 "계속하라고" 지시했고, 최신 SHA·해시 중심 반복 보고를 지양하고 **남은 핵심 코드/실사용 검증에 집중**하도록 요구했다. 기존 원본 100단계, 저장 캐릭터/설정·SQLite 보존, 네 플랫폼 중복 포함 FIFO, Windows Tk/EXE, 공식 Open-LLM-VTuber·Live2D, GPT-SoVITS 한국어 음성, OBS 출력 목표는 그대로다. 새 브랜치/강제푸시/재개발/웹·HTML 앱·사용자 PC 접속/로그인/방송/녹화/채팅 게시/권리 없는 음성 훈련·유료 API 금지. 원래 AISTING 예약 생성 대화를 최우선으로 이용하고, 불가피하게 다른 대화에 표시될 경우 본 문서와 GitHub 소스/이력을 읽어 전체 인계하며 다른 프로젝트 예약이나 매시간 주기는 변경하지 말 것.

### 이번 회차의 뒤이은 수정과 원인
- 해당 원격 코드 변경: `5584c15851f11cffb32e673c5c50ad327ed998c6`, 파일 `.github/workflows/build-windows.yml`. 실제 Windows OBS 통합검사에서 OBS websocket 연결·입력 생성·현재 장면 PNG 수신은 성공했으나, 임시 색상 소스 설정 직후 OBS 렌더 PNG 차이 검사 `Real OBS source changed but OBS-rendered pixels did not`로 실패한 job 확인. **검사 PASS를 조작/무시하지 않고**, 최대 10회 1초 간격으로 다시 실제 OBS PNG를 관찰하도록 조정. 10초 내 픽셀이 바뀌지 않으면 동일하게 실패한다. 소스는 disposable CI OBS에서만 조작, 사용자 OBS/라이브 송출은 변경하지 않음.
- 최신 주요 코드/테스트 (위 13절에서 자세히 기록) `3f9145ae3e921c01ccf80f101ad8faaf7dce0664`, 기존 AISTING `desktop_chat_tab.py` 실제 native Tk 승인형 공식 AI·Live2D·OBS 동시 검사, 저장 캐릭터/공식 설정 확인, OBS 녹화/송출 상태 검증, OBS 안전 상태와 실제 미터 연결 분리 및 공개 채팅 중복 개시 차단. 이 코드는 main에 누적 반영된 것이지 실제 사용자 모델에서 전 기능을 통과한 것은 아니다.

### 최종 확인한 CI와 실행파일
- 기존 코드를 포함한 **최종 회귀검사**: https://github.com/junggyeol4444/AISTING/actions/runs/39348949679 — `completed/success`, 실제 로그 **2,368개 검사, 2개 건너뜀, 실패 0**. 소스/Tk 버튼·OBS 안전 경합 관련 모의·오프라인 검증을 포함.
- **최종 Windows 워크플로**: https://github.com/junggyeol4444/AISTING/actions/runs/39348949700 — `completed/success`. `windows-exe`, `korean-public-chat-readonly`, `twitch-public-readonly`, `obs-real-readonly`, `ollama-real-local-e2e` 5개 job **모두 success**. OBS 임시 색상 소스의 실제 픽셀 변화도 최종 PASS.
- 새 Windows Actions artifact: `AISTING-Windows-EXE-integrated`, id **12232700558**, 크기 **19,634,834 bytes**, GitHub artifact **ZIP** SHA-256 **0fc60e04a6d1e9e5ce63975a523ff3ec6592632764b25fb70f87abf3ec793e60**. 개별 EXE 해시 아님. 워크플로 Artifacts에서 확인.
- 문서 저장으로 추가 git commit가 발생하므로 다음 실행 시 `main`은 새 HEAD를 가진다. 위 검증은 실제 기능 수정/워크플로 코드에 대해 완료된 최종 소스 기준이다.

### 반드시 미완료로 유지할 항목
실사용 Windows PC의 버튼을 눌러 **권리 확보된 GPT-SoVITS 한국어 모델과 실제 음성→공식 Live2D 음성 동기→OBS 영상+음성 한 경로**가 입증됐다는 것은 아니다. 실제 YouTube 라이브 인증 수신, 장시간 실운용, 여러 플랫폼 동시 연결, 수백명 채팅의 실제 1~3초 처리도 미실증. GitHub CI에서는 승인되지 않은 계정·음성 모델·사용자 PC를 사용하지 않았고, 음성/렌더/OBS 완전체 E2E 성공으로 주장하지 않는다. 사용자의 원본 캐릭터/SQLite 데이터는 코드 수정 대상이 아니었다.

### 다음 실행에서 병행할 실질 작업
1. 사용자가 기존에 승인한 공식 Live2D/GPT-SoVITS/OBS 실행 환경이 접근 가능하면 Tk 수동 버튼→합성/립싱크/프로그램 프레임+입력미터까지 실제 측정해 실패 원인 수정. 접근 불가면 모의 테스트 결과를 실증으로 승격하지 않는다.
2. 원본 `original_plan_full_pipeline.py`의 공식 AI 응답 시간과 OBS 미터 실제 관찰 시간 중복 조건을 엄격하게 교차검증해 조기 관찰 종료가 발생하는 문제 개선.
3. 1366×768 원본 GUI에서 입력·승인 버튼·상태 표시가 실제로 보이는지와 중단/재진입·캐릭터 재시작 지속성·SQLite 데이터 보존 사용자 흐름 점검.
4. YouTube 실제 인증 데이터가 없을 때는 API 정책·커서/중복 유지에 대한 보존형 개발만 수행. 네 플랫폼 공개 읽기 및 실채팅 FIFO 오류를 다중 작업으로 수정.
5. 다음 CI 작업/새 EXE artifact 및 오류를 본 GitHub 문서에 계속 누적. 예약 시간·대화 유지 기준 불변.

## 15. 2026-10-20 10시 KST 연속 개발 — 한국어 음성 지연 관찰·실제 TTS 설정 보호

### ① 사용자 원문 지시/금지·원본 기획
사용자는 "계속" 작업을 요구. 핵심 미완료 기능인 **Windows 네이티브 Tk EXE의 실제 한국어 GPT-SoVITS→공식 Live2D 립싱크→OBS 음성/영상 연결**을 우선 개발하고, SHA 반복 조회/형식적 검사만 성과로 삼지 말 것. 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 본 인수인계 앞 절의 지시 유지. 브랜치 생성·삭제, 강제푸시, 이전 기능 원복, 새 웹/HTML 앱, 유료 API, 계정 로그인, 방송 시작·녹화·게시, 사용자 PC 접속, 권리 없는 음성 훈련 금지. 사용자 동의·실제 권리 없으면 실제 모델을 실행하지 말 것. 모든 채팅(중복 포함)을 도착 FIFO대로 처리. 원래 예약 생성 대화 유지 및 기존 1시간 예약/다른 프로젝트 예약 절대 변경 금지.

### ② 실제 완료 작업/반영 파일과 커밋
- `37ae467e28f4f599bef0ab95f1b32778e0530aae`, `da76b72e560ed9acfb7fd82c2f0408e3823f13e9` — `src/ai_broadcaster/original_plan_full_pipeline.py`: 기존 OBS 실제 입력 미터/프로그램 프레임을 공식 AI 질문 중 최대 6회 짧은 관찰 구간으로 확인하여 한국어 음성 합성 지연 시 **처음 8초 검사만으로 음성을 놓치는 문제**를 개선. 질문 시작 전 관찰 시간을 소진하지 않도록 Event 동기화. 실제 AI 질문 한 번만 전송하고 AI 응답 전에 모든 OBS 관찰이 먼저 끝나면 동시 검증 미완료 처리. 미터 신호/정상 경로 후보는 가짜 오디오 생성이나 실제 송출 인증이 아님.
- `23cd0b4f692fb59d0091a565cb69e7cdced64230`, `a4d1b815daff11af3b287cfaaa1ca9dd0c7b5aea` — `tests/test_aisting_official_chat_obs_pipeline.py`: 늦게 시작된 OBS 입력 신호의 뒤늦은 감지 및 조기 종료 실패 판정 회귀 2개, 실제 1~3초 블로킹 관찰을 반영한 deterministic mock 수정.
- **실수·복구 기록(반드시 유지):** `eda1d69d9322bc5acaf5d23e53f31b547bdea05e`에서 `src/ai_broadcaster/original_plan_tts.py`에 새 helper를 잘못 삽입해 파일이 비정상적으로 커졌음. 해당 실패 코드는 성과로 인정 불가. `70ef10d8b951356cf63b80464f8145016a2723f9`에서 **이 잘못 삽입한 파일만 이전 정상 바이트와 동일하게 복구**, 원래 GPT-SoVITS 소스 해시 `81627af7496ae7e6d34ffde83a233501dbf48f64`. 다른 코드·사용자 자료는 복구/롤백하지 않았음.
- `89f45d8d248b3fbc4b164122c8cb5c361b73bf0b` — **신규 읽기 전용 검사** `src/ai_broadcaster/official_tts_readiness.py`: 저장된 공식 `conf.yaml`의 character_config.tts_config에서 실제 엔진이 GPT-SoVITS인지, 한국어 음성/참조 언어인지, localhost 음성 API 및 참조 음성 설정 존재 여부 확인. 실제 실행 TTS 서버나 음성 권리의 증거는 아님. 원본 설정 파일 수정하지 않음.
- `588259cd8c5600989daa3bbe0b21baa0430da12d`: 기존 `src/ai_broadcaster/desktop_chat_tab.py`의 승인형 실제 AI·Live2D·OBS GUI 호출 **이전·이후 두 번** 저장 TTS 설정 검사.
- `2a67a162aa0c6b24272f62fca529d125f4eb1f6b`: `tests/test_aisting_gui_official_full_pipeline.py` 기존 승인/취소 callback fixture 갱신.
- `dc45c7017b1657b0ed7a3af4cdb9b4d4d146b05e`: `tests/test_aisting_official_korean_tts_readiness.py` 신규 6개 검사: 저장 엔진·한국어/로컬 주소·참조 설정·중복 키 확인.

### ③ 검증/진행 중 CI
- 초기 변경은 모의 OBS monitor가 비정상적으로 즉시 종료되는 모의 시간과 신규 테스트 fixture 오기로 회귀 검사 실패했음. 숨기지 않고 재현하여 수리. 실패 기록 https://github.com/junggyeol4444/AISTING/actions/runs/39351731572
- **최신 실제 테스트 코드 기준** 회귀검사 https://github.com/junggyeol4444/AISTING/actions/runs/39352557815 : `completed/success`, **2,376 tests, 2 skipped, 0 failures**.
- 같은 코드 Windows 빌드/통합검사 https://github.com/junggyeol4444/AISTING/actions/runs/39352557854 : 이 인수인계 작성 직전 **진행 대기(queued)**. `windows-exe`, `obs-real-readonly`, `ollama-real-local-e2e`, `twitch-public-readonly`, `korean-public-chat-readonly` 작업. 후속 실행에서 최종 결과와 Artifact ID/digest를 꼭 확인. 이전 성공을 새 코드 PASS로 오인 금지.

### ④ 남은 실제 개발/검증
1. 권리 확보된 참조 음성과 설치/작동 중인 GPT-SoVITS 한국어 음성 서버의 **실제 추론·음질**, 공식 Live2D 모델의 음성 RMS/입 움직임·OBS 프로그램 오디오/영상의 **동일 발화 실측**은 여전히 불가능/미실증. 새 부하 검사나 가짜 TTS로 성공 대체 금지. 저장 config 선택 확인만 완료.
2. YouTube 실제 소유 인증/API 키와 활성 생방송 채팅/전체 페이지 수신은 미실증. 다른 플랫폼과 합쳐 100~500명 실제 FIFO·24시간 연속·지연 실측도 남음.
3. Windows x64 GUI/EXE에서 실제 사람의 클릭→캐릭터 지속 저장→공식 음성→Live2D→OBS 출력 전체 과정 미검증. CI GUI 생성/자체검사는 이 실증이 아님. 실제 송출/녹화는 사용자 승인 없이 금지.
4. 실제 서버가 기존 디스크 conf.yaml을 다시 읽었는지 확인되지 않았으므로 설정 선택 성공 = 실제 엔진 동작 성공이라는 확답 금지.

### ⑤ 실제 저장소/main 및 ⑥ Actions/EXE
- GitHub `junggyeol4444/AISTING`; **기존 main에만 누적 반영**. 최신 실제 기능 코드 커밋 `dc45c7017b1657b0ed7a3af4cdb9b4d4d146b05e` (문서 갱신 이후 HEAD는 새 SHA). SHA는 후속 코드 덮어쓰기 방지용으로만 내부 활용.
- 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39352557815 PASS.
- 새 Windows https://github.com/junggyeol4444/AISTING/actions/runs/39352557854 마지막 확인 대기 — artifact 및 SHA-256 **아직 확인 안 됨**, 창작 금지.
- 이전 Windows/OBS/공개 채팅 성공 https://github.com/junggyeol4444/AISTING/actions/runs/39348949700, 기존 artifact `AISTING-Windows-EXE-integrated` ID `12232700558` ZIP SHA-256 `0fc60e04a6d1e9e5ce63975a523ff3ec6592632764b25fb70f87abf3ec793e60`. **이전 코드**, 이번 수정 미포함.

### ⑦ 사용자 자료·설정 보존
기존 저장 캐릭터(이름/말투/성격)/SQLite 기억/로컬 설정/공식 모델·음성·OBS 자료는 수정/삭제하지 않았음. 검사 API는 읽기 전용이며 작업 종료 시 OBS 녹화·송출을 시작하지 않는다. GUI 검사는 사용자 1회 승인·로컬 엔진 및 저장 캐릭터 정합성 필요.

### ⑧ 다음에 바로 할 구체적 묶음 작업
1. 최신 Windows 통합 run 최종 상태, jobs, 새 EXE artifact ID/ZIP 해시 확보. 실패 시 오류 직접 수정하고 다시 통과 확인.
2. 공식 native child `_observe_actual_live2d_model`의 실제 GPT-SoVITS 지연 상황에서 RMS 관찰이 너무 빨리 끝나는지를 소스/Windows 측정 기반으로 검사하고 정확히 수정 (가짜 샘플 금지).
3. 사용자의 승인된 GPT-SoVITS/Live2D 실제 모델·OBS가 있는 경우, GUI 버튼/캐릭터/동시 신호를 실기기에서 실증. 없다면 미검증 분명히 구분.
4. YouTube API cursor/무손실 FIFO, 네 플랫폼 채팅 및 Stop·재진입·장시간 성능 병렬 점검. GitHub main 소스와 문서를 매회 갱신.

### ⑨ 원래 예약 생성 대화 지속·이전 사유
원래 AISTING 예약을 생성한 대화에서 매시간 결과를 이어가는 것이 사용자의 최우선 요구. 기술적으로 다른 대화에 결과가 출력된다면 기존 데이터를 초기화하거나 사용자에게 다시 요청하지 말고, **이 GitHub 전체 문서**와 원본 기획/코드·CI를 먼저 읽고 다른 대화에 나온 사유를 사실대로 기록. 현재 작업에서 예약 시간/다른 프로젝트 예약은 변경·생성·종료하지 않았음.

### 15절 최종 실제 Windows 검증 확정 (뒤늦은 완료 상태 반영)

- **같은 실제 기능 코드 기준 Windows 통합검사** https://github.com/junggyeol4444/AISTING/actions/runs/39352840989: `completed/success`. 정확히 `windows-exe`, `korean-public-chat-readonly`, `twitch-public-readonly`, `obs-real-readonly`, `ollama-real-local-e2e` 5개 job 모두 `completed/success`.
- 실제 Windows EXE artifact: `AISTING-Windows-EXE-integrated`, id `12234051349`, 크기 `19,643,098` bytes, GitHub artifact **ZIP** SHA-256 `0f719857a796d22711974f64b6cb704ec6ebb2800a8aafa14a10519d0fdc9e29`; EXE 파일 단독 해시 아님.
- 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39352557815 : 2,376개 실행, 건너뜀 2개, 실패 0, `completed/success`.
- 본 내용은 코드 성공 범위인 GUI 생성/빌드, 공개 읽기 전용 플랫폼, 실제 로컬 Ollama/OBS CI를 뜻함. **사용자 승인 음성 모델에서 GPT-SoVITS 한국어 실제 음성·공식 Live2D/OBS 전체 출력 실사용 증명이 아니다.**
- 인수인계 문서만 추가 저장해 새 CI가 자동 시작할 수 있음. 앞서 확인한 위 5개 job의 실제 성공 증거는 사라지지 않는다.

## 16. 2026-10-20 현 대화 실개발·실검증 — Windows 원본 Tk 화면에서 승인 버튼 직접 호출, SQLite 보존 검증

### ① 사용자 원본 기획/지시/금지
사용자가 "계속개발 하고 검증하라고 왜 검증 안하는데"라고 명확히 지적. 기존의 단위/오프라인 검사와 Windows EXE **실제 사용자 버튼 흐름**은 다르므로, 이번에는 원본 AISTING 네이티브 Tk UI에서 **실제 버튼과 이벤트 루프를 실행**하는 CI 검증을 추가했다. 여전히 원래 docs/ORIGINAL_PLAN.txt · docs/ROADMAP_100.md · config/roadmap.json, Windows 10/11 x64 AISTING.exe, 생성 후 영속 캐릭터·SQLite·설정, 기존 공식 Open-LLM-VTuber·Live2D, GPT-SoVITS 한국어 음성, OBS 화면/오디오, CHZZK/SOOP/Twitch/YouTube 중복 포함 FIFO 목표 유지. 브랜치 생성/삭제, 강제 푸시, 재개발/웹·HTML 대체, 실제 방송 시작/녹화/채팅 게시, 미승인 유료 API·계정 로그인·사용자 PC 원격 접근, 권리 없는 음성 훈련 및 사용자 데이터 삭제/덮어쓰기 금지. 기존 매시간 예약 및 다른 프로젝트 예약 변경하지 않음.

### ② 실제 코드 개발 및 확정된 수정 파일/커밋
- `1f7254d5ebdea347d4cfcfaf77e464f6b0dec01e`: `scripts/gui_official_pipeline_click_windows.py` 신규. Windows CI에서 **원본 `AistingApp` 실제 Tk 창/노트북을 열고 `LocalChatTab._pipeline_button.invoke()`로 실제 UI 명령을 수행**. 기존 설정·SQLite 테스트 파일을 Windows 임시 디렉터리에 고립. 실제 승인 거부, 단일 질문/스레드/이벤트 결과, 버튼 상태 복귀, 에러 발생/입력 보존, OBS WebSocket 암호 미노출, 기존 설정·SQLite 바이트 그대로 보존을 검사. 공식 실제 음성/Live2D/OBS 외부 연결만 격리 모의 결과로 대체했으며 **실제 모델 성공이 아님**.
- `9836746bb80dcb18ca681924eb89b5a9a7aa2f07`: `.github/workflows/build-windows.yml`의 기존 Windows EXE 빌드 job에 실제 Tk 버튼 클릭 smoke 실행 단계를 추가. 실패하면 Windows 빌드 전체 FAIL.
- `430e0b560f42659041671f8534e861170aa98cc6`: `src/ai_broadcaster/desktop_chat_tab.py`에서 기존 공식 Live2D/OBS 실제 검사 버튼을 1280×768 화면 내에 표시되도록 대화 기록 위로 배치. 원래 Tk 앱 UI만 수정, 캐릭터/SQLite/기획 설정 보존.
- **실패·수리 이력, 숨기지 말 것**: 첫 Windows 클릭검사 https://github.com/junggyeol4444/AISTING/actions/runs/39354154896 `failure`; GUI 위치/승인 거부/모의 성공 결과/실패 복구/SQLite 파일 무변경은 통과했으나 테스트 코드의 `sqlite3.connect` 컨텍스트 매니저가 연결을 닫지 않아 Windows 임시 파일 제거 `WinError 32`. `ec48c1b82e0f53db9d9830e49401b7174965f855`에서 테스트 파일 SQLite 연결 명시 닫기.
- 다음 Windows 클릭검사 https://github.com/junggyeol4444/AISTING/actions/runs/39354549476 `failure`: SQLite 연결은 종료되지만 CI 보존 데이터 INSERT가 commit되지 않아 SELECT 0건. 애플리케이션의 기존 사용자 DB 손실 증거 아님. `3da7d7ff1a2fcdb6ac885f2008531614669eca77`에서 테스트 SQLite 생성 INSERT를 트랜잭션 커밋 후 명시 닫기로 수정. 이전 기획/코드 버전 원복 없음.
- 모든 위 소스/워크플로 변경은 GitHub `junggyeol4444/AISTING` 기존 **main**에 실제 누적 반영.

### ③ 진행/완료 CI 및 ⑥ 실제 EXE artifact
- **최종 회귀검사** https://github.com/junggyeol4444/AISTING/actions/runs/39354772472 — `completed/success`. Windows workflow 같은 커밋에서 회귀 2,376개 실행, 실패 0 (건너뜀 여부는 이 로그와 별개 확인).
- **최종 Windows 통합검사** https://github.com/junggyeol4444/AISTING/actions/runs/39354772476 — `completed/success`, `windows-exe`, `obs-real-readonly`, `ollama-real-local-e2e`, `twitch-public-readonly`, `korean-public-chat-readonly` 5개 job 모두 success.
- **실제 Windows GUI 로그 증빙** (windows-exe job): `NATIVE_BUTTON_GEOMETRY 244 277 749` (검사 버튼 화면 안에 있음); `GUI_DECLINE_NO_SEND_PASS`; `GUI_BUTTON_THREAD_EVENT_SUCCESS_ROUTE_PASS (SIMULATED OBS/MODEL)`; `GUI_FAILURE_RECOVERY_PASSWORD_REDACTED_PASS`; `CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS`. 사용자 실제 클릭/외부 원격 접속 아님, CI Windows Tk 네이티브 버튼 command 호출임.
- 실제 새 Windows EXE artifact: `AISTING-Windows-EXE-integrated`, id **12235020298**, ZIP 크기 **19,642,574 bytes**, GitHub artifact **ZIP SHA-256** `eaadf41545797a4895d34132dd39ba2a2bc6adf12778b83ce7b9ff59dba36577`. EXE 단일 파일 해시로 표시 금지. 기존 CI run Artifacts에서 다운로드.
- 문서 커밋 때문에 `main` HEAD는 바뀜. 직전 실제 코드/CI 검증 커밋 `3da7d7ff1a2fcdb6ac885f2008531614669eca77`. 다음 회차에는 최신 원격 HEAD를 내부 확인하되 사용자에게 SHA를 개발 성과처럼 제시하지 말 것.

### ④ 아직 미구현·미검증
- 실제 사용 권리/참조 WAV와 GPT-SoVITS 설치 모델로 실행한 **실제 한국어 합성**, 공식 Cubism 모델의 RMS/입 파라미터, 실제 동일 발화 OBS 영상+음성 경로 전체 검증 — 사용자/CI에 필요한 실모델·음성 자료 및 승인된 PC 환경이 없어서 **미실증**. 이번 GUI 테스트의 파이프라인 결과는 외부 서비스만 모의하며 합성 성공 주장 금지.
- YouTube 실제 사용자 활성 라이브 인증 수신, 4개 플랫폼 동시 실시간 전체 FIFO, 지연 1~3초·수백명·24시간 연속 실운용 미검증.
- 실제 Windows 사용자 PC에서 사람이 한 번 설치한 EXE를 반복 실행하고 공식 Live2D/OBS/실제 모델을 연결하는 사용자 인수 검사 미검증. GitHub-hosted Windows VM의 native Tk test와 엄격히 구분.
- 기존 CI의 로컬 Ollama 추론·OBS 읽기 전용 및 외부 공개 채팅 성공은 실제 GPT-SoVITS→Live2D 통합 성공과 다르다.

### ⑤ 정확한 저장소/파일/커밋 및 ⑦ 설정 보존
위 커밋·변경 파일은 `junggyeol4444/AISTING` main. 원본 캐릭터 이름/말투/성격, SQLite 기억/로컬 설정, 공식 모델/OBS 실제 자료와 원본 100단계 완료 상태 변경 없음. 테스트로 만든 고립 Windows 임시 파일만 사용하고 검증 후 삭제. 실제 사용자 데이터는 읽기/수정하지 않았다.

### ⑧ 다음 실행 복수 과제
1. 실사용 원본 GUI에서 운영자 승인→권리 있는 한국어 GPT-SoVITS→실제 Live2D 오디오/입 움직임→OBS 동일 음성 입력 전체를 실제 모델 환경에서 수행하고 실패 원인 수정. 승인된 모델/PC 환경이 없으면 실증 PASS를 주장하지 않음.
2. 원래 `original_plan_full_pipeline.py`의 오디오 OBS 미터 관찰 시간과 Live2D RMS 시간의 실제 교차 구간·캡처 증거를 보강. 단순 '두 곳 모두 소리 있음'이 아니라 **같은 발화의 시간상 연결** 확인. 기존 동시 음성 6구간 검사 유지.
3. 실제 Windows GUI를 1280×768 외 1366×768 등에서 시험하고 닫기/재실행·캐릭터 영속·SQLite 무손실 흐름 보완. EXE selftest 외 실제 GUI 이벤트 증빙 계속.
4. YouTube 실제 사용자 승인 키 없이는 공식 API 페이징·중복·순서 관련 무손실 구현과 로컬 회귀까지만 하고 실제 인증 수신은 미실증 유지. 전체 플랫폼 장시간 부하/재시작 검사.
5. 최신 Windows Actions 및 EXE/사용자 실행 결과를 이 문서에 누적 갱신.

### ⑨ 원래 예약 대화 유지 및 불가피한 이동 사유
현재 사용자가 "계속개발 하고 검증하라고" 요청한 AISTING 대화에서 바로 이어서 작업함. 향후 시간/플랫폼 제한으로 다른 대화로 나타날 경우 원래 대화에 연결하려는 사용자 요청을 그대로 유지하고, 본 GitHub 인수인계와 원본 기획·코드·CI를 먼저 읽고 작업 복원. 다른 예약을 변경/종료하지 말 것.

## 17. 2026-10-20 11시 이후 사용자 요청: 복수 기능 묶음 개발 → 전량 회귀검사 → 오류 수정 → 전량 재검증

### ① 사용자 원 지시·금지/원본 기획
사용자는 "남은 것 좀 하라", "하나 개발·검증 후 다음으로 넘어가지 말고 개발하고 검증하고 수정하라"고 반복 지시. 이에 따라 이번에는 **음성·Live2D·OBS 관찰의 시간상 거짓 양성 방지, 공식 공개 채팅의 저장 캐릭터·한국어 GPT-SoVITS 안전 게이트, 기억 삭제 차단, 그리고 교차 모듈 검사**를 하나의 Git 커밋에서 묶음 반영하고 CI 전체 회귀검사를 실행. 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 Windows 10/11 네이티브 `AISTING.exe`/Tk, 원본 캐릭터 이름·말투·성격 1회 저장 유지, SQLite, 모든 플랫폼 중복 채팅 포함 FIFO, 기존 Open-LLM-VTuber/Live2D/GPT-SoVITS/OBS를 그대로 유지. 새 브랜치·강제 푸시·복구되지 않는 원본 교체·웹/HTML 대체·무단 로그인/유료 API·사용자 PC 원격 실행·실방송/녹화/게시·권리 없는 음성 모델 학습 금지. 기존 시간당 예약 및 타 프로젝트 예약 절대 변경 금지.

### ② 이번 실제 완료 개발 및 ⑤ 정확한 소스 변경
- Repo `junggyeol4444/AISTING` 오직 `main`, 묶음 코드/테스트 원자적 빠른전진 커밋 `f42e96d550817064f340a4801784711389755573`. 변경 파일 4개:
  1. `src/ai_broadcaster/original_plan_full_pipeline.py`: 공식 Live2D 립싱크와 OBS 선택 입력의 음성 후보를 **서로 다른 시간에 별도로 관찰했는데도 연결 성공 후보로 분류하는 오류 방지**. 각 OBS 읽기 구간의 `time.monotonic()` 시작/종료 시각과 공식 AI 한 번의 요청 시간 구간 중첩을 확인하고, 두 신호 존재+시간 중첩 후보가 함께 있어야 `verified_observation`이 true. **OBS 미터의 정확한 음성 프레임 타임스탬프가 아닌 관찰창 경계**이므로 실제 동일 발화/코덱/시청자 전달까지 증명하지는 않음. OBS preflight에서 취소될 때 불필요한 관찰 스레드를 깨우는 처리 추가.
  2. `src/ai_broadcaster/desktop_chat_tab.py`: 수동 한 건 검사만 적용되던 **저장 캐릭터/공식 Live2D 프로젝트 정합성 및 저장된 한국어 GPT-SoVITS TTS 선택 검사를 공식 공개 채팅 연결 시작 전에도 필수화**. 승인 전 파일/로컬 모델이 없거나 다르면 fail-closed. 운영자 AI/실측/공개 채팅 세션 실행 중에는 SQLite 대화 기억 삭제 버튼이 실제 삭제 작업에 들어가지 못하도록 제한. GUI에 음성↔OBS 관찰 시간 중첩 결과의 후보/미확인 표시 추가.
  3. `tests/test_aisting_official_chat_obs_pipeline.py`: OBS와 입 움직임이 모두 양수여도 **시간 중첩 후보가 없으면 전체 성공으로 표시하지 않으며**, 실제 오디오가 없어도 성공하지 않는 음성 관찰 교차 회귀 강화.
  4. `tests/test_aisting_gui_official_full_pipeline.py`: 공식 공개 채팅 연결 시 확정 캐릭터 미존재면 사용자 승인/송신 이전에 차단, 실측 중 삭제 방지 회귀 추가.
- 동일 `main`에서 선행 코드 내용을 되돌리지 않고 위 묶음의 과거 회귀검사와 현재 복수 구간 동작을 일치시키는 테스트 수정 커밋 `2082ae28e3b730bbb5d19eee49f2ba8d782bd556`; 변경 파일 `tests/test_aisting_official_chat_obs_pipeline.py`. 코드는 OBS 여러 번 관찰하므로 기존 `probe_count==1` 테스트 2곳을 `1<=probe_count<=6`으로 고침. 공식 AI 질문 중복 전송 금지 검사 유지.

### ③ CI 중간 실패 및 해결/⑥ 성공한 전체 회귀·EXE
- **실패 증거** https://github.com/junggyeol4444/AISTING/actions/runs/39356757325 : `completed/failure`, 실행 2,380개 중 **2개 실패**, 건너뜀 2. 실패 원인은 `test_existing_official_ai_turn_only_once_and_obs_read_only`, `test_obs_monitor_owns_separate_connection` 두 테스트가 기존 OBS probe 정확히 1회 가정을 했으나 실제 5회였기 때문. 실제 음성/인증 검증 실패가 아니라 변경된 관찰 방식에 대한 회귀검사 조건 오류.
- **최종 성공 전체 회귀** https://github.com/junggyeol4444/AISTING/actions/runs/39356851151 : `completed/success`, 실제 로그 `Ran 2380 tests`, `OK (skipped=2)`, 실패 0.
- **동일한 최종 소스의 Windows EXE·실제 Tk·공개 연동 검증** https://github.com/junggyeol4444/AISTING/actions/runs/39356851195 : `completed/success`; `windows-exe`, `obs-real-readonly`, `ollama-real-local-e2e`, `twitch-public-readonly`, `korean-public-chat-readonly` 5개 job 모두 PASS. 별도 EXE selftest/Windows Tk 격리 사용자 버튼 검사 포함; 음성·Cubism/OBS 전체 실송출 검증은 아님.
- 실제 Windows artifact `AISTING-Windows-EXE-integrated`, id **12236200160**, ZIP 크기 **19,645,783 bytes**, GitHub artifact **ZIP SHA-256** `773b13f6b5a98f733f8f37068b18a33ee6b133d32d7fb2f69ac2b08c1fce6621`. 개별 AISTING.exe 파일 SHA-256이 아님.
- 이번 검증 완료 소스 기준 `main` SHA는 `2082ae28e3b730bbb5d19eee49f2ba8d782bd556`이며 인수인계 문서 저장으로 최종 HEAD는 추가 이동한다. 다음 회차에는 실제 remote HEAD와 CI·파일를 내부 확인하되 **SHA 보고 자체를 개발 성과처럼 포장하지 말 것**.

### ④ 남은 기능·오류·미실증
1. **승인된 모델·실제 음성 참조 파일이 설치된 운영자의 Windows PC에서** 실제 한국어 GPT-SoVITS WAV 생성, 공식 Cubism RMS와 입 파라미터, 실제 OBS 입력 및 프로그램 음성/영상이 **동일한 발화로 이어지는지**는 실행하지 못함. Windows CI는 독립 OBS/Ollama와 격리된 UI 이벤트를 검증할 뿐, 동일 실제 한국어 음성 모델의 통합 실증이 아님. 관찰 시간 구간 중첩만으로 합성·음질·실송출 성공이라 하지 말 것.
2. YouTube 실제 소유 API 키와 활성 라이브 채팅 인증 수신 및 커서/FIFO 실증 미완료. 4개 플랫폼 100~500명 동시 고부하, 24시간 실운용, 1~3초 지연 실측 미완료.
3. 사용자 PC에서 실제 `AISTING.exe`를 실행해 캐릭터 저장→공식 Live2D 창→한국어 음성→OBS의 모든 버튼을 사용한 사용자 승인 경로 미검증. GitHub runner 결과로 대체 금지.
4. 사용자 원본 기획의 로드맵 91개 미승인 단계는 운영자 명시 승인 없이 completed로 표시하지 말 것. 초기 기획/정책 및 저장 정보 유지.

### ⑦ 사용자 자료·환경 및 ⑧ 다음 회차 묶음 작업
- 기존 저장 캐릭터·설정·SQLite·모델/OBS 자료 파일 미수정. 원격 GitHub 코드와 테스트 파일만 변경. 계정 로그인/방송 시작/녹화·채팅 게시·임의 TTS 학습 없음. Windows CI는 격리된 임시 테스트 파일과 공개 읽기 전용 검사를 사용.
- **다음 묶음**: 1) 실제 GPT-SoVITS 사용 권리·모델/OBS가 있는지 확인 가능한 환경에서 동일 음성 실증·오류 수정; 접근 불가면 단계 미실증 유지, 2) OBS 미터 이벤트와 Cubism RMS에 실제 같은 발화의 샘플 타임스탬프가 없는 한 "동일 음성 완전 증명" 금지·유효 증거 수집 강화, 3) 원본 네이티브 GUI 재시작/취소/예외·SQLite 영속 보존 및 공식 공개 채팅 FIFO 병행 검사, 4) YouTube API page/stop 및 권리 있는 로그인 없는 읽기 전용 실험, 5) 모든 수정 묶음 뒤 전량 회귀→Windows EXE/GUI·OBS/Ollama/공개 채팅 전량 검사→오류 묶음 수정 후 다시 전량 검사.
- **순서 중요**: 한 작업마다 회귀 빌드를 반복하는 대신 복수 기능을 계획·구현한 한 묶음을 종료한 뒤 전체 시스템을 검사한다. 실제 오류가 발생하면 누적 코드를 잃지 않고 고쳐서 다시 전량 검사한다.

### ⑨ 원래 ChatGPT 예약 생성 대화 유지
사용자가 만든 AISTING 매시간 예약은 가능한 한 바로 이 기존 원래 대화에서 이어져야 한다. ChatGPT 플랫폼이 대화를 강제로 이동시키는 것은 여기서 통제할 수 없으므로, 이동 시에는 본 문서와 원본 기획·GitHub 전체 이력·마지막 CI를 먼저 읽고 인계 사유를 명시하며 다시 사용자에게 설명을 요구하지 않는다. 이번 실행 중 예약·다른 프로젝트의 예약은 생성·수정·종료하지 않음.

## 18. 2026-10-20 11시 이후 최신 회차 — YouTube API 메시지 ID 리플레이와 Stop·재시작 안전성 묶음 개발/전량 검증

### ① 사용자 원본 요청·금지 및 기획 준수
사용자 지시 "계속": 이전에 반복 강조한 **여러 실질 기능 묶음 개발 → 전체 회귀검사 → 실제 Windows EXE·GUI 및 가능한 연동검사 → 실패 원인 수정 후 전량 재검증**을 그대로 따른다. 최신 SHA 표시는 목적이 아니라 누적 코드 덮어쓰기 방지용. 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 네이티브 Windows 10/11 Tk AISTING.exe, 저장 캐릭터 이름/성격/말투·SQLite·설정, Open-LLM-VTuber+GPT-SoVITS 한국어 음성+Live2D+OBS, 플랫폼 선택, 중복 포함 실채팅 FIFO 목표 유지. 브랜치 생성·삭제/강제푸시/원복/웹·HTML 대체/새 기능 임의 추가/유료 API·로그인/실제 방송 시작·녹화·게시/사용자 PC 접속/권리 없는 음성 학습 금지. 기존 1시간 예약과 다른 프로젝트 예약 변경 금지.

### ② 완료한 실제 누적 수정과 ⑤ 변경 파일·커밋
- 기존 `junggyeol4444/AISTING`의 `main`에 다음 **4개 파일을 단일 원자적 묶음 커밋** `a34c0b96bf17cb7fdc36727c5cea9c6296342384`로 반영. 분기 추가·강제 푸시·원본 파일 재개발 없음:
  1. `src/ai_broadcaster/multiplatform_readonly.py`: YouTube Data API liveChatMessages 목록의 **동일 `id` 이벤트가 페이지를 넘어 다시 돌아오면 시청자 질문을 중복 AI 요청하지 않도록** 최근 고유 ID 5만 개를 순환 기록해 중복 ID만 제거. 내용·발신자가 같아도 별도 `id`면 각각 FIFO 전달. ID가 없는 유효 이벤트는 누락 방지 차원에서 그대로 전달. ID 캐시를 제한해 24시간 장시간 실행의 메모리 무한 증가를 피함. 외부 계정/YouTube API 키가 없어 본 실행은 네트워크 실제 인증 수신을 수행하지 않음.
  2. `src/ai_broadcaster/desktop_chat_tab.py`: **공개 채팅 중지 버튼을 눌렀을 때 네트워크 수신 스레드의 종료를 무기한 기다리지 않고 즉시 Tk UI의 연결 상태·버튼을 복원**하고 기존 AI FIFO에 종료 신호를 넣음. 이전 세션 스레드에서 늦게 온 응답은 이미 있는 세션 범위 검사로 신연결과 분리. 실제 전송/방송 시작 없음.
  3. `tests/test_aisting_multiplatform_readonly.py`: 같은 메시지 ID 재전달 1회 처리와 별도 메시지 ID지만 텍스트 중복인 실제 3개 메시지의 FIFO 보존, ID 없는 유효 메시지 보존 회귀 2개.
  4. `tests/test_aisting_twitch_ai_integration.py`: 수신 스레드가 연결을 종료하기 전에 사용자 Stop을 눌러도 UI 즉시 복원되고, 이전 세션의 늦은 이벤트가 새 세션에서 처리되지 않음 확인 1개 회귀.
- 사용자 캐릭터 데이터베이스/설정·실제 모델·OBS 환경 미변경. 네이티브 Tk 기반만 수정.

### ③ 전량 검사·CI 진행 상태 및 ⑥ Windows EXE artifact
- 본 코드 커밋 전체 회귀검사 https://github.com/junggyeol4444/AISTING/actions/runs/39358345339 — **completed/success**, 실제 로그 `Ran 2383 tests`, `OK (skipped=2)`, 실패 0.
- 본 코드 커밋 Windows 통합검사 https://github.com/junggyeol4444/AISTING/actions/runs/39358345654 — **completed/success**, 5개 job 모두 성공:
  `windows-exe`(Windows EXE 빌드·실행·기존 실제 Tk GUI 단추 검사), `ollama-real-local-e2e`(CI 로컬 Ollama 실제 한국어 추론), `obs-real-readonly`(CI 실제 OBS 화면/입력 읽기 전용), `twitch-public-readonly`, `korean-public-chat-readonly`(치지직·SOOP 공개 수신).
- 최신 이 코드의 실제 GitHub artifact `AISTING-Windows-EXE-integrated`: ID `12236192940`, ZIP 크기 **19,650,903 bytes**, GitHub artifact **ZIP SHA-256** `747ef224d809fdb69360a18b6f949414832e9c645f4e279875e04d1a5b6c2944`. 개별 EXE 파일 해시와 혼동 금지.
- 문서 갱신 직전 코드 `main` HEAD `a34c0b96bf17cb7fdc36727c5cea9c6296342384`. 문서 갱신으로 새로운 커밋이 발생하므로 이후 HEAD는 다시 확인할 것. 문서-only 새 CI가 돌 수 있으나 소스 전체 CI 합격 사실과 구분.
- 이번 회차 기능 수정에 따른 실패가 없었음. 다만 테스트 성공을 실제 사용자 소유 PC·음성 모델 실사용 E2E 성공이라고 부르지 말 것.

### ④ 미완료·미검증/범위 구분
- **권리 있는 실제 GPT-SoVITS 한국어 음성**, 승인된 참조 WAV, 공식 Live2D/Cubism 실제 입 움직임, OBS 프로그램 영상과 오디오가 동일한 실제 발화로 연결되는 **사용자 Windows EXE 전 경로**는 자료·PC 모델 환경에 접근할 수 없어 미실증. CI의 독립 OBS/로컬 Ollama/GUI 모의 외부 서비스 성공과 엄격히 분리.
- 소유 API 키로 YouTube 실제 활성 생방송 채팅 수신, 다중 플랫폼 100~500명 실시간 FIFO, 1~3초 응답 및 24시간 무중단 실제 스트레스 검증 미완료. 특히 이번 YouTube 이벤트 ID 중복 제거는 오프라인 회귀 성공이며 실제 라이브 인증 연결 증명이 아님.
- 5만 개 이전의 오래된 YouTube ID 재등장 시 캐시에서 제거되어 중복 처리 가능성 존재(경계 있는 장기 메모리 정책). 동일 ID 중복을 영구 완벽 보장하지 않음. 반대로 별도 메시지 ID의 중복 텍스트는 의도적으로 각각 처리.

### ⑦ 사용자 데이터/설정 보존
기존 사용자 캐릭터 이름/말투/성격 확정 설정, 로컬 SQLite 기억, OBS·Live2D 설정, 플랫폼 선택·기본값 파일을 건드리지 않음. Windows CI는 격리된 테스트 파일·모의 GUI 외부 모델/승인 없는 공개 읽기 전용 소스만 사용. 무단 모델 훈련·API 로그인·채팅 전송/방송·녹화 시작 없음.

### ⑧ 다음 회차 구체적 복수 작업
1. 현재 YouTube API 페이지 경계의 동일 이벤트 ID 재수신에 대한 누락·중복 정책과 유실 없이 cursor/종료 순서 검증, 실제 키가 없으면 실제 활성 라이브 채팅 성공으로 주장하지 않음.
2. 초장시간 네 플랫폼 수신 정지/연결 실패/재연결에서 stale 이벤트·GUI 상태, AI FIFO 1~N천 건 장기 큐 메모리/지연 분석, 한국 플랫폼 공개 프로토콜 변경 위험 점검.
3. 공식 GPT-SoVITS 한국어 음성의 시간축, 공식 Live2D 입 움직임과 OBS 입력 미터의 **실제 동일 발화**를 확인할 수 있는 자료/승인 환경이 있다면 녹화·송출 없이 사용자 흐름 실증. 없으면 실증 미완료 분리.
4. 기존 프로그램 저장 캐릭터 재실행/SQLite 영속/실제 Windows GUI 버튼·실패 후 재진입을 묶음으로 수정하고 **전체 회귀·Windows EXE·실제 가능한 읽기 전용 통합검사 전량** 수행, 오류 발견 시 같은 묶음을 재검증.
5. 해당 commit/files/jobs/artifact/미검증을 본 GitHub 누적 문서에 계속 업데이트.

### ⑨ 원래 AISTING 예약 생성 대화 유지
사용자 최우선 희망은 기존 AISTING 예약 생성 원본 채팅에서 매시간 계속하고 타 대화로 임의 이동하지 않는 것. 대화 길이·플랫폼 차원에서 불가능한 경우 원래 문맥에 접근한 척하지 말고 본 GitHub 문서와 원본 기획·로드맵·main 이력·실제 CI를 먼저 읽어 이어가며, 이동 사유를 실제 확인 가능한 수준에서만 명시할 것. 이번 실행에서 예약을 만들거나 변경·종료하지 않았음.

## 19. 2026-10-20 원본 대화 연속 회차 — 실제 Cubism 입·음성 샘플 시각과 OBS 관찰 시간 교차 검증

### ① 원래 기획/사용자 강제 지시·금지
사용자는 계속 개발·검증을 요구하며 **복수 파일의 실질 개발을 묶어 → 전체 회귀검사 → 실패 수정 → 전체 회귀·Windows EXE/GUI/실연동 재검증**하기를 반복 지시했다. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 누적 Tk Windows 10/11 x64 AISTING.exe, 저장된 캐릭터 이름·말투·성격/SQLite/설정, 공식 Open-LLM-VTuber+Live2D, 권리 있는 한국어 GPT-SoVITS, OBS 실제 오디오·영상, CHZZK/SOOP/Twitch/YouTube 중복 포함 채팅 FIFO와 사용자 선택 플랫폼을 보존. 신규 브랜치·브랜치 삭제·강제푸시·기존 소스 원복·재개발/HTML앱·계정 로그인/유료 API·실방송/녹화 시작·채팅 게시·사용자 PC 접속·권리 없는 음성 훈련 금지. 기존 시간당 예약과 타 프로젝트 예약 변경 금지. 원래 대화가 지원되는 동안 원래 대화에서 이어가고, 시스템이 다른 대화에 표시할 경우 전체 문서로 먼저 인수인계한다.

### ② 누적 실제 코드 개발 완료 및 ⑤ 정확한 main/파일·커밋
- 실제 저장소 `junggyeol4444/AISTING`의 기존 `main`에 소스·테스트 4파일을 **단일 묶음 커밋** `349ccda36abc4bef0368dbaca265b5d5aa64664d`로 변경:
  - `src/ai_broadcaster/original_plan_frontend.py`: 실제 공식 WebView2/Cubism 관찰 시 RMS와 입 움직임이 **동일 샘플에서 변화**한 시점에 `time.monotonic()`을 기록, 해당 첫/마지막 실측 시각을 기존 IPC JSON에 추가. `OfficialLipSyncEvidence`에 실제 관측 시작·끝 필드를 추가하되 구버전 응답은 0으로 유지해 별도 실측의 성공 증거로 쓰지 않음. 비정상 숫자/NaN/역전된 시각은 거부.
  - `src/ai_broadcaster/original_plan_full_pipeline.py`: OBS 미터가 양성이라고 해도 **AI 질문 전체 시간대가 아닌, 실제 Cubism RMS↔입 겹침이 측정된 시각과 OBS 양성 음성 구간이 중첩되어야만** `temporal_overlap_candidate`를 true 처리. 공식 시각 정보가 없는 예전 IPC 답변은 동시 관찰 인증에 사용하지 않음. 단, OBS 오디오 미터는 정밀 샘플 타임스탬프가 아닌 관찰 구간이므로 **동일 음원·발화·방송 송출의 완전한 인과적 증명은 아직 아니다**.
  - `tests/test_aisting_native_live2d.py`/ `tests/test_aisting_official_chat_obs_pipeline.py`: 실제 샘플 시각 기록과 비어 있는/부정확한 응답의 fail-closed, 양성 신호만으로 거짓 인증하지 않는 검사 추가.
- 첫 전체 CI 테스트 실패 후 **수정 묶음 커밋** `0e5e7dfe35ecd5e5d4bb5c5ec808a099c8dfc361` (기존 main에 빠른전진, 원본 내용 유지):
  - `tests/test_aisting_native_live2d.py`: 모의 `time.monotonic` 호출 시퀀스가 새 실제 관찰 2회 추가를 반영하도록 수정. 실제 제품 로직의 관찰 샘플 수를 인위적으로 줄이지 않음.
  - `tests/test_aisting_native_live2d.py`: NaN·무한대·음수·문자열·역전된 시간 필드 입력 거부 검사 추가.
  - `src/ai_broadcaster/original_plan_full_pipeline.py`: OBS 독립 모니터가 시작 준비 지연·오류로 거부될 때 취소 이벤트를 설정하고 관찰 스레드를 깨워 불필요한 세션이 대기하지 않도록 보강. 승인하지 않은 질문 재전송 없음.
  - `tests/test_aisting_official_chat_obs_pipeline.py`: 실제 OBS 구간과 겹치지 않는 과거 Cubism 샘플은 전체 동시 성공으로 올리지 않는 회귀 검사 추가.
- 원래 캐릭터 설정, 저장 데이터, SQLite, 공식 모델 및 OBS 사용자 설정을 수정하지 않고 GitHub 원본 코드·테스트만 수정. 새 브랜치/강제푸시 없음.

### ③ 진행/CI 실패 및 수정 결과, ⑥ 실제 Windows EXE와 로그
- **실패 증거** 첫 버전 회귀: https://github.com/junggyeol4444/AISTING/actions/runs/39359362221 — `completed/failure`, `Ran 2384 tests`, 실패 1건 (`test_lipsync_probe_samples_real_viewer_values_not_random`: 새 Cubism `time.monotonic` 호출로 모의 시계 시퀀스와 샘플 수가 어긋남). 첫 버전 Windows https://github.com/junggyeol4444/AISTING/actions/runs/39359362233 역시 `failure`. **실패를 숨기지 않고 다시 코드·테스트를 수정한 후 모두 재실행**.
- **최신 전체 회귀 PASS**: https://github.com/junggyeol4444/AISTING/actions/runs/39359568732 — `completed/success`, 로그 `Ran 2386 tests`, `OK (skipped=2)`, **실패 0**.
- **동일 코드 기준 Windows 전체 PASS**: https://github.com/junggyeol4444/AISTING/actions/runs/39359568698 — `completed/success`. `windows-exe`(기존 Windows x64 EXE 빌드·실행/네이티브 Tk GUI 실버튼 격리 검사), `ollama-real-local-e2e`(격리 CI Windows에서 실제 로컬 Ollama 한국어 추론), `obs-real-readonly`(CI 실제 OBS 화면·입력 읽기 전용), `twitch-public-readonly`, `korean-public-chat-readonly`(치지직·SOOP 공개 수신) **5개 작업 모두 PASS**.
- 새 Windows artifact `AISTING-Windows-EXE-integrated`, id `12236263884`, 19,653,918바이트, GitHub artifact **ZIP** SHA-256 `4d0ea0ddca27a2c37ba951f7acdb6bddafeacb7571b7ddec770b6a3138caabc2`. EXE 단독 파일 해시는 확인하지 않았으므로 ZIP 해시와 혼동 금지.
- 실제 소스 검증 커밋 `0e5e7dfe35ecd5e5d4bb5c5ec808a099c8dfc361`. 이 문서 업데이트 자체가 main HEAD를 다시 이동하므로 다음 회차에 저장된 최신 HEAD 확인.

### ④ 남은 기능·오류·미실증
- 아직 **운영자 승인 한국어 GPT-SoVITS 실제 모델/권리 확보된 참조 음성에서 한국어 WAV 실제 합성·음질/지연**, 공식 Cubism 모델의 해당 발화와 OBS 프로그램 음성/영상 실제 동일 출력, 설치된 사용자 Windows EXE에서 전체 버튼 흐름 **실제 장비 실증 안 됨**. 기존 CI Windows Tk 실제 버튼은 외부 GPT-SoVITS/Live2D/OBS 동일 음성을 모의; 실제 Ollama/OBS 각각 독립 검사임. 모의 성공을 실사용 전체 경로 PASS라고 표시 금지.
- 실제 YouTube 소유 API 키/활성 생방송의 인증 채팅 수신, 네 플랫폼 100~500명 동시 수신·1~3초 실응답·24시간 스트레스, 여러 회차/종료 후 재기동 실운영 미검증.
- OBS 관찰 구간과 Cubism 실측 타임스탬프 겹침은 **음성 원본/샘플 파형 동일성 검증이 아닌 보수적 후보**. 실제 음성 소스 확인과 시각·오디오 지연 정밀 실측 필요. 승인되지 않은 녹화·방송은 금지.
- 기존 원본 `config/roadmap.json`의 승인 pending 항목은 변경하지 않음.

### ⑦ 사용자 자료/설정 보존
저장된 캐릭터 이름·말투·성격, SQLite 기억, 기존 설정·원본 기획·100단계 기록, 사용자 소유 모델·OBS 프로젝트/오디오 입력을 보존. CI는 격리 Windows/모의 장치/읽기 전용 공개 채팅만 접근, 계정 로그인·실제 송출/녹화·채팅 게시나 권리 없는 음성 모델 학습 없음.

### ⑧ 다음 회차의 구체적 복수 작업
1. 공식 WebView2/Cubism 실제 동작 모델과 권리 확인된 GPT-SoVITS 한국어 음성 서버/OBS 기존 음성 입력이 갖춰진 승인 환경을 사용할 수 있으면 동일 발화의 실제 TTS → 입 움직임 → OBS 음성/화면 관찰 사용자 흐름을 실행해 지연/음성 일치/오류를 재현·수정. 아니면 실제 모델 통합 실증은 미완료 유지.
2. 기존 Tk GUI 장시간 AI/OBS 관찰 중 Cancel/Stop/창 닫기 이후 작업 스레드·세션 정리/재실행, SQLite 및 캐릭터 재시작 영속 보존과 음성 길이 지연의 교차 회귀 추가.
3. YouTube API cursor/메시지 ID/Stop 및 치지직·SOOP·Twitch 네 플랫폼 멀티세션 FIFO 장기 부하·실제 공개 프로토콜/버전 오류 검사. 실제 YouTube 키가 없어도 API 시뮬레이션만 PASS 구분.
4. 여러 실질 코드·테스트를 묶음 개발한 뒤 **전량 회귀검사→Windows EXE/실제 Tk GUI→Ollama/OBS 읽기/플랫폼 실채팅 전량 검사**, 실패 시 묶음 수정 후 재검증. SHA 반복 보고 대신 남은 실제 기능 완성을 우선.
5. 새 run/artifact/커밋/인수인계 파일을 누적 저장, 다른 프로젝트 예약 변경 금지.

### ⑨ 원래 예약 생성 대화 유지·불가능 시 인계
사용자가 AISTING 예약을 만든 원래 이 대화에서 계속 작업·결과 보고하는 것을 최우선으로 요구. 시스템의 채팅 길이/플랫폼 제약으로 다른 대화에 결과가 나타날 때는 이동을 임의로 했다고 꾸미지 말고 본 전체 GitHub 인계와 원본 문서·최신 main/CI 확인 후 **전체를 인수인계하고 다음 작업 그대로 이어감**. 이번 작업 중 기존 매시간 예약을 수정/종료하지 않음.
