# v94 / 원본 093 기억 검색과 다음 방송 연동 — 오프라인 부분 개발

## 실제 구현 범위

- v93 원본 092 `OfflinePastBroadcastMemory`를 재사용한다. 검색 대상은 운영자가 **직접** 수동으로 가져와 확인한 모의 회차 카드뿐이며, 컴퓨터 폴더를 자동 검색하거나 실제 방송 기록·계정·음성 자료를 수집하지 않는다.
- 운영자 수동 검색어(최대 100자, 공백 구분 최대 8단어)와 카드 이름/문구의 소문자 포함 일치(AND)로 결과를 최대 20개 표시한다. 의미 검색·벡터 DB·AI 검색은 **아니다**.
- 운영자는 결과 중 **한 회차를 직접 선택**해 최대 5건 문구를 다음 **가상** 회차의 참고 자료 구조체로 준비한다. 회차 체크섬과 과거 기록의 모의 채팅 포함 승인값을 그대로 보존하며, 다른 회차 자료를 섞지 않는다.
- 운영자가 가상 질문을 직접 입력하여 버튼을 누르면 선택 참고 문구를 **일반 모의 입력 텍스트**에 넣고 기존 `MockReplyGenerator`로 예시 답변을 만든다. 이는 이미 있던 문자열 반향 기반의 무네트워크 **모의 응답기**이며 실제 AI 모델의 회상·이해력이 아니다. 실제 방송 대화 흐름이나 로컬 Ollama 프롬프트에 기억을 자동 주입하지 않는다.
- 검색어 수정·기억 파일 수동 교체·카드 추가/삭제·새 검색·초기화 시 이전 결과/준비 상태를 무효화한다. 별도 기록·설정 자동 저장 없음. 수동 기억 카드의 JSON 평문 및 SHA256은 암호화가 아니다.
- `mock_only=true`, `model_connected=false`, `automatically_injected=false`, `actual_broadcast_verified=false`, `approval=pending` 으로 표시한다. 원본 `093` 완료 승인과 `010` 최종 사용자 승인, `config/roadmap.json` `pending` 불변.

## 미구현·미검증

- 의미 검색, 실제 LLM/가상 인물의 사실적 장기기억, 진위/출처 평가, 오류 회상 억제, 시청자 개인 데이터 보호 정책 및 실제 다음 방송 프롬프트 자동 연결은 **미구현·미검증**.
- OBS/플랫폼 채팅/Windows TTS/아바타/방송 송출·예약·외부 AI 및 GitHub·원격 서버와 연결하지 않았다.
- 실제 Windows 10/11 EXE GUI와 장시간 SQLite 안정성은 미검증. 단위 테스트에서 기존 SQLite `ResourceWarning`이 지속되므로 별도 후속 조사 필요.
- 사용자 직접 할 일은 `docs/REAL_DEVICE_ACCEPTANCE_CHECKLIST.md` 마지막 구간에서 확인한다. 추가 사용자 PC 접근·설치·인증·권리/동의 수집 없음.

## 테스트 및 증거

`PYTHONPATH=src python -m unittest discover -s tests -q` — 전체 자동 테스트; `xvfb-run -a python scripts/run_stage88_gui_regression.py 0 30` / `30 60` / `60 92` — Linux Tkinter GUI 회귀; `scripts/gui_offline_memory_recall_smoke.py` — 신규 검색/명시적 다음 모의 질문/기억 변경 무효화/외부 접속 차단; Python AST 검사. 결과와 압축 해제 재검증, 파일 경로 보존 및 CRC는 `logs/STAGE94_FINAL_VALIDATION.txt`에 별도로 기록한다.

**코드 개발 도달 범위만 93/100**이며 실제 완성률·실기기 성공률은 아니다.
