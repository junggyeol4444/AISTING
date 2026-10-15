# AISTING v80 · 원본 079 자연스러운 종료 멘트/자동 종료 — 오프라인 계약만

## 근거 / 실제 구현 범위

`docs/ORIGINAL_PLAN.txt` §2-2, §4-3, §4-4의 절차는 최대 방송시간 이후 **종료 예고 → 작별 인사 → 방송 종료**다. v79의 078 `BroadcastDurationRules`가 반환한 검증된 **최대 시간 도달 판정**이 있어야만 종료 절차 시뮬레이션이 시작된다. 최소 방송시간 이전에 자동 종료를 진행하지 않는다.

`src/ai_broadcaster/offline_broadcast_closing.py`에 결정적인 인메모리 상태 기계를 추가했다:

1. `notice_pending` — 캐릭터 이름으로 마무리 예고 문장 표시 대기
2. `farewell_pending` — 예고가 화면 표시 콜백에 성공한 경우에만 작별 인사 표시 대기
3. `virtual_ended` — 마지막 문구 표시를 확인한 뒤 **메모리 안의 가상 종료 플래그**만 참으로 자동 전환

표시 콜백에서 오류가 발생하면 이전 상태와 미표시 문구를 보존한다. 무한 재시도·다음 단계로 자동 건너뛰기·중복 종료는 없다. 사용자 GUI에는 기존 `방송 화면 구성 미리보기` 탭에 **마무리 멘트 모의 준비** 및 **다음 멘트 표시 / 가상 종료** 버튼 두 개를 추가한다. 실제 대화 생성 모델 호출이 아닌 **고정 한국어 예시 문장**이다. 멘트 자연스러움/캐릭터 부합 여부는 사람이 판단해야 한다. GUI에서 대사 표시는 Tk 문자열일 뿐 소리로 출력되지 않는다.

**자동 종료라는 단어는 마지막 문구를 전달한 뒤 가상 상태가 자동으로 `virtual_ended`로 전환된다는 뜻만 갖는다.** 실제 OBS 송출 종료, 종료 시간 감지 스케줄러, 실시간 자막/음성, 네트워크 호출, 방송 제어, 프로그램 종료, 사용자 설정 저장 등은 전혀 수행하지 않는다. 실제 방송의 무인 안전 종료 기능은 미구현이다. 자동 공지 게시/장기 기억 추가/랜덤 종료/채팅 저조 종료는 구현하지 않았다.

기존 플랫폼·콘텐츠·캐릭터·음성·아바타·사용자 자료 및 기획안은 그대로 보존한다. 사용자가 화면/시간/음량/프로필을 바꾸면 이전 가상 종료 세션이 무효화된다. 원본 079와 최종 승인 010은 `pending`; **코드 도달 범위 79/100**은 실제 방송 기능 완료 또는 제품 완성도가 아니다.

## 테스트 절차 / 한계

- `PYTHONPATH=src:tests python -m unittest tests.test_offline_broadcast_closing -v`
- `PYTHONPATH=src:tests python -m unittest discover -s tests -q`
- `xvfb-run -a python scripts/gui_offline_broadcast_closing_smoke.py`
- `scripts/gui_*_smoke.py` 개별 회귀 검사
- 전체 파일 Python AST 검사 및 새 ZIP 별도 압축 해제·재검증

실제 Windows 10/11, 실제 TTS 스피커, OBS WebSocket, 실제 방송 종료/권한/계정, 안전 강제 종료·종료 실패 재시도 정책은 **미검증·승인 대기**다. `docs/REAL_DEVICE_ACCEPTANCE_CHECKLIST.md` 참고.
