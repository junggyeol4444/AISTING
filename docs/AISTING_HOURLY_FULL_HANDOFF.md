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
