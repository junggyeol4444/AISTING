"""Update an EXISTING AISTING source tree (never creates a new project).

This script refuses missing/mismatched source and preserves the original file.
It NEVER accesses GitHub, installs dependencies, or starts broadcasting.
Default is --check: no writes. Explicit --apply only after user inspection.

Verified original baselines (GitHub main, read-only):
 desktop.py a5df12a74a27a5a50657da9c968253859b98b8ed
 offline_settings.py 769ea22a59b490d9eeb27913aa569550f3b57da3.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

BASELINE_DESKTOP_SHA = 'a5df12a74a27a5a50657da9c968253859b98b8ed'
BASELINE_OFFLINE_SHA = '769ea22a59b490d9eeb27913aa569550f3b57da3'
SOURCE_REL = Path('src/ai_broadcaster/desktop.py')
OFFLINE_SETTINGS_REL = Path('src/ai_broadcaster/offline_settings.py')
MODULE_REL = Path('src/ai_broadcaster/original_plan_studio.py')
MODULE_SOURCE = Path(__file__).resolve().parent / 'payload' / MODULE_REL
EXTRA_MODULES = (
    Path('src/ai_broadcaster/original_plan_tts.py'),
    Path('src/ai_broadcaster/original_plan_obs.py'),
    Path('src/ai_broadcaster/original_plan_readiness.py'),
    Path('src/ai_broadcaster/original_plan_ws.py'),
    Path('src/ai_broadcaster/original_plan_conversation.py'),
    Path('src/ai_broadcaster/original_plan_avatar.py'),
    Path('src/ai_broadcaster/original_plan_frontend.py'),
    Path('src/ai_broadcaster/original_plan_config_io.py'),
    Path('src/ai_broadcaster/original_plan_persona_store.py'),
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    found = text.count(old)
    if found != 1:
        raise ValueError(f'기존 AISTING {label} 코드 확인 실패 (일치 {found}개). 강제 수정하지 않습니다.')
    return text.replace(old, new, 1)


def modify_existing_desktop(src: str) -> str:
    """Surgical changes to EXISTING application. All diagnostic pages remain."""
    r = replace_once
    src = r(src,
        'from .persona_modes import chosen_persona\n',
        'from .persona_modes import chosen_persona\n'
        'from .offline_settings import active_persona\n'
        'from .original_plan_studio import OriginalPlanStudio\n',
        'integration imports')
    src = r(src,
        'self.title("AISTING | 오프라인 AI 방송인 개발본")',
        'self.title("AISTING | 내 AI 방송인")', 'window title')
    src = r(src,
        'self.geometry("860x720")',
        'self.geometry("960x740")', 'window size')
    src = r(src,
        'self.minsize(760, 625)',
        'self.minsize(840, 640)', 'minimum size')
    src = r(src,
        'style.configure("TNotebook.Tab", padding=(12, 7), font=("Malgun Gothic", 10))',
        '# Keep the 100 development pages reachable without displaying 100 tabs.\n'
        '        style.layout("AISTING.TNotebook.Tab", [])\n'
        '        style.configure("AISTING.TNotebook", background="#F4F7FB")',
        'operator notebook style')
    src = r(src,
        'self._tab_nav = tk.StringVar(value="방송 설정")',
        'self._tab_nav = tk.StringVar(value="방송인 홈")', 'default start page')
    src = r(src,
        'navigation.pack(fill="x", pady=(0, 5))\n        ttk.Label(navigation, text="화면 이동").pack(side="left")',
        'navigation.pack(fill="x", pady=(0, 8))\n'
        '        for name in ("방송인 홈", "내 캐릭터", "방송 설정", "시청자 채팅 연습", "아바타 미리보기"):\n'
        '            ttk.Button(navigation, text=name, command=lambda page=name: self._goto_page(page)).pack(side="left", padx=(0, 4))\n'
        '        ttk.Label(navigation, text="전체 도구").pack(side="left", padx=(10, 0))',
        'compact everyday navigation')
    src = r(src,
        'tabs = ttk.Notebook(main)\n        self._tabs = tabs',
        'tabs = ttk.Notebook(main, style="AISTING.TNotebook")\n        self._tabs = tabs',
        'notebook widget')
    src = r(src,
        'settings = ttk.Frame(tabs)\n        rehearsal = ttk.Frame(tabs, padding=12)',
        'studio = ttk.Frame(tabs, padding=8)\n'
        '        character_tab = ttk.Frame(tabs, padding=14)\n'
        '        settings = ttk.Frame(tabs)\n'
        '        rehearsal = ttk.Frame(tabs, padding=12)',
        'existing studio & character pages')
    src = r(src,
        'for tab, label in ((settings, "방송 설정"), (rehearsal, "시청자 채팅 연습"),',
        'for tab, label in ((studio, "방송인 홈"), (character_tab, "내 캐릭터"),\n'
        '                           (settings, "방송 설정"), (rehearsal, "시청자 채팅 연습"),',
        'page registry')
    src = r(src,
        'self._settings_canvas = settings_canvas\n        self._build_settings(settings_body)',
        'self._settings_canvas = settings_canvas\n'
        '        self._build_settings(settings_body, character_tab)',
        'settings / character editor wiring')
    src = r(src,
        'settings_canvas = tk.Canvas(settings, highlightthickness=0, borderwidth=0)',
        'self._settings_footer = ttk.Frame(settings)\n'
        '        self._settings_footer.pack(side="bottom", fill="x")\n'
        '        settings_canvas = tk.Canvas(settings, highlightthickness=0, borderwidth=0)',
        'pinned preferences footer')
    src = r(src,
        'self._build_voice(voice_test)\n        self._build_avatar(avatar)\n        self._build_local_operation(local_operation)',
        'self._build_voice(voice_test)\n'
        '        self._build_avatar(avatar)\n'
        '        self._original_studio = OriginalPlanStudio(studio, self)\n'
        '        self._build_local_operation(local_operation)',
        'studio initialization')
    src = r(src,
        'self._speech_cancel.set()\n        self._speech_pending.clear()',
        'self._original_studio.close()\n'
        '        self._speech_cancel.set()\n'
        '        self._speech_pending.clear()',
        'studio shutdown')
    src = r(src,
        '    def _section(self, parent, title):',
        '    def _goto_page(self, label: str) -> None:\n'
        '        for page in self._tabs.tabs():\n'
        '            if self._tabs.tab(page, "text") == label:\n'
        '                self._tabs.select(page)\n'
        '                self._tab_nav.set(label)\n'
        '                return\n'
        '        raise ValueError("화면 없음: " + label)\n\n'
        '    def _section(self, parent, title):',
        'navigation implementation')
    src = r(src,
        'def _build_settings(self, tab) -> None:',
        'def _build_settings(self, tab, character_tab=None) -> None:',
        'settings signature')
    src = r(src,
        'character = self._section(tab, "5. AI 방송인 캐릭터 (기본값 / 직접 만들기)")',
        'character = self._section(character_tab if character_tab is not None else tab,\n'
        '                                  "AI 방송인 캐릭터 · 최초 확정 저장 후 자동 불러오기")',
        'separate character editor')
    src = r(src,
        'ttk.Label(character, textvariable=self._persona_preview, justify="left",\n'
        '                  wraplength=715).pack(anchor="w", pady=(5, 0))',
        'ttk.Label(character, textvariable=self._persona_preview, justify="left",\n'
        '                  wraplength=715).pack(anchor="w", pady=(5, 0))\n'
        '        ttk.Button(character, text="캐릭터 확정·저장",\n'
        '                   command=self._save_character_identity).pack(anchor="e", pady=(10, 0))',
        'separate committed identity button')
    src = r(src,
        'ttk.Button(tab, text="설정 PC에 저장", command=self._save).pack(anchor="e")',
        'ttk.Button(self._settings_footer, text="방송 설정 저장 (캐릭터 제외)",\n'
        '                   command=self._save).pack(side="right", padx=12, pady=8)',
        'sticky settings save')
    src = r(src,
        '    def _current_persona(self) -> dict[str, str]:\n'
        '        """현재 GUI 모드의 실사용 캐릭터. 기본값은 직접 입력을 무시한다."""\n'
        '        code = PERSONA_MODES.get(self._persona_mode.get())\n'
        '        return chosen_persona(code, {key: entry.get() for key, entry in self._persona.items()})',
        '    def _current_persona(self) -> dict[str, str]:\n'
        '        """Only committed persona is used for real AI and live avatar."""\n'
        '        return active_persona(self.settings)\n\n'
        '    def _save_character_identity(self) -> None:\n'
        '        try:\n'
        '            mode = PERSONA_MODES[self._persona_mode.get()]\n'
        '            draft = {key: entry.get().strip() for key, entry in self._persona.items()}\n'
        '            chosen_persona(mode, draft)\n'
        '            from .original_plan_persona_store import commit_character_identity\n'
        '            updated = commit_character_identity(self.settings, mode, draft)\n'
        '        except (OSError, ValueError, KeyError, RuntimeError) as exc:\n'
        '            messagebox.showerror("캐릭터 저장 실패", str(exc), parent=self)\n'
        '            return\n'
        '        self.settings = updated\n'
        '        self._original_studio._refresh_persona()\n'
        '        self._status.set("캐릭터 확정 저장 완료 · 재실행 시 자동 사용")',
        'saved identity isolation')
    src = r(src,
        '        try:\n'
        '            data["persona_mode"] = PERSONA_MODES[self._persona_mode.get()]\n'
        '            # 기본 모드로 돌려도 사용자가 써 둔 직접 제작 초안은 안전하게 보존한다.\n'
        '            data["persona"] = {key: item.get().strip() for key, item in self._persona.items()}\n'
        '        except KeyError:\n'
        '            messagebox.showerror("캐릭터 설정", "올바른 캐릭터 방식을 선택해 주세요.", parent=self)\n'
        '            return',
        '        # Ordinary broadcast settings Save never commits draft identity.\n'
        '        data["persona_mode"] = self.settings["persona_mode"]\n'
        '        data["persona"] = deepcopy(self.settings["persona"])',
        'general Save isolation')
    src = r(src,
        '        try:\n'
        '            save_settings(data)\n'
        '        except (OSError, ValueError) as exc:\n'
        '            messagebox.showerror("설정 저장 오류", str(exc), parent=self)\n'
        '            return\n'
        '        self.settings = data',
        '        try:\n'
        '            from .original_plan_persona_store import save_broadcast_without_persona\n'
        '            data = save_broadcast_without_persona(self.settings, data)\n'
        '        except (OSError, ValueError, RuntimeError) as exc:\n'
        '            messagebox.showerror("설정 저장 오류", str(exc), parent=self)\n'
        '            return\n'
        '        self.settings = data\n'
        '        self._original_studio._refresh_persona()',
        'broadcast save preserves latest confirmed identity')
    return src


def modify_existing_offline_settings(src: str) -> str:
    """Surgically route the original general settings writer through v18's lock.

    The original save_settings signature remains unchanged. Ordinary saves
    preserve the *latest confirmed on-disk persona*, including legacy data.
    A character may only change via the dedicated confirmation operation.
    """
    old = '''def save_settings(value: dict[str, Any], path: Path | None = None) -> Path:
    target = path if path is not None else settings_file()
    clean = validate_settings(value)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A fixed settings.tmp path can overwrite an unrelated file (or follow a
    # symlink) and concurrent saves can corrupt each other's temporary data.
    # Create a private, unique sibling and replace only after a full flush.
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(clean, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
'''
    new = '''def save_settings(value: dict[str, Any], path: Path | None = None) -> Path:
    """Save ordinary settings under the same lock as character confirmation.

    A legacy caller may hold a stale character draft. It must not silently
    commit that draft or overwrite a newer character confirmed elsewhere.
    """
    target = path if path is not None else settings_file()
    from .original_plan_persona_store import save_broadcast_without_persona
    # Reading before the lock is intentional: the merge routine acquires
    # the OS lock and rejects non-persona changes that raced this read.
    observed = load_settings(target)
    if not isinstance(value, dict):
        raise ValueError('방송 설정은 JSON 객체여야 합니다.')
    clean = deepcopy(value)
    # Even an invalid unsaved character draft is outside general Save.
    clean['persona_mode'] = observed['persona_mode']
    clean['persona'] = deepcopy(observed['persona'])
    clean = validate_settings(clean)
    save_broadcast_without_persona(observed, clean, path=target)
    return target
'''
    return replace_once(src, old, new, 'actual offline_settings.save_settings')


def require_verified_local_copy(root: Path, original: bytes) -> None:
    """Fail closed: never patch a checked-out original by accident.

    The marker is created by prepare_local_source_copy.py after an exact copy
    and verification. This is a guard against accidental original-tree edits,
    not a cryptographic proof against a maliciously forged marker.
    """
    marker = root / '.aisting_local_copy_provenance.json'
    if marker.is_symlink() or not marker.is_file():
        raise ValueError(
            '기존 원본 직접 패치를 금지합니다. '
            'prepare_local_source_copy.py로 검증된 별도 로컬 사본을 만든 뒤 적용하세요.'
        )
    try:
        record = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('로컬 사본 출처 기록이 손상되었습니다. 적용하지 않습니다.') from exc
    if not isinstance(record, dict) or record.get('purpose') != 'local copy of EXISTING AISTING, no github write':
        raise ValueError('검증된 기존 프로그램 로컬 사본 기록이 아닙니다.')
    if record.get('desktop_git_blob_sha') != git_blob_sha(original):
        raise ValueError('로컬 사본 기록과 desktop.py 원본 버전이 다릅니다.')
    checks = record.get('original_required_sha256')
    if not isinstance(checks, dict):
        raise ValueError('로컬 사본 필수 파일 해시 기록이 없습니다.')
    required = (
        'src/ai_broadcaster/desktop.py', 'scripts/run_desktop.py',
        'docs/ORIGINAL_PLAN.txt', 'docs/ROADMAP_100.md',
        'config/roadmap.json', 'docs/REQUIREMENTS.md', 'docs/STATUS.md',
    )
    for name in required:
        digest = checks.get(name)
        target = root / name
        if (not isinstance(digest, str) or len(digest) != 64
                or target.is_symlink() or not target.is_file()
                or hashlib.sha256(target.read_bytes()).hexdigest() != digest):
            raise ValueError('로컬 사본 필수 파일 무결성 불일치: ' + name)
    if (root / '.git').exists() or (root / '.git').is_symlink():
        raise ValueError('Git 메타데이터가 있는 소스는 원본일 수 있어 패치하지 않습니다.')
    # v12: the seven required files alone do not protect existing user
    # settings, memory databases, tests, and the other legacy source files.
    # Reject old manifests rather than claiming whole-tree preservation.
    inventory = record.get('original_all_sha256')
    if (not isinstance(inventory, dict) or not inventory
            or record.get('all_existing_files_verified') != len(inventory)):
        raise ValueError('전체 기존 파일 무결성 기록이 없는 사본입니다. v12 사본을 다시 만드세요.')
    from pathlib import PurePosixPath
    for rel, expected in inventory.items():
        if (not isinstance(rel, str) or not rel or '\\' in rel or '\x00' in rel
                or PurePosixPath(rel).is_absolute()
                or any(piece in ('', '.', '..') for piece in rel.split('/'))
                or rel == '.aisting_local_copy_provenance.json'
                or rel.startswith('.git/')
                or not isinstance(expected, str) or len(expected) != 64
                or any(c not in '0123456789abcdef' for c in expected)):
            raise ValueError('전체 기존 파일 무결성 기록 형식이 올바르지 않습니다.')
    # v14: preserve directory layout as well, including empty directories.
    original_dirs = record.get('original_all_directories')
    if (not isinstance(original_dirs, list)
            or record.get('all_existing_directories_verified') != len(original_dirs)
            or len(set(original_dirs)) != len(original_dirs)):
        raise ValueError('전체 기존 폴더 기록이 없는 사본입니다. v14 사본을 다시 만드세요.')
    for rel in original_dirs:
        if (not isinstance(rel, str) or not rel or '\\' in rel or '\x00' in rel
                or PurePosixPath(rel).is_absolute()
                or any(piece in ('', '.', '..') for piece in rel.split('/'))
                or rel == '.git' or rel.startswith('.git/')):
            raise ValueError('전체 기존 폴더 기록 형식이 올바르지 않습니다.')
    # Enumerate the entire actual copy and reject unrecorded, removed,
    # symlinked or modified files. No user data is read into logs.
    current: dict[str, str] = {}
    current_dirs: set[str] = set()
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(folder) / name
            rel = path.relative_to(root).as_posix()
            if rel == '.aisting_local_copy_provenance.json':
                if path.is_symlink() or not path.is_file():
                    raise ValueError('로컬 사본 출처 기록이 링크/특수 파일입니다.')
                continue
            kind = path.lstat().st_mode
            if stat.S_ISLNK(kind) or not (stat.S_ISREG(kind) or stat.S_ISDIR(kind)):
                raise ValueError('로컬 사본에 링크/특수 파일이 존재합니다: ' + rel)
            if stat.S_ISDIR(kind):
                current_dirs.add(rel)
            if stat.S_ISREG(kind):
                current[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    if current_dirs != set(original_dirs):
        raise ValueError('로컬 사본 전체 폴더 목록이 변경되었습니다.')
    if current != inventory:
        changed = sorted(set(current) ^ set(inventory) | {
            name for name in set(current) & set(inventory)
            if current[name] != inventory[name]
        })
        raise ValueError('로컬 사본 전체 파일 무결성 불일치: ' + ', '.join(changed[:5]))


def apply_existing_source(root: Path, *, write: bool = False) -> Path:
    if root.is_symlink():
        raise ValueError('원본 소스 폴더가 심볼릭 링크입니다. 안전을 위해 중단합니다.')
    root = root.expanduser().resolve(strict=True)
    if (root / 'src').is_symlink() or (root / 'src/ai_broadcaster').is_symlink():
        raise ValueError('원본 코드 경로에 심볼릭 링크가 있습니다. 중단합니다.')
    srcpath = root / SOURCE_REL
    offline_path = root / OFFLINE_SETTINGS_REL
    outputmodule = root / MODULE_REL
    if not root.is_dir() or not srcpath.is_file() or srcpath.is_symlink():
        raise ValueError('기존 AISTING desktop.py 원본 파일이 없습니다. 새 프로젝트를 만들지 않습니다.')
    if (not offline_path.is_file() or offline_path.is_symlink()
            or git_blob_sha(offline_path.read_bytes()) != BASELINE_OFFLINE_SHA):
        raise ValueError('기존 offline_settings.py 원본 SHA가 다릅니다. 사용자 설정 코드를 강제 수정하지 않습니다.')
    if not (root / 'scripts/run_desktop.py').is_file():
        raise ValueError('기존 AISTING Windows 실행 진입점이 없습니다.')
    target_modules = (MODULE_REL, *EXTRA_MODULES)
    for relpath in target_modules:
        dest = root / relpath
        if dest.exists() or dest.is_symlink():
            raise ValueError('추가 모듈이 이미 존재합니다. 덮어쓰지 않습니다: ' + str(relpath))
        if not (Path(__file__).resolve().parent / 'payload' / relpath).is_file():
            raise ValueError('수정 패키지 파일이 없습니다: ' + str(relpath))
    original = srcpath.read_bytes()
    original_sha = git_blob_sha(original)
    if original_sha != BASELINE_DESKTOP_SHA:
        raise ValueError(
            'AISTING 원본 main 소스가 확인한 버전과 다릅니다. '
            f'기존 버전 {original_sha}; 기대 {BASELINE_DESKTOP_SHA}. 수정 중단'
        )
    orig_text = original.decode('utf-8')
    mod_text = modify_existing_desktop(orig_text)
    offline_original = offline_path.read_bytes()
    offline_text = modify_existing_offline_settings(offline_original.decode('utf-8'))
    compile(mod_text, str(srcpath), 'exec')
    compile(offline_text, str(offline_path), 'exec')
    for relpath in target_modules:
        file = Path(__file__).resolve().parent / 'payload' / relpath
        compile(file.read_text('utf-8'), str(root / relpath), 'exec')
    print('기존 main desktop.py 확인:', original_sha)
    print('기존 main offline_settings.py 확인:', BASELINE_OFFLINE_SHA)
    print('기존 창 유지 · 기존 기능/100개 검증 화면 보존 · 새 스튜디오 탭 삽입')
    print('캐릭터 확정 저장 분리 · 미저장 초안 실사용 금지')
    print('GitHub 접근·설치·AI 실제 요청·외부 송출 없음')
    if not write:
        # The original checkout may be inspected read-only for anchor
        # compatibility, but only a verified copy can ever be written.
        marker = root / '.aisting_local_copy_provenance.json'
        if marker.exists() or marker.is_symlink():
            require_verified_local_copy(root, original)
            print('전체 기존 파일 해시 확인 완료 · 이 로컬 사본은 --apply 전제 조건 충족')
        else:
            print('원본 코드 위치 검사만 통과 · 검증된 로컬 사본이 아니므로 --apply는 차단됩니다.')
        print('검토 모드: 어떤 파일도 수정하지 않았습니다. --apply 사용 시에만 변경됩니다.')
        return srcpath
    # The SHA check above is necessary but insufficient: the same original
    # desktop.py is also present in the user's live source checkout.
    # Only the separately verified local development copy is writable.
    require_verified_local_copy(root, original)
    nonce = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup_desktop = srcpath.with_name(srcpath.name + '.before-original-plan-' + nonce + '.bak')
    backup_offline = offline_path.with_name(offline_path.name + '.before-original-plan-' + nonce + '.bak')
    # Back up both real existing source files before any source replacement.
    for path, content in ((backup_desktop, original), (backup_offline, offline_original)):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.read_bytes() != content:
            raise RuntimeError('기존 원본 소스 백업 검증 실패. 적용을 중단합니다: ' + str(path))
    staged: dict[Path, Path] = {}
    created: list[Path] = []
    replaced: list[tuple[Path, bytes]] = []
    try:
        for path, content in ((srcpath, mod_text.encode('utf-8')),
                              (offline_path, offline_text.encode('utf-8'))):
            with tempfile.NamedTemporaryFile('wb', dir=path.parent,
                                             prefix='.aisting-patch-', delete=False) as out:
                temp = Path(out.name)
                staged[path] = temp
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
            shutil.copymode(path, temp)
        if srcpath.read_bytes() != original or offline_path.read_bytes() != offline_original:
            raise RuntimeError('기존 소스가 작업 중 변경되었습니다. 덮어쓰지 않습니다.')
        # New modules are staged before either existing source is replaced.
        for relpath in target_modules:
            dest = root / relpath
            origin = Path(__file__).resolve().parent / 'payload' / relpath
            with dest.open('xb') as handle:
                created.append(dest)
                handle.write(origin.read_bytes())
        for path, before in ((offline_path, offline_original), (srcpath, original)):
            if path.read_bytes() != before:
                raise RuntimeError('기존 소스가 교체 직전 변경되었습니다: ' + str(path))
            os.replace(staged[path], path)
            staged.pop(path)
            replaced.append((path, before))
    except Exception as exc:
        rollback_errors = []
        for path, content in reversed(replaced):
            try:
                with tempfile.NamedTemporaryFile('wb', dir=path.parent,
                                                 prefix='.aisting-rollback-', delete=False) as out:
                    restore = Path(out.name)
                    out.write(content)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(restore, path)
                if path.read_bytes() != content:
                    raise RuntimeError('원본 복원 후 내용 불일치')
            except Exception as rollback_exc:
                rollback_errors.append(str(path) + ': ' + str(rollback_exc))
        if not rollback_errors:
            for new_path in created:
                new_path.unlink(missing_ok=True)
        if rollback_errors:
            raise RuntimeError('부분 적용 후 자동 복원 실패. 백업에서 수동 복원 필요: '
                               + '; '.join(rollback_errors)) from exc
        raise
    finally:
        for temp in staged.values():
            temp.unlink(missing_ok=True)
    print('기존 소스 변경:', srcpath, offline_path)
    print('원본 백업:', backup_desktop, backup_offline)
    print('실제 방송 코어/음성/OBS 연결 모듈:', ', '.join(map(str, target_modules)))
    return srcpath


def main() -> int:
    parser = argparse.ArgumentParser(description='Original AISTING local source revision')
    parser.add_argument('--source', type=Path, required=True,
                        help='기존 AISTING 프로젝트의 소스 폴더')
    parser.add_argument('--apply', action='store_true', help='원본 백업 후 기존 프로그램 수정')
    args = parser.parse_args()
    try:
        apply_existing_source(args.source, write=args.apply)
    except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
        print('수정 중단:', str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
