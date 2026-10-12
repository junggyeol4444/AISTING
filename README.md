# AISTING — AI 방송인 프로젝트

원본 기획안(`docs/ORIGINAL_PLAN.txt`)을 기준으로 100단계로 구축하는 자율 AI 버추얼 방송인 개발 저장소입니다.

## 현재 상태

- **단계 완료: 2/100** (요구사항·핵심 기능 정의).
- **3단계 방송 플랫폼 선택: 운영자 결정 대기.** 운영자가 선택하지 않은 항목은 임의 결정하지 않습니다.
- 별도 개발 산출물: 채팅 FIFO 대기열 / 방송 시작·종료 **모의 상태 머신** / 플랫폼 승인 설정 및 테스트.
- 실제 라이브 방송, AI 음성 응답, OBS 연동은 아직 작동하지 않습니다.

## 모의 실행 및 테스트

Python 3.11 이상 환경에서 외부 패키지 없이 실행할 수 있습니다.

```sh
python tools.py validate
python -m unittest discover -s tests -v
python scripts/demo_session.py
```

## 일정 및 자동화

**정기 예약 작업은 중지되어 있습니다.** GitHub Actions에는 시간 예약(`schedule`)이 없으며, 코드 변경(push/PR) 때의 자동 테스트 또는 수동 실행만 설정되어 있습니다. ChatGPT 쪽 예약도 비활성화 상태입니다. 운영자가 "예약"이라고 지시하기 전에는 다시 켜지 않습니다.

## 개발 원칙

- 운영자가 직접 채팅으로 요청하면 그 시점에 실제 개발을 진행하고 GitHub 저장소에 변경을 반영합니다.
- 채팅은 기본적으로 전부 반응하고 인위적 지연·선별은 넣지 않습니다. 실제 응답 생성 엔진은 향후 연결합니다.
- 자연스러운 캐릭터 행동은 운영자가 판단합니다.
- 운영자가 PC를 켰다고 알려주면 설치 프로그램·계정·예상 비용을 한 번에 설명하고 승인을 기다립니다.
- 승인 없는 프로그램 설치, 유료 결제, 외부 공지 게시, 음성 복제, 방송 송출은 하지 않습니다.

## 주요 파일

- `docs/ROADMAP_100.md` — 100단계 전체 로드맵.
- `config/roadmap.json` — 단계 상태 데이터.
- `docs/FEATURE_SCOPE.md` — 반드시 구현할 기능.
- `docs/PLATFORM_DECISION.md` — 3단계 운영자 결정 대기 사항.
- `src/ai_broadcaster/session.py` — 모의 방송 상태 및 채팅 큐.
- `src/ai_broadcaster/platform_config.py` — 플랫폼 승인을 강제하는 설정.
- `docs/SESSION_ENGINE.md` — 엔진의 구현 범위와 한계.
