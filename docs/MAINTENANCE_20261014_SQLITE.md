# AISTING 유지보수 기록 — 2026-10-14 / 누적 소스 v102

이 문서는 원본 100단계 개발표의 **새 단계가 아니다**. 원본 010/100 운영자 승인과 실제 제품 출시는 계속 `pending`이다. 기존 v101 소스에 대한 SQLite 경고 원인 분석과 안전한 회귀 수정을 기록한다.

## 확인한 실제 원인과 범위

v101의 `PYTHONWARNINGS=always::ResourceWarning python -m unittest discover -s tests -p test_response_records.py -v` 재현에서 **37개 테스트는 통과했지만 SQLite 연결 미종료 경고 5건**이 발생했다. 원인은 `tests/test_response_records.py`의 `with sqlite3.connect(...) as db:` 다섯 곳이었다. SQLite 연결의 컨텍스트 관리자는 트랜잭션 커밋/롤백을 수행하지만 연결 객체를 `close()`하지 않는다. 따라서 과거 전체 테스트에서의 경고를 `offline_chat.py`의 누수라고 단정한 보고는 실제 재현 위치를 잘못 짚은 것이었다. `offline_chat.LocalMemory._connection()`은 이미 `finally: db.close()`로 연결을 닫고 있었다.

## 실제 수정

1. `tests/test_response_records.py` 다섯 곳을 `with closing(sqlite3.connect(...)) as db, db:`로 변경해 테스트용 연결도 명시적으로 닫도록 했다. 기존 테스트의 DB 내용·트랜잭션 검증은 유지한다.
2. `src/ai_broadcaster/response_records.py`의 `_readonly()`에서 `PRAGMA query_only=ON` 실패 시 새로 열린 연결을 반드시 닫도록 예외 경로를 보완했다. 예외는 숨기지 않고 다시 발생시킨다.
3. 신규 회귀 테스트 2개를 추가했다: 저장·조회·삭제의 실제 SQLite 핸들이 모두 닫혔는지 확인, PRAGMA 실패 시 핸들 닫힘 확인.
4. 최종 검수/운영자 점검 화면의 고정 경고 문구를 **테스트 픽스처 경고 수정·Windows 장시간 자원 검증 미완료**로 수정했다. 기존 출시 차단과 승인 대기 상태는 그대로 유지한다.

## 검증 한계

Linux/Python 3.13 개발 환경의 단위 테스트 및 Xvfb 가상 Tk 화면 시험만 수행한다. 사용자 Windows PC, EXE, 실제 TTS/아바타/OBS/플랫폼 채팅, 장시간 실사용, 파일 잠금 및 장기 메모리 누수는 검사하지 않았다. 위 테스트 경고 5건이 사라진 것은 확인했지만, Windows 실제 환경의 SQLite 안정성을 증명하는 것은 아니다. 원본 기획안과 `config/roadmap.json`은 바꾸지 않았다.

검증 원문은 `logs/MAINTENANCE_20261014_*.log` 및 ZIP 외부 `AISTING_v102_MAINTENANCE_VALIDATION.txt`를 참고한다.
