## 160. 2026-10-24 — 실제 Ollama 500건 FIFO 부하검사의 GUI 실행기 재사용 경로 일치 개발

### 기준·원본 보존
- 회차 시작 실제 `main` HEAD: `ea1ae040075f40c95b3f48643896bf3802865c1c`. 원본 1~159절 및 과거 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`, 기존 실제 소스 기준으로 누적했다.
- 기존 실사용 GUI의 `LocalChatRunner`는 세션마다 모델·설정·SQLite 기억·생성기를 한 번 생성해 채팅별 응답에 재사용하지만, 500건 부하검사 스크립트는 `run_local_chat`을 매 메시지 호출하여 매번 재생성했다. 따라서 기존 500건 계측은 실사용 GUI와 실행기 생성 비용이 달랐다.

### 이번 회차 실제 코드 개발
- `scripts/aisting_real_ollama_fifo_soak.py`: `_make_isolated_production_reply`를 개발해 임시 폴더의 설정·SQLite만 사용하는 **단일 `LocalChatRunner`**를 시험 세션 시작 시 1회 생성하고 500개 입력의 기존 단일 AI FIFO에서 재사용한다. 채팅마다 실제 로컬 Ollama 추론을 수행하며 출력 생략·병렬 추론·토큰 길이 96·keep_alive 10m 변경은 없다. 원본 사용자 기억·캐릭터·설정은 열거나 수정하지 않는다.
- `tests/test_aisting_real_local_fifo_soak.py`: 기존 모의 계약검사 12곳의 패치 대상만 새 실행기 구조에 맞춰 보존·수정하고, 실행기 1회 생성·2회 재사용·격리 SQLite 경로·모델 변경 거절을 검사하는 신규 계약검사 1건을 추가했다. 모의 검사를 실제 Ollama·시청자 실증으로 표시하지 않는다.
- 이번 회차에서 **코드와 검사는 작성했으나 직접 실행하지 않았다**. 최종 CI 결과도 아직 확인 전이다. 실제 1~3초 달성이나 수백 명/24시간 방송 성공을 주장하지 않는다.

### 기존 CI 최종 상태·실패 원문 유지
- 96절 Windows `39722213656`: 전체 `completed/cancelled`; Windows EXE·OBS 읽기·Twitch 읽기·Ollama 개별 작업은 성공, 한국어 공개 채팅 읽기 작업은 취소. 전체 성공이 아니다.
- 96절 실제 Ollama 500건 `39720448468`: 작업 `completed/success`, 처리 500/500·실패 0이지만 **3초 초과 500건**, 전체 p95 **2979.984초**, FIFO p95 **2973.875초**, AI p95 **7.875초**. 로컬 지연 목표 실패.
- 159절 전체 회귀 `40082324846`: `completed/failure`, **2714건 실행·36건 실패·31건 오류·2건 건너뜀**. 기존 Twitch AI/FIFO 및 OBS 관련 실패를 숨기지 않는다.
- 159절 Windows `40082324848`: `completed/cancelled`; Windows EXE 작업 취소, 기타 일부 개별 읽기 작업 성공. 전체 통합 성공 아님.
- 159절 실제 Ollama 500건 `40082324845`: `completed/success`, 처리 500/500·모델 실패 0, **499건 3초 초과**, 전체 p95 **1595.078초**, FIFO p95 **1591.890초**, AI p95 **4.187초**. 실제 시청자 500명이나 1~3초 성공이 아니다.
- 이번 160절 반영 후 새 HEAD/CI 실행번호 및 결과는 **다음 조회 전 미확정**이며, 완료·성공으로 표시하지 않는다.

### 완료·안 한 것·남은 것·진행 중 멈춘 것·다음 인계
- **실제 완료:** 기존 실사용 `LocalChatRunner` 재사용 경로에 맞춘 500건 실제 모델 부하검사 코드 변경, 기존 가상 계약검사 12곳의 구조 대응, 신규 가상 계약검사 1건 작성, 과거 원문 보존형 160절 추가.
- **안 한 것:** 신규 테스트 직접 실행, 전체 회귀 통과, Windows 10/11 네이티브 EXE·GUI·OBS·권리 확인 한국어 GPT-SoVITS WAV→공식 Cubism 입→동일 발화 OBS 실증, 실계정 방송/녹화/채팅 발신, 실제 4플랫폼 수백 명, 실제 24시간, 시청자 1~3초 달성.
- **미완료:** 기존 36 실패·31 오류 수정·전체 재검증, 실제 Windows EXE/GUI·OBS·로컬 모델 통합검사, 권리 있는 WAV/입/OBS 동일 발화, 4플랫폼 무누락, 24시간 재연결·안전성, 로컬 FIFO 대기 및 시청자 E2E 병목.
- **진행 중 멈춘 것:** 새 실행기 재사용 경로의 CI 검증, 실제 Ollama 500건의 재측정과 기존 결과 비교, 운영자 권리/실제 환경이 필요한 통합 실증.
- **다음 회차:** 반드시 현재 `main` HEAD와 160절의 `hourly-development.yml`, `build-windows.yml`, `real-500-fifo-windows.yml` CI 최종 상태/실패 로그를 재조회한다. 1~160절 원문과 모든 과거 부록 및 기획·로드맵·실제 소스 기준으로 개발 우선 → 전체 회귀/Windows 네이티브 검사 → 오류 수정 후 전체 재검증 순서를 유지한다. 기존 매시간 예약 유지·중복 생성 금지. 다른 프로젝트/Drive/브랜치/예약 변경 없음.

### 160절 후속 — 실제 코드 반영 HEAD·신규 CI 추적 (2026-10-24)
- 코드·계약검사·전체 인수인계 반영 커밋: `e2c30e6c7df87378c51ef068b065393b97e432fd`. 시작 HEAD `ea1ae040075f40c95b3f48643896bf3802865c1c` 대비 **ahead 1, behind 0**으로 fast-forward 확인. 코드·기존 테스트·인수인계 원문 외 사용자 설정/SQLite/캐릭터를 변경하지 않았다.
- 전체 회귀 [40086142026](https://github.com/junggyeol4444/AISTING/actions/runs/40086142026): 최초 확인 시 `queued`. 신규 계약검사 통과·전체 회귀 성공 미확인.
- Windows EXE [40086142033](https://github.com/junggyeol4444/AISTING/actions/runs/40086142033): 최초 확인 시 `queued`. Windows 10/11 GUI·OBS·권리 있는 실제 한국어 GPT-SoVITS·공식 Cubism 통합 성공 미확인.
- 실제 로컬 Ollama 500건 [40086142064](https://github.com/junggyeol4444/AISTING/actions/runs/40086142064): 최초 확인 시 `queued`. 기존 159절 499건 3초 초과를 해소했다고 주장하지 않는다.
- 후속 문서 커밋이 새 `main` HEAD와 CI를 다시 만들 수 있다. 다음 회차는 이전 SHA를 최신으로 가정하지 말고 **실제 main HEAD와 해당 HEAD의 모든 CI 및 실패 로그**부터 재조회한다. 기존 매시간 예약 유지·중복 생성 금지.
