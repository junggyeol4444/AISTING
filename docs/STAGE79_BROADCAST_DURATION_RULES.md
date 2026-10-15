# AISTING v79 · 원본 078 방송 최소·최대 시간 규칙 구현 (오프라인 부분)

## 원본 근거와 범위

- `docs/ORIGINAL_PLAN.txt` [4-3 종료각 판단]에는 **최소 방송 시간 약 1시간**, **최대 방송 시간 약 3시간**을 기본값으로, 운영자가 값을 바꿀 수 있도록 규정한다.
- 이번 단계는 판정 로직을 구현한다. **079 자연스러운 종료 멘트/자동 종료는 구현하지 않는다**. OBS·실제 방송·자동 스케줄러·외부 연결·실제 시계 타이머·기존 설정 영구 변경 없음.
- 실제 방송 시간 규칙으로 사용하는 것은 미검증이며 078 및 010 승인 상태는 `pending`이다.

## 로컬 코드

- `src/ai_broadcaster/offline_broadcast_duration.py`: 기본 최소 60분/최대 180분, 운영자 지정 정수 1~1440분, `minimum <= maximum` 검증. 정확한 초 단위 경과를 입력받는 불변 `DurationDecision` 반환.
- 최소 미달: `can_consider_ending=False`, `action='continue'`.
- 최소 이상/최대 미만: 종료를 *고려*할 수 있지만 종료를 실행하지 않고 계속.
- 최대 이상: `action='wrap_up_requested'`로 **마무리 판단 필요**만 보고. 실제 멘트·OBS 중단 없음.
- `BroadcastDurationSession`: 향후 별도 승인된 로컬 호출자가 단조 증가 시간값을 명시적으로 전달하는 인메모리 인터페이스; 역행·NaN·무한값 거부. 현재 GUI에서는 호출하거나 실제 시간을 자동으로 확인하지 않음.
- 기존 `방송 화면 구성 미리보기` 탭에 최소·최대·가상 경과(분) 입력, 수동 평가 버튼을 추가. 입력 변경 및 방송 화면/음량/선택 변경 시 이전 판정 무효화.
- 시뮬레이션 입력 `가상 경과(분)`은 0~10080 범위의 정수만 허용하며 실제 방송 경과 시간을 주장하지 않는다. 네트워크, OS/사용자 PC 시계, 장치 및 설정 파일을 읽지 않는다.
- 선택적 '채팅 저조 종료', 정해진 시각대, 랜덤 변주 등은 **운영자 명시 선택 전 기본 적용하지 않는다**. 이전 채팅 전체 응답 원칙이나 지연 방침에도 영향 없음.

## 테스트 및 제한

- 단위: `PYTHONPATH=src:tests python -m unittest discover -s tests -p test_offline_broadcast_duration.py -v`; 정확한 경계, 반전 설정, invalid/NaN, 역행, 불변 판정, 외부 연결/시간 지연 금지.
- 전체: `PYTHONPATH=src:tests python -m unittest discover -s tests -q`; GUI는 `xvfb-run -a python scripts/gui_offline_broadcast_duration_smoke.py`, 기존 `scripts/gui_*_smoke.py` 전체 개별 실행.
- Linux 가상 화면 테스트는 실제 Windows/설치된 음성/OBS/실제 방송으로 대체할 수 없다. **사용자가 추후 Windows에서 실제 시간 경과·절전/복귀·타이머 동작과 방송 종료 조건을 승인 후 직접 검증해야 한다.**
- 구체 결과: `logs/STAGE79_*`, `TEST_RESULTS.txt`; 유효하지 않은 검사/미실행 항목은 성공이라고 보고하지 않는다.
