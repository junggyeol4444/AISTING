# AISTING v88 — 원본 087 네이버 카페 공식 연동 검토 (오프라인 사전 점검)

## 원본 요구 및 제약

- `docs/ORIGINAL_PLAN.txt` 5부 5-2의 **공식 API 우선**·계정 및 권한 확인·보조 브라우저 방식 주의, 원본 `docs/ROADMAP_100.md`의 087 항목을 보존한다.
- 실제 API는 현재 지원 여부/엔드포인트/글쓰기 권한/정책·요청 형식을 **조회하거나 검증하지 않았다**. 과거 기획안에서 가능하다고 적은 내용도 현행 API 제공의 증거로 사용하지 않는다.
- GitHub, 모든 외부 서버, 네이버 로그인/계정/토큰/카페 ID, 브라우저 자동화, 실제 게시, OBS/실방송, 사용자 PC·음성 수집, 승인 없는 설치를 **하지 않았다**. 실제 공식 API 연동 및 Windows 검증/최종 승인은 `pending`이다.

## 이번 실제 구현

- `src/ai_broadcaster/offline_naver_cafe_review.py`를 추가했다. 기존 084 `PrebroadcastNoticeDraft`를 재사용하여 *검토 전용* 제목·본문·KST 일치 검사, 길이·제어 문자·멘션/URL 입력 차단, 이전 게시/예약 여부 거부를 실행한다.
- `CafeOfficialApiReview.to_report_json()`은 **API HTTP 요청 형식이 아니라 오프라인 사전 점검 자료**다. `official_api_capability`, `current_terms_and_scope`, `cafe_write_permission`은 모두 `unverified`; `credentials`, `cafe_target`은 null; `network_enabled`, `browser_automation_enabled`, `api_payload_ready`, `published`는 false로 고정한다. 제목 100자, 본문 5000자는 단지 **이 구현의 로컬 검토 제한**이며 네이버 공식 API 한도가 아니다.
- `네이버 카페 공식 연동 검토` 탭에서 운영자가 `084 방송 전 공지 초안`을 만들어 둔 경우에만 보고서를 수동 표시한다. 초안·주제·시간·설정에 변화가 발생하면 이전 보고서를 무효화하거나 검토를 거절하며 저장·전송하지 않는다.
- 계정이나 게시 대상, 카페 주소를 방송 플랫폼 선택으로 자동 유추하지 않는다. 본 단계에서는 연동과 게시를 위한 외부 전송 코드는 존재하지 않는다.

## 검증·한계

- 신규 `tests/test_offline_naver_cafe_review.py`: **23/23 PASS** (형식·상태·원본 변조·위험 문자·입력 유효성·무접속·무파일 변경).
- GUI `scripts/gui_offline_naver_cafe_review_smoke.py`: **PASS** (Linux 가상 Tkinter). 기존 GUI 회귀 85개 포함 **86/86 PASS**, 다만 Windows 실행과는 다르다.
- 전체 자동 테스트 1658개 통과, Python 구문 검사와 별도 압축 해제 후 검증은 `logs/STAGE88_FINAL_VALIDATION.txt` 참고.
- 사용자 별도 확인: 현행 네이버 공식 문서, 인증/글쓰기 API 지원 범위·약관, 카페 게시판 권한, 글 제목·본문 형식, 게시 빈도·중복·개인정보·저작권·실기기 성능. 사용자 명시적 승인 이후에만 실제 연동을 별도 개발/검증할 수 있다.
- 원본 087 `[ ]`, `config/roadmap.json`의 087 `pending`, 010 최종 승인 `pending`을 유지한다. **코드 개발 도달 범위 87/100**은 실제 제품 완성도/실제 카페 연동 성공을 뜻하지 않는다.
