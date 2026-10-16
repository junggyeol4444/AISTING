param(
    [Parameter(Mandatory=$true)]
    [string] $ExistingProject
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ExistingProject).Path
# Build only the separate verified local copy; never write build files into
# the user's original checkout, even when the entry point exists there.
$marker = Join-Path $root '.aisting_local_copy_provenance.json'
if (!(Test-Path -LiteralPath $marker -PathType Leaf)) {
    throw '원본 폴더에서는 빌드하지 않습니다. 검증된 로컬 사본 출처 기록이 필요합니다.'
}
if (Test-Path -LiteralPath (Join-Path $root '.git')) {
    throw 'Git 체크아웃 원본은 빌드하지 않습니다. 별도 사본을 선택하세요.'
}
$provenance = Get-Content -LiteralPath $marker -Raw -Encoding UTF8 | ConvertFrom-Json
if ($provenance.purpose -ne 'local copy of EXISTING AISTING, no github write' -or
    $provenance.desktop_git_blob_sha -ne 'a5df12a74a27a5a50657da9c968253859b98b8ed') {
    throw '검증된 기존 프로그램 로컬 사본 기록이 아닙니다.'
}
$moduleNames = @(
    'src/ai_broadcaster/original_plan_studio.py',
    'src/ai_broadcaster/original_plan_tts.py',
    'src/ai_broadcaster/original_plan_obs.py',
    'src/ai_broadcaster/original_plan_readiness.py',
    'src/ai_broadcaster/original_plan_ws.py',
    'src/ai_broadcaster/original_plan_conversation.py',
    'src/ai_broadcaster/original_plan_avatar.py',
    'src/ai_broadcaster/original_plan_frontend.py', # v25 official renderer integration retained
    'src/ai_broadcaster/original_plan_config_io.py',
    'src/ai_broadcaster/original_plan_persona_store.py'
)
foreach ($module in $moduleNames) {
    if (!(Test-Path -LiteralPath (Join-Path $root $module) -PathType Leaf)) {
        throw "수정 모듈이 없습니다. 기존 로컬 사본에 v26 패치를 먼저 적용하세요: $module"
    }
}
if (!(Get-ChildItem -LiteralPath (Join-Path $root 'src/ai_broadcaster') -Filter 'desktop.py.before-original-plan-*.bak' -File)) {
    throw '원본 desktop.py 백업이 없습니다. 안전한 패치 적용 여부를 확인하세요.'
}
if (!(Get-ChildItem -LiteralPath (Join-Path $root 'src/ai_broadcaster') -Filter 'offline_settings.py.before-original-plan-*.bak' -File)) {
    throw '원본 offline_settings.py 백업이 없습니다. 안전한 패치 적용 여부를 확인하세요.'
}
$entry = Join-Path $root 'scripts\run_desktop.py'
if (!(Test-Path -LiteralPath $entry)) { throw '기존 AISTING scripts\run_desktop.py를 찾을 수 없습니다.' }
# v13: verify every preserved original file and exact patched desktop/modules
# BEFORE invoking PyInstaller. A provenance marker alone is insufficient.
$audit = Join-Path $PSScriptRoot 'audit_local_patch_preservation.py'
if (!(Test-Path -LiteralPath $audit -PathType Leaf)) {
    throw 'v26 기존 파일 보존 감사 도구가 없습니다. 빌드를 중단합니다.'
}
& python $audit --source $root
if ($LASTEXITCODE -ne 0) {
    throw '기존 AISTING 사본 보존 감사 실패. 빌드를 시작하지 않습니다.'
}
Push-Location $root
try {
    python -c 'import tkinter; import PyInstaller' 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Python/Tkinter/PyInstaller가 설치되어 있지 않습니다. 자동 설치하지 않습니다.'
    }
    $requirements = @(
        'config', 'docs', 'logs/STAGE100_FINAL_VALIDATION.txt',
        'logs/STAGE100_UNITTEST.log'
    )
    foreach ($item in $requirements) {
        if (!(Test-Path -LiteralPath $item)) {
            throw "기존 원본에 포함해야 할 자료가 없습니다: $item"
        }
    }
    # Keep the user's prior dist/AISTING.exe and original build artifacts intact.
    # This builds a new EXE from the *existing patched* desktop.py.
    # Never overwrite a prior revision build. Reject an existing output path.
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fffffff'
    $out = Join-Path $root ("dist-local-revision-v26-" + $stamp)
    $work = Join-Path $root ("build-local-revision-v26-" + $stamp)
    if ((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $work)) {
        throw '새 빌드 경로가 이미 존재합니다. 기존 산출물을 덮어쓰지 않습니다.'
    }
    $arguments = @(
        '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--name', 'AISTING', '--paths', 'src',
        '--distpath', $out, '--workpath', $work, '--specpath', $work,
        '--add-data', 'config;config', '--add-data', 'docs;docs',
        '--add-data', 'logs/STAGE100_FINAL_VALIDATION.txt;logs',
        '--add-data', 'logs/STAGE100_UNITTEST.log;logs',
        'scripts/run_desktop.py'
    )
    & python @arguments
    if ($LASTEXITCODE -ne 0) { throw '기존 AISTING Windows EXE 빌드 실패' }
    $exe = Join-Path $out 'AISTING.exe'
    if (!(Test-Path -LiteralPath $exe)) { throw '수정된 EXE 빌드 결과가 존재하지 않습니다' }
    Write-Host "기존 AISTING 소스를 수정해 만든 Windows 실행 파일: $exe"
    Write-Host '기존 dist/AISTING.exe는 변경하지 않습니다.'
    Write-Host 'Windows 빌드만으로 실제 AI·음성·Live2D·OBS 연동을 성공 판정하지 않습니다.'
} finally { Pop-Location }
