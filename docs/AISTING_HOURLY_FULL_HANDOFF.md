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

## 20. 2026-10-20 12시 KST 회차 — Windows Tk 공식 AI·Live2D·OBS 중지 처리/재진입 안전성, 실제 사용자 버튼 검증

### ① 원본 기획 및 사용자 강제 지시·금지
사용자가 단순 "계속"으로 원래 AISTING 예약 대화에서 **남은 실제 기능을 개발·수정·검증**하라고 지시한 상황. 앞 회차의 "하나씩 찔끔 개발·검증 반복 금지; 복수 실질 기능 개발 → 전체 회귀·Windows 실제 GUI/EXE 검사 → 오류 수정 → 전량 재검증"을 최우선으로 유지. 기초 파일 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 기존 Windows 10/11 x64 네이티브 `AISTING.exe`/Tk, 확정 캐릭터 이름·말투·성격 1회 저장·영구 유지, SQLite 기억·설정, 공식 Open-LLM-VTuber/Live2D/GPT-SoVITS 한국어 음성, OBS 프로그램 오디오·영상, YouTube/CHZZK/SOOP/Twitch 중복 포함 FIFO 수신, 사용자 선택 플랫폼 보존. 임의 신규 브랜치/삭제·강제푸시/원본 기능 복구/웹·HTML 대체/계정 로그인·유료 API/사용자 PC 원격 접속/실제 방송·녹화 시작·채팅 게시/권리 확인 없는 음성 훈련 금지. 이전 성공한 단위 검사·CI 모델과 실제 GPT-SoVITS→Cubism→OBS 전체 실증 구별. 매시간 기존 예약과 타 프로젝트 예약 변경·종료 금지. 원래 생성 대화 유지 최우선, 플랫폼의 불가피한 새 대화 출현 시 본 전체 문서+원본 기획+main을 먼저 읽고 인수인계.

### ② 이번 완료 코드/기능 및 ⑤ 정확한 변경파일·커밋
- GitHub `junggyeol4444/AISTING` **기존 `main`**, 신규 브랜치·강제푸시 없음.
- `4846aaded5ae6954ef65c1524d47d5bb4d162a66`: 5개 파일을 한 커밋으로 수정.
  1. `src/ai_broadcaster/original_plan_full_pipeline.py`: 명시 운영자 중지 `cancel_event` 추가. 이전에 승인·권리 확인된 단일 한국어 음성 요청일 때 OBS 사전 검사 시작 전, 공식 AI 전송 직전, 모니터 6구간 사이, 결과 최종 반환 전에 중지 확인. 중지 후 AI 요청 재전송·기존 늦은 결과 성공 처리 방지. 이미 upstream에 전달된 요청은 무효화/전송 취소로 주장하지 않음. OBS 독립 모니터는 Event로 중지 신호 확인.
  2. `src/ai_broadcaster/desktop_chat_tab.py`: 기존 네이티브 Tk 공식 실측에 **"실측 중지 요청" 버튼** 추가. 실행 중에만 활성화, 중지 눌러도 기존 AI request 작업 스레드가 반환하기 전에는 새 실행 버튼을 막음. 완료 이벤트에서 오류/중지/정상 성공을 구분하며 GUI 상태 복구, 창 닫기 시 중지 이벤트 설정, 원래 입력 텍스트·캐릭터·SQLite 미수정. 이미 upstream에 도착한 질문을 취소한다고 거짓 안내하지 않음.
  3. `tests/test_aisting_official_chat_obs_pipeline.py`: 작업 시작 전 중지 시 OBS/AI 무호출, 승인 질문이 전송된 뒤 중지 시 긍정 결과 폐기·재전송 없음 검사 2개 추가.
  4. `tests/test_aisting_gui_official_full_pipeline.py`: 진행 중 중지 클릭은 GUI 잠금을 유지, 작업자 늦은 양성 결과를 중지로 처리하는 단위 회귀 추가.
  5. `scripts/gui_official_pipeline_click_windows.py`: Windows 가상 PC에서 **실제 Tk 버튼 클릭, 느린 외부 모델은 모의 스레드로 격리, 중지 버튼 클릭, 이미 들어온 결과 거부, 입력 내용 보존**까지 확인하는 E2E UI smoke 추가. AI 모델/Live2D/OBS 동일 발화 실제 통합은 이 검증에서 모의임.
- `5273606553b39b62cb64d4c51ce67024c4b189f3`: 변경된 worker 인수(중지 Event 4번째)의 기존 단위 검사 가정 수리, 수정 파일 `tests/test_aisting_gui_official_full_pipeline.py`.
- `b3197d463876c0ed14a7d9a86ca16bb8f94b5836`: `src/ai_broadcaster/desktop_chat_tab.py`의 race 수정. 성공 이벤트가 큐에 놓인 직후 운영자가 Stop을 누르더라도 **Tk 결과 처리 직전에 cancel_event를 다시 검사해 성공으로 표시하지 않음**. `tests/test_aisting_gui_official_full_pipeline.py`에 늦은 성공 큐 재현 검사.
- `306977935a1f6502e00d79531e34b32d5d957ac2`: 위 테스트 파일에 괄호 하나가 빠져 발생한 SyntaxError 수정. 이 커밋의 실제 소스/테스트가 아래 성공 CI의 기준. 문서 추가 커밋 이후 HEAD는 변경되므로 후속 실행에서 최신 원격 HEAD를 내부 재확인.

### ③ 검증 실패·수정 및 ⑥ 최종 GitHub Actions·실제 Windows EXE artifact
- 첫 묶음 검증 https://github.com/junggyeol4444/AISTING/actions/runs/39365352472 : `completed/failure`, **2,390 tests, 1 failure, skipped=2**. `test_explicit_approval_calls_one_worker_and_disables_button`는 기존 인수 3개를 가정하지만 새 실제 worker 인수는 Event 포함 4개 → 신규 Event 존재/미설정과 실제 질문 1회 전달 검증으로 수정.
- 추가 중지 경합 회귀 후 https://github.com/junggyeol4444/AISTING/actions/runs/39365536304 : `completed/failure`, 테스트 새 파일 188행의 `SyntaxError: '(' was never closed`로 테스트 로드 불가. 테스트 결과를 성공 처리하지 않고 원인 파일 문법 수정 뒤 전량 재실행.
- **최종 성공 전체 회귀** https://github.com/junggyeol4444/AISTING/actions/runs/39365639890 : `completed/success`, 실제 로그 `Ran 2391 tests`, `OK (skipped=2)`, **실패 0**.
- **최종 성공 Windows 통합** https://github.com/junggyeol4444/AISTING/actions/runs/39365639900 : `completed/success`, 5개 job 전체 `completed/success`: `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly`.
- Windows GUI 로그 명시 실버튼 확인: `NATIVE_BUTTON_GEOMETRY 244 277 749`, `GUI_DECLINE_NO_SEND_PASS`, `GUI_BUTTON_THREAD_EVENT_SUCCESS_ROUTE_PASS (SIMULATED OBS/MODEL)`, `GUI_FAILURE_RECOVERY_PASSWORD_REDACTED_PASS`, **`GUI_NATIVE_CANCEL_NO_LATE_SUCCESS_PASS (SIMULATED MODEL)`**, `CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS`.
- 실제 Actions artifact `AISTING-Windows-EXE-integrated`, id `12239054164`, 크기 `19,657,995`바이트, GitHub 산출물 **ZIP SHA-256** `134d5951eb0d847d513b83f7977fd6138e99c8505ee786553ac33a434dc84c92`; 개별 EXE 파일 해시 아님. 로그인된 GitHub 사용자는 Windows 워크플로 페이지에서 Artifacts를 내려받을 수 있음.
- 본 문서 업데이트는 별도 HEAD와 CI를 만들 수 있음. 위 검증은 전량 코드를 담은 마지막 기능 커밋의 실제 성공이고, 문서-only 커밋의 새 진행 CI와 구분.

### ④ 남은 기능·오류·실사용 미검증
- 실제 사용자 Windows PC에서 권리 확인된 음성 참조 및 GPT-SoVITS 모델/서버로 **한국어 TTS 합성 → 공식 Live2D 실제 Cubism 음성 동기 립싱크 → OBS 프로그램 음성·화면** 동일 발화 end-to-end 실측은 **미완료**. 이번 CI는 **Windows GUI의 실제 버튼·상태는 실행**했지만 음성/Live2D/OBS 같은 발화의 외부 서비스는 모의, 별도 CI OBS와 Ollama는 독립 실행이므로 전체 모델 실사용을 인증하지 못함.
- 실제 인증 YouTube 활성 방송 채팅 수신, 4개 플랫폼 실제 수백 명 동시 FIFO와 1~3초 처리·24시간 안정성은 검증하지 못함. YouTube 메시지 ID 중복 제거/오프라인 테스트와 실제 API 실증은 다름.
- Stop은 이미 공식 AI 서버가 받은 요청을 취소할 수 있는 방법이 아님. 중지 요청이 들어가면 새 요청 재전송 금지·GUI 늦은 결과 성공 표시 방지, 기존 외부 server가 처리를 지속할 가능성은 사용자에게 명확히 알림. 실제 외부 음성 모델/OBS 장시간 연결의 안전 종료 사용자 실기 검증 미수행.
- 원본 로드맵/사용자 개인정보·설정 상태의 pending 항목을 근거 없는 완료 상태로 변경하지 않음.

### ⑦ 데이터·설정·캐릭터 보존
원본 확정 캐릭터 이름·성격·말투/저장 설정/SQLite 기억/사용자 OBS 입력·장면/공식 Live2D 프로젝트를 건드리지 않음. 테스트는 임시 격리 SQLite·설정의 해시·값 불변으로 검증. 사용자 PC 접속·계정 로그인·방송/녹화/채팅 송신·권리 없는 모델 학습 없음.

### ⑧ 다음 회차에서 수행할 구체적 묶음 작업
1. 기존 승인형 공식 AI·GPT-SoVITS·Live2D/OBS **실제 모델**의 고지연 음성 합성·중지·재호출 중 라이브 세션 충돌/중복 발화, Windows 실기기 재실행·닫기·실패 복구 실증. 모델/권리/PC 접근이 없다면 완료 주장 금지.
2. 실제 Cubism 입 움직임 monotonic 타임스탬프 ↔ OBS 입력 미터 시간의 교차 관찰을 넘어 같은 음성 샘플인지 검증할 수 있는 실제 경로/오디오 증거 보강 (방송·녹화/외부 송신 없이 승인된 로컬 실측에서만).
3. YouTube 활성 채팅 키 없는 환경에서는 공식 API 응답·토큰·정지·메시지 ID 일관성 테스트 보강. 한국 2플랫폼/Twitch 포함 중복 채팅 FIFO/1~N천건 밀집 이벤트/중단·재연결 안전성 점검.
4. Windows 네이티브 GUI의 사용자가 Stop을 눌렀다가 닫기/재실행할 때 모델 서버의 이미 전달된 요청 및 후행 이벤트 누락/데이터 영속성 재검증. 전체 회귀 2391+ 및 Actions Windows 5개 잡을 묶음 끝에 전량 실행해 발견한 오류 수정 후 다시 반복.
5. 각 실행 끝에 최신 본 문서와 정확한 main commit, 변경 파일, 전체 검사 수, EXE Artifact 및 **실제 미실증**을 누적 기록.

### ⑨ 원래 대화 유지/불가피한 대화 이동 시
사용자는 **예약 생성 바로 이 AISTING 대화**에서 매시간 진행하고 다른 대화로 임의 이전하지 말라고 최우선 지시. 이 실행에서 원래 대화를 바꾸지 않았으며 일정 및 다른 프로젝트 예약 수정/종료 없음. 플랫폼 길이/예약 응답 연결 제약으로 다른 대화에 출력될 경우 이전 대화를 읽을 수 있다고 꾸미지 말고 **본 GitHub full handoff와 원본 기획/로드맵/최신 main/Actions**를 먼저 읽고 작업 복원, 사용자에게 재설명 요구 금지. 이동 사유도 확인 가능한 실제 플랫폼 제약만 보고.

## 21. 2026-10-20 12시 이후 연속 실행 — Stop 후 미완료 AI/SQLite 생명주기 보호와 Windows Tk 2,048 FIFO 부하검사

### ① 사용자 기획·강제 지시·금지 (기존 전체 문서 누적 유지)
원래 AISTING 예약 생성 대화에서 사용자가 "계속" 지시. 기존 고정 요구: 여러 **실질 기능을 묶음 개발한 뒤 전체 회귀검사, Windows 10/11 x64 네이티브 EXE·실제 Tk 버튼·로컬 Ollama·공식 OBS 읽기 전용·실제 가능한 공개 채팅 전체 검사, 실패 즉시 수정·전체 재검증**. 저장소 `junggyeol4444/AISTING`, `main`만 빠른전진 유지, 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 캐릭터 이름/말투/성격 1회 저장·SQLite 기억·앱 설정, 공식 Open-LLM-VTuber+Live2D, 권리 확보 한국어 GPT-SoVITS, OBS 오디오/영상, YouTube/치지직/SOOP/Twitch 중복 포함 FIFO, 플랫폼 선택 목표 불변. 임의 브랜치 생성·삭제/강제푸시/코드 원복/재개발·웹/HTML 대체/유료 API·로그인/사용자 PC 접속/실제 송출·녹화 시작/채팅 게시/권리 없는 음성 모델 훈련 및 사용자 데이터 임의 변경 금지. 기존 매시간 예약과 타 프로젝트 예약 변경·종료 금지. 예약을 만든 **원래 대화**에서 계속하는 것이 사용자 최우선 요구; 플랫폼 제약으로 다른 대화에 출력되면 본 GitHub full handoff를 먼저 읽고 복원, 이전 대화 내용을 읽은 척하거나 사용자에게 재설명 요구하지 않음.

### ② 이번 실제 개발 및 ⑤ git 파일·커밋
- `9e5eec522a170a20da060582a22cbe86b2a1c8f7`, 다음 두 파일을 기존 **main**에 보존형 수정:
  * `src/ai_broadcaster/desktop_chat_tab.py`: 새/중지된 공개 채팅 세션과 **실제로 아직 Ollama/공식 Live2D AI 작업·SQLite 기억 저장을 끝내지 못한 작업자**를 분리하여 추적하는 `_twitch_active_workers` lifecycle set 추가. Stop 버튼은 즉시 UI 읽기 중지 상태로 전환하지만, AI worker가 실제 종료해 종료마커를 Tk 메인 이벤트 루프에서 처리하기 전에는 **새 공개 채팅 AI 연결과 기억 전체 삭제 거부**. 이전 AI 세션 작업이 메모리에 작성 중인데 새 채팅이 같은 기억을 다시 쓰거나 운영자가 대화를 삭제하는 경합을 방지. 기존 응답 FIFO와 중복 채팅 보존 및 기존 Stop UI 동작 유지. 실제 worker `finally`에서 내부 종료마커 보내고, Tk 수신 큐에서는 이전 세션의 늦은 일반 채팅 결과를 여전히 무시하면서도 **해당 종료마커는 반드시 처리**해 잠금 해제. 종료 마커는 대화 내용·사용자 설정을 변경하지 않음.
  * `tests/test_aisting_twitch_ai_integration.py`: 같은 시청자의 동일 채팅 **2,048건 모두 순서·중복 보존·응답 수량** 검사; 이전 AI 작업이 실제 메모리 저장 과정에서 블로킹된 상태에서 Stop→기억 삭제·재연결 차단→worker 종료 이벤트→재연결 잠금 해제 테스트 추가. 테스트 내부 모델은 모의라 지연 1~3초 실제 인증 실증은 아님.
- `22a50a3ff89106b8827bddee0aea54a18f691ce6`, `scripts/gui_official_pipeline_click_windows.py`: 실제 GitHub Actions Windows Tk 앱을 열고 생산 코드의 **공개 채팅 Stop 버튼과 기억 삭제 Tk 버튼 직접 클릭, 블로킹된 이전 AI 응답 작업 존재 시 기억 삭제 및 재연결 차단, 작업 완료 후 잠금 해제**를 검증. AI 모델 응답만 모의, 실제 Windows GUI / 이벤트 루프는 실행.
- `d4f8c35b22a223f231c00b57b80282936fe16a76`, `scripts/gui_official_pipeline_click_windows.py`: Windows GUI 검사에서 `AistingApp`과 `operator_settings.DEFAULT_FILE`/ `conversation_memory.DEFAULT_MEMORY_FILE`의 모듈 import를 **`LOCALAPPDATA` 테스트 전용 경로 고정 이후**로 이동. 실제 설정·SQLite 기본 경로가 disposable CI 폴더 밖 사용자 폴더를 가리키면 검사 실패. 기존 CI 모의 캐릭터/설정/SQLite 내용 해시 불변 검사 유지. 실제 사용자 폴더 삭제·변경 없음.
- 위 파일만 수정; 사용자의 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 확정된 캐릭터/SQLite/OBS 원본 자료는 수정하지 않았다.

### ③ 전체 검증 결과 및 ⑥ Actions URL, Windows EXE 실제 artifact·SHA
- 앞선 소스 두 파일 기준 전량 회귀: https://github.com/junggyeol4444/AISTING/actions/runs/39366884886 : `completed/success`, **2,393 tests, skipped 2, failures 0**.
- Windows 실사용 버튼·AI worker-drain 추가 후 전량 회귀: https://github.com/junggyeol4444/AISTING/actions/runs/39367157853 : `completed/success`, **2,393 tests, skipped 2, failures 0**.
- 최종 `LOCALAPPDATA` 경로 격리 보완이 포함된 실제 최신 코드 기준 전량 회귀: https://github.com/junggyeol4444/AISTING/actions/runs/39367336333 : `completed/success`, **2,393 tests, skipped 2, failures 0**.
- **최종 Windows EXE/GUI/공개수신/OBS/Ollama 통합**: https://github.com/junggyeol4444/AISTING/actions/runs/39367336518 : `completed/success`이며 다음 5개 job 모두 `completed/success`: `windows-exe` (네이티브 Windows EXE 실제 빌드·기존 Tk 버튼 경로), `obs-real-readonly` (disposable Windows CI의 실제 OBS 프로그램 장면·프레임/소스 읽기), `ollama-real-local-e2e` (Windows CI에서 실제 로컬 Ollama 추론), `twitch-public-readonly`, `korean-public-chat-readonly`(치지직·SOOP 공개 채팅 읽기).
- 최신 Windows 네이티브 Tk GUI 로그 (외부 AI/Live2D/OBS 동일 발화는 모의): `GUI_REAL_WINDOWS_PROFILE_PATH_ISOLATED_PASS`, `GUI_NATIVE_CANCEL_NO_LATE_SUCCESS_PASS (SIMULATED MODEL)`, `GUI_STOP_INFLIGHT_SQLITE_DELETE_RECONNECT_BLOCKED_PASS`, `GUI_STOP_INFLIGHT_WORKER_DRAIN_RECONNECT_READY_PASS`, `CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS`. 실제 Windows GUI 버튼/이벤트 흐름은 실행, 실제 TTS→Cubism→OBS 하나의 발화는 실행하지 않음.
- 실제 Windows Actions artifact `AISTING-Windows-EXE-integrated`, ID **12239449527**, size **19,662,327 bytes**, artifact **ZIP SHA-256** `8a7cef54e6450771f2ca1152667dd2a0ca3b3d9cd28bc7191297296efffde4b0`. 이 값은 **ZIP digest이고 AISTING.exe 단독 파일 SHA가 아님**. 위 workflow run Artifacts에서 다운로드.
- 기능 수정 기준 `main` HEAD `d4f8c35b22a223f231c00b57b80282936fe16a76`. 인수인계 문서 업데이트 때문에 이후 실제 HEAD가 다시 바뀌며 최신은 다음 회차에서 확인할 것. 커밋 확인만으로 완료라고 주장하지 말 것.
- 이번 회차 전체 회귀/Windows 경로의 새 코드 실패 없음. 이전 성공한 검사만 재사용한 것이 아니라 위 각 최신 커밋에서 전량 다시 실행해 실제 확인.

### ④ 남은 기능·오류·실증 제한
- **실제 운영자 소유/권리 확보 음성 참조 모델**이 설치된 Windows PC의 GPT-SoVITS **실제 한국어 발화** → 공식 Live2D Cubism 실제 동기 입 움직임 → OBS **동일한 음성**의 프로그램 오디오·영상 경로, Windows AISTING.exe로 전 기능 사용자 조작 실증은 **여전히 미완료**. 이번 Windows Actions의 실제 OBS 읽기와 로컬 Ollama/GUI 버튼 성공은 서로 독립된 CI 작업이며 TTS/Live2D/OBS 동일 발화 전체 실증이 아니다. 음성 합성·모델 자체 음질/시간 지연 증명 아님. 모델/권리 자료/사용자 PC를 임의 요구·접속·훈련하지 말 것.
- YouTube 소유 계정의 키를 이용한 활성 라이브 채팅 **실제 인증 수신** 미완료. 네 플랫폼 실제 100~500명 1~3초 응답/24시간 운영 스트레스 미실증. 2,048건의 동일 채팅 FIFO는 **로컬 모의** 검사로서 실제 플랫폼/모델 부하가 아니다.
- Stop 후 이전 모델 요청을 **취소/되돌리는 것은 불가능할 수 있음**. 이번 변경은 실제 완료 전 메모리 삭제/새 모델 연결을 막아 교차 write 위험을 낮춘 것이며 모델 비정상 hang의 강제 종료 기능은 아님. 동일 발화 음원 샘플 검증/24시간 실제 고장 회복 정책은 후속 작업.
- 사용자 데이터/설정/캐릭터/SQLite 원본 보존, CI는 disposable 임시 사용자 폴더와 모의 외부 발화만 사용. 승인 없이 방송·녹화·채팅 게시·외부 계정 로그인 없음.

### ⑧ 다음 회차에서 반드시 진행할 복수 작업
1. 진짜 승인된 GPT-SoVITS/Live2D/OBS 모델이 있는 환경에서 동일 한국어 음성의 전송→음성 합성→입 움직임→OBS 오디오/영상 타임라인을 **실제 동일 발화로 실증하고 오류 수정**. 없는 경우에는 그 한계를 명시하고 코드·검사·관찰 품질만 개선, 가짜 PASS 주장 금지.
2. 원래 Win Tk EXE의 캐릭터/SQLite 재시작 영속 저장을 실제 앱 프로필 경로의 사용 흐름으로 검사. 채팅 Stop 중단/재시작 작업자/SQLite 파일 잠금, 수천 건 FIFO, 사용자 설정 불변과 정확한 GUI 상태 회복을 함께 확인.
3. 플랫폼 YouTube page/token/ID 중복 보존·중단/재연결/실제 공개 읽기 프로토콜, 한국 2플랫폼/Twitch 및 24h 장기 작업 큐 메모리/CPU/지연·오류 회복 검증. 키 없이 모의 YouTube 테스트를 실제 인증이라고 하지 말 것.
4. 매회 소스 복수 기능 작업을 묶어 진행한 후 전량 회귀·실제 Windows EXE/GUI·CI OBS/Ollama/공개 채팅 전체 검사, 중간 실패 시 원인 수정 후 **다시 전체를 재검증**. 해당 Actions·Artifact ID/ZIP digest·최종 SHA·변경 파일·남은 미실증을 같은 GitHub handoff에 누적.
5. 기존 예약 시간 유지·원래 대화 연결 최우선, 다른 프로젝트 예약 변경하지 않음. 새 채팅에 나타났다면 이전 전체 인수인계와 main 기획 문서부터 읽고 동일 프로젝트를 이어갈 것.

### ⑨ 대화 유지/예약
이번 실행은 기존 AISTING 사용자 대화 안에서 계속 진행. 예약 실행 주기 변경/생성/종료, 타 프로젝트 예약 변경·삭제 없음. 플랫폼 제약으로 새 대화에 출력 시 본 문서를 먼저 읽고 해당 변경 사유를 확인 가능한 범위에서 기록, 사용자가 다시 설명하도록 요구하지 않음.

## 22. 2026-10-20 AISTING 연속 작업 — 수동 Ollama/공식 Live2D/공개 채팅 간 SQLite 작업 충돌 차단

### ① 사용자 원본 요청/금지사항 및 기준
사용자가 "계속"으로 원래 AISTING 대화 안에서 기존 main 코드 개발·수정·실질 검증을 지시. 사용자가 반복 강조한 **복수 기능 묶음 개발 → 전체 회귀 및 Windows EXE/실제 Tk 버튼·OBS/Ollama/공개 채팅 통합검사 → 오류 수정 → 동일 전체 재검증**을 따름. 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 본 문서 앞 절을 반드시 유지. Windows 10/11 x64 기존 Tk `AISTING.exe`, 생성 후 확정 캐릭터 이름·말투·성격 1회 저장·계속 유지, SQLite 기억/설정, 공식 Open-LLM-VTuber/Live2D+권리 있는 한국어 GPT-SoVITS, OBS 음성·영상, YouTube·치지직·SOOP·Twitch 중복 채팅 FIFO와 플랫폼 선택 목표 불변. 새 브랜치/강제푸시/원본 재개발·웹/HTML 대체/유료 API·무단 로그인/사용자 PC 접속/방송·녹화·채팅 발신/권리 없는 모델 학습·캐릭터·SQLite 수정 금지. 예약 시간 변경·타 프로젝트 예약 수정/종료 금지. 가능하면 원래 AISTING 예약 생성 대화에서 계속하고, 불가피한 대화 이전 시 본 GitHub 전체 문서·원본 기획·latest main을 확인하여 사용자 재설명 없이 이어감.

### ② 실제 구현 변경 ⑤ 파일 및 커밋
GitHub `junggyeol4444/AISTING`, **기존 main에만 빠른전진 반영**:
- `6691268008d13a55e3f2e4ba85ee3d7928e4763f`: 파일 3개를 묶음 원자적 커밋:
  1. `src/ai_broadcaster/desktop_chat_tab.py`: `_submit`에서 진행 중 공개 채팅 세션과 Stop 후 아직 SQLite 기억 저장 중인 `_twitch_active_workers`를 검사해 **수동 Ollama 질문/동시 기억 쓰기 차단**. `_start_official_pipeline`도 이전 공개 채팅 AI worker가 완전히 종료되기 전에는 별도 공식 AI/Live2D/OBS 실측 시작 차단. `_start_twitch`에서 수동 Ollama AI 작업 `_busy` 중에는 공개 채팅 AI 연결 차단. 앱 종료 상태 `_closed`도 확인. 같은 확정 캐릭터/기억 데이터가 이전 모델 응답과 새 모델 응답으로 동시에 수정될 수 있는 실사용 경합 차단. 정상 독립 입력은 기존 방식 그대로 실행.
  2. `tests/test_aisting_gui_official_full_pipeline.py`: 위 수동/공개/공식 세 실행 경로의 Stop 이후 교차 경합, 버튼·입력 내용 유지, 거부 시 외부 AI 미호출 회귀 3개 추가.
  3. `scripts/gui_official_pipeline_click_windows.py`: disposable Windows VM에서 실제 `AistingApp`/Tk UI를 열고 앞서 구현된 Stop→SQLite worker 종료 차단 검사에 더하여 **수동 텍스트 전송, 공식 OBS 실측, 공개 채팅 연결 실제 각 Tk 버튼을 눌렀을 때 이전 worker가 남아 있으면 모두 시작되지 않음**을 확인. 외부 모델 서비스 응답만 격리하여 대체; 실제 GPT-SoVITS/Live2D/OBS 동일 발화 통합 증거는 아니다.
- `8f3402ecb5683b416d397fc91563d22336bdbb3e`: `tests/test_aisting_gui_official_full_pipeline.py`의 두 오래된 가짜 GUI fixture에 production 코드가 사용하는 `_closed=False` 상태를 정확히 추가. **실제 코드의 프로그램 종료 차단 기능을 제거/완화하지 않고 기존 테스트를 수정**. 이전의 세 사용자 작업 충돌 차단 유지.
- 후속 사용자 기획/기억·SQLite 실데이터/공식 모델/OBS 소스 파일 미변경.

### ③ 실제 오류·검증·수정 ⑥ Windows EXE/Actions
- 초기 전체 회귀검사 https://github.com/junggyeol4444/AISTING/actions/runs/39369086799 `completed/failure`, `Ran 2396 tests`, **2 errors**, `skipped=2`; 오류 `test_official_public_chat_requires_committed_character_before_consent`, `test_platform_reader_does_not_interrupt_approved_full_probe`의 오래된 `SimpleNamespace` 모의 Tk 객체에 `_closed` 누락. 실제 AistingApp 생성자는 해당 플래그를 가지고 있음. 위 테스트 fixture에 실제 상태 추가 후 전량 재검사.
- **최종 전체 회귀** https://github.com/junggyeol4444/AISTING/actions/runs/39369181912 `completed/success`: `Ran 2396 tests`, `OK (skipped=2)`, **실패 0**.
- **최종 동일 코드 Windows 통합검사** https://github.com/junggyeol4444/AISTING/actions/runs/39369181862 `completed/success`: `windows-exe` (네이티브 Windows EXE 빌드/자체 실행, 실제 Tk GUI 버튼 시나리오), `ollama-real-local-e2e` (CI 격리 환경 실제 로컬 Ollama 한국어 추론), `obs-real-readonly` (별도의 실제 OBS 장면/미터 읽기), `twitch-public-readonly` (Twitch 공개 수신), `korean-public-chat-readonly` (치지직·SOOP 공개 수신) **5개 job 모두 PASS**.
- 실제 Windows GUI job log 필수 증거 `GUI_MANUAL_OFFICIAL_PUBLIC_AI_CROSSMODE_SQLITE_GUARD_PASS`, `GUI_STOP_INFLIGHT_SQLITE_DELETE_RECONNECT_BLOCKED_PASS`, `GUI_STOP_INFLIGHT_WORKER_DRAIN_RECONNECT_READY_PASS`, `CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS`, `GUI_REAL_WINDOWS_PROFILE_PATH_ISOLATED_PASS`.
- 실제 새 GitHub Windows EXE Artifact `AISTING-Windows-EXE-integrated`, ID **12241021086**, size **19,664,646 bytes**, **artifact ZIP** SHA-256 `e14bf08a30cd0c3c570040e8ab35956f0efca99adbddb5700afca24a1224c192`. 이 해시는 ZIP의 digest로 개별 AISTING.exe hash 아님.
- 이번 기능 코드 확인 커밋 `8f3402ecb5683b416d397fc91563d22336bdbb3e`. 본 문서만 수정해도 git main HEAD와 새 CI가 이동할 수 있으므로 다음 실행에서는 최신 main 다시 확인하고 **문서 추가 CI와 기존 실제 코드 성공 run을 구분**.
- 사용자의 기존 100단계 승인/진행 상태를 CI 통과만으로 변경하지 않음.

### ④ 계속 남은 실제 미완료 기능
1. 실제 운영자 승인/권리 확보된 **GPT-SoVITS 한국어 음성 모델·참조 WAV**에서 발화 합성→공식 Live2D/Cubism의 해당 실제 RMS·입 움직임→OBS 프로그램 오디오·영상의 **동일 발화 전체 실기기 E2E**는 아직 실행·검증하지 못함. Windows CI에서 Tk 실제 버튼은 실행했지만 음성 모델/OBS 동시 서비스는 **모의/독립 검사**였으므로 "최종 완료" 주장 금지.
2. **실제 YouTube 활성 라이브 채팅의 소유 키/인증 수신**, 네 플랫폼 동시 실제 100~500명·1~3초 응답·24시간 무중단 부하 실증 미완료. 시뮬레이션 FIFO·YouTube API page/id 테스트 성공을 실제 인증 연결로 주장하지 말 것.
3. 운영자 PC에서 실제 `AISTING.exe` 사람의 실행→캐릭터 생성/재진입·영속 SQLite 기억→공식 Live2D/GPT-SoVITS→OBS 출력, 외부 서비스 안전한 Stop/이상 종료/권한/장시간 GPU/메모리 실증 미완료. 사용자 PC 접근 권한·권리 있는 모델 미제공 시 실제 사용자 테스트 수행 불가.
4. 앞절의 pending original roadmap 항목을 임의 완료 처리하지 않음. 이번 묶음은 서로 다른 AI 작업이 동시에 SQLite에 쓰는 것을 차단했지, 모든 남은 실기기 음성·라이브 연결을 구현했다고 주장하지 않는다.

### ⑦ 사용자 데이터 보존/⑧ 다음 회차 복수 기능
- 사용자 캐릭터 이름/성격/말투·원본 설정·SQLite 기억·OBS/Live2D 프로젝트를 건드리지 않고 GitHub 소스/테스트만 변경. Windows 실버튼 검사는 `LOCALAPPDATA`를 일회용 VM 폴더에 먼저 격리해 원본 설정과 DB 경로를 보호. 계정 로그인·실방송/녹화·채팅 발신·권리 없는 모델 훈련 없음.
- 다음 묶음: (i) 종료·재진입 중 확정 캐릭터·SQLite 실제 persistence round-trip과 Windows Tk 입력·버튼 사용자 흐름 실검증, (ii) 공식 GPT-SoVITS/Live2D/OBS 동일 발화 실제 입력 자료가 접근 가능한 승인 환경에서는 직접 통합 실증·오류 수정, 없으면 미검증 구간 구분, (iii) YouTube API cursor/중복 ID·중지/재연결, 치지직/SOOP/Twitch 공개 수신과 24시간 긴 큐/worker hang 동시성·1~3초 실응답 개선, (iv) 묶음 변경 전부 끝나면 전체 회귀 2396+, Windows EXE/Tk 실버튼/OBS/Ollama/공개채팅 job 실행·실패 수정 후 전량 재검증, (v) 모든 실제 코드·테스트·CI·Artifact·남은 실증 결과를 GitHub 누적 문서에 유지.
- 예약 주기/원래 대화 및 다른 프로젝트 예약은 이번 회차 변경하지 않았다.

## 23. 2026-10-20 같은 대화 최신 실행 — 여러 핵심 기능을 먼저 묶음 개발한 뒤 전체 검사·수정·Windows 재검증

### ① 사용자 원문 지시·기획 및 금지
사용자의 이번 지시: "계속. 내가 개발하고 검증하라고 했지 전부 개발하고 왜 하나 개발하고 검증하고 … 내말 무시하니?" **기능 하나씩 만들어 매번 검사하다가 끝내는 방식 금지**. 현존 실사용 코드를 기준으로 여러 남은 기능을 묶어 구현하고, 묶음 전체가 끝난 뒤 회귀/Windows GUI/EXE/실제 가능한 OBS·Ollama·공개채팅 검사를 일괄 실행. 중간 오류 발견 시 수정 후 전량 재검증. `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 이전 인수인계 전체·사용자 기획이 기준이다. Windows 10/11 x64 기존 `AISTING.exe` 네이티브 Tk만 사용. 기존 확정 캐릭터 이름/말투/성격 1회 저장 및 SQLite 기억, GPT-SoVITS 한국어 TTS/공식 Live2D/OBS, 치지직·SOOP·YouTube·Twitch 모든 채팅/중복 포함 FIFO 유지. 브랜치 생성/삭제·강제푸시·재개발/웹·HTML 대체·유료 API/사용자 계정 무단 로그인·사용자 PC 무단 접속/방송/녹화·채팅 발신/무권리 음성 훈련 및 저장된 사용자 데이터 변경 금지. 원래 매시간 AISTING 예약 및 다른 프로젝트 예약 변경 금지. 사용자에게 SHA만 보고하면서 작업하지 않는 척하는 행위 금지.

### ② 실제 완료한 묶음 개발·⑤ 소스/커밋
- 기존 GitHub `junggyeol4444/AISTING` **main** 하나에 **7개 파일을 1개 원자적 기능 묶음 커밋** `c9163210526ad0553d8787984281a667876b150a`로 빠른전진:
  1. `src/ai_broadcaster/multiplatform_readonly.py`: 읽기 전용 YouTube videos/liveChat/messages HTTP 요청마다 유효한 사용자 `max_seconds`의 남은 기간을 고려한 로컬 timeout 한도 적용(기본 최대 10초; 짧은 제한의 최솟값 0.1초), 제한이 지나서 뒤늦게 도착한 페이지의 구식 채팅을 새 메시지로 표시하지 않음. 이미 요청한 `pageToken`을 서버가 다음 토큰으로 그대로 반환하는 비정상 상태는 채팅을 전달하기 전 명확히 실패하고 무한 재조회/중복 API 사용을 방지. 별개 ID의 동일 텍스트는 FIFO로 각각 보존, 기존 50,000 ID 순환 dedup 유지. 실제 사용자 인증/API 키를 이용한 라이브 방송 접속은 하지 않았음.
  2. `src/ai_broadcaster/desktop_chat_tab.py`: 실제 플랫폼 네트워크 리더 쪽에 `_enqueue_public_event` 도입. Tk 메인 스레드가 읽는 결과 큐가 4096개 이상일 때 네트워크 **수신 스레드만** 역압 대기, 주기적으로 Stop 확인 후 깨어나므로 GUI 멈춤/무한 대기 없이 정상 실행 시 모든 수신 메시지/중복/FIFO 보존. Stop 또는 앱 닫기는 이미 정의된 정책에 따라 종료. 기존 작업자·SQLite 보호 및 원본 Tk 화면 유지.
  3. `src/ai_broadcaster/original_plan_full_pipeline.py`: 공식 음성·Cubism↔OBS 동시 검사 마지막 `ensure_offline()` 후에도 운영자 Stop Event를 다시 검사. 마지막 OBS status 요청 중 취소하면 실제 출력 후보를 GUI에 성공으로 되돌리지 않음. 음성 질문 이미 송신된 경우 재전송 없음, 실제 녹화/송출 명령 없음.
  4. `tests/test_aisting_twitch_ai_integration.py`: 작게 제한한 읽기 큐에서 네트워크 스레드 역압 후 이벤트 5건 정확한 FIFO·무누락 처리, 대기 중 Stop이면 추가 채팅이 큐에 들어가지 않는 회귀 2개.
  5. `tests/test_aisting_multiplatform_readonly.py`: YouTube 반복 페이지 토큰 안전 종료·단일 ID 무중복, 매우 짧은 운영자 검사 제한에서 HTTP 요청 timeout 상한 및 Stop 정상 종료 회귀 2개.
  6. `tests/test_aisting_official_chat_obs_pipeline.py`: 마지막 OBS status 읽기 중 운영자가 Stop 요청하면 이미 전송된 질문 1회는 그대로 두면서 전체 동시 관찰 성공으로 분류하지 않는 검사 추가.
  7. `scripts/gui_official_pipeline_click_windows.py`: 기존 Windows 실제 AistingApp/Tk 버튼 이벤트·외부 모델만 mock하는 안전 검사 흐름 끝에 **실제 격리된 사용자 Windows LOCALAPPDATA 경로**로 신규 확정 custom 캐릭터를 `commit_character_identity`로 디스크에 저장, 실제 `ConversationMemory` SQLite에 중복 채팅 텍스트 2건을 기록, 별도 연결로 재조회, Windows Tk 앱 완전 종료 후 **동일 프로필에서 AistingApp 창을 실제 다시 생성하고 저장 캐릭터 모드·이름·성격·말투·SQLite 2건 및 Chat 탭을 확인**하는 실사용 영속 검사 추가. 테스트는 임시 Windows 전용 폴더만 읽고 쓰며 원래 사용자 PC/캐릭터 파일에 접근하지 않음. 앞서 만든 기존 격리 테스트 설정/SQLite 해시는 변경하지 않음.
- **중간 오류 수정 커밋** `bbded9f96321fe45cb21dab51932a643279d23b0`: `tests/test_aisting_multiplatform_readonly.py`의 YouTube Stop 테스트가 기존 정상 `stopped` lifecycle event를 오류로 가정한 새 테스트 기대값을 정정. 실제 프로덕션 Stop 동작을 제거하지 않음. 이 수정까지 포함한 동일 코드 전체를 다시 검증.
- 원래 main 코드를 지우거나 브랜치를 교체하거나 로드맵 승인 상태를 수정하지 않았다.

### ③ 실제 전체 검증/실패 수정/⑥ Windows 산출물
- 첫 묶음 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39371944536 : `completed/failure`; `Ran 2401 tests`, 1 failure, 2 skipped. `test_youtube_small_operator_budget_bounds_http_timeout`의 모의 채팅 Stop 이벤트 `('stopped','existingChatId')` 발생을 예상하지 못한 테스트 오류. 첫 Windows https://github.com/junggyeol4444/AISTING/actions/runs/39371944502 역시 같은 변경의 예전 단위검사가 실패해 전체 PASS 아님. 즉시 기존 테스트 기대값을 정정하여 **전체 검사 재수행**.
- **최신 수정 코드 전체 회귀 PASS** https://github.com/junggyeol4444/AISTING/actions/runs/39372153240 : `completed/success`, 로그 `Ran 2401 tests`, `OK (skipped=2)`, 오류·실패 0.
- **같은 실제 수정 코드 Windows 전체 PASS** https://github.com/junggyeol4444/AISTING/actions/runs/39372153245 : `completed/success`이며 5개 job 모두 `completed/success`: `windows-exe`(Windows x64 EXE 실제 빌드·실행/원본 Tk 창 버튼·재시작·보존), `obs-real-readonly`(별도 격리 실제 OBS 확인), `ollama-real-local-e2e`(별도 실제 로컬 Ollama 한국어 추론), `twitch-public-readonly`, `korean-public-chat-readonly`(치지직·SOOP 실제 공개 수신).
- Windows job 로그에서 `GUI_NATIVE_CHARACTER_SQLITE_REOPEN_PERSISTENCE_PASS` 및 **`GUI_NATIVE_RESTART_REAL_PERSONA_SQLITE_PERSISTENCE_PASS`** 실제 확인. 기존 `GUI_NATIVE_CANCEL_NO_LATE_SUCCESS_PASS (SIMULATED MODEL)`, `GUI_MANUAL_OFFICIAL_PUBLIC_AI_CROSSMODE_SQLITE_GUARD_PASS`, `CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS` 확인. GPT-SoVITS/Live2D/OBS 동일 실제 발화가 아님.
- 신규 Windows Actions Artifact `AISTING-Windows-EXE-integrated`, ID **12242386195**, size **19,668,124 bytes**, 산출물 ZIP digest SHA-256 `d7fd6ceadafb55de83c62f1d22adc3c5c6c404d16ffeb89f21f938d9bd3b8b9d`. EXE 단독 해시로 표시 금지.
- 마지막 기능 검증 원본 커밋 `bbded9f96321fe45cb21dab51932a643279d23b0`. 이 문서 갱신 후 main은 새 documentation commit으로 앞서 나가고 CI가 다시 발생할 수 있음. 다음 회차는 실제 HEAD와 해당 커밋의 테스트·artifact 구분.

### ④ 여전히 남은 기능·실증 한계 (완료 표기 금지)
1. 사용자 소유·음성 권리 확보된 **실제 GPT-SoVITS 모델과 참고 WAV**로 생성한 한국어 음성 → 실제 공식 Cubism/Live2D 립싱크 → 동일 발화가 흐르는 OBS 실제 프로그램 오디오·영상 및 EXE에서 사용자 버튼 전체 흐름은 **실기기 모델/권리/환경 접근이 없어서 미완료**. 코드는 연결·검사 준비, Windows 실제 Tk 버튼은 테스트했지만 외부 음성 모델/OBS 동일 발화는 모의/독립 CI임. 실제 음질·지연·동일 음원 여부 PASS 아님.
2. 실제 사용자 소유 YouTube API 키/활성 라이브 채팅 조회·인증 수신, 네 플랫폼 수백 명 실제 부하·응답 1~3초·24시간 운영 실측 미실증. 이번 YouTube 커서와 API 시간 제한은 **모의 응답 단위 검사** 통과다.
3. 사용자 Windows PC에 설치된 실제 GPT-SoVITS·WebView2·Live2D 에셋·OBS가 함께 작동하고 며칠 연속 재실행/실방송 품질을 유지하는 전 경로 미검증. 운영자 미승인 상태에서 방송 시작·녹화·채팅 게시·음성 학습/사용자 데이터 외부 송신하지 않는다.
4. `config/roadmap.json`의 원본 100단계 중 사용자 승인 pending 상태를 임의 완료 처리하지 않음. 실제 사용자 설치/전 기능 동작 검증에 아직 인적 장비·외부 인증 의존성 있음.

### ⑦ 사용자 원자료 보존
모든 코드/테스트는 기존 GitHub main에서 빠른전진 변경, 원본 기획·roadmap·user 캐릭터/기억/OBS 자료 미변경. Windows CI의 persist 시나리오는 일회용 LOCALAPPDATA에서만 완전 격리 실행, 기존 사용자 PC 원격 접속 없음. 음성/OBS 실제 방송·녹화/채팅 송신 없음. 기존 시간당 예약·타 프로젝트 예약 변경하지 않음.

### ⑧ 후속 실행 시 해야 할 실제 복수 기능 묶음
1. 합법적 음성·Live2D/OBS 장비가 제공되는 운영자 승인 Windows 환경에서는 **GPT-SoVITS 실제 한국어 TTS 출력 → 원래 Live2D/Cubism 입 움직임 → OBS 실제 오디오/영상 동일 발화**를 종단 간 실측·문제 수정. 이런 환경에 접근 불가하면 미실증 유지.
2. 장시간 플랫폼 읽기와 AI 모델 응답 시간 사이의 이벤트 큐·FIFO·역압 정책에서 24h·100~500명 실제 동시 유입, UI/메모리/CPU·발화 1~3초 지연을 실제 부하와 CI 성능 테스트로 구분 검증. YouTube 키가 없으면 합법 공개 모의 API cursor/Stop/재연결 테스트만 수행, 실인증 성공으로 포장 금지.
3. 기존 Tk GUI의 캐릭터 확정·방송설정 원자 저장/재실행·SQLite 중복 기억 2건 이상의 여러 번 재부팅·Windows 파일 잠금/종료 시 스레드 청소/사용자 버튼 결과 직접 확인을 추가 검증.
4. 여러 기능 개발·오류 수정부터 먼저 **한 묶음으로** 완료한 뒤 전체 회귀 + Windows EXE·Tk GUI + 실제 가능한 Ollama/OBS/공개 채팅 통합 검사. 발견된 오류 수정 후 해당 **최신 코드 전체 재검증**. 단일 코드마다 검사 반복·CI 통과로 핵심 미완료 부분 완료 주장 금지.
5. 실제 변경 소스·실패·수정·테스트 합계/Actions 링크/Windows artifact ID/digest/미실증을 이 동일한 전체 인수인계 문서에 누적 유지.

### ⑨ 대화·예약 유지
가능하면 이 원래 AISTING 사용자/예약 대화에서 매시간 개발·검증·결과 보고. 기술적으로 다른 대화에 출력되면 원래 대화를 참조한 척하지 않고 본 GitHub 전체 인수인계, 원본 기획·로드맵·main과 마지막 CI를 먼저 확인하여 맥락 손실 없이 이어감. 이번 회차 기존 예약 및 다른 프로젝트 예약을 생성·변경·중지하지 않았음.

## 24. 2026-10-20 같은 AISTING 대화 — AI FIFO 장기 역압/YouTube 순환 페이지 토큰/네이티브 GUI 3회 재실행 묶음

### ① 사용자 원문 요구와 고정 금지사항
이번 지시 `계속`. 최근 사용자 지시대로 **남아 있는 복수 기능을 한 묶음으로 먼저 개발하고, 코드·테스트 개발이 끝난 뒤 전량 회귀 및 Windows EXE·실제 Tk GUI·OBS/Ollama/공개 수신 검사**; 실패 시 한 부분만 PASS 처리하지 말고 누적 전체를 수정·재검증한다. 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 이 인수인계 전체가 최우선. Windows 10/11 x64 네이티브 `AISTING.exe`/Tk GUI 유지; 캐릭터 이름·말투·성격 최초 1회 확정 후 SQLite 기억 포함 영속, 원래 선택 플랫폼·기획, 공식 Open-LLM-VTuber/Live2D, 사용자 권리 확보 GPT-SoVITS 한국어 TTS, OBS 실제 오디오/영상과 4개 플랫폼(치지직/SOOP/Twitch/YouTube) 중복 문장도 모두 FIFO 응답. 사용자 PC 무단 접속·라이브 송출/녹화/채팅 게시, 무단 API 결제·계정 로그인·음성 모델 훈련, HTML/웹 대체·임의 새 브랜치/강제푸시·설정/캐릭터/SQLite 삭제·로드맵 pending 임의 완료 금지. 기존 시간당 예약과 타 프로젝트 예약을 변경하지 말 것. 가능한 경우 예약 원래 대화에서 계속하고 다른 대화에서 실행된 경우 본 파일을 온전히 먼저 읽고 이어갈 것.

### ② 실제 여러 기능 묶음 개발·⑤ 정확한 소스 변경/커밋
- `junggyeol4444/AISTING` 기존 **main**, 기능 5파일을 단일 fast-forward commit `cb1b944555a3b9cfc1b7c15820f1c37b26c155a8`로 동시에 수정. 새 브랜치·강제푸시·원본 기획/로드맵 변경 없음.
  1. `src/ai_broadcaster/desktop_chat_tab.py`: 앞서 `_results` Tk 수신 큐만 `4096`개 역압 제한하던 **실제 AI 응답 대기 `_twitch_ai_inbox` SimpleQueue의 무한 대기 누적 버그**를 수정. 이제 공개 채팅 리더가 `_results` 및 AI FIFO 길이를 함께 확인하여 느린 로컬 AI 응답 속도에 맞춰 네트워크 **리더 스레드에서만** 잠시 대기. Tk 메인 이벤트 루프를 막지 않으며 Stop Event가 오면 풀려나 뒤늦은 채팅을 추가하지 않음. 메시지 텍스트의 중복을 삭제하거나 합치지 않고 기존 수신 순서 유지. 버퍼 규모는 각 대기 큐 최대 4096 근방으로 유도, 네트워크/OS 버퍼 전체의 절대 메모리 상한 보장이나 실제 24시간 시험과는 다름.
  2. `src/ai_broadcaster/multiplatform_readonly.py`: YouTube API `nextPageToken`이 단순 즉시 같은 토큰을 반복하는 경우뿐 아니라 **A→B→A처럼 여러 페이지가 순환하는 경우**를 감지. 최근 페이지 토큰을 최대 10,000개 유계 deque/set으로 기록, 순환 확인 즉시 재전송되는 페이지 내용을 AI FIFO에 넣기 전 중단. 메시지 고유 ID 기준 재수신만 중복 제거하고 별도 ID의 동일 문장은 각각 유지. 실제 소유 YouTube 계정/인증 채팅을 수행한 것은 아님.
  3. `tests/test_aisting_twitch_ai_integration.py`: 느린 AI로 미처리된 메시지 대기열 때문에 리더가 역압을 받는지, AI 대기열이 비워지면 같은 순서로 재개하는지, 중지 누르면 새 채팅을 더 쌓지 않고 대기에서 종료하는지 재현 2개 검사.
  4. `tests/test_aisting_multiplatform_readonly.py`: 3개 YouTube 모의 페이지에서 A→B→A 토큰 순환을 재현, 마지막 잘못된 페이지는 전달되지 않고 먼저 유효하게 받은 별도 ID의 같은 문장 2건은 각각 전달되는지 검사.
  5. `scripts/gui_official_pipeline_click_windows.py`: 기존 disposable Windows runner의 **실제 `AistingApp` Tk 창**에서 1280×768과 1366×768에 공식 음성/OBS 버튼이 실제 화면 안에 있는지 확인. 기존 창 종료→재시작 이후 다시 3번째 실제 Tk 앱을 생성해 한 번 확정된 캐릭터 이름/스타일/성격, 별개의 동일 질문 두 건과 응답 순서가 실제 SQLite에서 변함없이 남았는지 검증. 외부 모델/OBS/TTS 동일 음성은 별도로 실증하지 않았고, 테스트는 CI 전용 LOCALAPPDATA만 사용.

### ③ 전량 검사·수정 상태 / ⑥ Windows EXE 산출물
- **최신 기능 묶음 전체 회귀** https://github.com/junggyeol4444/AISTING/actions/runs/39374581641 — `completed/success`, 실제 로그 `Ran 2404 tests`, `OK (skipped=2)`, 실패 0.
- **동일 코드 기준 Windows 통합** https://github.com/junggyeol4444/AISTING/actions/runs/39374581632 — `completed/success`, 정확히 `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly` 5개 job 모두 성공. CI 실제 Ollama/OBS/공개 수신은 독립 작업; 실제 GPT-SoVITS→Live2D→OBS 동일 한국어 발화 통합은 아님.
- Windows EXE 빌드 후 실제 Windows Tk GUI 로그 `GUI_NATIVE_1280_1366_WIDTH_BUTTON_VISIBLE_PASS`, `GUI_NATIVE_THIRD_SESSION_CHARACTER_MEMORY_PERSISTENCE_PASS`, `GUI_NATIVE_RESTART_REAL_PERSONA_SQLITE_PERSISTENCE_PASS`, `GUI_MANUAL_OFFICIAL_PUBLIC_AI_CROSSMODE_SQLITE_GUARD_PASS`, `CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS` 확인. 사용자 PC 실기기 방문/화면 클릭이라고 주장하지 말 것; GitHub Windows runner에서 네이티브 원본 Tk 콜백을 실제 실행한 것.
- 새 GitHub EXE artifact `AISTING-Windows-EXE-integrated` ID **12241984483**, ZIP bytes **19,669,882**, artifact **ZIP SHA-256** `ef61c6335b0ee1163317e5f217a34e34bcf6ce11c633f0237e5350c1fec4d6b3`. EXE 파일 단독 SHA 아님.
- 이번 묶음의 최초 전체 회귀/Windows 실행에서 모두 성공하였으므로 중간 실패/수정 없이 최종 합격. 본 인수인계 문서 업데이트 이후 main HEAD가 새 커밋으로 이동, 문서-only 새 CI가 발생할 수 있음. 위 기능 코드 검증 커밋 `cb1b944555a3b9cfc1b7c15820f1c37b26c155a8`과 구분.
- Windows 10/11 실제 사용자 PC의 모든 음성·방송 기능이 되는 것으로 보증하지 않음.

### ④ 남은 기능과 미검증/실증 경계
1. **진짜 사용자 권리 확보 음성 모델·참조 WAV가 있는 Windows PC에서 GPT-SoVITS 한국어 음성 생성 → 원본 공식 Live2D/Cubism 실제 해당 발화 립싱크 → OBS 오디오·영상이 한 발화로 연결되는 전체 경로**는 여전히 실제 모델/권한/장비 접근이 없어 미실증. 현재 CI는 원본 Tk 네이티브 GUI에 대한 격리 외부 mock + 독립 OBS/Ollama 검사.
2. 실제 소유 YouTube API 키/활성 라이브 채팅 인증 수신, 네 플랫폼 동시 100~500명 응답 지연 1~3초와 24시간 무인 장기 실운용 미완료. 유계 10,000 페이지 토큰 캐시의 오래된 토큰 재등장은 감지되지 않을 수 있음. AI 큐 제한은 로컬 메모리 폭주 위험을 낮출 뿐 긴급 상황/채팅 폭주를 처리한 실제 성능 숫자가 아님.
3. 원래 Windows 설치 EXE를 사용자가 직접 설치·조작한 장기 세션, 권리·모델·OBS 버전별 정합성 및 라이브 동시 출력 미검증. OBS 장면 읽기와 사용자 승인 녹화·실방송은 엄격히 별개, 승인 없이 송출·녹화 금지.
4. `config/roadmap.json`의 pending 항목을 CI 성공만으로 completed 처리 금지. 남은 기획 우선 순위는 사용자 원문 및 본 문서 전항에 있는 실사용 미완료 기능 그대로.

### ⑦ 사용자 자료/설정 보존
원본 저장 확정 캐릭터 이름·말투·성격/SQLite·Windows 사용자 OBS 구성·공식 Live2D 모델을 건드리지 않고 GitHub 소스·검사 파일만 수정. Windows 실제 앱 3회 생성 검사에 사용된 설정과 SQLite는 임시 LOCALAPPDATA에서만 생성/재조회/삭제. 사용자 PC 및 실제 방송 계정 접속/외부 송신·녹화/음성 학습/유료 API 호출 없음.

### ⑧ 다음 회차의 구체적인 복수 과제
- 실제 승인된 GPT-SoVITS 한국어 음성·Live2D 에셋·OBS가 사용 가능한 환경이면 **동일 발화 전체 E2E 및 한 번의 질문만 전달되었는지 직접 검증/결함 수정**. 아니면 대체 mock를 실기기로 포장하지 않기.
- Tk+AI 수신 FIFO를 수천건 이상 동시 유입하고 모델 응답이 늦을 때 GUI 반응/메모리·CPU·중지/재연결을 더 오래 점검. 네 플랫폼 실제 24h·수백 명 처리 및 지연은 독립 미실증 유지.
- 실제 Windows EXE 사용자 설정/SQLite 여러 세션 영속, 강제 비정상 종료 복구/OBS 외부 연결 중단, YouTube API token/HTTP 중단·유효 채팅 수신 재시도에 대한 중복 방지 고도화.
- 여러 남은 기능 먼저 묶음 개발 → 전량 회귀 + Windows EXE/Tk GUI + 가능한 실제 OBS/Ollama/공개 채팅 검증 → 실패 수정 후 전량 재검사. 완료한 작은 단위만 보여주지 말고 기획 전체의 미완료를 중심으로 작업.
- 신규 코드/검사/Actions/artifact/실제 미완료를 본 파일에 누적, 브랜치·예약/타 프로젝트 예약 변경 금지.

### ⑨ 원래 예약 대화·이동 사유
기존 AISTING 예약을 만든 원래 채팅에서 결과를 이어가는 사용자 지시 유지. 이 회차 예약 만들기/수정/종료 없음. 플랫폼 시스템 제약으로 다른 채팅에서 나타날 경우 본 GitHub 누적 인수인계 1~24절과 원본 기획/100단계 상태/최신 main/Actions를 우선 읽어 변경 사유를 확인 가능한 수준에서만 설명, 사용자에게 맥락 재입력 요구하지 않음.

## 25. 2026-10-20 15시 이후 원래 대화 계속 — YouTube 유휴 채팅 유지·응답 무결성·Tk 대화 출력 상한 묶음 개발

### ① 원본 기획/사용자 명령·금지
사용자 지시 "계속"에 따라 원래 AISTING 예약 대화에서 기존 GitHub `junggyeol4444/AISTING` **main**을 이어서 개발. 원본 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 및 누적 전체 인수인계 1~24절 우선 확인. 사용자가 정한 순서 **복수 실제 기능을 먼저 묶음 개발→전체 회귀검사·Windows 실제 EXE/네이티브 Tk GUI/OBS/Ollama/공개 채팅 통합검사→실패 수정 후 전량 재검증**, 기능 하나씩 검증 후 개발 반복 금지. 원래 확정한 캐릭터 이름·말투·성격 1회 저장, SQLite 기억·설정, Windows 10/11 x64 `AISTING.exe`/Tk 원본, 공식 Open-LLM-VTuber/Live2D/Cubism·권리 확보된 GPT-SoVITS 한국어 음성·OBS, 4개 플랫폼(치지직/SOOP/Twitch/YouTube) 모든 실제 채팅과 동일 문장 중복도 FIFO 응답 목표 보존. 임의 신규 브랜치/삭제·강제푸시/이전 코드 재개발·웹/HTML 대체·사용자 PC 무단 접속·계정 로그인/유료 API·실방송/녹화·채팅 게시·권리 없는 음성 훈련·SQLite/원본 설정 삭제·미승인 100단계 완료 주장 금지. 매시간 기존 AISTING 예약과 타 프로젝트 예약 변경/중지/생성하지 않음.

### ② 실제 완료한 복수 개발 및 ⑤ 정확한 파일/커밋
- 기존 `main`에 소스·테스트 총 **4개 파일을 1개 원자적 fast-forward 커밋** `94681a654041484768b8e84dca28a1b1d39d8b0b`로 반영:
  1. `src/ai_broadcaster/multiplatform_readonly.py`: YouTube `liveChatMessages.list`의 빈 채팅 페이지에서 **현재 `pageToken`과 `nextPageToken`이 같아도 `items=[]`일 때는 유휴 응답으로 취급하고 API 지정 `pollingIntervalMillis`만큼 기다렸다가 다음 요청**. 무해한 무채팅 폴링에서 불필요하게 연결 종료하던 문제 보완. 메시지가 들어 있는 중복 토큰이나 여러 페이지의 순환 A→B→A는 기존처럼 배포 전 실패 처리; 메시지 ID가 다른 같은 문장은 모두 전달, 동일 ID만 유계 캐시 기준 중복 제거. 응답이 JSON 객체가 아니거나 메시지 목록이 배열이 아니면 아무 채팅도 내보내기 전 유효성 검증으로 거부. YouTube 실제 소유 계정/라이브 인증 테스트 아님. 공식 문서 `liveChatMessages.list` 페이지 토큰과 서버 지정 폴링 지침 확인(https://developers.google.com/youtube/data/live/reference/rest/v3/liveChatMessages/list).
  2. `src/ai_broadcaster/desktop_chat_tab.py`: 기존 네이티브 Tk `_dialog` Text 위젯의 화면 대화 기록이 24시간 길게 누적되어 메모리가 계속 증가할 수 있으므로 **표시된 화면 텍스트 물리 줄 수가 12,000줄을 넘으면 맨 위 4,000줄을 묶음 삭제**. Tk UI에만 적용, 기존 FIFO 메시지/중복/AI 요청·SQLite 지속 기억·화면에 새로 표시하는 채팅 내용은 수정하거나 버리지 않음. 매 메시지 하나씩 비용 큰 잘라내기 작업을 하지 않음. Text 위젯 예외에서도 `state=disabled` 복구.
  3. `tests/test_aisting_multiplatform_readonly.py`: YouTube 최초 빈 페이지→같은 토큰을 유지한 빈 응답→늦게 도착한 한국어 채팅의 유지/순서/종료 이벤트를 검사; 비객체 HTTP 응답이 채팅을 전달하지 않고 거부되는지 검사. 기존 잘못된 토큰/메시지 ID/유저별 중복 보존 테스트 유지.
  4. `tests/test_aisting_gui_transcript_window.py` 신규: 실제 production `LocalChatTab._append`을 대상에 호출해 중복된 한국어 채팅 문자열/유니코드 출력 순서 보존, 표시창 12,000줄 초과에서 **표시만 상단 정리**, Tk 오류 시 disabled 복구를 검증. 실제 Tk GUI 자체의 Windows 실행은 별도 통합검사에 포함되어 있으나 이 파일의 표시 상한 검사는 Headless fake Text 단위검사이며 실제 사용자 PC의 24시간 가동 실증이 아니다.
- 위 4개 파일 밖 원래 100단계 기획, 캐릭터/설정/SQLite, OBS 프로젝트, Live2D 모델/음성 파일 미변경.

### ③ 전량 검사·발견 오류 및 ⑥ 실제 Actions Windows 산출물
- 묶음 커밋의 전량 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39379572203 — `completed/success`, 실제 로그 `Ran 2409 tests`, `OK (skipped=2)`, **실패 0**.
- 동일 소스 Windows 전체 https://github.com/junggyeol4444/AISTING/actions/runs/39379572287 — `completed/success`, `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly` 5개 작업 모두 성공. `windows-exe` job은 실제 Windows x64 네이티브 EXE 빌드/앱 자체 실행과 기존 Windows Tk GUI 버튼·설정 보존 검증; OBS 및 Ollama는 독립 Windows CI 검사. 실제 GPT-SoVITS+Cubism+OBS의 동일 발화 엔드투엔드 성공 증명이 아님.
- 실제 Windows Artifact `AISTING-Windows-EXE-integrated`, ID **12244409763**, ZIP bytes **19,674,147**, GitHub artifact **ZIP SHA-256** `3b02a37376536e7a653514a7dbf7596d0bd33d54c154eab1900dae215a985eb4` (개별 EXE 해시 아님).
- 이번 기능 수정본의 최초 전체 회귀 및 Windows 통합검사 모두 성공. 중간 실패가 없었으므로 오류 수정으로 인한 추가 커밋 없음. 이 문서 갱신은 별도 main 커밋과 새 CI 실행을 발생시킬 수 있으며, 위 이미 성공한 실제 소스 커밋 `94681a654041484768b8e84dca28a1b1d39d8b0b`과 구분.

### ④ 미완료 기능·미실증을 완료로 포장하지 말 것
- 실제 권리를 확인한 GPT-SoVITS 한국어 음성 모델 및 참조 WAV가 운영자 Windows PC에 설치된 상태에서 **한 한국어 발화의 GPT-SoVITS 실제 합성→공식 Live2D/Cubism 입 움직임→OBS 프로그램 음성·영상 전체 연동 실증** 미수행. Windows CI의 실제 Tk/UI·OBS·Ollama 성공은 독립 경로이며, 동일 발화는 외부 모델 mock/미실행이므로 전체 PASS라고 표시 금지.
- 실제 활성 YouTube 라이브의 사용자 소유 Data API 키/승인으로 실제 채팅 수신, 네 플랫폼 100~500명 동시 실제 FIFO·1~3초 응답·24시간 무인 가동 실증 미완료. 가짜 API 페이지 응답 검증 통과를 실제 인증 수신 성공으로 주장하지 않음.
- Tk 표시 대화 기록은 길이가 넘으면 **옛 표시 줄만 정리**됨. 이것은 모든 과거 채팅의 영구 기록/전수 보관 기능이 아니다. 시청자 모두에게 응답하려는 실제 AI FIFO·SQLite 저장 기록과 구분. 장시간 실제 사용자 장비·실라이브 환경에서 CPU/메모리 수치를 측정한 것은 아님.
- 사용자 원래 100단계 승인 pending은 변경하지 않음. 실제 GPT-SoVITS 모델·WebView2 공식 Live2D·OBS 설치 실기기 E2E 및 장시간 장애 회복이 남아 있다.

### ⑦ 사용자 데이터·프로젝트 보존, ⑧ 다음 회차
원래 설정 캐릭터·SQLite·OBS·Live2D 자료·기획서 미수정. GitHub main에만 fast-forward 코드·테스트 변경. CI는 disposable Windows 사용자 폴더와 공개 읽기 전용, 모의 음성 경로만 사용. 사용자 PC 원격 접근·무단 라이브/녹화·채팅 게시·음성 훈련·유료 API 사용 없음.
- 다음 묶음에서는 모델/참조 음성·OBS를 사용할 명시적으로 승인된 Windows 환경이 있다면 실제 GPT-SoVITS 한국어 발화→공식 Live2D/Cubism→OBS 동일 발화 실측을 구현/실행/오류 수정. 환경 없으면 외부 모델 PASS 가정 금지.
- YouTube 실제 라이브 방송 승인·API 키가 있으면 실제 수신 연결 및 커서/FIFO/중단 지연 측정. 그렇지 않으면 모의 API 장시간 변칙 응답과 중복·쿼터·중지/연결 복구의 누적 기능/검사 계속.
- 24시간/수백 명 공개 채팅·느린 로컬 AI 응답으로 인한 큐 지연/GUI 표시창 CPU·메모리/응답시간, 캐릭터/SQLite 실기기 재시작 및 OS 비정상 종료 데이터 복구를 구분 검증.
- 기능 여러 개 먼저 개발한 뒤 **전량 회귀+Windows EXE·네이티브 GUI+가능한 Ollama/OBS/공개 채팅 검사**, 실패 발견 시 고쳐서 전량 재검증. 이 문서에 변경 파일/CI/Artifact ID/미실증을 누적 업데이트.
- 기존 시간당 AISTING 예약과 타 프로젝트 예약은 이번 실행에서 변경/생성/종료하지 않음. 원래 예약 생성 대화에서 이어가라는 사용자 요청 유지. 플랫폼이 불가피하게 별도 채팅으로 연결하면 이전 기획·본 문서 1~25절·최신 main/CI 우선 읽어 사용자 설명 반복 없이 인수인계.

## 26. 2026-10-20 이번 연속 실행 — SQLite 외부 파일 보호, 구형 설정 4플랫폼 지원, YouTube 일시 장애 자동복구 묶음 개발·Windows 재검증

### ① 사용자 원지시/금지·기획 재확인
사용자 지시 "계속": 사용자 지정대로 **실질적으로 남은 기능을 여러 개 한꺼번에 개발한 다음 전체 회귀/Windows EXE·실제 Tk·OBS/Ollama·공개 채팅 검사를 통째로 실행, 오류 발견 시 고쳐서 전량 재검증**. 기존 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 본 문서 1~25절, 기존 Windows 10/11 x64 네이티브 EXE/Tk, 확정 캐릭터 이름·말투·성격과 SQLite 기억, 공식 Open-LLM-VTuber/Live2D·권리 있는 GPT-SoVITS 한국어 음성·OBS, 네 플랫폼(치지직/SOOP/Twitch/YouTube) 모든 채팅/중복 포함 FIFO 목표를 계속 유지. 신규 브랜치 생성/삭제·강제푸시·웹/HTML로 바꿈·코드 재개발·원본 롤백·유료 API/계정 로그인·사용자 PC 무단 접속·실방송/녹화·채팅 게시/사용자 데이터 변경 및 권리 없는 음성 훈련 금지. 기존 AISTING 매시간 예약·타 프로젝트 예약 변경하지 않음. SHA 숫자 검사가 개발 성과는 아님.

### ② 실제 코드·테스트 변경/⑤ main 커밋
- GitHub `junggyeol4444/AISTING` 기존 `main`에 **6파일을 단일 묶음 기능 커밋** `d23d5ee57761781c49913f2f71361410e5e6b61b`로 반영:
  1. `src/ai_broadcaster/conversation_memory.py`: 기존 SQLite 경로가 이미 있을 경우 **읽기 전용 URI 접근으로 application_id, 유일한 exchanges 테이블, 열 이름·선언 타입·PK·NOT NULL 스키마 확인 후에만 실제 기록용으로 열기**. 다른 프로그램 테이블/손상된 파일/링크 경로는 읽기 전용 확인에서 거절하여 새 exchanges 테이블을 만들지 않음. 기존 정상 AISTING 기억은 그대로 다시 열기/쓰기. 실제 사용자 DB를 수정하지 않고 CI 임시 DB로 시험.
  2. `src/ai_broadcaster/operator_settings.py`: 구형 운영 설정 `PLATFORMS`에 누락된 **soop** 추가, 현재 GUI의 `offline_settings.py`가 제공하는 치지직·SOOP·유튜브·트위치 네 플랫폼과 일치. 기존 JSON 스키마/저장 캐릭터 값을 초기화하지 않음.
  3. `src/ai_broadcaster/multiplatform_readonly.py`: 소유 API 키로 승인된 경우에만 실행되는 YouTube read-only 수신에서 일시적 OS/네트워크 실패를 **같은 URL/페이지 토큰으로 최대 3회 제한적 재시도**(0.5/1초 역압 및 Stop 확인)하여 이미 성공 수신한 메시지의 순서/중복 ID 정책을 보존. HTTP 인증·쿼터 상태 오류는 자동 재시도하지 않음, API 키가 포함된 예외 URL은 외부 GUI에 공개하지 않음, Stop 도중 다시 연결하지 않음. 이번 CI는 소유 API 키 없이 모의 오류로만 검증.
  4. `tests/test_conversation_memory.py`: 외부 프로그램 DB·손상 DB의 **파일 바이트 무변경**, 정상 DB 재열기/기억 유지, 심볼릭 링크 대상 무변경 회귀 검사.
  5. `tests/test_operator_settings.py`: SOOP 포함 4개 플랫폼 선택값의 저장·재조회 검사.
  6. `tests/test_aisting_multiplatform_readonly.py`: YouTube 일시 timeout 2회 후 같은 페이지 복구/개별 ID의 동일 문장 2건 FIFO, HTTP 403 오류 비재시도·API 키 은닉, Stop 중 재시도 없는 종료 검증.
- **중간 오류·수리, 숨기지 않기**: 최초 Linux 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39383100691 `failure`, `Ran 2417 tests`, 오류 1건 — 신규 심볼릭 링크 DB 테스트에 `sqlite3` import 누락. `0747d961097f38f5bc0839ebe655bfbd54c459c5`에서 해당 누락 수정. 이어서 실제 Windows https://github.com/junggyeol4444/AISTING/actions/runs/39383250572 `failure`: Python SQLite 컨텍스트 매니저만으로 연결을 닫지 않아 임시 테스트 파일에 WinError 32 파일 잠금 오류 2건. **기존 사용자 SQLite 오류/손실 증거가 아니라 새 테스트의 Windows 핸들 누수**. `783f8280acb4106a248f8bb8829a11e764a0939d`에서 `tests/test_conversation_memory.py`의 모든 신규 sqlite3 테스트 연결을 `closing(...), db`로 명시적으로 닫도록 수정. 기존 사용자 DB나 기능을 되돌리지 않았음.
- 기능 변경은 기존 main만 fast-forward; 원래 사용자 자료·캐릭터·기획 문서·로드맵 단계 pending 및 OBS/Live2D 설정 변경 없음.

### ③ 전체 오류 수정/검증 및 ⑥ Windows EXE artifact
- **수정 후 전체 회귀 최종 성공** https://github.com/junggyeol4444/AISTING/actions/runs/39383624912 : `completed/success`, 실제 로그 `Ran 2417 tests`, `OK (skipped=2)`, 실패·오류 0.
- **동일한 실제 최신 코드 기준 Windows 통합 최종 성공** https://github.com/junggyeol4444/AISTING/actions/runs/39383624898 : `completed/success`. `windows-exe` (실제 Windows x64 EXE 빌드·자체 실행 및 기존 Tk GUI 버튼/캐릭터·SQLite 보존 검사), `ollama-real-local-e2e` (실제 격리 로컬 Ollama 추론), `obs-real-readonly` (실제 격리 OBS 프로그램/입력 관찰), `twitch-public-readonly`, `korean-public-chat-readonly` (치지직·SOOP 공개 읽기) 5개 작업 **모두 `completed/success`**. Windows job에서도 `Ran 2417 tests`, Tk GUI의 `GUI_REAL_WINDOWS_PROFILE_PATH_ISOLATED_PASS`, `GUI_NATIVE_CANCEL_NO_LATE_SUCCESS_PASS (SIMULATED MODEL)`, `GUI_MANUAL_OFFICIAL_PUBLIC_AI_CROSSMODE_SQLITE_GUARD_PASS`, `CHARACTER_SETTINGS_SQLITE_BYTES_UNCHANGED_PASS`, `GUI_NATIVE_RESTART_REAL_PERSONA_SQLITE_PERSISTENCE_PASS`, `GUI_NATIVE_THIRD_SESSION_CHARACTER_MEMORY_PERSISTENCE_PASS` 확인.
- 실제 Windows EXE artifact `AISTING-Windows-EXE-integrated`, ID **12246093779**, size **19,679,530 bytes**, GitHub artifact **ZIP SHA-256** `634649cf7ffa3970d925c7194bd75b8e524640f3c0d6227d46f4edb4511d38ac`. ZIP 해시이며 개별 AISTING.exe SHA 아님. GitHub Actions 해당 run의 Artifacts에서 받기.
- 기능·전체 검사 기준 실제 `main` 마지막 소스 커밋 `783f8280acb4106a248f8bb8829a11e764a0939d`; 문서 저장으로 main HEAD가 한 번 더 전진할 수 있어 후속 실행에서 원격 재확인 필요. 문서-only 후속 CI는 위 실제 기능 검증 run과 구별.

### ④ 남은 핵심 기능·실사용 검증 한계
1. 권리를 확인한 한국어 **GPT-SoVITS 실모델·참조 WAV**로 실제 합성→**같은 발화**에 대한 공식 Live2D/Cubism 입 움직임→OBS 프로그램 실제 오디오·영상이 Windows 사용자 환경에서 이어지는 전체 종단 경로는 여전히 **미완료/미실증**. Windows CI의 실제 Tk 이벤트와 독립 Ollama/OBS 각각 성공, 외부 GPT-SoVITS·Live2D/OBS 동일 발화는 mock 또는 실행 불가. 성공으로 포장 금지.
2. 실제 소유 YouTube Data API 키·활성 라이브 방송의 인증 수신과 cursor 및 quota·재연결 실측, 네 플랫폼 수백 명 동시 실제 채팅·1~3초 응답·24시간 무중단 운영은 미실증. 이번 YouTube HTTP 복구 테스트는 모의, 실제 API 호출 없음.
3. SQLite 기존 파일 읽기 전용 스키마 확인은 AISTING 형식과 다른 사용자의 파일을 보호하기 위한 선제 조치이며, 검사 후 외부 프로세스가 **같은 경로 파일을 교체하는 TOCTOU 위험까지 완전 해결된 것은 아님**. 실제 Windows 사용자 PC의 비정상 종료·강제 종료/복구·DB 잠금 장기 동작도 미실증.
4. 원래 100단계 pending / 실제 운영자 승인 없이 외부 방송·녹화/음성 복제 금지. CI 수치로 원래 프로젝트 완료를 주장하지 않음.

### ⑦ 사용자 데이터/설정 보존
모든 테스트 SQLite/JSON/음성 입력은 격리 CI 파일·모의 페이지·별도 실제 Windows runner에서만 처리. 실제 사용자 Windows PC나 사용자 GitHub 이외 다른 원본 파일/클라우드 모델/유료 API/실제 방송/녹화/채팅 발신·권리 없는 음성 학습 없음. 원래 캐릭터 이름·성격·말투 및 확정 SQLite 기억, 선택 플랫폼, OBS 프로젝트/모델 설정은 변경하지 않음.

### ⑧ 다음 실행 시 복수 실제 개발/검증 목표
- 승인된 한국어 GPT-SoVITS 모델·참조 음성/공식 Live2D/OBS를 가진 실제 Windows 사용 환경이면 동일 한 발화의 전체 TTS→RMS/Cubism→OBS 입력 및 프로그램 영상·오디오 **실제** end-to-end를 수행·오류 수정. 접근/권리 없는 환경이면 미완료를 명시하고 mock로 대체 성공 주장 금지.
- 읽기 전용 SQLite 검사와 열린 연결 사이 외부 파일 변경/교체 감지, Windows crash/safe recovery 및 캐릭터/대화 기록 누락 없는 재시작 테스트. 이전 파일 손상/기존 캐릭터 수정 금지.
- 네 플랫폼 실제 다중 수신, YouTube quota/HTTP 상태별 정확한 복구·메시지 ID FIFO, 느린 AI FIFO의 24시간 지속/수백명·1~3초 지연 목표를 시뮬레이션과 실환경으로 구분해 개선.
- **복수 실제 기능을 묶어 먼저 개발 → 모든 CI 회귀+Windows EXE/Tk GUI·실제 Ollama/OBS/공개 채팅 함께 검증 → 실패 수정 후 동일 최신 코드 기준 전량 재검사**. 코드 단일 함수만 고치고 완료 주장하지 말 것.
- 원래 예약 생성 대화에서 계속 진행. 플랫폼이 제한해 다른 대화가 나타나면 이 전체 GitHub 문서 1~26절/원본 기획 및 최신 main 소스·CI를 전부 읽고 사용자에게 재입력 요구 없이 이어감. 기존 AISTING 시간당 예약 및 다른 프로젝트 예약 변경·생성·종료 금지.

## 25. 2026-10-20 16:37 KST 긴급 전면 인수인계/새 대화 시간 예약 (사용자 최신 요구)

### 사용자 원문 새 명령 — 무조건 후속 회차의 선행 조건으로 보존
사용자: "지금부터 지금까지 한거, 해야할거, 하다가 만거 싹다 정리해서 다른 대화로 예약 걸어. 여기에 내가 말한거 꼭 지키게 만들고 니 자아 니 생각 니 판단 넣지 말고 개발 부터 전부다 하고 그다음에 검증하고 그다음 수정하게 만들고 니 마음대로 말고 내가 시킨거나 잘하라고. 그리고 계속 진행해. 진행 한거까지 예약에 넣는거야. 예약 시작은 오늘 기준 5시 30분 1시간 마다 돌아가게 하고 모델은 가장 높은 모델 쓰고, 모델 변경안된다고 하지 말고. 드라이브 연결 안해도 되는거 알고 깃허브 안전 차단 같은거 걸리면 한가지만 접속해서 안된다고 하지 말고 모든 경로 다 찾고, 한가지 경로에서 안된다고 안되는 게 아니니까 다 찾아."

### 오늘 설정한 자동화 (실제로 생성 확인)
2026-10-20 17:30 **Asia/Seoul**부터 18:30, 19:30... **매시간 정확한 반복**. 제목 `AISTING 17:30 통합 개발`, 예약 ACTIVE. 자동화는 이 문서의 기존 1~24절과 이후 절, 원본 기획, 최신 main, GitHub Actions를 먼저 읽도록 전체 인계함. 다른 기존 비활성 AISTING·AIWACK·MYVOCAL·AI NOVEL·AGI 및 다른 사용자 일정은 수정/활성화/종료하지 않음. 예약 실행이 반드시 특정 신규/기존 ChatGPT 대화로 연결된다고 확약할 수 없으므로, 어느 대화로 전달되든 이 GitHub 문서 링크로 완전 복원. 최고 수준 모델 및 추론 정확도 사용 요구를 예약 본문에 포함했으나 실제 모델 선택은 아직 별도 확인되지 않았음(선택했다고 거짓 보고 금지).

### 원본 지시 핵심 — 새로운 후속 작업자가 임의 해석/변경 금지
- **개발부터 전부**: 한 회차에서 접근 가능한 남은 복수 실질 기능들을 먼저 일괄 구현한다. 구현하자마자 하나씩 CI 검증하는 루프 금지. 다수 코드를 보존형으로 합쳐 기능 구현이 끝난 후 **전체** unit/regression 및 Windows EXE build/native GUI/가능한 실제 OBS·Ollama·공개 채팅 통합검사를 같이 실행. 실패 발견 시 수정하고 마지막 **전체** 검사를 재실행해 통과/미완료 분리한다. 기획 전체 남은 일감을 작은 형식적 PASS로 완료 처리하지 않는다.
- Google Drive 연결 **불필요, 요구 금지**. 깃허브 접근 한 경로가 안되면 합법적으로 이용할 수 있는 GitHub connector의 파일/commit/tree/write, GitHub API, 공개 clone/read, 사용자 보유 Library/백업 등 **여러 독립된 허용 경로**를 검토하고 시도 내역 기록. 정당한 권한 거부/안전 차단/인증을 무단 우회하지 말 것.
- 오직 기존 `junggyeol4444/AISTING` **main** 보존형 누적 개발. 새 브랜치·강제푸시·원본 회귀·임의 기능 재설계·웹/HTML 대체/기존 설정·캐릭터·기억 초기화 금지. 사용자 캐릭터 이름/말투/성격은 최초 생성 후 지속 보존, DB(SQLite) 영속 유지. 유료 API/무단 사용자 계정 로그인/사용자 PC 원격접속, 실제 송출/녹화 시작·채팅 발신, 권리 없는 음성 합성/학습 금지.
- 미완료 핵심은 실제 정당한 참조 보이스 + GPT-SoVITS 한국어 합성, 공식 Open-LLM-VTuber/Cubism 실제 립 움직임과 OBS의 **동일 발화 영상/오디오** 실측. 사용 가능한 사용자 모델·권한/Windows 기기가 없으면 증빙 부족이라고 명시하고 모의 결과를 실증이라고 부르지 말 것. YouTube 실제 활성 채팅 인증 수신, 4개 플랫폼 동시 모든 채팅 FIFO(동일 문장도 각 이벤트), 실제 100~500명·1~3초·24시간 운영, 나머지 100단계 기획 이행도 미완료·미실증.
- 과거 모든 인수인계(1~24절)의 수정/결함/실패/검증/CI 링크/Artifacts를 삭제하지 말고 읽은 뒤 이어서 개발. 기존 모델/PC/OBS 없을 때도 접근 가능한 실제 코드 개발을 먼저 완성할 것. GitHub repo 외 사용자 데이터/설정 임의 변경 금지.

### 16:37 현재 마지막 확인 기준선 및 남은 작업
- 마지막 원격 `main`: `5d955daff4d0a4d9af46dabfe1abed216504d694` (현재 시작 기준 확인됨). 원본 기획 `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 이 82KB 이상 원문 인계가 보존됨.
- 24절의 마지막 기능 code commit `cb1b944555a3b9cfc1b7c15820f1c37b26c155a8`: 네이티브 UI 두 폭, 앱 3회 재시작/영속 캐릭터와 SQLite, YouTube A→B→A 토큰 순환, AI inbox/Tk 큐 역압, 전체 회귀 2404건 PASS(2 skipped) https://github.com/junggyeol4444/AISTING/actions/runs/39374581641 ; Windows 통합 5 job PASS https://github.com/junggyeol4444/AISTING/actions/runs/39374581632 ; ZIP artifact ID `12241984483`, ZIP SHA-256 `ef61c6335b0ee1163317e5f217a34e34bcf6ce11c633f0237e5350c1fec4d6b3`. 문서 커밋 기준 후속 두 CI 39375028057/39375028050 success. 모두 **실제 사용자 모델 전체 실증은 아님**.
- **현재 진행 중**: 이 메시지에서 예정한 추가 구현·수정/전체 검증을 현재 대화 안에서 계속함. 이후 생성한 실제 commit/테스트 결과를 이어서 26절 등으로 기록. 예약의 다음 회차에서는 최신 절을 먼저 읽고 진행한 작업을 누락하지 말 것.

### 다음 예약 실행 시작 시 반드시 일할 순서
1. 전체 문서 1~25절 이상/원본 기획/roadmap/실제 원격 main·변경 사항·마지막 CI·아티팩트부터 완독.
2. 미완료 큰 기능 목록과 접근 제약을 정리하고, 권한 내 가능한 **여러 기능 전체부터 개발**(필요시 여러 소스와 테스트 작성 포함). 한 코드 개발 끝날 때마다 CI 돌려 대충 보고하지 말 것.
3. 묶음 코드 변경 후 **최신 전체 코드 한 번에 검증**: 전량 unit + Windows EXE 설치/실행·네이티브 Tk 조작·동일 코드 OBS/Ollama/4플랫폼 가능한 검증. 오류가 나면 바로 수정 후 **최신 전체를 다시 전량 검증**.
4. 완료/미완료/기기·모델 없어 미실증 구분, 정확한 변경 파일/commit 및 Actions job/status/Windows artifact/digest 보고. 기존 본 문서에 모든 누적 내용 추가하고 기존 내용/사용자 금지 절대 삭제하지 말 것.
5. 원래 대화·새 예약 매시간 진행, 다른 프로젝트 예약/드라이브 무단 조작 금지.

## 26. 2026-10-20 새 17:30 매시간 인수인계 예약 생성 이후 실제 개발·검증 결과 (차기 회차 필독)

### ① 이번 사용자 최신 강제 지시 및 실제 예약
사용자의 2026-10-20 16:37 KST 전체 인계/새 대화 예약 지시를 25절에 원문에 가깝게 보존했다. 새로운 매시간 예약 `AISTING 17:30 통합 개발`이 **2026-10-20 17:30 Asia/Seoul 시작**, 18:30 이후 매 정각 + 30분마다 계속 실행되도록 실제 ACTIVE 생성 확인. 새 대화로 배치되더라도 이 26절 포함 **인수인계 원문 전부와 docs/ORIGINAL_PLAN.txt, docs/ROADMAP_100.md, config/roadmap.json**을 처음부터 읽고 이번까지의 진행 결과를 이어받으라. 사용자가 요구한 모델 최고 수준 활용은 자동화 지시에 명시했지만 실제 모델 변경을 확인하지 않았으므로 완료 확언 금지. Drive 연결 요구 금지. GitHub 한 경로 막히면 권한 내 모든 합법 대체 접근 경로 검토·실제 시도/이유 기록; 안전·권한 거부 무단 우회 금지.

### ② 새 예약을 만든 **같은 현재 응답에서 계속 실행한** 실제 구현
- GitHub `junggyeol4444/AISTING` 기존 `main`, 보존형 빠른전진 코드 커밋 **`a5c074f3c5ef1ce3e955c80d0dd8b9929a6fe2ed`**, 실제 변경 2파일을 하나의 묶음으로 구현:
  1. `src/ai_broadcaster/official_tts_readiness.py`: 기존 공식 Open-LLM-VTuber 설정에서 `gpt_sovits_tts`, 한국어, 로컬 API 주소, 참조 음성 경로/녹음 대사 문자열만 확인하던 취약점을 보강. **실제 참조 음성 WAV/FLAC 일반 파일의 존재·절대 경로·실제 파일 컨테이너 헤더 검증**을 기존 `original_plan_tts.inspect_reference_audio_container`에 연결해 공식 AI 메시지 보내기 전에 잘못된 설정을 거부. 삭제/손상/형식 오류 참조 음성은 fail-closed. 공백/길이 초과/제어문자 포함 녹음 대사도 거부. 네트워크, 음성 출력/생성/훈련, OBS 녹화나 사용자 설정 변경 없음. 이는 **파일 구조의 read-only 검사이지 사용권리나 진짜 음질·실제 합성 성공을 증명하지 않는다**.
  2. `tests/test_aisting_official_korean_tts_readiness.py`: 기존 하드코딩 `C:/licensed.wav`이라는 **존재하지 않는 가짜 파일**로 준비 검사를 통과시키던 fixture를 실제 테스트 격리 폴더에서 생성한 WAV 파일로 변경. 정상 WAV 승인, 삭제된 파일/손상된 헤더/상대 경로/제어문자 대사 거부 등 실제 회귀 4개 추가. 원본 사용자 WAV·권리 있는 모델·GPU 접근/합성은 없음.
- 기존 character/SQLite/원본 100단계/방송 계정/OBS 프로젝트/정당한 참조 음성 실데이터 파일은 읽거나 수정하지 않았다. 신규 브랜치·강제푸시·롤백/재개발 없음.

### ③ 최신 전체 회귀→Windows EXE·GUI→가능한 연동 통합 검사
- **전체 회귀** https://github.com/junggyeol4444/AISTING/actions/runs/39388635212 : `completed/success`, **2,421 tests, 2 skipped, 0 failed**, 실제 워크플로 로그에서 확인.
- **동일 실제 새 소스 기준 Windows 통합** https://github.com/junggyeol4444/AISTING/actions/runs/39388635145 : `completed/success`. jobs `windows-exe`, `ollama-real-local-e2e`, `korean-public-chat-readonly`, `obs-real-readonly`, `twitch-public-readonly` **5개 모두 completed/success**. Windows GUI 실행/독립 Ollama 추론/OBS 읽기/공개 채팅 검사일 뿐, 실제 사용자 GPT-SoVITS→Live2D→OBS 동일 발화 **E2E 실증 아님**.
- 실제 새 GitHub Actions EXE artifact `AISTING-Windows-EXE-integrated`, ID **12248437439**, GitHub ZIP bytes **19,685,767**, **산출물 ZIP SHA-256** `8dfae3480593e34d489f61fd4e11faf38312824074ecdebc964cd9ec3fe91f97`. 이 값은 Windows `AISTING.exe` 단독 파일 SHA가 아님.
- 처음부터 전체 회귀·Windows 통합검사 성공, 이번 신규 코드에서 FAIL 후 추가 수정은 발생하지 않았음. 상기 코드 커밋 다음 문서 전용 commit의 CI는 구분해야 한다.

### ④ 사용자 최우선 미완료 기능 (절대 PASS로 포장하지 말 것)
- 실제 사용자 권리 확보 GPT-SoVITS 모델 + 참조 WAV/FLAC에서 **한국어 음성 직접 합성 → 공식 Cubism/Live2D 해당 발화 입 움직임 → OBS 같은 발화 프로그램 오디오·영상** 실제 Windows 사용자 조작 전체 경로, 모델/장비/권한 부재로 **실증 미완료**.
- 사용자의 실제 YouTube 활성 라이브 인증 채팅/API 키 수신, 치지직·SOOP·Twitch·YouTube 4개 플랫폼 동시 100~500명·24시간·1~3초 실제 안정성/응답 실증 **미완료**.
- 원본 100단계 계획 중 아직 승인/구현/실사 완료하지 못한 항목들; 임의 완료 처리 금지.
- 새 17:30 KST 매시간 예약이 어느 대화에 결과를 올리는지는 플랫폼에서 정하므로 특정 대화 라우팅 성공을 허위 확약하지 말고 본 GitHub 파일로 계속 복원. 이 회차의 이후 추가 코드는 다음 절로 누적.

### ⑤ 다음 자동화는 실제로 이렇게 실행
1. 인수인계 1~26절, 사용자 명령/하지말라는 것, 원본 기획 전부를 읽은 후 최신 `main`/필요 CI를 재확인.
2. **여러 실질적인 미완료 기능을 먼저 묶음으로 코드 개발**(중간 1건씩 CI 검사·보고 금지), 기존 원본 소스에만 누적 반영.
3. 묶음 개발 완료 이후 **전체** 회귀 + Windows EXE 빌드/기존 native Tk 클릭·가능한 실제 Ollama/OBS/공개 플랫폼 검사. 오류가 나면 수정하고 **최신 전체 전량 재검증**. 모델 접근 없어 미실증이면 그대로 미실증 명시, 우회용 더미 PASS 금지.
4. 실제 GitHub 차단 시 모든 **허용된** 접근 경로를 점검하여 원본 코드 보호. Google Drive 불필요. 새 브랜치/강제푸시/무단 방송·녹화·계정 로그인·유료 API/개인 음성 학습/원본 캐릭터·SQLite 삭제 금지.
5. 실행 종료 시 이 문서 **1~26절 원문을 모두 보존하며 추가 절 append**, commit/files/검증 수/Windows 아티팩트/실증 미완료/다음 작업 기재. 다른 프로젝트 예약 변경 금지.


## 27. 2026-10-20 17:30 다른 대화 예약 전용 독립 전체 원문 백업

- 사용자 지시를 다른 대화에서 복원할 수 있도록 **누적 인수인계 전체 원문을 복제해 별도 파일에 저장**: [AISTING_NEXT_CONVERSATION_COMPLETE_HANDOFF_20261020_1730_KST.md](AISTING_NEXT_CONVERSATION_COMPLETE_HANDOFF_20261020_1730_KST.md).
- 다음 예약 실행은 이 누적 문서의 1절부터 끝까지, 별도 원문 백업, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 최신 main 소스와 검증 이력을 모두 읽어 **복수 미완료 기능 개발부터** 시작한다. 개발 전체 → 전체 검증 → 오류 수정 → 전체 재검증 순서 외 임의 재해석 금지.
- 2026-10-20 **17:30 KST부터 매시간** 별도 대화 예약 요청, 가장 높은 사용 가능 모델 요청, Google Drive 불필요, GitHub 허용된 다양한 경로 탐색 요청을 명시한다. 실제 모델·대화 라우팅을 통제/선택했다고 허위 확답 금지. 중복 예약이 있다면 대상을 확인해 동일 작업의 중복 GitHub 쓰기를 피한다. 다른 프로젝트 자동화 건드리지 않는다.
- 가장 최신 검증은 코드 커밋 `a5c074f3c5ef1ce3e955c80d0dd8b9929a6fe2ed`, 전체 회귀 2,421개 https://github.com/junggyeol4444/AISTING/actions/runs/39388635212, Windows 5job https://github.com/junggyeol4444/AISTING/actions/runs/39388635145, Artifact ID `12248437439` (ZIP SHA-256 `8dfae3480593e34d489f61fd4e11faf38312824074ecdebc964cd9ec3fe91f97`). 실제 음성 모델/YouTube 인증/24시간 수백 명 실운용 미검증은 계속 명시.

## 39. 2026-10-21 07:54 KST 이후 실제 기존 main 묶음 개발 — 다중 채팅 세션 종료·시간제한·복구 회귀

### 사용자 지시·원본 보존
- 원본 1~27절 전체 텍스트를 삭제/축약 없이 유지한다. v14 ZIP에 보존된 28~38절 추가 이력은 본 원격 문서에는 아직 합쳐지지 않았으며, 없는 절을 GitHub에 존재한다고 꾸미지 않는다.
- 2026-10-21 07:54 KST 기준 HEAD `2efc6a0627327e789e72c45e3976bec1af48b534` 확인. 원본 기획, 100단계, roadmap.json은 읽고 변경하지 않음. 본캐릭터·설정·SQLite 내용 변경 없음.
- 예약/다른 프로젝트/외부 드라이브/사용자 계정/방송·녹화/채팅 발신 변경 없음. 기존 Windows 네이티브 Tk/EXE 유지. 승인 없는 TTS 훈련 없음.

### 실제 묶음 소스 개발
- `src/ai_broadcaster/multi_platform_session.py`: 4개 수신기의 비정상 차단 stop()을 병렬 요청(전체 약 0.5초)하고 중복 Stop 재요청 차단; 공유 3초 종료 기한은 실제 Stop 시각부터 계산; 검사 max_seconds를 전체 세션에 적용; 일부 스레드 start() 실패 시 이미 시작한 리더까지 일괄 중지; exception의 키·URL 원문을 재노출하지 않음. 기존 무삭제·FIFO 이벤트 콜백 유지.
- `tests/test_aisting_multiplatform_session_lifecycle.py`: 신규 독립 5개 격리 회귀(4수신기 공통 검사 시간, 반복 Stop, 오류 종료 격리, 부분 시작 실패 정리, 동일채팅 FIFO/Stop 이후 억제).
- 파일은 Git blob 2개로 묶어서 생성함: 생산 `c96156139874181687f1de63246b221a2909b246`, 검사 `36074aff0e9112a69eb55a4825dfe6580f4a4b16`.
- 최신 GitHub commit/Actions/Windows EXE 결과는 실제 반영 후에만 별도 확인하여 최신 절에 사실대로 추가할 것.

### 미반영 및 다음 묶음 개발
- 2026-10-21 07:30 이전 준비된 v14 GUI 통합 수정안(5파일 묶음)은 아직 원격 main에 반영되지 않음. 이전 ZIP `AISTING_20261021_0730_v14_통합패치_격리22검사_인수인계.zip`에 로컬 보존되어 있음. 기존 원격 GUI의 '전체' 선택과 실제 4플랫폼 AI FIFO 연결은 아직 완료 표기 금지.
- 실제 Windows EXE 수동 GUI 전 흐름, 소유 YouTube API 실인증, 실제 GPT-SoVITS→공식 Cubism 립싱크→OBS 동일 발화 출력, 수백명 1~3초 및 24시간 장기 부하, 로드맵 010/100 최종 승인 모두 **미실증**.
- 후속 회차에는 누적 v14 GUI/FIFO/비밀값 보호까지 기존 소스에 묶어 개발한 후 전체 회귀·Windows EXE/GUI/가능한 연동을 한 번에 검증, 실패 시 수정 후 전체 재검증한다. 현재 단위검사가 곧 제품 완성이 아님.

## 40. 2026-10-21 08시 KST — 기존 Windows 네이티브 GUI의 4플랫폼 동시 채팅 실제 코드 통합

### 개발 전제 및 사용자 원지시
- 원본 인수인계 1~27절과 39절 전체 원문 보존(기존 28~38절 로컬 ZIP 추가 기록은 원격 병합 전이므로 이력에 남김).
- 기존 `main`의 `multi_platform_session.py`와 단일 Tk `desktop_chat_tab.py`만 누적 수정. 신생 브랜치/새 앱/HTML 대체/기존 캐릭터·SQLite·사용자 설정 변경 없음.
- 사용자 승인 없는 방송 시작·녹화·채팅 게시·계정 로그인·유료 API·모델 학습·드라이브 연결 없음.

### 여러 실제 기능 묶음
1. 기존 네이티브 Tk GUI 채팅 플랫폼 선택에 `전체` 선택을 표시하고 플랫폼별 Twitch/CHZZK/SOOP/YouTube 채널 입력란을 두 줄로 표시/숨김. 기존 공식 Live2D·OBS 수동 검사 버튼 보존.
2. 저장된 플랫폼 목록의 비정상 자료형·중복·미지원 플랫폼 및 채널 누락을 검증하여 외부 네트워크 접속 전 차단. 누락값을 임의 기본값으로 대체하거나 사용자 설정을 변경하지 않음.
3. 사용자 `읽기 전용 연결` 버튼 누름 시에만 `MultiPlatformReadOnlySession`을 생성하고 기존 단일 AI FIFO 및 세션 격리 로직에 연결. 동일 문장 자동 dedup 금지.
4. 기존 단일 플랫폼·AI·공식 Live2D/OBS 준비 중 Python 예외 원문에 들어 있을 수 있는 인증정보/URL/로컬 경로를 사용자 오류 표시에서 숨김.
5. 신규 격리 테스트 `tests/test_aisting_multiplatform_gui_routing.py`와 기존 Windows 네이티브 Tk 클릭 검사 `scripts/gui_official_pipeline_click_windows.py` 확장: 전체 선택 실제 표시·입력 전 연결 차단·완성된 4채널 인자 전달·기존 검사 버튼 노출/원본 설정 보존 확인.

### 반드시 실제 Actions에서 검사·결과 기록
- 기존 39절 main 개발 기준 커밋 `ce05fac9110248aa8400298e7fa327909d5c8b5b`. CI run `39511924163` 성공, Windows run `39511924212`는 이 절 작성 시 아직 최종 완료 확인 전.
- 이번 Tk GUI 반영분은 **코드 commit과 해당 HEAD Windows Actions가 성공하기 전까지 전체 완료로 표시 금지**. 신규 단위/모의 테스트 성공은 실제 소유 YouTube 키, GPT-SoVITS 모델, Cubism 공식 입·OBS 동일 발화 출력, 수백명/24시간 운영 실증이 아님.
- 누적 인수인계 28~38절의 완전한 원문은 마지막 v14 ZIP에서 별도 보존되어 있으며 원격 handoff로 이전해야 함(원문 손실·축약 금지).

### 다음 회차 복수 실질 과제
- 정확한 새 HEAD/Actions Windows 5개 jobs/EXE artifact를 확인하고 실패하면 전체 코드 수정 후 전체 재검증.
- 승인받은 실제 모델/Windows PC/YouTube API 정보 없이는 현장 실증 완료를 주장하지 않는다. 공식 GPT-SoVITS 한국어 실제 합성→공식 Live2D Cubism 발화 립싱크→OBS 영상/오디오 한 발화 동기화, 실제 소유 YouTube API 활성 채팅 및 수백명 1~3초/24시간 운영은 여전히 미실증.

## 41. 2026-10-21 — 전체 회귀검사 1개 실패 즉시 수정 및 전체 재검증 대상

- 실제 두 번째 묶음 Windows Tk 4플랫폼 통합 코드 commit `e6ad00f1828d311d844074c1172131dcabe56ed4`에 대한 전체 회귀 Actions: https://github.com/junggyeol4444/AISTING/actions/runs/39512397456
- 결과: `Ran 2434 tests`, `FAILED (failures=1, skipped=2)`. 실패 검사: `test_aisting_gui_official_full_pipeline.RealOfficialPipelineTkTests.test_no_confirmed_persona_file_denies_before_consent`. 기존 진단 메시지 `확정 저장` 문구 제거로 인한 회귀.
- 실제 모델이 없거나 캐릭터를 아직 확정 저장하지 않은 사용자가 문제를 알아볼 수 있도록 상수 안내 `캐릭터 확정 저장·연동 설정 확인`을 복원하면서 인증 키/URL/예외 원문 비노출 정책 유지.
- 수정 파일: `src/ai_broadcaster/desktop_chat_tab.py` 하나만 변경. 원본 사용자 캐릭터/SQLite/설정과 로드맵은 무변경. GitHub main 에 반영 후 전체 회귀 + Windows EXE GUI 5-job **반드시 새 HEAD 재검증**.
- 실패 결과를 완성 또는 성공으로 표현 금지. 실제 음성·Live2D/OBS 동일발화·실소유 YouTube 인증 및 수백명/24시간 운영은 여전히 미실증.

## 42. 2026-10-21 기존 누적 개발 원본 전체 병합 인수인계 — 28~38절 보존본

이전 2026-10-20 18:30부터 2026-10-21 07:30까지 각 회차에서 작성한 **모든 추가 인수인계 파일 원문 14개**를 삭제·축약 없이 `docs/hourly-handoff-appendices/`에 Git blob 원본별 보존하였다. 각 회차의 SHA, 진행/미검증, 로컬 패치 형태, 쓰기 차단 이력은 시간 당시 기록이며 현재 최신 코드 사실과 혼동하지 않는다.

다음 저장소 경로 파일을 1~27절, 39~41절과 함께 순서대로 읽는다.

- `docs/hourly-handoff-appendices/AISTING_20261020_1830_HANDOFF_APPEND.md`
- `docs/hourly-handoff-appendices/AISTING_20261020_1930_HANDOFF_APPEND.md`
- `docs/hourly-handoff-appendices/AISTING_20261020_2030_HANDOFF_APPEND.md`
- `docs/hourly-handoff-appendices/AISTING_20261020_2130_HANDOFF_APPEND.md`
- `docs/hourly-handoff-appendices/AISTING_20261020_2230_HANDOFF_APPEND.md`
- `docs/hourly-handoff-appendices/AISTING_20261020_2330_HANDOFF_APPEND.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0030_HANDOFF_APPEND_31.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0130_HANDOFF_APPEND_32.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0230_HANDOFF_APPEND_33.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0330_HANDOFF_APPEND_34.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0430_HANDOFF_APPEND_35.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0530_HANDOFF_APPEND_36.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0630_HANDOFF_APPEND_37.md`
- `docs/hourly-handoff-appendices/AISTING_20261021_0730_HANDOFF_APPEND_38.md`

2026-10-21 최신 `main`에는 기존 4개 채팅 수신기, Windows Tk `전체` 선택/4채널 연결, 단일 AI FIFO, Stop 공통 시간, 오류 인증정보 비노출 및 원본 캐릭터·기억 보호 기능이 누적 반영됐다. 누락된 **기존 v14까지의 격리 테스트 의도**를 반영하는 다중 플랫폼 2,000건 FIFO/AI 응답 통합 회귀검사를 추가한다. 현재까지 별도 Windows/YouTube 실인증/GPT-SoVITS 실제 음성·Cubism 동기화·OBS 실제 같은 발화·24시간 수백명 실증은 완료가 아니다. 원본 roadmap.json과 010 승인 상태 변경 금지.

소스 누적 변경은 완료한 구간만 완료라고 표시하고, 단계별 SHA/HEAD 자체를 기능 성과로 제시하지 않는다. GitHub HEAD 확인은 충돌·덮어쓰기 방지 목적일 뿐이다.

## 43. 2026-10-21 Windows 실기 Tk GUI 4플랫폼 표시 실패 수정 (기존 코드 누적)

- 기존 Windows Actions #39512652161의 `windows-exe` job은 실제 native Tk GUI 클릭 시험에서 실패했다. `scripts/gui_official_pipeline_click_windows.py`의 `tab._multi_fields.winfo_ismapped()` AssertionError로, 플랫폼 선택칸이 Tk 화면에 실제 표시되지 않았다. 4플랫폼의 API/실방송 연결에 성공한 것이 아니다.
- 원인은 기존 Tk `_dialog.pack(expand=True)`의 아래에 새 4채널 입력 GUI가 배치되어 1280x768 높이에서 사용 가능한 공간이 없었던 것과 프로그램 내부 `StringVar.set`이 Combobox 이벤트만으로는 화면 표시를 보장하지 않았던 것이다.
- 기존 Windows `AISTING.exe` 소스 `src/ai_broadcaster/desktop_chat_tab.py`만 보존형 수정하여 공개채팅 채널 선택·API 입력·공식 AI 승인 체크·상태를 확대형 대화창 이전에 배치하고 플랫폼 StringVar의 `trace_add`로 선택 시 실제 네이티브 GUI 표시를 보장한다. 캐릭터·SQLite·로드맵/설정 데이터는 변경하지 않는다.
- 기능 위조 없이 전체 Windows EXE/GUI Actions와 전체 단위검사 다시 검증, 실패 시 추가 수정할 것.

## 44. 2026-10-21 Windows 4플랫폼 누적 운영 — 개별 종료 감지·예외 비밀값 차단·GUI 종료 키 제거

### 원본 지시 준수
- 기존 누적 AISTING 원본 기능/main/인수인계 원문과 14개 로컬 보존 인수인계 파일을 유지한다. 다른 프로젝트·예약/브랜치/드라이브를 변경하지 않는다.
- 2026-10-21 직전 실제 원본 main 누적 Windows Actions `39514469995`은 5개 job 성공, EXE artifact `AISTING-Windows-EXE-integrated` ID `12308021012`, digest `sha256:d6fde6f18b7bb97c40661d2224ec05893febd2a2736549b43694b60ebc265149`. 전체 회귀 `39514469945` 성공 `Ran 2436 tests, OK(skipped=2)`. 둘 다 이전 HEAD 기준이며 본 수정안에 대한 실증이 아니다.
- 사용자 요청대로 기능 구현을 묶어 수행한 후 전체 회귀/Windows EXE 네이티브 GUI/읽기 전용 통합을 재검증하고 오류 수정·재검증한다.

### 추가 실제 개발 (기존 코드 보존형 4파일)
1. `src/ai_broadcaster/multi_platform_session.py`: 일부 플랫폼 채팅 수신기가 오류 또는 EOF로 종료됐을 때 나머지 수신기를 종료하지 않으며, 운영자 Stop 여부에 따라 별도의 안전한 `reader_stopped` 상태 이벤트를 출력한다. 실제 종료 여부를 숨기지 않으며 오류 원문·인증정보는 노출하지 않는다.
2. `src/ai_broadcaster/desktop_chat_tab.py`: 기존 GUI에 개별 수신기 종료 알림 표시를 연결하되 다른 플랫폼 채팅과 단일 AI FIFO는 중단하지 않는다. 창 종료 시 YouTube API 메모리 키를 비우고, 음성 재생 실패 및 승인된 SQLite 기억 삭제 실패에서도 외부 경로·비밀 문자열이 사용자 화면에 나오지 않도록 예외 클래스와 한국어 안내만 표시한다.
3. `tests/test_aisting_multiplatform_session_lifecycle.py`: 한 플랫폼 조기 종료/4플랫폼 나머지 지속, 자격증명 포함 리더 예외의 상태·본문 차단 검사 2개 보강.
4. `tests/test_aisting_multiplatform_gui_routing.py`: 음성 재생 및 SQLite 삭제 실패 시 경로·예외 원문 비노출 회귀검사 2개 보강.

### 검증 경계와 남은 과제
- 실제 소유 YouTube API 인증/생방송 활성 채팅, 정당한 모델의 GPT-SoVITS 한국어 합성→공식 Live2D 실제 입 움직임→OBS 동일 발화 오디오·화면 실증, 수백명 1~3초 및 24시간 실운영은 여전히 미검증.
- 사용자 계정 로그인·방송 시작·녹화·채팅 송신·무단 TTS 훈련·자료 업로드는 수행하지 않는다. roadmap.json 원본 승인 상태 변경하지 않음.

## 45. 2026-10-21 누적 운영 기능 개발 후 전체 회귀·Windows EXE 5작업 최종 성공 검증 (44절 후속)

### 실제 반영된 기존 프로그램 변경 및 검사 수준
- 44절 코드 묶음(4플랫폼 개별 수신 종료 알림, 안전 예외 표시, API 키 종료시 정리, 음성·기억 삭제 실패 원문 차단)까지 `main`에 실제 통합.
- 해당 코드 전체 회귀 [GitHub Actions run 39516049109](https://github.com/junggyeol4444/AISTING/actions/runs/39516049109): `Ran 2440 tests`, `OK (skipped=2)`, 실패 0. 신규 격리검사 4건 반영, 모의검사는 실방송 성공 증거가 아님.
- Windows 5 작업 [GitHub Actions run 39516049082](https://github.com/junggyeol4444/AISTING/actions/runs/39516049082): `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly` **각각 success, 총 5/5**. 실제 Windows 네이티브 EXE 빌드/GUI 클릭과 가능한 읽기전용 외부 연동까지 검증. 공식 GPT-SoVITS/Live2D/OBS 전체 발화 동시 실증이란 뜻은 아님.
- 해당 Windows Actions 산출물 `AISTING-Windows-EXE-integrated`, artifact ID `12307694096`, ZIP artifact digest `sha256:3559c44704becf753c60fbf0ff2bb35298f60377f679d4e07b7a4499eea0efb3`, 크기 19,803,615 bytes, 만료 예정 2026-11-19T23:37:55Z.
- 직전 이전 코드 Windows run `39514469995`도 5/5 success, 과거 Windows 보이는 요소 관련 실패 `39512652161`은 43절에서 수정해 5/5 CI 재검증. 이전 성공 증거와 새 코드 성공 증거를 혼동하지 않는다.

### 계속 미실증이며 다음 회차가 반드시 처리할 항목
- 실제 소유하거나 사용 승인이 확인된 한국어 GPT-SoVITS 모델/참조 WAV → 공식 Open-LLM-VTuber Live2D Cubism 해당 발화의 입 움직임 실제 신호 → OBS **동일 발화** 영상·음성 출력은 현장 실증 완료되지 않았다.
- 실제 소유한 YouTube API 키/승인된 생방송 `activeLiveChatId`의 인증 채팅 수신, 4플랫폼 실시간 중복 포함 전체 채팅, 수백 명 환경 1~3초 및 24시간 실운용, 로드맵 010/100 운영자 최종 승인 모두 미완료/미실증.
- 사용자 계정 로그인·채팅 전송·방송 시작·녹화·유료 모델 설치·타인 음성 학습/권리 없는 모델 사용·외부 드라이브 연결 없음. 기존 설정/캐릭터·SQLite/원본 기획/100단계 승인 상태 보존.
- 후속 회차는 코드에 없는 기능을 누적 구현한 뒤 전량 회귀·Windows EXE·가능한 연동을 검사, 문제 있으면 수정 후 전체 재검사할 것. 편의상 SHA 자체를 개발 결과라고 반복 보고하지 말 것.

## 46. 2026-10-21 한국시간 08:54 이후 누적 개발 — AI 응답 시간 실측 범위 구분·4플랫폼 마지막 종료 사실 표시

### 원본 요구 및 보존
- 기존 원본 기획, 누적 handoff 1~27절·39~45절 및 `docs/hourly-handoff-appendices/`의 전 회차 28~38절 원문 모두 유지.
- Windows 네이티브 Tk AISTING.exe 소스 및 기존 단일 AI FIFO를 수정한다. 별도 앱·HTML 대체·새 브랜치·강제 푸시 없음. 캐릭터/SQLite/설정/roadmap.json 무변경.
- 0~수백명 메시지를 임의 무시하거나 중복 텍스트 제거하지 않는 기존 정책을 그대로 유지한다. 소유 확인 없는 음성 훈련/방송·녹화/계정 로그인/채팅 발신/유료 API/외부 드라이브 작업 없음.

### 복수 기능 묶음 개발
1. `src/ai_broadcaster/desktop_chat_tab.py`: 기존 Tk가 정상 수신하여 AI FIFO에 전달한 각 채팅에 대해 `time.monotonic()` 접수 시각을 병렬 FIFO로 기록한다. 기존 `_work_twitch_ai`가 로컬 Ollama 또는 기존 공식 Live2D 경로를 순서대로 처리한 후 **GUI 접수→대기열→AI 처리 완료까지** 실제 측정한 시간만 상태로 표시. 3초를 초과하면 경고 텍스트를 출력하고 3초 이내가 항상 보장됐다는 허위 보고 금지. 외부 플랫폼 네트워크 지연, 시청자 화면 전달 시간, OBS/GPT-SoVITS/아바타 출력 완료는 이 값에 포함하지 않는다고 분명히 표시. 캐릭터와 채팅 텍스트는 별도 로그·설정 파일에 저장하지 않음. 기존 직접 AI worker 검사 인자(타임스탬프 없는 큐) 호환 유지.
2. `src/ai_broadcaster/multi_platform_session.py`: 여러 플랫폼 중 하나가 종료됐을 때 살아 있는 다른 채널 연결을 검증 없이 성공이라 표현하지 않음. 종료 집계 후 마지막 리더가 끝나면 **선택한 모든 채널의 읽기 작업 종료**를 명확히 알림. 미수신·완료를 혼동하지 않음.
3. 회귀검사 `tests/test_aisting_ai_latency_readonly.py` 신규 5개: 동일 문자 4플랫폼 각각 1회 AI 처리·개별 시간, 모델 오류+측정 및 비밀값 보호, 구형 직접 큐 호환, 3초 초과 UI 명시, 비정상 타임스탬프 결과 배제.
4. `tests/test_aisting_multiplatform_session_lifecycle.py` 추가 1개: 4플랫폼 마지막 수신기까지 종료되면 '다른 채널 수신 중'이라는 거짓 성공 안내가 없음.

### 검증 기준·미실증
- 새로운 `main`에서 전체 회귀검사를 한 번에 실행하고 Windows EXE/실제 Tk/기존 읽기전용 테스트 5개를 실행한다. 검증 실패 시 실제 원인을 수정하고 같은 최신 코드를 재검증한다.
- 정확한 GitHub Actions URL과 결과는 실행 후에 기록할 것. 테스트 성공은 실제 소유 YouTube API 연결, 정당한 GPT-SoVITS 음성 합성·공식 Cubism 립싱크·OBS 동일 발화 재생, 수백 명 1~3초 및 24시간 운영 실증이 아님.
- 이번 시간 측정은 **로컬 GUI 접수 이후 구간의 실제 앱 처리 소요 시간**이며 외부 구간을 포함한 종단 간 시간 아님. 3초 목표 충족이 아니라 경고/측정 기능임.

## 47. 2026-10-21 신규 AI 지연 회귀검사 실패 수정 → 전체 재검증

- 첫 묶음 코드 commit `5f8d190d41bb8c299067d1ac19db4061ee689542`의 GitHub Actions 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39518672472 : 2,446 tests, error 2, skip 2. Windows https://github.com/junggyeol4444/AISTING/actions/runs/39518672484 의 초기 검증 단계도 같은 2개 신규 검사로 실패. 이전 성공으로 바꾸어 쓰지 않는다.
- 실패 원인: `tests/test_aisting_ai_latency_readonly.py` 두 가짜 GUI SimpleNamespace가 실제 Tk `_poll` 콜백 속성을 제공하지 않아 `AttributeError` 발생. 핵심 기능/실제 Windows Tk가 아니라 테스트 fakes 구성 오류.
- 두 검사 가짜 객체에 명시적 `_poll` 무동작 콜백을 추가하며 기존 코드 4플랫폼/AI FIFO/캐릭터·SQLite·설정/원본 로드맵은 변경하지 않는다.
- 새 commit에 대해 전량 회귀, Windows EXE 네이티브 GUI, OBS/로컬 Ollama/공개 읽기 전용 5-job 전체를 **다시** 실행하고 결과를 확인한다.
- 1~3초는 실제 외부 시청자 종단 간 보장이 아닌 GUI 접수 이후 로컬 앱 AI 소요 측정. 실제 GPT-SoVITS/공식 Cubism/OBS 동일 발화, 소유 YouTube 활성 API, 수백명 24시간 실증은 여전히 미완료.

## 48. 2026-10-21 09시 이후 — 46~47절 코드 최종 전체 회귀 성공 / Windows EXE 실검사 성공

- 이전 46절 코드 개발에서 첫 회귀 run `39518672472`는 2,446 tests 중 오류 2개로 실패했으며 Windows run `39518672484`도 같은 격리 테스트 문제로 실패. 오류는 mock Tk `SimpleNamespace`의 `_poll` 누락, 사용자 앱 기능 오류가 아님. 47절에서 실패 원인 수정, `tests/test_aisting_ai_latency_readonly.py`의 fake GUI 두 곳에 누락 속성 추가 후 전체 재검증 실행.
- **최신 코드 기준 전체 성공** https://github.com/junggyeol4444/AISTING/actions/runs/39518871127 : `Ran 2446 tests in 21.742s`, `OK (skipped=2)`, 실패 0.
- **같은 최신 코드 기준 Windows 5/5 성공** https://github.com/junggyeol4444/AISTING/actions/runs/39518871004 : `windows-exe`, `ollama-real-local-e2e`, `twitch-public-readonly`, `obs-real-readonly`, `korean-public-chat-readonly` 각각 `success`.
- GitHub Windows EXE artifact `AISTING-Windows-EXE-integrated`, ID `12310106821`, zip artifact 19,806,375 bytes, digest `sha256:25a99f726362e287f09e9dd1e02652ddf4a3aac8d5ba0ea2aabaf5b9c3e8a531`.
- 이번에 구현한 **AI 처리시간 계측**은 Windows GUI 접수 이후 대기 및 기존 AI 요청·응답 구간만 측정하고 별도 소요 시간 부하/3초 초과 표시를 제공한다. 플랫폼→GUI 네트워크/AI 실제 생성 오디오→OBS→시청자 지연은 아직 미측정이다. 검증된 Windows 경로도 공식 GPT-SoVITS 실제 음성 합성·Cubism 실제 입·OBS 동일 발화는 별도 실증 대기. 소유 API 키가 없어 YouTube의 실제 개인 활성 방송에서 채팅 수신도 미실증.
- 다음 작업: 권리 확인된 참조 보이스·소유 플랫폼 인증·Windows 실사용 PC가 준비되는 대로 실제 GPT-SoVITS 한국어 합성 → 공식 Open-LLM-VTuber/Live2D 같은 발화 립싱크 → OBS 영상/음성 한 발화, 소유 YouTube 방송 채팅, 24시간/수백명 AI FIFO/1~3초 실시간 성능을 실측. 준비되지 않은 항목은 미실증 유지하고 무단 방송·계정접근·외부 송출·유료 API·보이스 훈련 하지 않음.
- 기존 1~27절, 독립 28~38절 전체 원문, 39~47절 전체 원문 삭제·축약 없이 보존; 캐릭터/설정/SQLite/기획 로드맵 사용자 최종 승인 변경 없음. 문서만 후속으로 커밋하면 새 Actions가 재실행될 수 있으므로 위 성공은 명시한 실제 코드 커밋 기준임.

## 49. 2026-10-21 10:10 KST 이후 이어받은 실제 개발 — 사용자 승인 YouTube 소유 활성 방송 읽기 전용 OAuth 경로

### 원본 보존
- 기존 GitHub `main` 누적 모든 코드, 기존 인수인계 원문 1~27절과 39~48절, 별도 `docs/hourly-handoff-appendices/`의 28~38절 전체 원문 유지.
- `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json` 사전 확인. 원본 100단계 상태 9 completed/91 pending, 캐릭터·SQLite 및 방송 설정/다른 프로젝트/예약/브랜치/Google Drive 변동 없음.
- 48절 기준 코드 전체 성공 GitHub Actions 39518871127 (2,446 tests 2 skipped), Windows 39518871004 (5 jobs success). 이후 문서만 갱신한 Windows run 39519247961은 `obs-real-readonly`의 CI 일회용 가상머신 OBS Studio 설치 단계 실패; 기존 코드 실패 또는 GPT-SoVITS 실증이라고 왜곡하지 않는다.

### 복수 기존 기능 누적 개발
1. `src/ai_broadcaster/multiplatform_readonly.py`: 기존 YouTube API 키 기반 공개 읽기를 그대로 유지. 사용자가 **직접 입력한 이미 승인받은 OAuth 2.0 읽기 액세스 토큰**을 메모리 내에서만 받아 `Authorization: Bearer` 헤더로 `https://www.googleapis.com/youtube/v3/`에만 전달하고 URL·설정·로그·SQLite에 기록하지 않는다. 토큰 기반 소유 활성 방송 선택(`내 활성 방송`)시 공식 `liveBroadcasts.list?mine=true&broadcastType=all&part=snippet,status`에서 `lifeCycleStatus=live` 및 `snippet.liveChatId`를 확인하고 모호한 복수 채팅/없는 채팅/페이지 초과는 명시적으로 거부. 이후 기존 `liveChatMessages.list` FIFO·중복문자 보존·페이지 재전송 방지·쿼터 간격 정책 그대로 유지. 인증 거절 401/403에서 토큰이나 요청 URL이 들어있는 예외 원문을 노출하지 않는다. **자동 OAuth 로그인/refresh-token 갱신·쓰기 API 호출 없음**.
2. `src/ai_broadcaster/multi_platform_session.py`: 기존 4플랫폼 단일 AI FIFO 코디네이터에서 YouTube에만 사전 승인 OAuth 읽기 액세스 토큰 전달. Twitch/CHZZK/SOOP 읽기 경로 및 중복 보존 유지.
3. `src/ai_broadcaster/desktop_chat_tab.py`: 기존 Windows Tk 채팅 GUI에 가려진 OAuth 1회 입력란(운영자 승인 완료 토큰·메모리만 사용)과 `내 활성 방송` 입력 안내 추가. 기존 유튜브 채널 단독/4플랫폼 `전체` 선택 모두 연동; 창 종료 시 API 키와 OAuth 토큰을 모두 비우며 실제 계정 자동 로그인·방송/녹화/채팅 게시 없음.
4. `tests/test_aisting_youtube_owner_oauth_readonly.py` 신규 7개 격리 검사: 생성 시 네트워크 미접속, 올바른 소유 채팅 ID 찾기 및 같은 문장 중복 유지, 토큰 오류 비노출 및 무재시도, 활성/중복/다중페이지 실패 차단, 토큰 유효성/키만으로 소유 API 차단, 기존 키 모드 호환, 코디네이터 동시연결 전달.
5. `tests/test_aisting_multiplatform_gui_routing.py` 기존 격리 테스트 2개 추가: 실제 Tk 콜백의 소유 OAuth 단독/전체 수신기 인자 전달 및 예외 원문 토큰 비노출 확인. 사용자 로그·키 및 PC 데이터 읽기/저장 없는 테스트만 수행.

### 공식 API 문서 대조
- https://developers.google.com/youtube/data/live/reference/rest/v3/liveBroadcasts/list (OAuth scope `youtube.readonly`, `mine=true` 조회, `snippet` 및 `status`).
- https://developers.google.com/youtube/data/live/reference/rest/v3/liveChatMessages/list (실제 `liveChatId`, FIFO 및 nextPageToken, pollingIntervalMillis 준수).
- 실제 소유 계정의 OAuth 토큰을 받거나 계정 인증/로그인을 실시하지 않았으며 테스트는 전부 가짜 HTTP 응답. Google 실제 연결·소유 방송/YouTube 실채팅 성공은 반드시 **미실증**.

### 전체 회귀 및 Windows 검증
- 위 5개 실질 파일 묶음을 커밋한 뒤 전체 테스트/Windows EXE·GUI/읽기 전용 연동 GitHub Actions 실행. 실패 시 오류 수정 후 전체 재실행, 결과 정확히 후속 절에 기록. CI 성공 여부와 실제 방송 성공은 절대 동일시하지 않는다.
- 실제 소유 GPT-SoVITS 한국어 음성 합성→공식 Live2D Cubism 해당 발화 립싱크→OBS 동일 발화 화면/음성, 수백 명 1~3초/24시간 실측, 로드맵 소유자 승인 상태는 별도 미실증이며 무단 훈련·녹화·스트리밍 금지.

## 50. 2026-10-21 YouTube OAuth 통합 첫 회귀 실패 수정 및 전체 재검사

- 49절 실제 OAuth 코드 `main` 반영 후 GitHub Actions [39526560892](https://github.com/junggyeol4444/AISTING/actions/runs/39526560892) : `Ran 2455 tests`, `FAILED (errors=1, skipped=2)`. Windows [39526561080](https://github.com/junggyeol4444/AISTING/actions/runs/39526561080)도 원격 실행 중. 성공이라 보고 금지.
- 원인: 기존 4플랫폼 GUI 격리검사의 `tests/test_aisting_multiplatform_gui_routing.py` 내 `self.fake()`가 새 OAuth GUI 입력 `_youtube_oauth_token`을 제공하지 않아 `AttributeError`. OAuth 기능 자체를 실제 YouTube로 실행한 것이 아니며, 원본 설정/SQLite/사용자 계정 접근 없음.
- 수정: 같은 검사 파일의 격리 fake 객체에 `_youtube_oauth_token=Value()`을 명시적으로 추가한다. 동작 API의 OAuth 토큰 메모리 전용 사용/연결·공식 API 키 기존 경로를 그대로 보존한다.
- 전체 회귀 및 Windows EXE 5-job 전체를 수정된 새 `main`으로 재실행, 실패 시 수정→전체 재검증하고 결과를 후속 절에 사실대로 남긴다.

## 51. 2026-10-21 10시 이후 — 소유 YouTube OAuth 읽기 경로 통합 개발·오류 수정·전체 최종 재검증

### 최신 실제 코드 및 회귀검사
- 49절에서 기존 Windows AISTING Tk 채팅 탭과 4플랫폼 코디네이터/유튜브 리더에 **사용자가 직접 발급받아 입력한 읽기 전용 OAuth 토큰의 메모리 전용 사용**, `mine=true` 보유 방송 열람, 활성 `snippet.liveChatId` 확인, 채팅 읽기 API Bearer 헤더 전송 기능을 누적 구현. 기존 API 키 공개 채팅·중복문자 보존·단일 AI FIFO 유지.
- 첫 코드 Actions run `39526560892`의 전체 회귀는 **2,455 검사 중 오류 1·건너뜀 2**. 50절의 기존 가짜 GUI 입력 객체 누락(`_youtube_oauth_token`) 수정 후 전체 재실행. 이전 실패를 완료로 표기하거나 삭제하지 않는다.
- **최종 수정 코드 전체 회귀 성공** https://github.com/junggyeol4444/AISTING/actions/runs/39526713351 : `Ran 2455 tests`, `OK (skipped=2)`, 실패·오류 0.
- **동일 코드 Windows 통합 성공 5/5** https://github.com/junggyeol4444/AISTING/actions/runs/39526713350 : `windows-exe`, `ollama-real-local-e2e`, `obs-real-readonly`, `twitch-public-readonly`, `korean-public-chat-readonly` 모두 `success`.
- 실제 Windows EXE 산출물: `AISTING-Windows-EXE-integrated`, artifact ID `12312943437`, ZIP 크기 `19,811,468 bytes`, artifact digest `sha256:c49df0a7e08f90d14dc7c4e9f5179e5220b119528637aaab6cc6fa9539171d1c`. 이 산출물은 GitHub Actions Windows 빌드 결과이며 사용자 PC/실방송 검증과 다르다.
- 실행 전 제약: 사용자가 실제로 읽기 전용 OAuth를 승인/발급해야 하며, GUI에는 이미 승인된 액세스 토큰만 입력 가능. **자동 로그인·OAuth 신규 발급·갱신/저장 없음**. 계정·키 실정보 없이 테스트는 모두 가짜 네트워크 응답이었다.

### 다음 기능 및 실증
- 소유 계정의 실제 OAuth 토큰으로 **읽기 전용 소유 활성 방송 채팅 수신**은 아직 미실증. OAuth 토큰 만료 시에는 인증 오류를 표시하고 임의 자동 재승인/재시도하지 않는다.
- 한국어 GPT-SoVITS 합성 → 공식 Open-LLM-VTuber/Live2D Cubism 실제 발화 입 움직임 → OBS의 **동일 발화** 오디오/영상, 실제 시청자 송출, 4플랫폼 실수백명 1~3초 및 24시간 장기 운용은 아직 미실증/미완료.
- 기존 원본 기획/100단계 중 최종 010 승인 대기·캐릭터/SQLite/사용자 설정 보존, 다른 프로젝트/예약/드라이브/방송·녹화/무단 로그인·채팅 발신/유료 API 또는 권리 없는 음성 훈련 미수행. 모든 이전 인수인계 1~50절 및 별도 보존 28~38절 유지.
- 다른 회차는 먼저 위 전체 handoff + 모든 원본 계획/roadmap/main을 읽고, 잔여 여러 기능 묶음 실제 구현 후 **전체** 회귀/Windows EXE GUI/가능 연동 검증, 실패 시 수정 후 **전체** 재검증. SHA·HEAD는 외부 코드 덮어쓰기 방지 용도로만 확인하며 코드 성과로 보고하지 않음.

## 52. 2026-10-21 — 핵심 기능 미실증 원인 실제 소스 조사 및 Windows GPT-SoVITS 실합성 GUI 직접 연결

### 원인: 기존 코드가 있어도 최종 실증을 수행하지 않은 구간
- 소유 YouTube OAuth API reader는 구현·격리 HTTP 검증됐지만 실제 승인 토큰과 소유 활성 방송이 GitHub CI에 없음. CI의 fake OAuth HTTP가 실계정 수신이나 시청자 인입의 증거일 수 없음.
- 공식 `src/ai_broadcaster/original_plan_tts.py`에 `synthesize_local_gpt_sovits` 실제 `127.0.0.1:9880/tts` 요청·PCM WAV 검사 함수가 **이미 있었으나**, Windows 기존 네이티브 채팅 GUI의 별도 실제 합성 버튼과 저장된 기존 Open-LLM-VTuber `conf.yaml`에서 해당 함수까지 호출하는 경로가 없었음. 대화 중 무조건 음성 합성하는 임의 사용은 권리/승인 위반 가능.
- 실제 GPT-SoVITS 모델·합법 참조 음성·사용자 Windows 실행 서버, 공식 WebView2 Live2D, OBS 선택 오디오 입력 동시 존재가 검증되지 않아 저장된 설정 문자열 검사와 OBS 미터 후보가 곧 동일 발화 실증은 아님. 현재 CI Windows runner의 Ollama·OBS read-only 작업은 이 전체 조합을 실제 소유 모델로 실행하지 않음.
- CI 2,455+ 테스트와 Windows 5 jobs가 성공하더라도 실제 방송 100~500명/24시간, 외부 시청자 1~3초 종단 간 전체 지연 측정이 수행된 것이 아님. 기존 단일 AI worker FIFO는 각각 AI 실제 소요시간이 1초라면 500명 신규 메시지의 마지막 건은 약 500초 대기가 생길 수 있어 1~3초 보장은 현재 증명 불가. 사용자가 요청한 전부응답·중복보존을 임의 생략하지 않는다.

### 이번 회차 실개발 — 기존 소스 파일을 함께 확장
1. `src/ai_broadcaster/official_tts_readiness.py`: 기존 저장된 공식 프로젝트의 실제 `conf.yaml`에서 `GPT-SoVITS` 엔진·한국어/로컬 endpoint·실존 WAV/FLAC 참조·녹음 대사를 검증해 동일 실제 합성 API에 전달하는 `read_saved_korean_gpt_sovits_config` 및 권리·실행승인 2중 게이트 `synthesize_saved_korean_gpt_sovits` 추가. 기존 `require_saved_korean_gpt_sovits` 호출 계약·안전검사 그대로 유지.
2. `src/ai_broadcaster/desktop_chat_tab.py`: **기존 Windows Tk 앱**에 `실제 GPT-SoVITS 음성 단독 합성` 버튼을 설치. 기존 공식 프로젝트·참조 파일을 확인하고 권리·1회 실제 합성 승인 후 사용자 입력 한국어 문장 1개를 로컬 엔진에서 실제 생성. 결과의 유효 WAV 프레임/재생 시간/Hz만 확인; 사용자 승인 없이 음성 모델 설치·훈련·파일기록·스피커 재생·방송·OBS 수정 안 함. 별도 worker 사용으로 Tk 메인 스레드 프리징 방지, 진행 중 다른 AI·Live2D·채팅/기억 삭제 동시 실행 방지. 합성 WAV만 성공해도 Live2D/OBS 동일발화가 검증됐다고 보고 금지. 시간 제한/오류 클래스만 화면 노출.
3. `tests/test_aisting_real_tts_gui_probe.py` 신규 독립 6건: 승인 전 요청 없음, 사전 조건 실패시 승인 누르기 이전 차단, 실제 로컬 추론 호출 및 버튼 잠금, 실패시 경로 비노출, 권리 게이트, 실제 설정→기존 추론 전달·재생/저장 금지.
4. `scripts/gui_official_pipeline_click_windows.py`: 실제 Windows 네이티브 Tk 페이지에 새로운 버튼이 화면 안에 표시되는지 및 승인 전 외부 음성 요청이 차단되는지 검증.

### 사용자 지시/미실증/후속
- 기존 1~51절 및 분리 보존 28~38절 원문 삭제·축약 금지, main 빠른전진만, 원본 100단계/캐릭터/SQLite/설정/예약·다른 프로젝트·드라이브 무변경.
- 코드를 실제 main 반영 후 **전체** 2,455+ 회귀와 Windows 5-job EXE/GUI 테스트를 동시에 실행, 실패하면 수정 후 전체 재검증. 성공 테스트는 실제 소유 모델 음성 합성·동일발화 OBS 출력·실사용자 24시간 시청자 1~3초 증거가 아님.
- 실제 GPT-SoVITS 합성은 권리 확인된 참조 음성/모델과 Windows 로컬 엔진이 연결되고 **운영자가 실제 버튼 승인**할 때만 가능. 가짜 모델·불명확한 음성 권리/사용자 PC 무단접근으로 성공 대신 채우지 않음. YouTube는 소유 방송의 읽기 OAuth 동의·토큰이 있어야 실증 가능.
- 다음 회차: 실제 로컬 음성/Live2D/OBS 각 단계 결과와 전체 발화 상관성을 구분하는 진단, 동시에 100~500명 FIFO 실제 처리량과 1~3초 미달 원인을 수치화해 모두 보존하는 기존 코드 발전 필요.

## 53. 2026-10-21 — 실제 TTS 버튼 묶음 최초 회귀검사 실패 수정

- 52절 기능 개발 `main` commit `9fa47b03969e2448404d1d6f08f5da677e4a0ed3`의 첫 전체 Actions https://github.com/junggyeol4444/AISTING/actions/runs/39530009832 : **2,461 검사, 오류 1, 건너뜀 2**. 오류는 새 `tests/test_aisting_real_tts_gui_probe.py`의 `SimpleNamespace` 테스트 GUI에 `_work_official_tts_probe` bound callback 누락(`AttributeError`). 실제 GPT-SoVITS 서버의 음성 합성 오류와는 별개.
- 테스트 fake에 실제 기존 GUI worker 메서드를 명시적으로 바인딩하여 테스트가 사용자 승인 이후 호출·메시지 큐 상태를 검증하도록 수정. 기존 프로그램 코드/권리 게이트·캐릭터·설정·SQLite 변경 없음.
- 수정 후 전체 회귀, 기존 Windows 네이티브 EXE/GUI 및 5-job 검증을 동일 최신 코드로 재실행한다. 반드시 결과를 추가 기록하고 모의 테스트만으로 실제 GPT-SoVITS/Live2D/OBS 합성을 성공 주장하지 않는다.

## 54. 2026-10-21 — 기존 실제 4플랫폼 Windows GUI FIFO 응답시간·장시간 경과 실측 계측 개발

### 직전 전체 실증 기록 확인 (53절 수정 성공)
- commit 775fa3269c4b602f84d794b8bfa8fef01b28e8c0 기준 full regression https://github.com/junggyeol4444/AISTING/actions/runs/39530298737 : **2,461 tests passed, 2 skipped**. Windows https://github.com/junggyeol4444/AISTING/actions/runs/39530298959 : **5/5 jobs success** (windows-exe, korean-public-chat-readonly, twitch-public-readonly, obs-real-readonly, ollama-real-local-e2e). 첫 한 건 테스트 오류는 53절에서 이미 수정됨.
- CI 통과는 사용자 실 소유 방송 계정·한국어 GPT-SoVITS 음성 모델·Cubism 립싱크·OBS 최종 음성/시청자 전달의 실제 증명이 아님.

### 이번 묶음 개발 후 전체 재검증
1. src/ai_broadcaster/live_runtime_metrics.py 추가: **실제 로컬 Windows GUI 수신**의 FIFO 대기·실제 AI 생성 처리·합계 초, 초과 3초·실패·유효하지 않은 단조 시각·오류·수신 접수와 완료 차이, 최근 최대 1,024 샘플 p95 및 세션 로컬 실행시간. 채팅 텍스트·사용자명·API 토큰·음성 파일 저장 금지. 수신기의 24시간 경과는 OBS 송출 24시간 증거가 아니라는 명시적 상태. 500/2,000/10,000건에서도 샘플 메모리 제한. 지연을 일부러 추가하거나 이미 받은 독립 메시지를 임의 버리지 않음.
2. src/ai_broadcaster/desktop_chat_tab.py 수정: 기존 single AI worker의 AI 처리 시작 단조 시각을 실제 수신 GUI 접수 시각과 결합. 기존 이벤트 twitch_ai_latency 계약과 새 twitch_ai_timing (대기, 추론, 총계, 실패)를 동시에 보고. 연결 시작 시 세션별 메트릭 초기화, 실제 채팅 각각 수신 계수, 실제 오류 및 운영자 Stop 완료 계측; 이전 세션을 새 세션에 섞지 않음. 한국어 원래 GUI 대화창에 최초 3건·25건마다 실제 계측 요약, Stop 후 최종 합계 표시. 텍스트/일반 방송 채팅 외부 발신 없음.
3. tests/test_aisting_real_live_runtime_metrics.py 신규 8건: 500건 p95 대기·AI 분리, 10,000건 샘플 한도, 24h 로컬 경과 허위 방송 증명 방지, 단조 시각 유효성, 2,000건 중복/실패 보존, 실제 worker 성공/실패 시간 이벤트와 기존 호환성, Tk 기존 폴 처리 연결.
4. docs/LIVE_REAL_FIFO_LATENCY_AND_24H_VALIDATION.md 신규: 사용자 Windows 실사용 단계, 소유 YouTube OAuth 읽기 절차, GPT-SoVITS 허가 음성, 실제 Cubism RMS/OBS 미터 겹침, 수백명 24시간 단말 수신 확인, 최종 관객 1~3초 구간은 아직 미계측 명시.

### 현재 검사 경계
- 이 개발은 1~3초를 **보장**하지 않음. 실제 로컬 FIFO 대기가 3초를 넘는 건을 정량적으로 밝혀 미충족을 확인할 수 있음. 로컬 3초 이내가 시청자 종단 간 3초 보장은 아님.
- 실제 Windows 사용자 방송·참조 음성·OBS·YouTube 소유 OAuth는 사용자 자산 및 운영자 명시적 동의가 필요한 외부 런타임. 사용자가 승인하지 않은 로그인·마이크 녹음·방송 시작/중지/계정 송신은 하지 않음. 드라이브 무연결, 다른 프로젝트 무변경.
- user instruction: main 누적 수정만, 1~53절 기존 기록 그대로 보존, 신규 브랜치/강제푸시/원복 없음, 한국어 사용자 표시, 실제 전체 테스트와 Windows EXE/GUI 검사 결과를 확인 후 실패면 재개발·재검증. 단순 2,000건 격리 모의로 실사용 인증 금지.

## 55. 2026-10-21 — 본인 소유 YouTube 읽기 OAuth 운영자 동의부터 네이티브 Windows 채팅 GUI 연결 개발

### 선행 전체 회귀 완료
- 54절 local real FIFO metrics main commit 727666f76831c17f8d30a9aecdfa966a20bbbc9e, workflow https://github.com/junggyeol4444/AISTING/actions/runs/39532204720 : 2,469 passed, 2 skipped, 실패 0. Windows https://github.com/junggyeol4444/AISTING/actions/runs/39532204746 : 최종 job 상태 별도 확인 필요. 이전 단계 한 건 mock 대신 실제 사용자 수신 지연을 분리해 계측하도록 코드를 연결했음. 새 Google 인증 구현은 이 통과 회차에 포함되지 않음.

### 이번 개발 (새 HTML/web 앱이 아닌 기존 Tk Windows EXE)
1. src/ai_broadcaster/youtube_desktop_oauth.py 신설: YouTube Data API 소유 계정 읽기 전용 Google 데스크톱 OAuth 인증을 **운영자가 GUI에서 누른 뒤에만** 개시. 공식 시스템 브라우저 Google consent; 암호학적 PKCE S256·state CSRF·127.0.0.1 임시 loopback callback·일회성 code 교환 Google token API. scope youtube.readonly만 요청, browser log/HTTP error text에 코드·token 노출 금지, 외부 호스트에서 callback 수신 금지. refresh token 요청/파일 저장/채팅 송신/방송 송출/자동로그인 안 함.
2. src/ai_broadcaster/desktop_chat_tab.py 확장: 기존 '유튜브 OAuth 읽기 토큰' 입력 오른쪽에 'Google 소유 계정 읽기 승인' 버튼, 승인 다이얼로그 및 운영자가 제공한 데스크톱 client ID/secret 입력, UI 멈춤 방지 background worker, 결과는 GUI의 기존 토큰 메모리 상태에만 반영. 승인 성공 후에도 '내 활성 방송' 선택 및 기존 시작 버튼을 사용해야만 실제 실시간 채팅 API 조회 개시. 재인증 흐름과 다른 AI·채팅 작업의 중복 시작 차단.
3. scripts/gui_official_pipeline_click_windows.py: 기존 네이티브 Tk 실클릭 Windows E2E 검사에 OAuth 버튼 표시/1280 폭 확인 및 승인 거부 시 Google 브라우저 열림·client prompt·로그인·네트워크 0건인 fail-closed 검사.
4. tests/test_aisting_owner_youtube_desktop_oauth_pkce.py 신규 11건: PKCE, read-only scope, state mismatch·중복 코드 차단, 미승인 상태 무시, 잘못된 client ID 차단, Google token POST 정확성(모의 URL), 권한 누락 차단, 127.0.0.1 로컬 callback 실제 HTTP 통신 테스트, GUI 거절/오류/메모리 수신.
5. docs/LIVE_REAL_FIFO_LATENCY_AND_24H_VALIDATION.md: 기존 54절 원문 보존, 소유자 OAuth Google 운영자 동의 실사용 절차 및 토큰 만료 재승인 한계 추가.

### 외부 실사용 증명의 정확한 경계
- OAuth 로컬 승인 코드↔Google token API 연결은 실제 사용자 소유 Google 개발자 OAuth client 설정과 운영자 로그인 동의가 있어야 성공. 이 코드가 CI에서 mock으로 성공해도 실제 소유 방송 읽기/게시된 메시지 인입 성공은 아님.
- 브라우저는 구글 인증 규격상 외부 Google 계정 동의를 보여줄 때만 사용. 사용자 프로그램은 Windows Tk EXE 그대로, 웹/HTML UI나 Drive 연동 추가하지 않음.
- 24시간 YouTube OAuth access token 만료 재인증 문제는 실환경에서 여전히 확인 필요(운영자 권한 갱신 방침 결정 필요). 외부 계정 임의 인증/갱신 없음.
- 기존 1~54절 삭제/축약 금지; main에 누적 변경만, 버전 되돌리기/새 브랜치/force push 없음; 사용자 캐릭터/프로필·SQLite·OBS·음성 권리는 유지.

## 56. 2026-10-21 — Google 동의 취소 즉시 처리 및 완료 CI 후속
- 55절 main 2f3f86a5d6f126f1df6f8f478b49dbcfaf628501 전체 검증 https://github.com/junggyeol4444/AISTING/actions/runs/39533089714 : **2,480 tests passed, 2 skipped**. Windows EXE https://github.com/junggyeol4444/AISTING/actions/runs/39533089642 : **5/5 jobs success** (windows-exe, twitch-public-readonly, korean-public-chat-readonly, ollama-real-local-e2e, obs-real-readonly). 실제 소유 Google 계정/OAuth/한국어 음성 모델·24시간 시청자 실증은 아님.
- 운영자 Google 동의 거절한 뒤 OAuth 콜백 상태가 유효하면 이전에는 150초 만료까지 기다릴 수 있던 문제 해결: 승인 취소 표시 시 즉시 거절 완료하고 네이티브 GUI를 복구. 악성·무효 state/임의 요청은 별도 무시/상한 유지. 비문자 token_type 응답에서 AttributeError 대신 안전한 명시적 RuntimeError로 종료, 원본 응답/자격증명 비노출.
- 새 로컬 loopback 실제 HTTP 취소 시나리오와 잘못된 token_type 테스트 2건 추가, 비동기 로컬 응답 검증 race 줄이기 위해 테스트 스레드 join.
- 변경 파일: src/ai_broadcaster/youtube_desktop_oauth.py, tests/test_aisting_owner_youtube_desktop_oauth_pkce.py, 본 누적 문서. 기존 소스/기획서/캐릭터/모든 단일 AI FIFO/4플랫폼/Windows/로컬 설정 및 1~55절 유지. main 빠른 전진만. full regression 및 Windows build 다시 검증.
- 다음 핵심 실증: 유저 본인 소유 Google OAuth desktop client 및 본인 방송 동의, 실제 음성 권리확인 GPT-SoVITS 모델·Official Live2D·OBS 같은 발화, 100~500명·24시간·관객 1~3초. 실행을 허용받지 않은 실제 계정/음성/방송을 임의로 만지지 않음. 갱신 토큰 없는 Google online OAuth access token의 만료 이후 24시간 연속 소유 방송 수신을 보장할 수 없으므로 계속 미검증.

## 57. 2026-10-21 실제 한국어 GPT-SoVITS WAV → 실제 OBS 오디오 입력 실행 버튼 누적 연결

### 검증된 기존 요소와 외부 환경 경계
- 이전 회차 main 3c3139347b7b433708c26a18d1f390fa749de786의 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39533463390 는 2,482건 통과, 2건 건너뜀. Windows EXE/GUI·Ollama·OBS 읽기전용·공개채팅 5개 작업 https://github.com/junggyeol4444/AISTING/actions/runs/39533463364 성공. 이를 실제 소유 음성 모델/실방송 성공으로 재해석하지 않음.
- 원본 1~56절 전체 보존. docs/ORIGINAL_PLAN.txt와 docs/ROADMAP_100.md 및 config/roadmap.json 원본 유지, 캐릭터·SQLite 및 사용자 설정 변동 없음.
- 이미 존재하던 src/ai_broadcaster/original_plan_voice_obs_bridge.py의 verify_gpt_sovits_to_obs는 **실제** 승인된 로컬 GPT-SoVITS /tts WAV를 수신한 뒤 OBS WebSocket의 방송·녹화 상태를 검사하고, 임시 파일과 고유한 ffmpeg 음성 소스를 만들어 실제 OBS 오디오 미터 신호를 관찰한 뒤 소스를 제거하는 구현임. 유효한 실제 모델과 사용권리/승인된 음성 파일/실행 중인 OBS가 없으면 성공할 수 없음.

### 이번 실개발 변경 묶음
1. src/ai_broadcaster/desktop_chat_tab.py 기존 Windows Tk GUI에 '실제 GPT-SoVITS 음성 → OBS 입력 검사' 명시적 버튼 추가. 현재 기존 공식 프로젝트의 저장된 한국어 모델·참조 WAV/FLAC·참조 대사를 읽고, 사용자 실제 한국어 입력/OBS 암호 준비/기존 사용 중인 AI 작업 차단·권리 확인/임시 OBS 오디오 입력 생성에 관한 개별 동의 후에만 기존 verify_gpt_sovits_to_obs를 비동기 단 한 번 호출. 기존 OBS 방송/녹화·씬 안전 검사/임시 소스 정리는 **기존 실제 브리지 구현**이 담당.
2. 기존 GPT-SoVITS 음성만 테스트하는 버튼, 본래의 '공식 AI→Live2D→OBS 같은 발화 동시 실측' 버튼과 동일한 busy 상태를 공유해 동시 모델/OBS 충돌을 회피. 실증 신호 미확인/작업 실패 시 원본 경로·WebSocket 암호/예외 원문을 화면에 표시하지 않음. WAV→OBS 미터 신호 성공조차 **Live2D 립싱크 성공 또는 시청자 송출 성공이라고 표시하지 않음**.
3. tests/test_aisting_real_tts_obs_native_gui.py 신규 8개: 없는 모델/OBS 암호/승인 거절 시 IO 0건, 실제 기존 브리지에 승인+WAV/음성·로컬 API 인자 정확히 전달, 오류 시 비밀정보 보호, 실제 미터 신호와 무신호 결과 분리, 타 작업 중 요청 거부.
4. scripts/gui_official_pipeline_click_windows.py 기존 Windows 네이티브 Tk E2E 실클릭에 새 실제 음성→OBS 버튼 존재/승인 거부 시 외부 연결 없음 검사 추가.
- **검증 결과**: 본 코드를 main에 보존형 적용한 뒤 전체 회귀 및 Windows EXE GUI/OBS/로컬 Ollama/공개 읽기 실제 CI를 실행해 확인하고, 실패 시 코드/테스트 수정 후 전체 재실행할 것.

### 남은 핵심 실증
- 이 버튼은 기존 공식 프로젝트에 합법 한국어 GPT-SoVITS 모델·참조 파일이 실제 설치되고 서버가 실행되며, 로컬 OBS가 일시 정지된 사용 허가 상태에 있을 때 *진짜 음성→OBS 입력 실증*을 실행 가능하게 함. GitHub runner는 사용자 소유 보이스 모델 파일을 갖고 있지 않음; 이를 임의 훈련·무허가 샘플/가짜 오디오로 대체하여 GPT-SoVITS 성공으로 주장하지 않음.
- **전체 동일 발화**는 별도 기존 original_plan_full_pipeline.verify_official_chat_live2d_obs에서 이미 공식 Open-LLM-VTuber AI 한 세션, Cubism 입 + OBS 동일 미터 타임스탬프를 검사하며 이 기능과 임의 2중 TTS 호출하지 않음. 실제 모델·아바타·WebView2·OBS 경로의 동시 실증은 별도, 라이선스 명확한 자산 준비 필요.
- 실제 시청자 수백 명·24시간 스트리밍·최종 도달 지연은 운영자가 통제하는 실계정/장치 방송 실행이 있어야 관측 가능. 개발된 500~10,000건 큐·p95 국소 측정은 방송 도달 보장 아님.
- Google Drive 등 외부 드라이브 사용/요구 없음. 다른 프로젝트/예약/브랜치/전면 재개발/무단 방송·녹화·채팅 발신 없음.

## 58. 2026-10-21 — 57절 실제 GPT-SoVITS→OBS 네이티브 버튼 전체 검증 성공 및 인수인계

### 검증된 기존 main의 누적 코드와 이번 회차 결과
- 실제 코드 변경 커밋: https://github.com/junggyeol4444/AISTING/commit/41099c11137be378dbd3ab4fc7796cb7154f8629
- **전체 회귀 성공**: https://github.com/junggyeol4444/AISTING/actions/runs/39540229262 — Ran 2490 tests, OK(skipped=2), 실패 0. GPT-SoVITS→OBS 신규 GUI 관련 8건 격리검사 포함.
- **Windows 전체 성공**: https://github.com/junggyeol4444/AISTING/actions/runs/39540229198 — windows-exe, twitch-public-readonly, korean-public-chat-readonly, ollama-real-local-e2e, obs-real-readonly 총 5/5 성공. Windows 실버튼 로그에서 WINDOWS_ACTUAL_GPT_SOVITS_TO_OBS_BUTTON_DENY_NO_IO_PASS, WINDOWS_REAL_TTS_BUTTON_VISIBLE_OFFLINE_FAIL_CLOSED_PASS 확인. 승인 거절 시 계정/모델/OBS IO 0건.
- Windows EXE 산출물 AISTING-Windows-EXE-integrated, artifact ID 12319421532, ZIP 크기 19,840,393 bytes, SHA-256 digest 438ded189a1cc2764de6829cc2e04a6c1b64b88507af0746ae7d6d882ca96120.
- 기존 실제 original_plan_voice_obs_bridge.verify_gpt_sovits_to_obs를 native Tk에 연결. 저장된 한국어 GPT-SoVITS 설정→합법 참조 WAV/FLAC 실제 1회 합성→현재 OBS가 송출/녹화 중이 아닌지 확인→고유 임시 OBS ffmpeg 입력 생성→실제 미터 이벤트→임시 입력/WAV 정리. 권리와 각 단계 사용자 명시 승인 우선, 로컬 실제 환경 없는 CI 성공을 허위 GSV 합성 인증으로 바꾸지 않음.

### 실제 실행 증명의 남은 경계
- GitHub Windows CI에서 실제 OBS Studio와 실제 Ollama를 구동한 부분은 성공했지만, **이 CI에서 권리 확인된 GPT-SoVITS 학습 모델/한국어 참조 음성은 설치되어 있지 않음**. 승인 거부를 검증하는 native GUI 테스트는 실제 GSV 합성 성공의 근거가 아님.
- 실제 합법 보이스 참조·모델과 Windows OBS에서 새 버튼으로 WAV→OBS 신호 실증, 공식 Live2D의 같은 발화 RMS·입/동일 오디오 미터 시간 겹침, 원격 시청자 도달·수백명 24시간/1~3초 실증은 별개. GSV 합성 테스트 한 건과 별개 Live2D 대사를 짜맞춰 동일 발화 성공 주장 금지.
- Google 소유계정의 OAuth 인증/실방송 수신도 명시 운영자 권한 필요. 다른 장치/계정·음성 무단 접근 및 훈련/녹화/송출/채팅 발신 없음.
- 기존 1~57절 원문 및 28~38절 별도 보존 원문, original plan/100 roadmap/config/SQLite·설정·캐릭터·다른 프로젝트/예약 유지. main 외 branch·force push·rollback/Drive 연결 없음. 문서 전용 추가 커밋 후 CI가 재개되더라도 위 성공 run은 정확히 57절 코드 커밋 기준.

## 59. 2026-10-21 — 핵심 3경로 직접 개발: 실제 OBS 오디오 시각↔Cubism 입 상관 검증 및 실제 Ollama 4플랫폼 장시간 부하 실행

### 선행 원본·사용자 지시
- GitHub main 실제 HEAD 확인/원본 누적 handoff 1~58절 전부 보존(기존 28~38절 원문은 docs/hourly-handoff-appendices에 별도로 보존). ORIGINAL_PLAN.txt / ROADMAP_100.md / config/roadmap.json 원본 그대로. 다른 프로젝트, 예약/브랜치, 기존 설정/SQLite/페르소나 무변경. 사용자는 미개발 핵심을 실제로 구현하고 전체 검증하라고 반복 지시했음.
- 기존 58절 코드 회귀 2,490 tests/2 skipped, Windows EXE 5/5 jobs PASS 는 **이전 코드 기준**. 이번 변경 자체에 대한 Actions는 새 커밋 이후 확인해야 함.

### 이번 실제 코드 구현 — 기존 제품 소스 대체/재개발 아님
1. src/ai_broadcaster/original_plan_obs.py: 실제 OBS WebSocket input-volume-meter 이벤트에서 선택된 입력의 **0.001 이상 실제 비무음 신호**가 발생한 monotonic 첫/마지막 시간을 기록한다. 기존 OBS 입력 이름/UUID/mute/volume/route 검사를 유지하고, 이전 검사 자료는 zero 기본값으로 두어 시각이 없으면 증거 불충족. OBS 소스 생성/방송/녹화 없음.
2. src/ai_broadcaster/original_plan_full_pipeline.py: 기존 같은 Live2D Cubism/RMS 1회 발화 관찰을 유지하며, 단순 1~3초 OBS 관찰 윈도우 겹침만으로 동일 발화를 참으로 처리하던 오류를 수정. 실제 OBS **비무음 미터 이벤트 first/last**와 실제 Cubism의 first_audio_mouth/last_audio_mouth 시각이 같은 monotonic 시간에서 직접 겹쳐야만 temporal_overlap_candidate=True. 실제 OBStudio 입력 경로·씬 변경·오디오 신호 확인 조건 유지, 다른 발화 조각을 동일 출력으로 짜맞추지 않음.
3. tests/test_aisting_official_chat_obs_pipeline.py: 관찰 윈도우만 겹치고 실제 미터 발생 시각이 앞선 경우를 거부, OBS 이벤트 monotonic 값이 없으면 동일 발화 성공을 거부; 기존 실제 타임 윈도우 모의 검사 개선.
4. scripts/aisting_real_ollama_fifo_soak.py: 실제 사용자 Windows PC의 **설치된 실제 로컬 Ollama 모델과 AISTING의 기존 single-AI-worker FIFO**를 통과하는 4플랫폼 합성 500건 이상 스트레스/24h watchdog 실행기. 실제 로컬 run_local_chat / SQLite(격리된 OS temp directory) 경유, 절대로 모의 LLM 결과로 성능을 속이지 않음. 플랫폼/동일 문장 보존, 개별 실제 AI 성공/실패/p95/3초 초과·최대 Python 메모리/미처리 건수, 기간/처리량 보고. --arrival-rate로 synthetic feed 조절 가능, --hold-full-duration으로 운영자가 정확히 지정한 경과시간(최대 86,400초) 유지 검사 가능. 실제 시청자·방송 24시간 증거와 구별.
5. .github/workflows/build-windows.yml: 기존 Windows actual local Ollama job에서 실제 AISTING GUI+실제 Ollama 응답 후 4개 플랫폼 합성 채팅 각각 한 건씩 실제 원래 모델 경로(모델 qwen2.5:0.5b)를 실행하는 Windows E2E 스트레스 smoke 추가. CI 성공은 500명 실제 방송 24h 결과가 아니며 500명 본실측은 앞의 실행기를 원본 Windows 앱 환경에서 돌려야 함.
6. tests/test_aisting_real_local_fifo_soak.py: 모델 없이도 synthetic 동시 사용자 정의/중복·4플랫폼·24시간 한도/오류 거부를 검사. 실제 모델 사용 여부는 Windows E2E에서 확인.

### 다음 조치/검증 경계
- 위 실질 기능들을 묶어 기존 main에 커밋 → 전체 회귀/Windows 네이티브 EXE + 실제 Ollama + OBS 공개읽기 5-job 검사, 실패 시 소스/검사 오류 수정 후 전체 재실행. 결과/새 artifact를 반드시 60절에 정확히 추가.
- 사용자 계정 YouTube OAuth의 실제 동의와 본인 활성 방송 수신, 실제 권리 확인된 한국어 GPT-SoVITS 모델/참조 보이스를 활용한 실제 합성→공식 Live2D Cubism→OBS 동일 발화, 원격 시청자 최종 도달 지연/실제 방송의 수백명 24h은 **이 격리 GitHub runner에서 성공했다고 보고 금지**. 윈도우/모델 준비 없이 모의 입력으로 대신 성공 처리 금지. 로컬 OBS 입력 미터와 Cubism 시간 직접 상관 코드는 이제 실제 성공/실패를 제대로 가를 수 있어야 함.

## 60. 2026-10-21 59절 통합 코드 첫 전체 회귀 실패 실제 확인·수정

- 첫 수정 기준 main b19875573d1d8e848d85cf9aa0094c57fc0b3b1b 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39544322528 : 2,496 tests, failures=1, errors=1, skipped=2. Windows 전체 https://github.com/junggyeol4444/AISTING/actions/runs/39544322580 의 Windows EXE job도 같은 2개 단위 검사에서 실패. 성공이라 허위 보고하지 않음.
- test_aisting_official_chat_obs_pipeline.py의 지연 TTS 시간 mock 코드에서 import time 문이 사용 이후에 있어 UnboundLocalError가 발생했고, 음성과 입 움직임이 *서로 다르다*는 부정 예시에서 OBS의 음성 이벤트 마지막 시각을 관찰 창 종료 시각으로 설정해 실제로는 양쪽이 겹치는 잘못된 테스트 입력이었음.
- 기존 OBS 실제 monotonic 소리 first/last 기록 및 공식 Cubism first/last timestamp 직접 겹침 판정 기능 자체는 유지한다. 지연 TTS 테스트의 import 선행과 부정 예시를 80ms 넓은 관찰 구간 중 초기 1ms 비무음 OBS 신호만 있도록 정확히 수정. full regression/Windows EXE·real Ollama·OBS·CHZZK·SOOP·Twitch 5 jobs 모두 새 main으로 재실행하고 실패하면 코드 수정 후 전체 재검증한다.
- 59절에 이미 포함된 scripts/aisting_real_ollama_fifo_soak.py는 실제 4플랫폼 합성 채팅 500건 이상/24h 로컬 사용 가능한 스크립트이며, GitHub Actions에는 **모의 모델이 아닌 실제 CPU Ollama 4개 메시지** 간단 시험을 추가함. 이 짧은 시험의 성공이 수백명 실제 방송 24시간 결과는 아니다.

## 61. 2026-10-21 — 채팅 실수신 장애 확인 후 공식 Twitch 읽기 OAuth 기존 Windows·4플랫폼 연결

### 실제로 발생한 검증 결과
- 60절 테스트 시간 수정 commit 4eec3274af1cc5560abc536e6f9f0b2f18825f5c.
- 전체 회귀 https://github.com/junggyeol4444/AISTING/actions/runs/39544602085: **2,496 tests passed, 2 skipped, 0 failures**. OBS non-silent meter timestamp vs Cubism first/last strict overlap 검사 포함.
- Windows 통합 https://github.com/junggyeol4444/AISTING/actions/runs/39544602255: Windows EXE, 실제 Ollama, 실제 OBS, CHZZK/SOOP 읽기 **4/5 success**; Twitch 공개 읽기 1 job FAIL. 실제 IRC JOIN은 xqc/ow_esports/valorant 각 채널에서 확인됐지만 PRIVMSG가 0건이므로 실제 채팅 읽기 성공이라고 주장하지 않음.
- 실제 Ollama Windows 작업 로그에는 ACTUAL_OLLAMA_FOUR_PLATFORM_FIFO_SUCCESS 4, 실제 local p95 6.312초 측정. 실4명 시청자가 아니라 4개 플랫폼 별 1개 synthetic chat을 기존 실제 Ollama+SQLite/1-worker FIFO로 실행한 결과. **이미 3초 초과**, 그러므로 100~500명/1~3초 보장 검증 성공 금지. 기존 script 500건/24시간 옵션은 장시간 실측 수행시 사용할 실행 코드이지 현 GitHub CI에서 24시간 성공했다는 의미 아님.
- Twitch 개발자 공식 명세: https://dev.twitch.tv/docs/chat/irc 는 IRC 읽기에 이용자 OAuth access token + chat:read scope 및 PASS oauth:... 다음 NICK OAuth 소유 계정이 필요하다고 명시. 익명 justinfan JOIN은 실채팅 READ 성공 증거가 아님. 기존 익명 경로의 호환성은 유지하되 성공 단정 금지.

### 이번 누적 실제 코드 개발
1. src/ai_broadcaster/twitch_readonly.py 기존 읽기 전용 IRC 수신기에 운영자 제공 oauth_token / oauth_login 선택형 인자 추가. 2개 동시 제공 및 형식 검증; 명시 승인 토큰 사용 시 WSS 실제 PASS oauth:<token>, NICK 소유 계정 ID, CAP tags/commands, JOIN 순서로 인증하고 기존 모든 PRIVMSG 중복/순서 그대로 전달; PRIVMSG 게시/채팅 편집권한/로그인 자동화 없음. 익명 원래 생성/검사 호환 유지.
2. src/ai_broadcaster/multi_platform_session.py 기존 4플랫폼 읽기 코디네이터에 Twitch 전용 token·username 전달 추가. CHZZK/SOOP/YouTube 원본 코드/키·큐/캐릭터/설정 보존.
3. src/ai_broadcaster/desktop_chat_tab.py 원래 Windows Tk에 Twitch 읽기 승인 토큰(가려진 입력) 및 소유 계정 이름 입력줄을 추가하고 단일 Twitch/4플랫폼 전체 실제 채팅 수신 세션에만 메모리 자격증명 전달. 화면 종료 시 키/이름 삭제. 사용자 명시 수신 버튼 전 어떤 Twitch 네트워크 I/O도 실행하지 않음.
4. tests/test_aisting_twitch_owner_readonly_auth.py 5개 격리 테스트: 승인 수신기 초기 네트워크 없음, AUTH PASS/NICK 순서와 실제 중복 IRC 메시지 보존/발신 명령 없음, 잘못된 자격증명 차단, 4플랫폼 코디네이터 전달, 익명 하위 호환.
- 이후 전체 회귀/Windows 5-job 검증. Twitch 공개 CI job은 사용자 실제 인증정보가 없고 익명 읽기 메시지가 없으면 실패할 수 있으며 이를 PASS로 위장하지 않는다.

### 미완료의 정확한 범위
- GPT-SoVITS 한국어 실제 소유권 확인된 모델·참조 음성+Live2D·OBS 같은 발화 현장 실증 및 사용자 PC 실제 수백명·24h·시청자 1~3초는 아직 수행되지 않음. 새 OBS 시간 상관·실 Ollama 4건은 준비된 실행 가능한 도구/측정값이지 그 현장 증거가 아님. 사용자가 제공하지 않은 저작권 있는 보이스·계정에 접근하거나 모델 무단 훈련/방송·채팅 발신 금지.
- 기존 handoff 원문 1~60절 및 분리 보존 28~38절, ORIGINAL_PLAN/ROADMAP/roadmap.json, Windows 네이티브 GUI/모든 사용자 설정·SQLite 유지. only main fast-forward, 신규 브랜치/force push/rollback/Drive 연결 없음.

## 62. 2026-10-21 Twitch 읽기 OAuth 신규 검사 1건 실패 수정·실제 전체 재검증

- 첫 인증 코드 통합 main 98212d31029a6b50965cf592ac1e6601cca26bc8의 전체 https://github.com/junggyeol4444/AISTING/actions/runs/39545322611 은 2,501 tests, failures=1/skipped=2. Windows https://github.com/junggyeol4444/AISTING/actions/runs/39545322615 에서 windows-exe job도 동일 회귀 fail. Twitch 실제 public IRC 실수신 job은 이 시각 success였지만 OAuth 사용자 실제 토큰 실수신을 의미하지 않음.
- 신규 tests/test_aisting_twitch_owner_readonly_auth.py에서 빈 token 문자열 ''이 보안오류 메시지에 없다는 assertNotIn은 항상 실패하므로 비어있지 않은 token에 한해서 실제 노출 차단을 검증하도록 정정. src/ai_broadcaster/twitch_readonly.py의 token ASCII 형식 검증 강화(이상 Unicode 자격증명 방지); chat:read 자격증명은 운영자가 승인받아 입력하고 읽기 전용 WebSocket으로만 전달, 채팅 발신 없음. 익명 원본 경로 유지.
- 수정된 정확한 최신 main에서 전체 회귀와 Windows 네이티브 EXE/Ollama/OBS/CHZZK-SOOP/Twitch job 5개를 다시 검사하고 결과 미확정이면 완료라 보고 금지. 61절 외 기존 1~61절 모두 원문 보존.

## 63. 2026-10-21 최종 누적 통합 개발 검증 — 같은 발화 OBS 실제 이벤트·4플랫폼 실 Ollama·Twitch 허가 수신·Windows EXE 성공

### 완료하고 검증한 실개발
- **현재 실제 코드 커밋 5e6747c963b5a1b81f5a58429f6338b2521f0d18**: OBS 실제 InputVolumeMeters non-silent 이벤트의 첫/마지막 monotonic 시각 기록과 공식 Live2D Cubism 실제 입 변화/오디오 RMS 시각 겹침 검증, 기존 넓은 OBS 관찰창만 겹치면 성공하던 거짓 후보 차단.
- 기존 run_local_chat / LocalOllamaReplyGenerator / ChatPipeline / 하나의 AI FIFO로 실제 로컬 Ollama 추론을 실행하는 scripts/aisting_real_ollama_fifo_soak.py 추가. 합성 4플랫폼 각 건수·중복·500건 및 최대 24h 실행 옵션·로컬 대기/실제 모델 처리 p95·실패/3초 초과·미처리·Python 메모리 진단. 별도 실제 모델 런타임과 격리 temp SQLite 사용. AI 성능 실측에서 플랫폼→시청자 도달을 절대 성공 주장 금지.
- Twitch 공식 IRC chat:read User Access Token으로 WSS PASS oauth 인증 및 NICK 로그인 ID 입력 지원. 기존 익명 호환 유지하지만 익명 JOIN은 PRIVMSG 실수신 성공과 동치가 아님. 운영자 승인받은 토큰은 원본 Tk 메모리 입력/서버만 사용, 종료시 UI 비움. 사용자 계정 무단 로그인/채팅 발신·stream/edit 권한 사용 없음.
- 이번 실제 코드 변경은 기존 원본 기획·100단계 상태·기존 1~62절 인수인계/28~38절 별도 원문, 캐릭터/SQLite/나머지 3개 플랫폼 보존. main 빠른전진만, 다른 프로젝트·예약·Drive·브랜치 변경 없음.

### 첫 실패 → 수정 → 전체 재검증
- OBS 시간 관련 두 개의 신규 fixture에 Python import 순서 및 80ms 관찰 중 비무음 1ms만 남기도록 만드는 테스트 입력 오류가 있어서 **첫 GitHub 전체 회귀 39544322528와 Windows build 39544322580는 FAIL**. tests/test_aisting_official_chat_obs_pipeline.py 실제 테스트를 수정한 후 **39544602085 full regression 2,496 PASS / 2 skipped**. Windows 39544602255에서는 4개 성공, Twitch 공개 실채팅 0건으로 1개 FAIL.
- Twitch 공식 문서 https://dev.twitch.tv/docs/chat/irc 상의 chat:read 권한 요구를 대조해 허가받은 User Access Token을 사용하는 코드/GUI/5 tests를 추가. 첫 신규 검사에 빈 토큰 문자열의 assertNotIn 검사 오류가 있어 첫 전체/Windows run 39545322611, 39545322615 FAIL. 빈 문자열에는 검사 생략, nonempty token 누출 거부와 ASCII 검증을 강화.
- **최신 실제 코드 통합 최종 회귀** https://github.com/junggyeol4444/AISTING/actions/runs/39545547954 : **2,501 tests, 2 skipped, 실패 0**.
- **최신 Windows 네이티브 EXE·GUI/실제 Ollama/OBS/공개 채팅 최종** https://github.com/junggyeol4444/AISTING/actions/runs/39545547991 : 5/5 jobs success: windows-exe, obs-real-readonly, twitch-public-readonly, korean-public-chat-readonly, ollama-real-local-e2e.
- 실제 Windows EXE artifact: AISTING-Windows-EXE-integrated, ID **12321383424**, ZIP **19,844,818 bytes**, sha256 **b58c51be8570a7dfd750fba744b5bf012b1d25f436c84aa8a7c7a9fdabd5a45d**.
- 최초 Windows 실제 로컬 4플랫폼 각 1개씩 단일 Ollama 모델 처리 테스트에서 4/4 완료했지만 **로컬 p95 = 6.312초**인 사례가 있었음. 1~3초 목표를 달성했다는 증거가 아니고 실제 성능 개선의 필요 수치. 최종 Windows run에서의 실제 4채팅 처리 로그 또한 별도 확인 가능. Windows 이격리 런은 500명·24h **실사용** 검증이 아니라 실제 모델의 짧은 CI 소요 수치.

### 미완료의 물리적 실증과 다음 작업
- 사용자 소유한 합법 한국어 GPT-SoVITS 훈련 모델·참조 음성이 CI/내부 런타임에 제공되지 않음. 한국어 음성→Live2D 공식 Cubism 실제 입/OBS 실제 같은 발화 신호 동시 성공을 실제 모델·실사용 Windows 환경에서 아직 관측하지 못함. 그러나 실제 호출·동일 시각 판정 구현과 네이티브 EXE 버튼/권리게이트/OBS 읽기 검증은 구현됨.
- 사용자의 소유 YouTube/Twitch 계정 실제 OAuth 동의는 본인 승인 필요. 익명 Twitch 실제 공개 읽기 CI 성공이 운영자 계정 OAuth 성공은 아님.
- 실방송 100~500명 실제 시청자에 대한 24시간 안정성/최종 시청자 1~3초 종단간 지연도 사용자의 실제 장비/승인 방송에서 수행되지 않음. 500 합성 채팅을 실제 로컬 Ollama로 24시간 지속시키는 실행기는 존재하므로 차후 그 환경에서 **실제로 24시간 종료한 뒤에만** 성공 처리.
- 본 누적 기록은 전체를 삭제·요약·롤백하지 않는다. 다른 프로젝트/자동예약 사용자별 설정 변경 없음.
