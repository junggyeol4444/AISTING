# Windows 데스크톱 EXE 구성

원래 localhost 웹 브라우저 설정 화면이 구현되어 있었으나 사용자 지시에 따라
**웹이 아닌 네이티브 Windows EXE가 최종 배포 방식**으로 확정되었다.

- 창 UI: src/ai_broadcaster/desktop.py (Tkinter)
- UI 데이터 변환: src/ai_broadcaster/desktop_state.py
- 실행 엔트리: scripts/desktop_app.py
- 설정 저장: src/ai_broadcaster/operator_settings.py
- Windows 빌드: .github/workflows/build-windows.yml
- 다운로드: GitHub Actions 성공 실행의 AISTING-Windows-EXE ZIP → AISTING.exe
- 예약 워크플로 없음. PR / main push / 수동 실행에만 빌드.
- EXE에서 Python/PyInstaller 별도 설치가 필요 없도록 패키징.
- 설정 파일은 Windows LOCALAPPDATA/AISTING/operator_settings.json에 저장.
  EXE 임시 압축 해제 경로에 두지 않으며 GitHub에도 업로드하지 않는다.

## 초기 EXE의 작동 범위

플랫폼 복수 선택, 수다/게임 선택, 기본/사용자 캐릭터 설정, 목소리 및
아바타 선택, 무료/PC 전용 제한 적용, 설정 영구 저장.

이 단계는 **Windows 설정용 데스크톱 껍데기**이며 실제 AI 방송인 완성이 아니다.
아직 실제 LLM, OBS, TTS, 아바타 렌더링이 통합되지 않았다.
프로그램 실행/GUI 실제 조작 검증은 사용자의 PC 환경에서 추가 확인해야 한다.
Windows 코드 서명이 없어 SmartScreen 경고가 나타날 수 있다.
