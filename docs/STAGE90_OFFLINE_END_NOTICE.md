# v90 · 원본 089 방송 종료 공지 및 결과 기록 (오프라인 부분 구현)

## 요구사항과 기존 구조
- 원본: `docs/ORIGINAL_PLAN.txt` 5부 시작/종료 공지, 5-5 게시 완료 로그, `docs/ROADMAP_100.md` 089.
- 078 가상 경과 시간 판정, 079 마무리 예고 → 인사 → 가상 종료 순서를 **재사용**하며, 실제 방송 종료 상태를 새로 추론하지 않는다.
- 원본에서 의도한 자연스러운 실제 AI 종료 공지, 디스코드/카페 자동 게시 및 게시 성공 로그는 아직 **구현·검증되지 않았다**.

## 구현한 부분
- `src/ai_broadcaster/offline_end_notice.py`: 079의 두 멘트 확인 및 가상 종료 상태, 078의 최대 시간 판정, 사용자가 직접 입력한 KST 예정 시작 시각, 기존 플랫폼·콘텐츠·캐릭터 설정을 확인해 **가상 종료 공지 초안과 구조화된 결과 JSON** 생성.
- 결과 JSON은 `record_type=virtual_ending_only`, `actual_broadcast_verified=false`, `published=false`, `actual_end_time=null`, `viewer_count=null`, `actual_stream_status=not_checked` 등 명시적 미검증 표시. 실제 방송 데이터·개인정보를 자동 수집하지 않는다.
- `desktop.py`: 새 `방송 종료 공지·결과 기록` 탭. 최소·최대 시간 모의 판정과 079 가상 종료 후에만 수동 생성 버튼 사용. 메모리 전용 결과를 보여주고, **운영자가 수동 선택한 경로로만 JSON 저장**. 기존 파일이 있으면 덮어쓰지 않고 실패로 표시.
- 잘못된 KST 입력/미완료 종료/잘못된 시간 규칙/위험한 메모/설정 변경은 거부. 설정·종료 상태·입력 변경 시 이전 결과 무효. **자동 저장, 무인 예약, 실게시, OBS, 계정/API/네트워크 연결 전혀 없음**.

## 검증 범위
- 신규 단위 테스트 `tests/test_offline_end_notice.py`; GUI `scripts/gui_offline_end_notice_smoke.py`; 전체 회귀 검사 로그 `logs/STAGE90_*`.
- 원본 단계 089 및 010 사용자 최종 승인 상태 `pending` 유지; `config/roadmap.json` 변경 금지.
- 실제 Windows/EXE, 실제 TTS 및 아바타, 방송 종료 감지, 결과 통계, 시청자 수, 플랫폼·OBS·디스코드·네이버 카페 게시/게시 확인, 권리 및 자연스러움은 **미구현 또는 미검증**. 사용자에게 검증을 요청해야 하는 항목은 `docs/REAL_DEVICE_ACCEPTANCE_CHECKLIST.md` 참조.
- **코드 개발 도달 범위 89/100**은 실제 제품 완성률 또는 방송 성공률이 아니다.
