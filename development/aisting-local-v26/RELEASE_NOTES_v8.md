# AISTING 기존 소스 로컬 수정 패키지 v8 — 2026-10-15

## 실제 변경 파일

- `payload/src/ai_broadcaster/original_plan_ws.py` 신규: 공식 Open-LLM-VTuber `ws://127.0.0.1:12393/client-ws` WebSocket 업그레이드·서버 `set-model-and-conf` 초기화 메시지를 실제 로컬 서버에서 읽는 코드. 각 연결은 `operator_approved=True`가 필요하며, 모델 이름·설정 이름·Live2D 모델 경로만 반환. Python 표준 라이브러리 사용, 설치 없음. AI 대화/TTS/마이크/방송 명령을 전송하지 않음. 성공해도 실제 AI·음성·Live2D 작동을 의미하지 않음.
- `payload/src/ai_broadcaster/original_plan_studio.py`: 기존 방송인 홈에 **사용자 승인 확인** 후 공식 WebSocket 초기화 진단 버튼, 비동기 연결 상태 및 오류 표시. GUI 이벤트는 Tk 메인 스레드에서만 갱신.
- `apply_to_existing_aisting.py`: 원본의 로컬 **검증된 사본**에 추가할 `original_plan_ws.py` 모듈을 포함. GitHub 변경 없음.
- `build_existing_windows.ps1`: 원본 체크아웃 및 미검증 폴더에서 빌드하지 않도록 출처 기록·수정 모듈·백업 검사. 타임스탬프를 붙인 별도 출력 경로로 기존 EXE 보호. Windows 실행/실제 빌드 미검증.
- `tests/test_v8_official_ws_protocol.py`: WebSocket 표준 헤더·프레임·공식 초기화 메시지의 10개 보조 단위 검사. 가짜 AI 답변·가짜 음성/방송 성공 테스트가 아님.
- `tests/gui_existing_studio_smoke.py`: Linux/Xvfb 실제 Tk 창에서 새 상태 위젯 및 UI 이벤트 처리 확인. 공식 WebSocket 연결 자체는 수행하지 않음.
- `README_기존프로그램_수정안내.md`: v8 적용/빌드/검증 구분 및 안전 절차 안내.

## 실제 확인과 한계

- 기존 v7 ZIP 파일 실재 및 압축 무결성 확인 후 로컬 사본에서 개발. GitHub READ ONLY로 기존 main 트리(1112항목/1103파일) 및 공식 Open-LLM-VTuber `routes.py`, `websocket_handler.py`, `live2d_model.py` 프로토콜을 조회함.
- 기존 main 전체 소스 로컬 다운로드 시도는 GitHub DNS 접근 제한으로 실패. 실제 전체 원본에 패치를 적용한 결과나 완성 EXE를 만들었다고 주장하지 않음.
- Python 단위/보호 검사 **50개 통과**, Python 구문 검사, Linux Xvfb 실제 Tk UI 표시 검사 통과. 이는 **로컬 보조 검사**이며 공식 WebSocket 서버·AI 대화·음성·아바타·OBS 실기기 검증이 아님.
- Windows PowerShell/EXE 빌드 환경 없음. 실제 한국어 GPT-SoVITS·Live2D·OBS·플랫폼 채팅·자동 시작/종료·공지·장시간 운영 미완성·미검증.
- 원본 파일, GitHub, 사용자 PC, 예약, OBS, 계정, 모델, 외부 게시, 실제 방송은 변경/실행하지 않음.

## 사용자 PC 전용 실제 확인 방법과 합격 기준 (별도 승인 후)

1. 사용자가 소유하고 이미 준비한 공식 Open-LLM-VTuber를 직접 실행하고, AISTING 방송인 홈에서 해당 공식 프로젝트 폴더를 선택한다. 설치/모델 다운로드가 필요하면 먼저 사용자에게 별도 승인을 요청한다.
2. 공식 화면이 정상 실행 중인 상태에서 AISTING의 **“공식 WebSocket 초기화 확인”** 버튼을 누르고 이번 연결을 승인한다. 합격 범위는 `set-model-and-conf` 메시지에서 실제 설정명·Live2D 모델 이름/경로가 표시되는 것 **까지만**이다. 연결 실패 시 버튼의 오류 문구와 공식 서버 콘솔/로그의 시간대 및 오류를 기록하되 비밀번호·API 키·사용자 데이터는 제거한다.
3. 실제 AI 대화·한국어 음성·아바타 립싱크는 **공식 화면에서 별도로** 관찰해야 하며, 그 증거가 없으면 1단계 완료로 표시하지 않는다. OBS 송출/실제 방송은 이 검사에서 절대 시작하지 않는다.

## 다음 작업

기존 전체 AISTING 원본 소스를 안전하게 로컬 확보하고, 검증된 별도 사본에 v8 적용·캐릭터 확정 저장/재실행 및 원래 기능 회귀 검사. Windows EXE 제작 후 사용자 PC 실기기 확인. 이어 원본 기획안에 따라 실제 GPT-SoVITS, 플랫폼 채팅+OBS, 자동 종료/시작, 공지, 장시간 운영을 개발한다.

**이번 v8 로컬 수정 작업 구간은 끝났습니다. AISTING 전체 프로젝트는 아직 미완성입니다.**
