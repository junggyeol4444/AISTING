## 89. 2026-10-22 — Windows 저장 오류 실검사 통과·AI→Cubism→OBS 실측 지연 구간 개발

### 이번 회차 개발·실증 판정
- 시작 HEAD `1e7097fa8b021226a004d8fe795b609f9a6aef92`. 기존 인수인계 1~88절, 과거 모든 부록 21개, ORIGINAL_PLAN.txt·ROADMAP_100.md·config/roadmap.json 원문과 기존 main 소스를 재확인. 본 절은 기존 원문을 삭제/축약하지 않고 뒤에 추가.
- [88절 Windows CI 39695199304](https://github.com/junggyeol4444/AISTING/actions/runs/39695199304) 최종 **success**, 5 jobs 모두 success: windows-exe, obs-real-readonly, twitch-public-readonly, korean-public-chat-readonly, ollama-real-local-e2e. 88절 저장 오류 수정 Windows 회귀 및 네이티브 EXE/Tk GUI 빌드 통과. 실제 OBS는 읽기 전용 검사이며 TTS→Cubism→OBS 동일 발화 실증을 의미하지 않음.
- [88절 전체 검증 39695199091](https://github.com/junggyeol4444/AISTING/actions/runs/39695199091) **success**: 2,526개 테스트, 2개 skip, 실패 0.
- [88절 실제 Ollama 500건 39695199416](https://github.com/junggyeol4444/AISTING/actions/runs/39695199416)은 본 기록 시점 진행 중. 87절 실제 500건 [39689925496](https://github.com/junggyeol4444/AISTING/actions/runs/39689925496)은 최종 workflow 성공 상태지만 1~3초 목표 성공을 뜻하지 않음. 실제 시청자 수백 명/24시간 송출 실증은 없음.
- 새 코드 `src/ai_broadcaster/original_plan_full_pipeline.py`: 기존 `prompt_started_at`·`prompt_finished_at` 및 공식 Cubism 입+RMS 실측 monotonic 표본, OBS 실제 입력 오디오 미터 monotonic 표본을 재사용하여 `OfficialChatObsEvidence`에 `local_roundtrip_seconds`, `first_cubism_audio_seconds`, `first_obs_audio_seconds` 추가. 앞선 모의 결과와 외부 인코더/시청자 응답은 `None`·`viewer_end_to_end_verified=False`로 유지; 추정이나 가짜 지연값 없음. 기존 원본 질문 1회·방송/녹화 금지·사용권·OBS read-only·실측 겹침 검사 유지. 구간별 시각은 실제 사용자 승인을 받아 실행할 때만 획득되는 계측 코드이며, 본 회차 실제 한국어 GPT-SoVITS 모델/OBS 동일 발화 실측 데이터는 획득하지 못함.
- `tests/test_aisting_official_chat_obs_pipeline.py`: 구간 지연 측정 결과의 구조·시각 범위 검사, 표본 없는 경우 미측정/시청자 미실증 유지 계약 검사 2개 추가. 단위테스트 모의 OBS는 실사용 증빙으로 계산하지 않음.

### 건드리지 않은 대상
- 모든 캐릭터·설정·성격·말투, 사용자의 SQLite 기억, 사용자 계정 OAuth, OBS 장면/송출/녹화, 음성 모델·참조 WAV, 로드맵 `pending`, 메인 프로그램 임의 토큰 길이/keep_alive, 기존 원본 소스 기능 삭제 없음. 다른 프로젝트·예약·Drive·브랜치·force push·롤백 변경 없음.

### 미완료·다음 개발
- 실제 권리 있는 한국어 GPT-SoVITS WAV→공식 Live2D Cubism 입 움직임→OBS 동일 발화 오디오/영상 직접 확인 및 증거, 플랫폼 4개 수백 명 실제 채팅 무누락, 실제 24시간 방송 안전성과 재연결, 최종 시청자 E2E 1~3초는 여전히 미완료. 합성 메시지 500/500 처리 ≠ 실제 시청자 500명, OBS 읽기 ≠ 방송 인코딩/청취.
- 이어서 본 89절 코드 HEAD의 전체 GitHub 회귀·Windows EXE/GUI/OBS/로컬 Ollama CI 최종 결과를 수집, 실패 원인 수정 후 같은 전체 회귀를 재실행; 실제 로컬 모델/송출 단계에서 측정된 구간별 병목 개선, 기존 권리 확인·운영자 승인을 유지하여 실제 동일 발화의 오디오·영상 관측 코드를 계속 개발. 후속 90절 원문 append.
