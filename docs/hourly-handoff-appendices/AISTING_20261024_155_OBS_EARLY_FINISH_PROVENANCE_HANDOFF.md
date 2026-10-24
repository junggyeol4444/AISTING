# AISTING 155회차 원문 누적 인수인계

## 155. 2026-10-24 — OBS 조기 종료를 실제 동일 발화 선택 오디오 표본에 연동한 누적 개발

### 시작 상태·원문 보존
- 시작 main HEAD: `13657a091983b36a6ae570dd289ab034e6f5aea0`. 기존 1~154절 원문, 두 누적 인수인계, 97절 부록, 원본 기획·100단계 로드맵·설정 및 기존 소스를 보존한다.
- 이전 OBS 관찰 완료 판단은 `_observed_mouth_obs_overlap`의 미터 양성 구간과 입 시간 교집합만으로 OBS 관찰을 조기 종료할 수 있었다. 같은 발화의 실제 선택 오디오 표본 시각·경로가 확인되지 않아도 종료할 수 있어, 후속 실측 표본 확보 기회를 놓칠 수 있었다.
- 이번에는 `original_plan_full_pipeline.py` 기존 흐름에 `_confirmed_mouth_obs_audio_provenance`를 추가하고, 실제 질문 종료 뒤 OBS 관찰 조기 종료 조건을 실측 표본 2개 이상·현재 질문 시각 범위·채택 OBS 경로·오디오 관찰창 연속성 확인으로 강화했다. 불확정이면 운영자가 이미 지정한 관찰 시간 범위 안에서만 계속 관찰한다. 새로운 지연 설정·질문 재전송·OBS 송출/녹화/채팅 발신은 추가하지 않았다.
- 기존 `_observed_mouth_obs_overlap` 함수와 최종 결과 반환 계약은 변경하지 않았다. 신규 `tests/test_aisting_obs_early_finish_provenance_155.py`에 가상 계약검사 7건 작성. 이 검사는 실제 OBS·공식 Cubism 실증이 아니다.

### 이번 회차 CI 실측·실패 보존
- 96절 Windows CI [39722213656](https://github.com/junggyeol4444/AISTING/actions/runs/39722213656): `completed/cancelled`. OBS 읽기·Twitch 읽기·Windows EXE·Ollama 작업은 개별 성공, 한국 공개 채팅 읽기 작업은 취소. 취소 작업 로그는 BlobNotFound(404)로 확인 불가. 전체 성공으로 보고하지 않는다.
- 96절 실제 Ollama 500건 [39720448468](https://github.com/junggyeol4444/AISTING/actions/runs/39720448468): `completed/success`, 실제 500/500건 처리·실패 0·3초 초과 500건, 전체 p95 2979.984초, FIFO 대기 p95 2973.875초, AI 처리 p95 7.875초. 1~3초 목표 미달.
- 154절 최종 HEAD 전체 회귀 [40063220932](https://github.com/junggyeol4444/AISTING/actions/runs/40063220932): `completed/failure`, 2669건 중 36실패·31오류·2건 건너뜀. Twitch AI 연동 계약검사 실패도 로그에서 확인됨. 기존 실패를 숨기지 않는다.
- 154절 Windows EXE [40063220924](https://github.com/junggyeol4444/AISTING/actions/runs/40063220924): `completed/cancelled`, Windows 실사용 전체 성공 미확인.
- 154절 실제 Ollama 500건 [40063169931](https://github.com/junggyeol4444/AISTING/actions/runs/40063169931): `completed/success`, 500/500건·실패 0·3초 초과 500건, 전체 p95 2768.687초, FIFO 대기 p95 2762.906초, AI 처리 p95 6.078초. 실제 모델이나 FIFO 목표 성공으로 오인 금지.

### 완료·하지 않은 것·남은 것·진행 중 멈춘 것·다음 인계
- **실제 개발:** 기존 공식 Live2D→OBS 동시 관찰 소스에 조기 종료 출처 검증 기능 누적 추가, 신규 가상 계약검사 7건 작성. 기존 main의 원본 파일을 보존하며 추가 수정.
- **하지 않은 것:** 신규 검사 직접 실행·통과 확인, 전체 회귀 통과, Windows 10/11 네이티브 EXE/GUI 버튼 실사용, 권리 확인된 한국어 GPT-SoVITS WAV→공식 Cubism 입→OBS 동일 발화 실증, 실제 4플랫폼 수백 명 무누락, 24시간 방송·재연결 실증, 시청자 E2E 1~3초 달성. mock를 실사용으로 보고하지 않는다.
- **미완료:** 기존 회귀 36실패·31오류, Windows EXE 통합·OBS 실기기 검증, 실제 권리 보유 음성·공식 Cubism 입·OBS 동일 발화, 실제 4플랫폼 수백 명·24시간·재연결 안전성, FIFO/AI/음성/영상/시청자 지연 병목 개선 및 전체 재검증.
- **진행 중 멈춘 것:** 155절 신규 CI 최종 결과 및 실제 Windows 환경·권리 모델·계정이 필요한 실증. 자동 CI가 시작되더라도 통과 전에는 미검증.
- **다음 시작 기준:** GitHub `junggyeol4444/AISTING/main`의 **실제 최신 HEAD를 재조회**하고 155절 신규 CI 결과·실패 로그를 확인한다. 코드 커밋 및 최종 인수인계 커밋은 현재 main에서 조회한다. 원문 1~155절과 모든 부록·캐릭터·SQLite·설정·기획을 그대로 보존하며 개발 우선→전체 회귀/Windows 실검사→오류 수정·전체 재검증. 새 브랜치/force push/롤백/다른 프로젝트·Drive·예약 변경, 무단 계정/OAuth·송출·녹화·채팅 발신·모델 훈련·권리 없는 보이스·토큰 96·keep_alive 10m 변경 금지.

### 155절 실제 반영 HEAD 및 신규 CI 추적 추가 (원문 뒤 누적)
- 첫 155절 코드·테스트·원문 인수인계 실제 반영 HEAD: `6e6ae5186d49b4db308872f260e851d3c09f2656` (시작 `13657a091983b36a6ae570dd289ab034e6f5aea0` 대비 `ahead_by=1, behind_by=0`; 기존 원본 보존).
- 해당 HEAD [전체 회귀 40067021099](https://github.com/junggyeol4444/AISTING/actions/runs/40067021099): 최초 조회 `queued`. 7건 신규 계약검사 실행/통과 및 전체 회귀 성공 여부 **미확정**.
- 해당 HEAD [Windows EXE 40067021073](https://github.com/junggyeol4444/AISTING/actions/runs/40067021073): 최초 조회 `queued`. Windows EXE·GUI·실 OBS 성공 **미확정**.
- 해당 HEAD [실제 Ollama 500건 40067021030](https://github.com/junggyeol4444/AISTING/actions/runs/40067021030): 최초 조회 `queued`. 1~3초 성능 달성 **미확정**.
- 다음 실행은 인수인계 보강 커밋 이후의 **실제 main HEAD**를 반드시 다시 조회하고 위 CI 세 개의 최종 상태/실패 로그부터 확인한다. 인수인계 커밋 SHA를 문서 내용에 자기 참조로 고정할 수 없으므로 현재 브랜치 HEAD 조회를 기준으로 한다.
