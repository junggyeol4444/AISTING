# 29단계 · 저장 기록과 새 대화 연속성 구조 검증

- 기준: v28 전체 누적 ZIP을 추출해 기존 파일을 유지하고 신규 파일 추가 및 desktop.py에 탭 연결.
- 새 파일: src/ai_broadcaster/conversation_continuity.py, tests/test_conversation_continuity.py, scripts/gui_conversation_continuity_smoke.py.
- 수정 파일: src/ai_broadcaster/desktop.py.
- 기능: 사용자 명시적 버튼 실행에서만 저장 기록 DB 읽기; 최신 세션의 저장 성공 응답과 신규 입력 간 맥락 전달 가능 구조 점검. 직전 최대 8건, FIFO, 세션 경계 및 중복 입력을 검사. 조회 전 파일 생성 없음, DB 변경 없음.
- 범위 제한: 새 대화에 실제 AI 답변을 생성하거나 이전 기록을 모델에 주입하지 않음. 자연스러움/의미 이해/장기 기억 검증 아님. Windows 실기기 및 EXE 미검증.
- 승인: 10단계 최종 승인 대기, 11단계 이후 사용자 PC 정보 수집 미실시, 공식 9/100 유지.
- 금지 작업: GitHub, 외부 네트워크, Ollama 실접속, OBS, 프로그램 설치, PC 원격 제어 미실시.
