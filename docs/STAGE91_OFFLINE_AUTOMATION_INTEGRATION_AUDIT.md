# v91 · 원본 090 방송 자동화 전체 검증 — 오프라인 통합 감사 (실제 방송 미검증)

## 원본과 검토한 근거
- `docs/ORIGINAL_PLAN.txt`: 4부 방송 시작·진행·종료 자동화, 5부 디스코드·카페 공지, 7부 방송 통합 검증.
- `docs/ROADMAP_100.md`: 원본 090 ‘방송 자동화 전체 검증’.
- `config/roadmap.json`: 090 및 최종 사용자 승인 010 모두 **pending** (수정하지 않음).
- 기존 단계 077 채팅·무음 음성·Tk Canvas, 078/079 시간·마무리, 081/082 일정·가상 시작, 084~089 공지·연동 전 검토·가상 표시·가상 종료 결과 기록을 **그대로 재사용**.

## 실제 추가한 코드
- `src/ai_broadcaster/offline_broadcast_automation_audit.py`: 하나의 사용자가 지정한 KST 가상 방송 회차를 바탕으로 **15개 fail-closed 모의 검증**. 시작 일정 준비, 공지 형식/카페 API 미확인 상태, 가상 시작 및 중복 시작 차단, 가상 공지 표시/중복 차단, 채팅 3건→모의 답변→무음 음성 구간→Canvas 텍스트, 최소·최대 시간 경계, 예고→인사→가상 종료, 종료 공지 결과, 종료·재시작 중복 차단 및 미게시/미검증 플래그 유지. 하나라도 실패하면 즉시 ‘미통과’.
- `desktop.py`: 신규 ‘방송 자동화 전체 모의 감사’ 탭. 기존 081 일정 초안을 사용, 운영자 입력 KST/방송 주제와 **사용자가 현재 선택한** 플랫폼·캐릭터·콘텐츠·음성·아바타를 검사. 스크래치 Tk Canvas 분리; 기존 방송 화면, 채팅 수신함, 가상 방송 진행 상태, 운영자 기록에 접근하지 않는다. 시간·일정·화면 구성/음량/설정 변경 시 결과 표시 무효화.
- `tests/test_offline_broadcast_automation_audit.py`: 신규 24개 테스트. 시작 미준비, 외부 실행 플래그, 선택 불일치, 잘못된 날짜/음량/플랫폼/목소리, 3D 선택 유지, 가상 공지 실패, 화면 불일치·실제 송출 성공의 허위 주장, 종료 멘트 표시 실패, 세션 재사용/파일·네트워크·프로세스 접근 금지 검사.
- `scripts/gui_offline_broadcast_automation_audit_smoke.py`: 실제 Linux Xvfb Tkinter에서 15개 검사 통과, 미등록 일정 실패, 시간·주제·음량 무효화, Canvas 무음 텍스트 출력 확인 및 파일 생성 없음.

## 중요한 한계
- 이번 검증이 통과해도 실제 **채팅 수신, AI 모델 출력, 음성 재생, 라이브 아바타/립싱크, 실제 시청자 화면, 실제 시간 1~3시간 진행, 디스코드·카페 게시, OBS 송출 및 종료**는 보증되지 않는다. 네이버 카페 공식 API 글쓰기 지원 여부도 확인하지 않았다.
- 일정은 **수동 입력 시각**, 시간은 **가속된 가상 경과시간**이고, 음성은 **Canvas 문자 표시**다. 실제 스케줄러나 방송 제어 또는 네트워크/계정/PC 접근 기능은 추가하지 않았다.
- `simulated_only=true`, `actual_broadcast_verified=false`, `actual_publication_verified=false`, `approval=pending`. 이들 값은 내부 자동 테스트 통과로 바뀌지 않는다.
- 채팅·화면 모의 시험을 수행하려면 사용자가 선택한 **플랫폼 1개 이상과 Windows 무료 음성 방식**이 필요하다. 선택이 미정이면 자동 선택하지 않고 미통과다. 외부 3D 모델도 임의 2D로 대체하지 않는다.
- 모든 검사는 버튼을 눌러야 시작하고 메모리에만 남는다. 자동 스케줄·네트워크·OBS·공지 게시, 사용자 PC 접근·음성 자료 수집·설치는 없다.
- Windows 실제 PC/EXE, 소리·영상·아바타 자연스러움·실시간 연결·권리 검증 및 최종 사용자 승인은 `docs/REAL_DEVICE_ACCEPTANCE_CHECKLIST.md`에 별도 대기. **코드 도달 범위 90/100은 제품 완성률이 아니다.**

## 검증 증거
- 신규 단위 시험 및 전체 자동 테스트: `logs/STAGE91_UNITTEST.log`.
- GUI 전체 회귀: `logs/STAGE91_GUI_BATCH_0_30.log`, `logs/STAGE91_GUI_BATCH_30_60.log`, `logs/STAGE91_GUI_BATCH_60_89.log` (Linux Xvfb, 89/89 스모크 스크립트).
- Python AST: `logs/STAGE91_SYNTAX.log`.
- 독립 ZIP 압축 해제본 검증: `logs/STAGE91_REEXTRACTED_UNITTEST.log`, `logs/STAGE91_REEXTRACTED_GUI.log`.
- v90 원본 829개 파일 경로 보존·원본 기획안·로드맵 JSON 해시 및 최종 ZIP CRC: `logs/STAGE91_PRESERVATION.log`와 `logs/STAGE91_FINAL_VALIDATION.txt`.
