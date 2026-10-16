# AISTING 기존 프로그램 로컬 수정본 v2

**원본 소스 유지 / GitHub 직접 개발·커밋 없음**

원본 GitHub `main`의 `src/ai_broadcaster/desktop.py`를 읽기 전용으로 대조한 뒤, 이 대화의 작업 공간에서 수정 패치를 작성했습니다. 적용 대상은 원본과 동일한 Git blob SHA `a5df12a74a27a5a50657da9c968253859b98b8ed`인 *기존 AISTING 앱*입니다. 다른 버전에는 임의로 적용하지 않습니다. 새로운 프로젝트를 만들지 않습니다.

이번 변경에서:

- AISTING `AistingApp`의 첫 화면을 방송인 홈으로 전환하되 기존 개발/도구 화면은 보존.
- 저장된 캐릭터 이름/성격/말투를 사용하고, 캐릭터 확정 저장을 일반 설정 저장에서 분리.
- 사용자가 직접 지정한 공식 Open-LLM-VTuber 서버를 `uv run --offline --no-sync run_server.py`로 실행, 실패 시 별도 로컬 로그 경로와 종료 코드 표시. 공식 Live2D 창을 사용자 명시적 버튼 클릭으로 열도록 연결.
- 공식 프로젝트의 GPT-SoVITS (`tts_model: gpt_sovits_tts`) 한글 음성 연결 항목을 명시적 승인/백업 후 수정하는 기능과 GUI 추가. 기존 LLM·Live2D 설정은 유지.
- `obsws-python`이 이미 패키징되어 있다면 실제 로컬 OBS WebSocket 5 장면/송출 상태를 조회할 수 있는 GUI 추가. 실제 장면 전환 및 **별도 승인 후** 방송 명령 API 코드 포함. 기본 GUI는 읽기만 하며 송출하지 않음.
- Windows 빌드는 별도의 `dist-local-revision` 경로를 사용해 기존 EXE를 보존하며 원본 기획안/검증 로그 리소스를 포함.

**개발 vs. 검증:** 로컬 Python 단위/보호 검사 11개 통과, Linux Xvfb 실제 Tk UI 표시 검사 통과. 이 테스트는 실방송 모의 검증이나 실제 연결 성공을 뜻하지 않습니다. Windows EXE 구동, 실제 Open-LLM-VTuber 모델·음성·Live2D 구동, GPT-SoVITS 한국어 합성, OBS 및 플랫폼 실제 방송은 검증 전입니다.

원본 전체 소스와 Windows 환경이 로컬 컨테이너에 없어 기존 AISTING 전체 프로젝트 소스 ZIP이나 Windows EXE를 재빌드한 것처럼 보고하지 않습니다. 이 파일은 *기존 소스용 수정 패키지*입니다. 패치 적용 자체가 사용자 PC 실기기 검증의 합격 기준은 아닙니다.
