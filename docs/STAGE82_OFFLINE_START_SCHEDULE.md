# v82 / 원본 081 방송 시작 일정 관리 기능 — 오프라인 초안

## 원본 요구의 구현 범위

원본 기획안의 '방송 시작 시각은 운영자가 설정, 랜덤 변주는 선택' 원칙과 원본 로드맵의 **081 방송 시작 일정 관리 기능 구현**을 따른다. 082 자동 방송 시작 제어, 083 시작~종료 자동 진행, 084 이후 공지 생성/게시/외부 연결은 구현하지 않는다. 기존 기획안·설정·캐릭터/아바타·음성·플랫폼·콘텐츠 선택을 보존한다.

## 이번 구현 (코드 구현 범위 81/100)

- 앱의 새 **방송 시작 일정 초안** 탭에서 한국 시간(KST, UTC+09:00) 월~일 요일과 `HH:MM` 시작 시간을 최대 14개까지 추가/선택 제거한다. 같은 요일/시간 중복 거부, 엄격한 날짜·시각 유효성 검사 및 정렬·불변 초안 객체 사용.
- 날짜·시각 `YYYY-MM-DD HH:MM`를 운영자가 **직접 입력했을 때에만** 이후 5건을 계산한다. 동일 시각이면 지나간 것으로 판정하고 다음 주 항목을 반환한다. OS 현재 시간·PC 위치·정보를 자동 수집하지 않음.
- **수동 버튼**으로만 지정된 AISTING 로컬 데이터 폴더에 독립 JSON `broadcast_schedule_draft.json`을 원자적으로 저장, 불러오기, 삭제한다. 사용자의 기존 `settings.json` 및 기타 데이터를 건드리지 않는다. 불러오기 실패 시 메모리 초안 유지, 손상/과다/승인 값/심볼릭 링크 거부.
- 저장 레코드는 항상 `scheduled_execution=false`, `broadcasting_authorized=false`, `obs_connected=false`, `final_approval=false`. 기존 `config/roadmap.json` 및 운영자의 앱 기본 설정도 자동 실행 비활성 상태 유지.
- 초안/계산은 **실제 예약 실행이 아니다**. 백그라운드 타이머, 자동 시작 스케줄 등록, OBS 제어, 플랫폼 로그인, 링크 생성, 방송 켜기, 음성 출력, 공지/외부 서버 접속 전부 없음.

## 주의 사항 및 실기기 확인 대기

- 한국 시간은 현대 KST 고정 UTC+09:00으로 계산한다. 이 단순화는 과거 DST 기록을 재현하지 않으며, 설정을 바꾼 Windows 실제 시계/절전/재기동/장기 예약의 동작을 검증하는 것이 아니다.
- 현재는 단순한 **매주 반복 시작시각**만 모델링하며, 휴무일·일회성 일정·시간 변주·방송 겹침 정책·정확한 무인 방송 트리거/실패 복구는 미구현. 실제 방송 시각 정책 확정, OBS·플랫폼 연결, 음성/아바타 장치 및 방송을 관통하는 실기기 검증/승인 필요.
- 사용자가 자동 개발 예약을 끈 상태는 별도이며, 앱 내부 `scheduled_execution`도 **항상 비활성** 상태이다.

## 실행 증거

- `tests/test_offline_broadcast_schedule.py`: 새 단위 테스트 21개.
- `scripts/gui_offline_broadcast_schedule_smoke.py`: 격리된 임시 폴더에서 실제 Tkinter 화면의 추가/거부/예정 계산/로컬 저장·불러오기·삭제/자동실행 비활성을 테스트. Linux 가상 화면에서만 검증.
- `logs/STAGE82_UNITTEST.log`, `logs/STAGE82_GUI_ALL.log`, `logs/STAGE82_SYNTAX.log`, `logs/STAGE82_REEXTRACTED_UNITTEST.log`, `logs/STAGE82_REEXTRACTED_GUI.log`, `logs/STAGE82_PRESERVATION.log`, `logs/STAGE82_FINAL_VALIDATION.txt` 확인.
- 010 사용자 최종 승인과 실제 Windows/OBS 방송 검증은 계속 `pending`. 개발 범위 도달은 81/100이지만 제품의 실제 완성 비율이 아님.
