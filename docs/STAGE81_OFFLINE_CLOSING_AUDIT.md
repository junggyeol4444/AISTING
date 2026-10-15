# AISTING v81 · 원본 080 자동 종료 전체 검증 (오프라인 모의 감사만)

## 원본 근거와 실구현

원본 `docs/ORIGINAL_PLAN.txt`의 방송 최소/최대 및 **마무리 예고 → 인사 → 종료** 순서와 원본 080 목표 `자동 종료 전체 검증`을 기준으로 한다. 기존 v79의 `BroadcastDurationRules` 및 v80의 `OfflineBroadcastClosing` 상태 기계를 그대로 활용한다. 중복 종료 구현이나 실제 송출 모듈이 아니다.

신규 `src/ai_broadcaster/offline_broadcast_closing_audit.py`는 12개 독립된 메모리 시나리오를 검증한다: 최소 시간 미달 / 최대 시간 직전 시작 차단 / 최대 시간 도달 대기 / 예고 후 인사 대기 / 인사 후 가상 종료 / 예고 실패 보존 / 인사 실패 보존 / 자동 재시도 없이 수동 재개 / 중복 종료 차단 / 콜백 재진입 차단 / 세션 간 상태 격리 / 스냅샷 변조 차단. 각 결과는 불변 데이터 객체의 `passed`와 설명으로 반환하며, 하나라도 실패하면 전체 `미통과`를 표시한다. 의도적으로 잘못된 종료 구현을 주입했을 때 실패를 숨기지 않는지 테스트한다.

운영자는 기존 `방송 화면 구성 미리보기` 탭의 `080 자동 종료 전체 모의 검증` 버튼을 눌러 현재 최소·최대 시간 설정과 캐릭터 이름으로 **격리된 샘플 세션**을 감사할 수 있다. 현재 방송 화면 미리보기가 유효해야 시작한다. 이미 진행 중인 079 가상 종료 세션/문구/실제 사용자 설정은 변경하지 않는다. 화면·시간·캐릭터·음량 등 기존 무효화 이벤트는 감사 보고서를 무효화하며 임의로 승인 상태를 바꾸지 않는다.

**사용자 기기에서의 자동 방송 종료, 실제 시계, 자연스러운 실제 한국어 TTS, 방송 화면/OBS/플랫폼 상태는 한 번도 검사하지 않았다.** 테스트 결과 '가상 종료'는 실제 종료 검증이 아니며, 원본 080 및 사용자 최종 승인 010은 계속 `pending`이다. 코드 도달 범위만 80/100이며 실제 제품 완성도와 무관하다.

## 코드 검사 재현

- `PYTHONPATH=src:tests python -m unittest tests.test_offline_broadcast_closing_audit -v`
- `PYTHONPATH=src:tests python -m unittest discover -s tests -q`
- `xvfb-run -a env PYTHONPATH=src python scripts/gui_offline_broadcast_closing_audit_smoke.py`
- `scripts/gui_*_smoke.py` 개별 실행 (Linux 가상 화면)
- 전체 Python AST 구문 검사 / ZIP CRC·이전 파일 보존 확인 / 별도 압축 해제 후 재검증

실기기·권리·실제 OBS/음성·영상·실제 방송 종료는 사용자 승인 또는 별도 직접 검증이 필요한 항목으로 `docs/REAL_DEVICE_ACCEPTANCE_CHECKLIST.md`에 남겨 놓았다. GitHub, 외부 서버/클라우드 API, 계정, 유료, 설치, OBS, 사용자 PC 정보/음성 수집 수행 없음.
