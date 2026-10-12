# AISTING — AI 방송인 프로젝트

원본 기획안(\`docs/ORIGINAL_PLAN.txt\`)을 기준으로 100단계로 구축하는 자율 AI 버추얼 방송인 개발 저장소입니다.

## 현재 상태

- **공식 단계 완료: 2/100**. 3단계(방송 플랫폼 실제 선택)는 운영자 선택 대기.
- 운영자 정책: 방송 플랫폼·콘텐츠·목소리·아바타는 나중에 **직접 선택**, 캐릭터는 기본값/직접 설정, **내 PC에서 실행, 유료 프로그램·API·구독·에셋 구매 금지**.
- 선택형 설정 화면은 완성했으나 실방송/AI LLM/TTS/아바타/OBS 연결은 아직 하지 않았습니다.
- 기존 엔진 코드는 모의 채팅 FIFO 처리, 응답 파이프라인 및 방송 상태 검증만 수행합니다.

## 내 PC용 설정 화면 (사용자 승인 후 실행)

추가 Python 패키지 없이 Python 3.11+가 있는 PC에서:

\`\`\`sh
python scripts/settings_server.py
\`\`\`

주소: http://127.0.0.1:8765

플랫폼 다중 선택, 수다/게임, 기본/직접 캐릭터, 목소리·아바타를 선택할 수 있습니다.
설정 내용은 이 PC의 \`data/operator_settings.json\`에만 저장하고 GitHub 저장소에는 올리지 않습니다.
실제 방송 송출, 다운로드, 음성 복제, 결제는 발생하지 않습니다.

## 검증/모의 실행

\`\`\`sh
python tools.py validate
python -m unittest discover -s tests -v
python scripts/demo_session.py
python scripts/demo_chat_pipeline.py
\`\`\`

## 일정과 자동화

정기 예약 작업은 **중지**했습니다. GitHub Actions는 코드 push/PR 또는 수동 실행 시 테스트용으로만 동작합니다. 사용자가 명시적으로 "예약"이라고 지시하기 전에는 시간 예약을 활성화하지 않습니다.

## 개발 지침

- 운영자가 채팅으로 지시하면 이 저장소에서 직접 코드를 개발하고 검증합니다.
- 모든 채팅에 반응하는 기본 방침을 유지하고 의도적 지연/선별은 기본으로 두지 않습니다.
- 자연스러운 캐릭터 행동은 운영자가 판단하며 기본 캐릭터는 임시값입니다.
- PC 사용 준비가 되면 OS/CPU/GPU/RAM을 확인한 후 필요한 프로그램/무료 여부/계정 준비를 한 번에 안내하고 설치는 승인 후 진행합니다.
- 승인 없는 유료 결제, 계정 연결, 외부 공지, 음성 복제, 방송 송출은 하지 않습니다.
- 로컬 모델의 품질/속도는 아직 사양 미확인으로 보장하지 않습니다. 장비와 전기 사용은 완전 무료라고 보장할 수 없습니다.

## 문서

- \`docs/ORIGINAL_PLAN.txt\` — 원본 기획안
- \`docs/ROADMAP_100.md\`, \`config/roadmap.json\` — 100단계 작업 목록
- \`docs/OPERATOR_SETTINGS.md\` — 사용자 선택 사항 및 로컬 설정 화면
- \`docs/FEATURE_SCOPE.md\` — 필수/선택 기능 구분
- \`docs/STATUS.md\` — 구현/미구현/예약 현황
- \`src/ai_broadcaster/session.py\` — 모의 방송 상태 머신
- \`src/ai_broadcaster/platform_config.py\` — 플랫폼 승인 제어

## 새 기능: 무료 로컬 AI 응답 어댑터

`src/ai_broadcaster/local_llm.py`는 **설치된 로컬 Ollama만 사용**하는 응답 생성기입니다. 설치나 실행은 운영자 승인 전까지 하지 않으며, 모의 HTTP 테스트만 자동으로 진행합니다. `docs/LOCAL_LLM.md` 참조.
