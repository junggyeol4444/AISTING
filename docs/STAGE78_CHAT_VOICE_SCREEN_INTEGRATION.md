# v78 · 원본 077 시청자 채팅·음성·화면 통합 테스트 — 오프라인 부분 검증

## 범위와 한계

기존 061 가상 플랫폼 연결 → 062 모의 수신 → 063 FIFO 동기화 → 065 MockCoreReplyPort 응답 → 073 **무음 텍스트** 구간 분할/화면 표시 → 074 Canvas 구성 점검을 실제 Python 객체 호출로 연결한다. 화면은 별도의 임시 Tkinter Canvas이며 버튼 클릭당 가상 채팅 3건을 처리한다. 운영 중의 수신함/대화 기록/방송 화면/설정/데이터는 수정하지 않는다. 중복된 채팅 내용도 각각 1회 응답해야 하며 2D/3D 미선택 상태의 자동 대체를 허용하지 않는다.

새 단위 테스트는 응답 순번, 무음 구간별 Canvas **텍스트 아이템**의 기대 문자열, 내부 처리 커서, 누락·불일치·예외 시 실패 보고, 임의의 음성 방식으로 대체 금지, 선택/플랫폼 검증, 외부 파일/DB/네트워크/프로세스 금지를 검증한다. GUI 스모크는 Linux Xvfb Tk에서 실제 `Canvas.type`/`itemcget`을 호출한다.

**진짜 방송 검증은 아니다.** 채팅 3건은 사람이 만든 가상 메시지, 응답은 기존 결정적 Mock 포트, 음성은 스피커로 재생되지 않는 문자, 화면은 실제 송출 프레임이 아닌 로컬 자리표시자다. 모의 결과가 PASS여도 실제 시청자에게 소리나 영상이 전달되는지 확인할 수 없다. 실제 Windows 10/11, EXE, 라이브 채팅 계정/인증, TTS 엔진·음성 품질, 캡처/OBS, 네트워크 복구 및 송출, 지적재산권/설치 권한/자연스러움/사용자 승인은 전부 **미검증**이다. 외부 연결 금지 조건을 유지한다.

## 발견하여 수정한 결함

첫 실제 Tk GUI 스모크에서 `TclError: unknown option "-text"`가 발생했다. 073에서 만든 음성 오버레이 태그에 **rectangle과 text 두 유형의 아이템**이 함께 있어 rectangle에 텍스트 속성을 요청한 것이 원인이다. 077 통합 검사는 Canvas 아이템 종류를 `type(id) == 'text'`로 먼저 판단한 다음 문자 비교하도록 수정했다. 이 오류는 단순 가짜 Canvas만으로는 검증하기 어려웠다. 전 GUI 리그레션을 다시 수행했다.

## 운영자에게 남겨 둘 미검증·승인 항목

`docs/REAL_DEVICE_ACCEPTANCE_CHECKLIST.md` 참조. 이 문서는 검증 계획이지 사용자 PC 자동 탐색, 자동 설치, 방송 시도 지시가 아니다. Windows 실기기/최종 승인은 별도 pending. 원본 077 체크박스와 `config/roadmap.json`의 상태를 바꾸지 않았다. 코드 개발 **도달 범위만 77/100**이다.

실행 예시: `PYTHONPATH=src:tests python -m unittest discover -s tests -q` 및 Linux 가상 환경에서 `xvfb-run -a env PYTHONPATH=src:tests python scripts/gui_offline_chat_voice_screen_integration_smoke.py`.
