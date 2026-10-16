# AISTING v14 — Windows 실제 원본 사본 확인 인계 (미실행)

이 문서는 사용자 PC에서만 확인할 절차입니다. 이 회차에는 Windows·실제 방송 프로그램을 실행하지 않았습니다. **사용자 승인 없는 설치/다운로드/로그인/음성 재생/송출/게시를 금지합니다.**

## 사본·보존 검사 (외부 방송 영향 없음)

1. 기존 AISTING 전체 원본 폴더를 그대로 보존하고, 현재 열려 있는 AISTING 프로그램/파일 편집기를 닫아 원본 파일이 복사 중 바뀌지 않게 합니다.
2. v14 패키지를 별도 폴더에 압축 해제합니다. `python verify_local_revision.py`로 패키지 무결성을 확인합니다.
3. `python prepare_local_source_copy.py --source "C:\\AISTING" --destination "C:\\AISTING_copy_v14"`를 실행하면 **읽기 전용 미리보기**만 합니다.
4. 사본 생성을 별도로 승인한 경우에만 위 명령 끝에 `--copy`를 붙입니다. 기존 원본 내부/상위 경로에 사본을 만들지 않습니다.
5. `python apply_to_existing_aisting.py --source "C:\\AISTING_copy_v14"`는 패치 위치를 **읽기 전용**으로 검사합니다. 별도 승인이 있으면 `--apply`로 **사본만** 수정합니다.
6. `python audit_local_patch_preservation.py --source "C:\\AISTING_copy_v14"`를 실행합니다.

**합격 기준:** 사본 기록에 기존 파일 SHA-256 전체 목록과 `original_all_directories`가 존재하고, 사본에 빈 폴더가 그대로 있으며, 패치 후 감사에서 `desktop_patch_exact_match`, `original_desktop_backup_verified`가 참이고 `baseline_existing_files_preserved`, `baseline_directories_preserved` 수치가 표시됩니다. 이는 파일 보존 검사 합격일 뿐 실제 AI 방송 합격이 아닙니다.

**실패 시 수집:** 실행 명령, 종료 코드, 오류 문구, Python 버전, Windows 버전, 원본·사본의 상대 경로와 폴더 개수, 해당 단계에서 나온 콘솔 로그를 기록합니다. `settings.json`, `conf.yaml`, 음성 원본, API 키, 토큰, 대화 기억 DB 내용은 공유하지 않습니다. 실패하면 원본을 수정하지 않고 중단합니다.

## 실제 기능 확인 (사용자 PC 전용·명시적 별도 승인 필요)

원본 7부 1단계의 실제 공식 Open-LLM-VTuber AI 한국어 대화·실제 TTS 음성·Live2D 입 움직임을 먼저 각각 확인해야 합니다. 2단계 GPT-SoVITS 한국어 참조 음성·모델 연결, 3단계 OBS 화면/오디오와 실제 플랫폼 채팅은 별개 증거가 필요합니다. 4~7단계 종료/스케줄/공지/장시간 운영은 그 이후 검증합니다. 합격은 실제 입력·출력·화면/오디오·로그를 사용자가 확인하는 것이며, 로컬 모의 검사/HTTP 200/초기 WebSocket 메시지/파일 존재만으로 합격하지 않습니다. 방송 시작·송출·게시·모델 학습은 이 문서가 승인하지 않습니다.
