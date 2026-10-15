# AISTING v87 — 원본 086 방송 시작 공지 자동 게시 (오프라인 상태 계약만)

## 원본 계획과 승인 경계

- 근거: `docs/ORIGINAL_PLAN.txt` 5부 디스코드 공지, `docs/ROADMAP_100.md` 086, 이전 081~085 로컬 구현.
- 본래 목표는 실제 방송 시작에 맞춰 디스코드/카페 등에 자동 공지를 게시하는 것이다. **실제 게시/접속/계정/토큰/웹훅/HTTP/OBS/일정 백그라운드 실행은 금지 상태라 구현도 검증도 하지 않았다.** 본 오프라인 모의 표시가 본래 목표를 완료했다는 뜻이 아니다.

## 코드 변경 범위

- `src/ai_broadcaster/offline_notice_posting_rehearsal.py`: 기존 082 `OfflineStartController` 수동 가상 시작 및 085 `prepare_discord_notice_dry_run`을 재사용하는 별도 메모리 상태 감사. 신규 전송 클래스나 API 없음.
- 082 시작 제어기에 읽기 전용 `active_occurrence` 속성만 추가. 현재 가상 방송 시작 시각이 **원본 공지에 적힌 KST 시각**과 정확히 같고, 자동 실행/실제 송출/외부 게시 설정이 명시적으로 `False`일 때만 검토용 문구를 로컬 화면에 표시하도록 허용.
- **수동 버튼**을 눌러 로컬 화면에 실제 표시가 성공한 경우에만 같은 발생 시각의 재표시를 막는다. 표시 실패는 기록을 소비하지 않는다. 시작 전/다른 날짜/종료 후에는 거절한다.
- 원본 084 초안 내용·GUI 표시 텍스트·현재 설정 변경 시 이전 표시 결과 무효. 일정 수정/가상 방송 종료 시도 무효. 중복 방지 집합은 **메모리 내에서만** 유지하고 종료 뒤 사라진다. 이것이 실제 중복 게시 방지나 크래시 후 복구를 증명하지 않는다.
- `desktop.py`에 `방송 시작 공지 게시 모의` 탭, 수동 조건 확인과 가상 화면 표시 버튼, 상태 텍스트를 추가. 초안/방송 설정/기존 파일은 자동 저장하지 않는다.
- 실제 전송 코드는 존재하지 않고 결과의 `published=false`, `scheduled=false`, `transport_used=false` 고정. 자동 타이머 감시 없음.

## 실제 시험과 한계

- 신규 단위 테스트 `tests/test_offline_notice_posting_rehearsal.py` **21개**: 잘못된 시작/종료/중복/실패/동일 시각/설정 차단, 멘션·미승인 초안 거부, 무접속/무프로세스/무파일 변경, 상태 불변성 포함.
- GUI `scripts/gui_offline_notice_posting_rehearsal_smoke.py`: 임시 설정 경로와 Linux Xvfb에서 실제 Tkinter 창 사용. 기존 일정 추가 → 가상 시작 → 공지 초안 생성 → 가상 화면 표시 → 중복 차단 → 변경 무효화 → 종료 후 차단 검증.
- 전체 테스트 로그 `logs/STAGE87_UNITTEST.log`, `logs/STAGE87_GUI_REGRESSION.log`, `logs/STAGE87_SYNTAX.log`, 압축 해제 검증 기록 `logs/STAGE87_REEXTRACTED_UNITTEST.log`, `logs/STAGE87_REEXTRACTED_GUI.log` 참조.
- GUI는 Linux 가상 화면 검사일 뿐 Windows 10/11/EXE·실제 디스코드 로그인/권한·게시·재시도·실제 자동 공지/알림·실제 시청 가능 여부·OBS 시작 및 자동화 품질은 **미검증**.
- 사용자 승인이 필요한 원본 086 및 010 단계는 `config/roadmap.json`에서 `pending` 유지, 기획안 수정 없음. **코드 개발 도달 범위 86/100**, 제품 완성률 아님.
