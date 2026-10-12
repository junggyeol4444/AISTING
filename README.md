# AISTING - Windows AI 방송인 프로그램

**최종 제공 형식은 웹사이트가 아닌 Windows EXE 프로그램**입니다.

## EXE 받는 법

GitHub Actions -> AISTING Windows EXE build -> 성공한 main 브랜치 실행 -> Artifacts -> AISTING-Windows-EXE.
ZIP 파일을 풀면 AISTING.exe가 나옵니다. 더블클릭하면 브라우저 대신 Windows 프로그램 창을 엽니다.

프로그램은 오픈소스 Python Tkinter GUI로 제작하며 GitHub의 Windows 러너에서 PyInstaller로 EXE를 빌드합니다.
최종 EXE를 쓰는 PC에는 Python과 PyInstaller를 별도로 설치할 필요가 없습니다.

## 지금 구현된 기능

- Windows 네이티브 방송 설정 창: 플랫폼 복수 선택, 콘텐츠, 캐릭터, 목소리, 아바타 선택.
- 집 PC/무료 사용 정책을 유지하고, 선택한 내용은 Windows 사용자 폴더에만 저장.
- 설정 저장은 방송이나 결제를 시작하지 않음.
- 모의 채팅 큐·방송 상태 머신·로컬 Ollama 연결 코드.
- 실제 방송 송출, TTS, 아바타 실시간 움직임, OBS 제어는 아직 미구현.

개인 설정 저장 위치: Windows LOCALAPPDATA/AISTING/operator_settings.json
코드 서명 미적용으로 Windows 보안 경고가 있을 수 있습니다. 출처를 확인하세요.

## 소스 실행과 테스트

Python 3.11+ 환경에서:
- python scripts/desktop_app.py
- python tools.py validate
- python -m unittest discover -s tests -v

## GitHub와 개발 규칙

PR/main push 시 테스트 및 Windows EXE 빌드만 자동 실행합니다. 예약 개발 작업은 꺼져 있으며,
사용자가 직접 "예약"이라고 지시하기 전까지 일정 예약을 켜지 않습니다.
유료 설치, 계정 연결, 실제 외부 송출은 운영자 승인 없이 하지 않습니다.
완료 공식 단계는 2/100이고 방송 플랫폼의 실제 선택은 아직 대기 중입니다.
자세한 내용은 docs/WINDOWS_DESKTOP.md 와 docs/STATUS.md 를 확인하세요.

## 신규: EXE 로컬 AI 대화 테스트 및 대화 기억

AISTING.exe에 **AI 대화 테스트** 탭을 추가했습니다. 사용자가 텍스트 전송을 누르면
내 PC의 로컬 Ollama에만 연결합니다. 설치한 모델 이름을 직접 입력하며,
최근 8개 대화 쌍을 SQLite에서 불러와 문맥에 포함합니다.
답변이 실제 출력된 다음에만 기억에 저장합니다. 기억 전체 삭제 버튼도 있습니다.
**로컬 모델 미설치 시 작동하지 않으며** 자동 설치나 방송 시작은 수행하지 않습니다.
자세한 내용: docs/CONVERSATION_MEMORY.md.

## 신규: 무료 한국어 Windows 음성 미리 듣기

EXE에 '무료 음성 미리 듣기' 탭 추가: 설치된 Windows 한국어 음성 목록 확인,
수동 음성 재생과 중지. 음성이 PC에 없으면 사용 불가, 유료 서비스나 다운로드를
자동으로 시작하지 않습니다. 아직 OBS 방송 출력용 TTS/립싱크 연결은 미구현.
자세한 내용: docs/WINDOWS_TTS_PREVIEW.md.

## 신규: AI 답변을 한국어로 직접 읽어주기

Windows EXE의 AI 대화 테스트 탭에서 무료 한국어 음성을 선택하고
AI 답변을 직접 듣거나, 사용자가 켠 경우에만 새 AI 답변을 자동 재생하도록 연결했습니다.
대사 읽기 중지, 긴 문장 분할 재생, 재생 실패와 대화 처리 분리가 적용되었습니다.
로컬 모델과 한국어 시스템 음성 설치는 사용자가 PC를 켰을 때 사양 확인 후 승인받아 진행합니다.
이 기능은 **PC의 대화 테스트**이며 실제 방송/OBS 립싱크 송출은 미구현입니다.
자세히: docs/REPLY_VOICE.md

## 기본 2D 아바타 미리보기

Windows EXE의 **2D 아바타** 탭에서 별도 캐릭터 파일 없이 자체 제작한
2D 샘플을 볼 수 있습니다. 음성 테스트/AI 대답 읽기 중 입이 움직이고,
오디오 없이 입 움직임을 시험할 수도 있습니다. 이는 **재생 상태 기반 동작 데모**로,
실제 Live2D/VRM 모델 또는 정밀 립싱크가 아닙니다.
`docs/AVATAR_PREVIEW.md` 참조.

## OBS 읽기 전용 연결과 아바타 별도 창

AISTING.exe에 **OBS 연결 확인** 탭이 생겼습니다. 사용자가 확인을 누르면
내 PC(127.0.0.1)에 실행 중인 OBS WebSocket v5로만 접속해
OBS 버전·장면 이름·현재 송출 상태를 **읽기만** 합니다.
실제 방송 시작이나 장면 조작은 수행하지 않습니다.
2D 아바타 탭의 **별도 창 열기**를 이용하면 OBS의 '창 캡처' 대상으로
수동 선택할 수 있습니다. `docs/OBS_PREVIEW.md` 참조.

## OBS 장면 소스 확인 (신규)

EXE의 OBS 연결 확인 탭에서 장면을 선택하면 그 안의 소스 목록과 활성/비활성 여부를
**읽기 전용**으로 확인할 수 있습니다. AISTING 창 캡처 소스는 후보만 보여주며,
실제 창이 제대로 캡처되는지는 OBS 화면에서 운영자가 확인해야 합니다.
소스 자동 추가·장면 변경·실방송 시작 기능은 여전히 없습니다. `docs/OBS_PREVIEW.md` 참조.
