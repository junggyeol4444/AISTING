# v76 · 원본 075 방송 송출 설정 연결 — 오프라인 검토 전용 초안

## 원본 요구 및 구현/미구현 구분

- 공식 100단계 항목: **075 방송 송출 설정 연결**. 외부 방송 송출/OBS 실제 설정 변경은 사용자 승인 없이 실행할 수 없어 **수동 검토 전용의 설정값 연결(메모리 초안)**만 구현함.
- 코드 개발 도달 범위 **75/100**은 실제 방송 송출 기능의 완료·품질 승인이나 Windows 실행 검증을 뜻하지 않음.
- `docs/ORIGINAL_PLAN.txt`, `config/roadmap.json`, 기존 저장 사용자 설정·캐릭터·목소리·아바타·플랫폼 선택은 수정하지 않음. 원본 010·075 모두 사용자 승인/실기기 검증 `pending`.

## 사용 방법

1. `방송 화면 구성 미리보기` 탭에서 기존 플랫폼/콘텐츠/캐릭터/음성/2D·3D 선택을 확인한다. 미선택·미구현 3D를 다른 선택으로 자동 변경하지 않는다.
2. `현재 선택으로 미리보기 갱신` → `음량·방송 화면 점검 (오프라인)` 순서로 수동 확인한다.
3. 정상적으로 화면 태그가 확인되면 **`송출 설정 초안 연결 (오프라인)`** 버튼을 누른다. 결과의 **'연결'은 메모리 상의 검증된 값들만 묶었다는 뜻**이며 실제 OBS·송출·장치 연결이 아니다.
4. `초안 JSON 보기`를 눌러 읽기 전용 검토 창에서 플랫폼 선택 순서, 640×360 가상 화면/콘텐츠/아바타, 설정상 음량/가상 문자 오버레이, 비활성 출력 플래그, 사용자 승인 대기를 살펴볼 수 있다. 파일 저장/클립보드 복사/계정 액세스 기능은 없다.
5. 선택·음량·가상 음성 상태·미리보기 변경 시 초안이 무효화되고 열린 검토 창도 닫힌다. 새 수동 점검과 새 초안 생성이 필요하다.

## 코드 구조/안전 원칙

- `src/ai_broadcaster/offline_broadcast_output_settings.py`: 불변 초안 `OfflineOutputSettingsDraft` + `prepare_offline_output_settings`.
- 이전 074단계 `BroadcastOutputAudit` 결과가 성공한 상태에서 **동일한 현재 Canvas/선택/설정음량의 재점검이 일치해야만** 초안 생성. 074단계 감사 구조에 가상 음성 경로 준비/진행 순번 메타데이터를 추가해 가상 경로가 감사 이후 달라진 경우도 거부.
- JSON `schema: aisting.offline_output_settings.review.v1`, `mode: offline_review_only`; `streaming_enabled`/`obs_connected`/`video_connected`/`audio_connected`/`account_connected` 모두 **false**, `destination` **null**. 동작 가능한 OBS 프로필/스트림 주소/스트림 키/API 토큰을 저장하거나 출력하지 않는다.
- `review_mapping()`은 검토용 새 데이터 사본만 반환. 사용자 settings.json 및 원본 설정 객체 변경 없음.
- 동작: **메모리와 로컬 Canvas 조회만**. 네트워크 요청/브라우저/OBS/소리·카메라/파일 쓰기/기본값 변경/백그라운드 스케줄러/자동 실행 없음.

## 자동 검증

- `tests/test_offline_broadcast_output_settings.py`: 18개 단위 시험. 정상/다중/미선택 플랫폼, 2D/3D·미선택, 미연결 음성 선택 유지, 0·100/잘못된 음량, 선행 점검 누락/오류, 손상 Canvas, 선택/설정 변경, 무음 문자 오버레이, 경로 변경 후 점검 무효화, 불변 객체/매핑 사본, 네트워크·프로세스·DB·파일 I/O 차단을 확인한다.
- `scripts/gui_offline_broadcast_output_settings_smoke.py`: Linux Xvfb의 실제 Tk에서 수동 순서 검사, 읽기 전용 JSON 창 열기/닫기, 음량 변경 시 창 무효화, 손상 태그 복구, 3D 자동대체 없음, 사용자 설정 비변경을 확인한다.
- 전체 기록: `logs/STAGE76_UNITTEST.log`, `logs/STAGE76_GUI_ALL.log`, `logs/STAGE76_SYNTAX.log`, `logs/STAGE76_FINAL_VALIDATION.txt`.

## 남은 사용자 직접 확인

OBS 및 실제 장면/방송 플랫폼 계정·자격 증명 연결, 물리 음량·음질·화면 화질·해상도·Windows 실기기/EXE, 실제 방송과 권리 검토, 최종 사용자 승인은 **전부 미구현·미검증·대기**. 다음 원본 **076 비공개 방송 테스트**도 승인 없는 실제 비공개 송출은 실행할 수 없으므로, 이후 단계는 오프라인에서 검증 가능한 부분과 실제 사용자 검증을 명확히 구분해야 한다.
