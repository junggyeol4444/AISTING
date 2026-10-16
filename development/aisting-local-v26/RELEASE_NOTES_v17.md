# AISTING 기존 프로그램 로컬 수정 v17 — 2026-10-16

## 변경
- `payload/src/ai_broadcaster/original_plan_persona_store.py`: 일반 방송 설정 저장 시 최신 디스크의 확정 캐릭터만 유지하고 미확정 초안은 버리는 `save_broadcast_without_persona` 추가. 다른 창의 방송 설정 변경 충돌 감지, 비공개 원본 백업, 원자적 교체. v16 캐릭터 확정 저장도 동일한 파일 교체 헬퍼를 재사용.
- `apply_to_existing_aisting.py`: 기존 `desktop.py`의 일반 `_save`를 새 헬퍼에 연결, 성공 후 저장 캐릭터 화면 갱신. 기존 메인 창·설정·기억·100단계 기능 삭제 없음.
- `tests/test_v17_broadcast_save_persona_isolation.py`: 보조 파일 수준 검사 8개 추가.
- `build_existing_windows.ps1`: 기존 EXE를 보호하는 v17 고유 빌드 경로.

## 검증 구분
이 패키지는 기존 전체 AISTING 소스가 아닌 수정안이다. 기존 전체 소스에 패치 적용, Windows EXE, 실제 AI/음성/아바타/OBS/채팅/자동 방송은 미검증. 보조 검사는 기존 offline_settings 전체 원본 대신 제한된 fixture를 사용한다.
