# AISTING 유지보수 — 설정 저장 원자성·기존 파일 보존 (v103)

원본 100단계 개발표에 추가하는 단계가 아니다. 사용자 최종 승인·실제 Windows/OBS 방송 검증은 계속 대기다.

## 확인된 실제 결함

`src/ai_broadcaster/offline_settings.py`의 기존 `save_settings()`는 설정 파일과 같은 폴더의 고정 경로 `settings.tmp`에 먼저 쓴 뒤 교체했다. 이 방식은 기존 `settings.tmp` 파일을 덮어쓰거나, 그 경로가 심볼릭 링크라면 다른 파일 내용을 변경할 수 있다. 또한 교체 실패 시 임시 파일이 남고, 다중 저장 시 임시 파일을 서로 공유한다. 새 회귀 테스트 4개 중 수정 전 3개가 실패하는 것을 확인했다(기존 임시 파일 보존, 링크 대상 보호, 교체 실패 시 임시 파일 정리).

## 수정

검증한 설정 JSON을 설정 파일과 **동일한 폴더**의 고유한 임시 파일(`NamedTemporaryFile`, `delete=False`)에 기록한다. `flush()` 및 `os.fsync()` 후 `os.replace()`로 원자적 교체를 요청하고, 성공·실패 모두 생성한 임시 파일만 정리한다. 고정 `settings.tmp` 파일과 링크는 건드리지 않는다. 이전 JSON 필드·선택값·저장 경로·사용자 수동 저장 UI 동작은 변경하지 않았다. 이 조치는 동시 저장 사이의 **데이터 무결성**을 개선하지만, 여러 앱 프로세스의 설정 변경을 병합하거나 마지막 저장자의 덮어쓰기를 방지하는 잠금은 구현하지 않는다. Windows 파일 잠금 동작은 실기기에서 확인해야 한다.

## 테스트

- 신규 회귀 4개: 기존 `.tmp` 파일 보존, `.tmp` 링크 대상 보존, 교체 실패 시 기존 JSON/정리, 저장·재조회 선택값 보존.
- 전체 자동 테스트: `PYTHONPATH=src PYTHONWARNINGS=always::ResourceWarning python -m unittest discover -s tests -v` — 2,002/2,002 통과, ResourceWarning 0건.
- Linux Xvfb 가상 화면 GUI 스모크: 기존 99개 스크립트 모두 통과(15/15/15/15/15/15/9개 구간).
- `python -m unittest discover -s tests -v` 단독 명령에서 기존 `test_all_chat_policy`의 `ai_broadcaster` 모듈 검색 경로 오류 1건도 확인해 해당 테스트의 다른 테스트들과 동일한 로컬 `src` 경로 초기화를 보완했다. 단독 실행과 `PYTHONPATH=src` 실행을 모두 재검증한다.

테스트는 임시 경로·모의 데이터만 사용했다. 실제 운영자 설정이나 PC를 읽거나 변경하지 않았다. Windows EXE, 장시간 실제 방송, TTS·아바타·OBS·플랫폼 연결은 미검증이다.
