# AISTING v86 — 원본 085 디스코드 공지 연결 (오프라인 메시지 형식 검사)

## 원본 요구사항 및 변경 범위

`docs/ORIGINAL_PLAN.txt` 5부 5-1 디스코드 공지 (공식 봇/채널 연결 및 게시)를 참고한다. 원본 `docs/ROADMAP_100.md` 085는 **디스코드 공지 연결**이다. 외부 서버 및 계정 연결 금지 때문에 **실제 디스코드 봇/API 연결, 채널 조회, 토큰 입력/저장, 게시와 자동 예약은 구현하거나 검증할 수 없다.** 현재 작업은 그 후속 승인 필요 작업을 대체하지 않는다.

## 구현된 기능 (모두 로컬)

- 084의 검토용 방송 공지 초안을 재사용해 `DiscordNoticeDryRun`을 구성한다. 완성된 원본 초안이 없는 경우 거절한다.
- `message.content`, `message.tts=false`, `message.allowed_mentions={parse:[], users:[], roles:[], replied_user:false}`를 포함한 **전송 불가능한 오프라인 JSON 검토 형태**를 만든다.
- `destination:null`, `connection:disabled`, `send_ready:false`, `published:false`, `mode:offline_review_only` 값을 고정한다. 이는 실제 봇 API 요청이 아니다. 채널·웹훅 URL·사용자 계정 토큰·인증 절차는 받지 않는다.
- 본문 1~2000자 범위, 제어 문자, 대량/지정 멘션, URL, 출처 시각 KST 확인 및 원본 초안의 미게시/미예약 상태 검사.
- `디스코드 공지 연결 모의` 탭에 수동 검사 버튼과 읽기 전용 JSON 검토창 추가. 이전 초안 편집, 일정·주제 변경, 설정 저장, 입력 변조 이후에는 검토 결과를 무효화하거나 거부한다.
- 치지직·유튜브·트위치 방송 플랫폼 선택으로 **디스코드 대상 채널을 추정하지 않는다**. 사용자 PC 접근/정보 수집, 외부 HTTP, OBS, 실제 방송/공지 업로드, 코드 다운로드/설치는 없다.

## 검증과 한계

- `tests/test_offline_discord_notice_link.py` 신규 21개 단위 테스트와 `scripts/gui_offline_discord_notice_link_smoke.py` 신규 Tkinter GUI 시험.
- `logs/STAGE86_UNITTEST.log`, `logs/STAGE86_GUI_REGRESSION.log`, `logs/STAGE86_SYNTAX.log`, `logs/STAGE86_FINAL_VALIDATION.txt`에서 정확한 결과를 확인할 수 있다.
- `DiscordNoticeDryRun` 결과 자체는 메모리에 머물고, 전송 호출 메서드는 존재하지 않는다. JSON을 실제 디스코드 서버에 보낼 수 있다는 뜻이 아니다.
- 실제 Windows GUI/EXE 실행, Discord 사용자 계정/봇 권한·채널 연결·API 호환성·실제 게시/중복/삭제/재시도, 방송 시작 공지 자동 게시(086), 사용자 최종 승인 등은 **전부 미구현·미검증**이다.
- **코드 개발 도달 범위만 85/100**. 원본 085와 원본 010의 승인 상태는 `pending`으로 유지했다.
