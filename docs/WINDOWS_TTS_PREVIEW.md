# Windows EXE 무료 한국어 TTS 미리 듣기

AISTING.exe의 무료 음성 미리 듣기 탭은 PC에 이미 설치된 한국어(ko-KR)
Windows System.Speech 음성만 목록으로 보여주고 재생합니다.

- 버튼을 눌러 한국어 음성을 확인하고 선택
- 미리 듣기 문장을 직접 입력 (1~600자)
- 음량 및 속도 지정
- 미리 듣기 버튼을 누르면 한 번 재생
- 중지 버튼으로 해당 TTS 작업만 종료
- 자동 설치, 유료 API, 외부 서버, 음성 복제, 계정 연결 없음

기술: Windows PowerShell과 .NET System.Speech.Synthesis.SpeechSynthesizer.
PowerShell 코드 본문은 고정, 사용자 문장은 stdin UTF-8 JSON으로 전송해
명령 실행 취약점을 피합니다.

**현재는 실제 방송용 음성이 아니라 로컬 테스트용입니다.**
실제 AI의 발화, OBS 출력, 아바타 립싱크 자동 연결은 아직 구현되지 않았습니다.
PC에 ko-KR 음성이 없으면 화면에 알려주며 임의 설치하지 않습니다.
Windows 실사용 환경에서 음질/음성 지원 여부 추가 검증이 필요합니다.

예약 작업 중지 유지.
