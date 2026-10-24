## 161. 2026-10-24 — 실제 FIFO 포화 대기시간의 최초 수신시각 보존 개발

### 기준 및 원문 보존
- 시작 시점 실제 main HEAD: `eb1adae620f349c5a5b6ca34c7b38f426e965860`. 원본 1~160절, 모든 과거 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 실제 소스를 기준으로 이어 개발했다.
- 기존 Windows 4플랫폼 실수신 경로는 네트워크 수신 콜백의 최초 시각 `reader_received_at`을 큐 포화 전부터 유지한다. 반면 기존 실제 Ollama 500건 부하검사 전용 `_TimestampedInputQueue.put_chat`은 포화된 큐가 풀린 **뒤** 시각을 기록하여 수용 대기시간을 로컬 FIFO 지연에서 누락할 수 있었다. 1~3초 계측의 실제 수신기와 부하검사 간 차이이며, 실제 처리량 개선이나 지연 목표 달성으로 간주하지 않는다.

### 이번 회차 실제 누적 개발
- `scripts/aisting_real_ollama_fifo_soak.py`: 큐 수용 시도 시각을 잠금/포화 대기 전에 한 번 기록하고, 수용 성공 시에만 같은 큐 잠금 내부에서 시각과 메시지를 원자적 순서로 접수하도록 변경했다. 큐 포화로 실패한 이벤트의 고아 시각은 만들지 않는다. 기존 단일 AI FIFO, 모델 실행기 재사용, 실모델 500건 실행 경로, 설정·SQLite 격리, 원본 응답 길이 및 모델 옵션은 그대로 유지했다.
- `tests/test_aisting_real_local_fifo_soak.py`: 실제 포화 큐를 기다리는 두 번째 생산자의 수신 시각이 **대기 해제 이전**에 기록됐는지 확인하는 신규 계약검사 1건을 추가했다. `threading.Event`로 포화 대기를 확인한 후 첫 항목을 소비하며, 메시지/시각 FIFO 순서와 잔여 고아 시각 부재도 검사한다. 이 검사는 실제 모델 호출이 없는 계약검사이며 실사용 성공으로 표시하지 않는다.
- 실제 코드 커밋 `da2830a2daff4577c8f405c88deca53c0616e3a0`, 검사 커밋 `91755e9a388b0a002412177ab48e34a4abfe0b2a`. 두 커밋 모두 기존 main에서 새 브랜치·force push 없이 누적했다.
- 신규 계약검사는 작성했지만 본 회차에서 직접 실행하지 않았다. 새 전체 회귀/Windows CI 결과는 이 기록 시점에 대기 중이며 통과라고 보고하지 않는다.

### CI 실제 상태·기존 실패 보존
- 96절 Windows `39722213656`: `completed/cancelled`; 개별 Windows EXE·OBS 읽기·Twitch 읽기·Ollama 작업은 성공, 한국어 공개 채팅 읽기는 취소. 전체 성공 아님.
- 96절 실제 Ollama 500건 `39720448468`: `completed/success`이나 처리 500/500, 3초 초과 **500/500**, 전체 p95 **2979.984초**, FIFO p95 **2973.875초**, AI p95 **7.875초**. 1~3초 목표 실패.
- 159절 전체 회귀 `40082324846`: `completed/failure`, **2714건·36 실패·31 오류·2 건너뜀**. 159절 실제 Ollama 500건 `40082324845`: 500건 처리·499건 3초 초과·전체 p95 **1595.078초**.
- 160절 최종 HEAD `eb1adae620f349c5a5b6ca34c7b38f426e965860` 전체 회귀 `40086198601`: `completed/failure`, 작업 `validate`의 `Validate project` 단계 실패. 원격 실행 로그 본문은 이 회차 조회 경로에서 확보하지 못했으므로 실패 상세 원인을 추정하지 않는다.
- 같은 160절 Windows `40086198624`: `completed/cancelled`, Windows EXE 작업 취소. OBS·Twitch·Ollama·한국어 공개 채팅 개별 읽기 작업 성공은 Windows 네이티브 통합 성공이 아니다.
- 160절 실제 Ollama 500건 `40086142064`: 마지막 조회 `in_progress`; 최종 처리량·지연·실패 수치는 미확정.
- 161절 검사 HEAD `91755e9a388b0a002412177ab48e34a4abfe0b2a` 전체 회귀 `40090053681`: 최초 조회 `pending`. Windows `40090053684`: `queued`. 161절 코드 HEAD `da2830a2daff4577c8f405c88deca53c0616e3a0` 실모델 500건 `40090038323`: `queued`. 문서 후속 커밋으로 새 HEAD/CI가 생길 수 있으므로 최종 상태는 다음 조회에서 확인한다.
- 원격 CI 실패 로그 ZIP/본문을 읽으려는 시도는 GitHub 연결의 로그 접근 제한으로 실패했다. 실패 사실과 단계만 확인했으며 원인·수정 성공을 꾸며 기록하지 않는다.

### 실제 완료·안 한 것·남은 것·진행 중 멈춘 것·다음 인계
- **완료:** 실제 부하검사 코드에서 포화 대기시간의 최초 시각 보존, 고아 시각 방지, 기존 계약검사 유지 및 신규 계약검사 작성, 기존 main 2개 코드/검사 커밋 누적.
- **안 한 것:** 신규 검사 직접 실행, 전체 회귀 성공, Windows 10/11 네이티브 EXE GUI 실기기 실행, 실제 한국어 권리 확인 GPT-SoVITS WAV→공식 Cubism 입→OBS 동일 발화 실증, 실제 4플랫폼 수백 명·24시간, 방송/녹화/채팅 발신, OAuth 대행, 모델 훈련, 1~3초 달성.
- **미완료:** 실제 로컬 FIFO 적체 및 1~3초 병목 해결, 기존 전체 회귀 실패/오류 수정과 전체 재검증, Windows GUI·OBS·로컬 모델 통합검증, 4플랫폼 실제 무누락 및 24시간 재연결/안전성, 권리 있는 실제 WAV·입·OBS 동일 발화의 실측.
- **진행 중 멈춘 것:** 160/161회차 실모델 500건 재측정과 신규 계약검사 CI 결과, Windows EXE 실제 검증, 실계정·권리 있는 음성/모델이 필요한 실증.
- **다음 회차:** 최신 main HEAD와 `40090053681`, `40090053684`, `40090038323`, `40086142064` 및 새 최종 HEAD의 모든 CI를 다시 조회한다. 기존 원문 1~161절과 과거 부록을 삭제·요약 대체하지 않고, 실제 코드 누적 개발 우선 → 전체 회귀/Windows 네이티브 검사 → 오류 수정 후 전체 재검증 순서를 지킨다. 기존 매시간 예약은 유지하고 중복 생성하지 않는다. 다른 프로젝트·Drive·브랜치·예약·사용자 계정·SQLite·캐릭터·설정은 변경하지 않았다.

### 161절 후속 — 실제 반영 HEAD·신규 CI 추적 (2026-10-24)
- 161절 코드·검사·전체 인수인계 최초 누적 HEAD: `bf19ce09ca4c50d7fe12785b10bf793fb8d043af`. 160절 시작 HEAD `eb1adae620f349c5a5b6ca34c7b38f426e965860` 대비 `ahead_by=3`, `behind_by=0` 확인. 기존 문서 두 개는 앞부분 원문 전체가 정확히 보존되었고 추가 30줄씩만 생겼다. 과거 부록·원본 소스·캐릭터·SQLite·설정은 삭제하거나 바꾸지 않았다.
- 최초 문서 HEAD 전체 회귀 [40090134919](https://github.com/junggyeol4444/AISTING/actions/runs/40090134919): 최초 조회 `queued`; Windows EXE [40090134918](https://github.com/junggyeol4444/AISTING/actions/runs/40090134918): `queued`. 코드/검사 HEAD 전체 회귀 [40090053681](https://github.com/junggyeol4444/AISTING/actions/runs/40090053681): `in_progress`; Windows [40090053684](https://github.com/junggyeol4444/AISTING/actions/runs/40090053684): `cancelled`. 실제 모델 500건 [40090038323](https://github.com/junggyeol4444/AISTING/actions/runs/40090038323): `queued`. 실제 160절 모델 500건 [40086142064](https://github.com/junggyeol4444/AISTING/actions/runs/40086142064): `in_progress`.
- 본 후속 기록 자체가 별도 fast-forward 문서 커밋을 만들므로 다음 회차는 이 SHA를 최종 HEAD로 가정하지 않고 **main 실제 HEAD와 최종 HEAD의 CI를 재조회**한다. 검사 성공·실모델 1~3초 달성·Windows GUI/OBS 실증은 미확인. 기존 매시간 예약 변경/중복 생성 없음.

