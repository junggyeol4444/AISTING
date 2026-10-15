# v46 / 원본 045 — 기본 한국어 음성 출력 경로 비재생 점검

## 기존 기능 검토와 비중복 구현

- 이전 버전부터 `offline_tts.py`와 데스크톱의 `무료 한국어 음성` 화면이 Windows System.Speech 기반 **사용자 수동 재생/중지** 및 마지막 답변 읽기를 제공한다. Windows PC에서 실제 소리가 났는지는 이번 환경에서 확인할 수 없으며, 새로운 음성 엔진/모델을 설치하거나 중복 구현하지 않았다.
- 원본 100단계 045의 승인 불필요 부분으로 `voice_output_validation.py`와 `한국어 음성 출력 모의 검증` 탭을 추가했다. 문장의 유니코드/중복/구간 순서 보존, 600자 이하 구간, 6000자 이내 전체 입력, 중단·오류 시 아직 처리하지 못한 구간 보존, 자동 재시도 없음, 선택형 Windows 음성 방식과 설정값 검증.
- 실패·중단 결과는 **모의 처리**이며 실제 합성/음성 출력에 대한 증거로 사용하지 않는다. 테스트/탭 진입 시 Windows 음성 목록·OS/사양·오디오 장치를 조회하거나 subprocess/네트워크를 시작하지 않는다.
- 기존 `_speech_worker`에서 실제 TTS 백엔드가 `False`를 반환하면 `speech_done`으로 잘못 보고할 가능성을 수정해 `speech_stopped`로 처리하도록 했다 (가상 백엔드로 GUI 회귀 검증).
- 음성 확보 방식이 `own_recording/consented_recording/licensed_recording/undecided`이면 아직 구성되지 않은 상태이므로 이번 Windows 출력 모의 실행을 차단한다. 사용자가 설정/음성 방식을 변경하면 화면의 이전 결과 무효화. 설정/기존 SQLite/음성 자료/기획안 내용은 자동 저장·접근하지 않음.

## 사용자 직접 확인이 필요한 미완료 부분

- 실제 Windows PC에서의 설치된 ko-KR 음성 존재·선택·듣기·음질·장치 및 EXE 구동 검증은 **미실행**. 사용자 승인을 받은 뒤 본인이 `무료 한국어 음성`에서 버튼으로 수동 확인할 필요가 있다. 010 최종 승인 및 011 이후 PC 정보 조회는 여전히 대기.
- 별도 로컬 TTS/사용자 목소리 학습·음성 복제는 아직 연결·설치하지 않았다. 소리 출력 모의 성공만으로 원본 045 완료 또는 사용자 품질 평가 합격을 주장하지 않는다.
- 플랫폼/콘텐츠/캐릭터/음성/아바타 선택을 유지하고 GitHub/클라우드/유료 서비스/설치/OBS/실방송/사용자 PC 원격 접근 없음.

## 검증 절차

```sh
PYTHONPATH=src python -m unittest discover -s tests -q
xvfb-run -a python scripts/gui_voice_output_validation_smoke.py
```

전체 GUI 회귀는 `scripts/gui_*smoke.py` 대상으로 진행하고 구체적인 통과 개수와 재압축 검증은 `logs/STAGE46_FINAL_VALIDATION.txt`에 기록한다. 테스트 OS는 Linux 가상 디스플레이이며 Windows 실기기가 아니다.
