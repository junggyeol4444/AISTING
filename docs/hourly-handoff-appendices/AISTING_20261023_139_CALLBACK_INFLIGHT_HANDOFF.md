# AISTING 139회차 전체 누적 인수인계 — 실제 콜백 진행 중 병목 관측


## 139. 2026-10-23 22:27 KST — 4플랫폼 진행 중 전달 콜백 병목 관측 누적 개발

### 원문·기준 및 사용자 제한 보존
- 시작 GitHub main HEAD: `c6c708b37b179c607f9a28a8da4201ce683363f7`. 개발 소스 반영 커밋: `3c8230fc07ae2f1eec270f48d08487db17b76f53` (기존 main에서 강제 없이 fast-forward 성공). 본 139절을 기존 1~138절 **뒤에만 추가**하며 1~97절 원문, 다음 대화 인수인계 전체, 기존 64개 과거 부록, 원본 기획·로드맵·설정·캐릭터·SQLite·실제 소스는 삭제/교체하지 않는다.
- AISTING만 개발한다. 새로운 브랜치·force push·롤백·다른 예약 변경·다른 프로젝트·Drive 접근, 계정/OAuth 동의 대행·채팅 발신·방송·녹화·권리 없는 음성 사용·모델 훈련·사용자 요청 없는 96토큰/keep_alive 10m 변경은 하지 않았다.

### 실제 수행한 개발 (139회차)
- `src/ai_broadcaster/multi_platform_session.py`: 기존 4플랫폼 수신 콜백의 **실제 GUI/AI FIFO 전달 진행 중 시작 시각**을 플랫폼별로 별도 관측하도록 구현. 완료 표본 p95만으로는 콜백이 멈춘 동안 병목이 보이지 않는 문제를 해결하기 위한 계측이다. 성공·거절·예외 모든 경로에서 진행 상태를 `finally`로 정리한다. 기존 플랫폼별 직렬화, 중복 사건 ID 처리, 전달 성공/실패 분리, 채팅 본문·닉네임·토큰 비저장 원칙을 유지한다.
- 같은 모듈 `reconnect_snapshot()`의 운영 경과 기준을 운영자 Stop 시각으로 제한해 Stop 이후 마지막 채팅/통신/읽기 실패 경과가 계속 증가하는 오인을 방지한다. 실제 24시간 방송 완료 또는 무누락을 주장하지 않는다.
- `src/ai_broadcaster/desktop_chat_tab.py`: 기존 한국어 Windows GUI 플랫폼별 진단에 '현재 전달 콜백 n초 진행 중' 또는 '현재 전달 콜백 없음'을 표시. 최근 완료 p95와 진행 중 시간을 혼동하지 않는다.
- `tests/test_aisting_callback_inflight_139.py`: 진행 중 계측, 예외 후 상태 정리, 플랫폼 간 비차단, Stop 이후 시간 동결의 로컬 계약검사 **4건 작성**. 테스트는 이번 회차에서 실행하지 않았다. 가상 수신기 테스트는 실제 플랫폼 수백 명/Windows EXE/OBS 실증이 아니다.
- 소스 2개 수정·테스트 1개 신설, 코드 커밋을 실제 main에 반영했다. 외부 모델·사용자 계정·기존 데이터는 변경하지 않았다.

### 확인한 CI와 실제 실패·미측정 (성공으로 둔갑 금지)
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): `completed/cancelled`; 4개 작업 성공, `korean-public-chat-readonly` 작업 취소. 취소된 작업의 로그 다운로드는 GitHub 404 `BlobNotFound`로 실패. **전체 Windows 통합 성공 아님**.
- 96절 실제 Ollama 500건 [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): `completed/success`, 합성 채팅 500/500 처리, 로컬 전체 p95 **2979.984초**, FIFO 대기 p95 **2973.875초**, AI p95 **7.875초**, 3초 초과 **500/500**. 실제 500명 시청자/24시간 방송 아님.
- 137회차 실제 Ollama 500건 [39947073270](https://github.com/junggyeol4444/AISTING/actions/runs/39947073270): `completed/success`, 합성 채팅 500건, 로컬 p95 **1522.406초**, 대기 p95 **1519.234초**, AI p95 **3.438초**, 3초 초과 **499/500**. 목표 실패.
- 138회차 전체 회귀 [39954515772](https://github.com/junggyeol4444/AISTING/actions/runs/39954515772) 및 Windows [39954515625](https://github.com/junggyeol4444/AISTING/actions/runs/39954515625)는 마지막 조회 `completed/cancelled`. 138회차 실모델 [39954516147](https://github.com/junggyeol4444/AISTING/actions/runs/39954516147)은 마지막 조회 `queued`. 기존 137회차 회귀 **30 failures / 35 errors / 2 skipped** 기록을 해결 완료로 처리하지 않는다.
- **139회차 새 코드 테스트 실행·최신 CI 최종 성공 미확인**. 완료 p95가 낮더라도 아직 진행 중인 콜백과 시청자 E2E는 별도다.

### 남은 작업·중단 지점·다음 실행
- 개발 중 남음: 권리 확인된 실제 한국어 GPT-SoVITS WAV → 공식 Live2D Cubism 입 움직임 → OBS 동일 발화의 실제 오디오/영상 연동, 4플랫폼 실제 수백 건·실제 수백 명 무누락 검증, 실제 24시간 재연결·안전성, 실제 AI/음성/영상/시청자 1~3초 병목 해소. 지금 추가한 콜백 관측은 이 목표 달성이나 음성·영상 실증이 아니다.
- 순서 유지: **기존 코드 전체 누적 개발 → 전체 회귀 및 Windows 네이티브 EXE/GUI·OBS·로컬 모델 통합검사 → 오류 수정 → 전체 재검증**. 작성만 한 139회차 테스트 4건은 미실행으로 인계한다.
- 다음 실행은 반드시 **그때의 main HEAD**와 해당 커밋의 최신 CI를 새로 확인한다. 이 139절 및 과거 모든 인수인계 원문을 보존하여 140절 이후 추가한다. 새로운 예약 생성·기존 예약 비활성화·다른 프로젝트 변경 금지.
