# AISTING 157회차 원문 누적 인수인계

## 157. 2026-10-24 — 공식 WAV 수신 시각의 질문 범위 검증으로 OBS·Cubism 상관 증거 오염 방지

### 시작 HEAD 및 원문·기획 보존
- 시작 `main` HEAD: `a99012456349c42f736088d77213d360f03d8b07`. 원래 1~97절 및 누적 98~156절, 두 전체 인수인계 문서, 기존 부록, `docs/ORIGINAL_PLAN.txt`, `docs/ROADMAP_100.md`, `config/roadmap.json`과 기존 소스·설정·캐릭터·SQLite를 삭제하거나 대체하지 않았다.
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): 전체 취소. 실제 OBS 읽기·Twitch 읽기·Windows EXE·Ollama 개별 성공, 한국 공개 채팅 작업 취소. 취소된 작업을 전체 성공으로 보고하지 않는다.
- 96절 실모델 500건 CI [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): 실제 Ollama 500/500 처리·실패 0, 3초 초과 500건, 전체 p95 2,979.984초, FIFO 대기 p95 2,973.875초, AI 처리 p95 7.875초. 실제 시청자 500명 아님.

### 이번 회차 실제 누적 코드 개발
- 기존 `src/ai_broadcaster/original_plan_full_pipeline.py`에서 공식 WebSocket WAV 수신 시각을 질문 시작~종료 범위와 대조하는 `_validated_current_prompt_wav_received_at`을 추가했다. 이전 발화·미래 시각·속성 누락·NaN·무한대·불리언 등은 유효한 현재 질문의 WAV 시각으로 채택하지 않는다.
- 기존 공식 WAV→OBS 입력 미터 음량 상관과 공식 WAV→Cubism RMS 비교 양쪽에 검증된 수신 시각만 전달한다. 질문 밖 WAV가 남아 있을 때 OBS 미터 및 Cubism RMS에 잘못 연결되는 후보 점수·지연 증거 생성을 막는다. 기존 정상 현재 질문의 WAV 시각, 함수 반환 계약 및 읽기 전용 경로는 유지한다.
- 기존 코드 수정 커밋: `59fa0d7383b9202013a0753835c4673246f26a14`.
- 신규 `tests/test_aisting_current_prompt_wav_origin_157.py` 가상 계약검사 10건 작성: 정상·시작/종료 경계·과거/미래 발화·속성 누락·숫자 아닌 값·질문 시각 형식 오류·역행·시작 0 차단. 검사 작성 커밋: `646258296bbbd321cdc3b228b6bda998492cc1e0`. **신규 검사는 작성했지만 직접 실행하지 않았다.**
- OBS 송출·녹화·채팅 발신·모델 훈련·권리 없는 음성·OAuth 동의 대행 없음. 토큰 길이 96/keep_alive 10m 또는 사용자 설정을 임의 변경하지 않았다. 원본 파일 삭제, 새 브랜치, force push, 롤백 없음.

### 검증·실패의 정확한 상태
- 이전 155회차 전체 회귀 [40067057711](https://github.com/junggyeol4444/AISTING/actions/runs/40067057711): 2,676건, **36 실패·31 오류·2 건너뜀**. 실제 로그에 공식 OBS 경로 및 Twitch FIFO·중지·응답 순서의 실패가 남아 있다. 신규 가상 검사 작성으로 이를 성공 처리하지 않는다.
- 이전 155회차 Windows CI [40067057726](https://github.com/junggyeol4444/AISTING/actions/runs/40067057726): Windows EXE 작업 취소. 개별 성공 작업만으로 전체 Windows 실사용 성공을 주장하지 않는다.
- 이전 155회차 실모델 500건 [40067021030](https://github.com/junggyeol4444/AISTING/actions/runs/40067021030): 500/500 처리, 3초 초과 500건, 전체 p95 2,504.484초, FIFO p95 2,499.234초, AI p95 5.671초. **1~3초 목표 미달**.
- 156회차 이후와 이번 157회차 새 전체 회귀·Windows·실모델 CI의 정확한 실행 번호/최종 결과는 이번 기록 시점에 확보하지 못했다. commit 연관 워크플로 조회는 빈 배열, 상태 조회도 빈 배열이었다. **미확인을 성공·실패·미실행으로 단정하지 않는다.**
- 이번 회차 실제 Windows 10/11 EXE 실행→GUI 버튼→실제 OBS·권리 있는 한국어 GPT-SoVITS·공식 Cubism 실증은 수행하지 않았다. 모의 검사와 실제 방송/시청자 검증은 다르다.

### 완료·안 한 것·미완료·진행 중 멈춘 것·다음 인계
- **실제 완료:** 기존 코드에 현재 질문 WAV 수신 시각 출처 검사 누적, 두 WAV 상관 경로에 적용, 신규 가상 계약검사 10건 작성, 157절 원문 누적.
- **안 한 것:** 신규 검사 직접 실행, 전체 회귀 통과, Windows 실사용·OBS·공식 Cubism·합법 한국어 GPT-SoVITS 동일 발화 실증, 실제 4플랫폼 수백 명, 실제 24시간 방송/재연결, 시청자 1~3초 달성.
- **미완료:** 기존 36 실패·31 오류 및 Windows EXE 취소 재검증, 실제 음성·입·OBS 동일 발화, 4플랫폼 무누락, 24시간 안전성, FIFO 장기 대기 병목, Windows 네이티브 통합검증과 오류 수정 후 전체 재검증.
- **진행 중 멈춘 것:** 157회차 신규 CI 확인과 Windows/실모델/실계정 환경이 필요한 검증. 확인되지 않은 실행 번호는 만들지 않는다.
- **다음 회차:** 현재 `main` HEAD 재조회 → 기존 96절 및 최근 CI 실제 상태/실패 로그 확인 → 기존 전체 코드 개발 우선 → 전체 회귀/Windows EXE·GUI·OBS·로컬 모델 검증 → 실패 수정 및 전체 재검증. 사용자 지시·원본·과거 부록 보존, main fast-forward만 사용. 다른 프로젝트·Drive·예약·브랜치 변경 금지.


### 157절 후속 CI 실행 번호 및 실제 실패 확인 (2026-10-24)
- 156회차 최종 HEAD `a99012456349c42f736088d77213d360f03d8b07` 전체 회귀 [40071095235](https://github.com/junggyeol4444/AISTING/actions/runs/40071095235): **2,682건·36 실패·31 오류·2 건너뜀**으로 완료/실패. 이전 문제 미해결. 같은 HEAD Windows [40071095267](https://github.com/junggyeol4444/AISTING/actions/runs/40071095267): OBS 읽기·Twitch 읽기·Ollama·한국 공개 채팅 읽기 개별 성공, **windows-exe 취소**.
- 157회차 신규 코드·계약검사 HEAD `646258296bbbd321cdc3b228b6bda998492cc1e0`의 전체 회귀 [40074810911](https://github.com/junggyeol4444/AISTING/actions/runs/40074810911): 확인 시 진행 중. Windows [40074810928](https://github.com/junggyeol4444/AISTING/actions/runs/40074810928): 취소. 실제 Ollama 500건 [40074799643](https://github.com/junggyeol4444/AISTING/actions/runs/40074799643): 확인 시 진행 중. 신규 10건 테스트의 실제 통과 여부는 확인되지 않았다.
- 157절 인수인계 두 문서까지 기록한 직전 HEAD `245c8cf17245209c910697920ce7b8da00fd29db`의 전체 회귀 [40074872723](https://github.com/junggyeol4444/AISTING/actions/runs/40074872723), Windows [40074872731](https://github.com/junggyeol4444/AISTING/actions/runs/40074872731): 확인 시 대기. 이 추가 기록을 반영하는 문서 커밋은 다시 HEAD와 CI를 변경하므로 **다음 회차는 실제 main HEAD와 해당 HEAD의 Actions 실행 번호·최종 결과를 반드시 다시 확인**한다.
