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
