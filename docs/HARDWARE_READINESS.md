# 12단계 준비 — CPU·RAM·GPU 참고 입력

`PC 사양 입력` 탭은 사용자가 **직접 알고 있는** CPU 이름·코어 수·RAM(GB)·GPU 이름·VRAM(GB)을 입력하는 곳입니다. 빈칸을 허용하며 CPU/GPU 이름은 각각 120자 이하입니다. 값은 현재 PC에서 자동으로 가져오지 않습니다.

- `입력값 검토`는 입력 형식과 빠진 항목만 정리합니다. CPU/GPU 성능, AI 모델 실행 가능 여부, OBS 방송 성능을 판정하지 않습니다.
- `사용자 입력만 PC에 저장`은 별도 확인 대화상자를 거쳐 `hardware_operator_note.json` 한 파일만 저장합니다. JSON에는 `source: operator_self_report`가 기록됩니다.
- `지난 입력 불러오기`와 `사양 참고 기록 삭제`는 사용자 버튼 클릭으로만 동작합니다. 삭제도 확인 대화상자가 필요합니다.
- 기존 방송 설정 `settings.json`, 대화 기억 `conversation.sqlite3`, OS 기록 및 10단계 승인 파일은 수정하지 않습니다.
- 파일 손상/형식 오류/크기 초과는 원본을 변경하지 않고 오류를 표시합니다.

**제한:** 이 기능은 실제 사용자의 CPU/RAM/GPU 확인을 수행하지 않았습니다. 로드맵 12단계는 미완료 상태로 유지합니다. Windows 실기기 검증이 필요합니다.

검증 코드: `tests/test_hardware_readiness.py`, `scripts/gui_hardware_readiness_smoke.py`.
