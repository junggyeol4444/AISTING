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

## EXE 로컬 AI 테스트 탭

사용자가 설치한 로컬 Ollama 모델명을 입력하고 **텍스트 전송**을 누를 때에만
PC 루프백에서 요청을 보내며, 별도 스레드로 창 멈춤을 방지합니다.
답변을 EXE에 표시한 후 SQLite에 저장하고, 이전 대화 문맥을 유지합니다.
기억 전체 삭제 전에 별도 확인 창을 보여줍니다.
TTS/OBS/실제 시청자 채팅은 아직 구현되지 않았습니다.

## 무료 음성 미리 듣기 탭

운영자가 버튼을 눌러 Windows의 ko-KR 시스템 음성으로 문장을 테스트하고 중지할 수 있습니다. 아직 방송용 자동 발화 기능은 아닙니다. docs/WINDOWS_TTS_PREVIEW.md 참고.

## AI 응답 음성 읽기 통합

AI 대화 테스트 화면에서 답변을 무료 로컬 Windows 한국어 음성으로 읽는 기능을 추가했습니다. 기본 자동 읽기는 꺼짐이며 사용자가 직접 켤 수 있고, 마지막 답변 수동 읽기/중지가 가능합니다. OBS, 실시간 채팅, 립싱크 자동 연동은 아직 없습니다. docs/REPLY_VOICE.md 참고.

## 2D 아바타 미리보기

무료 Tkinter Canvas로 만든 기본 캐릭터 샘플을 2D 아바타 탭에 표시하고,
PC 음성 출력 중 입을 반복적으로 움직이게 합니다. 정확한 음소 립싱크가 아니며
정식 Live2D 아바타도 아닙니다. `docs/AVATAR_PREVIEW.md` 참고.

## OBS 기초 연동

'OBS 연결 확인' 탭으로 로컬 OBS WebSocket 5.x를 읽기 전용 확인하고,
'2D 아바타' 탭의 별도 창으로 OBS 수동 창 캡처를 지원합니다. 자동 장면 전환/방송 송출은 아직 없습니다. `docs/OBS_PREVIEW.md`.
