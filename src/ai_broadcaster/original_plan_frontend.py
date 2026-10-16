"""Open the *installed upstream* Open-LLM-VTuber Live2D frontend, never a mock.

The Windows AISTING desktop remains the operator program. Official WebGL is
shown inside a native Windows WebView2 window, never an external browser.
This module neither downloads nor installs a renderer and never starts a server.
Opening it is opt-in and may let upstream JavaScript connect to real LLM/TTS
services, use microphones, create history or fetch resources: warn before open.
A successful local HTTP response is NOT proof of rendering, lip sync, or audio.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import http.client
from pathlib import Path
import re
import importlib.util
import subprocess
import sys

OFFICIAL_HOST = '127.0.0.1'
OFFICIAL_PORT = 12393
OFFICIAL_URL = f'http://{OFFICIAL_HOST}:{OFFICIAL_PORT}/'
_MAX_HTML = 128 * 1024


class FrontendUnavailable(RuntimeError):
    """Not enough evidence that the installed official frontend is served."""


@dataclass(frozen=True)
class OfficialFrontendReadiness:
    url: str
    local_frontend: Path
    http_status: int
    content_type: str


def _regular_file(path: Path, *, max_size: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise FrontendUnavailable('공식 프로젝트의 필수 일반 파일이 없습니다: ' + str(path.name))
    if not 0 < path.stat().st_size <= max_size:
        raise FrontendUnavailable('공식 프런트엔드 파일 크기가 예상 범위를 벗어납니다.')


def inspect_installed_official_frontend(project: str | Path) -> Path:
    """Read-only preflight; never call run_server.py (can fetch submodules)."""
    if not str(project).strip():
        raise FrontendUnavailable('공식 Open-LLM-VTuber 설치 폴더를 선택하세요.')
    try:
        root = Path(project).expanduser().resolve(strict=True)
        if not root.is_dir() or (root / 'frontend').is_symlink():
            raise FrontendUnavailable('공식 프런트엔드 폴더가 없거나 심볼릭 링크입니다.')
        _regular_file(root / 'run_server.py', max_size=2_000_000)
        _regular_file(root / 'pyproject.toml', max_size=2_000_000)
        _regular_file(root / 'conf.yaml', max_size=2_000_000)
        frontend = root / 'frontend' / 'index.html'
        _regular_file(frontend, max_size=_MAX_HTML)
        with frontend.open('rb') as f:
            head = f.read(_MAX_HTML)
        if not re.search(rb'<html(?:\s|>)', head, flags=re.I):
            raise FrontendUnavailable('설치된 공식 frontend/index.html에 HTML 문서가 없습니다.')
        return frontend
    except (OSError, RuntimeError) as exc:
        if isinstance(exc, FrontendUnavailable):
            raise
        raise FrontendUnavailable('공식 프런트엔드 파일을 검사할 수 없습니다.') from exc


def probe_official_frontend(project: str | Path, *, operator_approved: bool = False,
                            timeout: float = 4.0) -> OfficialFrontendReadiness:
    """Probe actual localhost HTML; no redirects or external HTTP requests.

    Requires one-shot approval because the installed server may log requests.
    HTTP does not prove what binary occupies the local port or that WebGL works.
    """
    if operator_approved is not True:
        raise PermissionError('이번 공식 프런트엔드 로컬 접속 승인이 필요합니다.')
    if type(timeout) not in (int, float) or not (0.5 <= timeout <= 15):
        raise ValueError('HTTP 제한 시간이 올바르지 않습니다.')
    index = inspect_installed_official_frontend(project)
    connection = http.client.HTTPConnection(OFFICIAL_HOST, OFFICIAL_PORT, timeout=timeout)
    try:
        connection.request('GET', '/', headers={'Host': '127.0.0.1:12393',
                                                'Accept': 'text/html'})
        response = connection.getresponse()
        # Do not follow 3xx (including external-location redirects).
        if response.status != 200:
            raise FrontendUnavailable('공식 로컬 화면의 HTTP 응답이 200이 아닙니다: ' +
                                      str(response.status))
        content_type = response.getheader('Content-Type', '').split(';', 1)[0].strip().lower()
        if content_type != 'text/html':
            raise FrontendUnavailable('로컬 서버가 HTML 프런트엔드를 제공하지 않습니다.')
        if response.getheader('Content-Length'):
            try:
                size = int(response.getheader('Content-Length'))
            except ValueError as exc:
                raise FrontendUnavailable('HTTP Content-Length 값이 잘못됐습니다.') from exc
            if size > _MAX_HTML:
                raise FrontendUnavailable('로컬 프런트엔드 HTML이 검사 상한을 초과했습니다.')
        raw = response.read(_MAX_HTML + 1)
        if len(raw) > _MAX_HTML or not re.search(rb'<html(?:\s|>)', raw, flags=re.I):
            raise FrontendUnavailable('로컬 HTTP 본문에서 HTML 문서를 확인하지 못했습니다.')
        # The official upstream mounts its installed 'frontend' directory as
        # static files. A 200 HTML response alone could come from a different
        # process/project occupying port 12393. Do not show that in AISTING.
        # This proves matching index bytes only, NOT running-server identity,
        # LLM, TTS, Cubism initialization, or consent for any other action.
        _regular_file(index, max_size=_MAX_HTML)
        disk_html = index.read_bytes()
        if not hashlib.compare_digest(hashlib.sha256(raw).digest(),
                                      hashlib.sha256(disk_html).digest()):
            raise FrontendUnavailable(
                '12393 로컬 서버 화면이 선택한 공식 프로젝트 frontend/index.html과 '
                '일치하지 않습니다. 다른 서버/프로젝트 화면 실행을 차단했습니다.'
            )
        return OfficialFrontendReadiness(OFFICIAL_URL, index, response.status, content_type)
    except (OSError, http.client.HTTPException) as exc:
        raise FrontendUnavailable('기존 공식 로컬 프런트엔드 서버에 연결하지 못했습니다.') from exc
    finally:
        connection.close()



def native_viewer_command(project: str | Path, *, frozen: bool | None = None) -> list[str]:
    """Launch existing AISTING with the selected original official project."""
    if not str(project).strip() or not Path(project).is_dir():
        raise FrontendUnavailable('선택한 공식 프로젝트 폴더가 없습니다.')
    if frozen is None:
        frozen = bool(getattr(sys, 'frozen', False))
    if frozen:
        return [sys.executable, '--aisting-live2d-viewer', str(project)]
    root = Path(__file__).resolve().parents[2]
    entry = root / 'scripts' / 'run_desktop.py'
    if not entry.is_file():
        raise FrontendUnavailable('기존 AISTING 데스크톱 실행 진입점이 없습니다.')
    return [sys.executable, str(entry), '--aisting-live2d-viewer', str(project)]


def _check_windows_native_dependencies() -> None:
    if sys.platform != 'win32':
        raise FrontendUnavailable('Live2D Windows 네이티브 화면은 Windows에서 실행해야 합니다.')
    try:
        installed = importlib.util.find_spec('webview')
    except (ImportError, ValueError):
        installed = None
    if installed is None:
        raise FrontendUnavailable('Windows WebView2 창용 pywebview가 없습니다. 자동 설치하지 않습니다.')


def _project_from_readiness(readiness: OfficialFrontendReadiness) -> Path:
    """Revalidate the exact local official project immediately before spawn."""
    if (not isinstance(readiness, OfficialFrontendReadiness)
            or readiness.url != OFFICIAL_URL or readiness.http_status != 200
            or readiness.content_type != 'text/html'):
        raise FrontendUnavailable('공식 로컬 화면 검사 결과가 유효하지 않습니다.')
    index = readiness.local_frontend
    if (not isinstance(index, Path) or index.name != 'index.html'
            or index.parent.name != 'frontend' or index.is_symlink()
            or index.parent.is_symlink()):
        raise FrontendUnavailable('공식 Live2D 파일 경로가 잘못됐습니다.')
    project = index.parent.parent
    verified = inspect_installed_official_frontend(project)
    if verified != index:
        raise FrontendUnavailable('승인 후 공식 Live2D 파일이 변경됐습니다.')
    return project


def open_prechecked_frontend(readiness: OfficialFrontendReadiness, *,
                             operator_approved: bool = False) -> bool:
    """Launch a native Windows window, never an external web browser.

    A successful Popen only means it launched a child process; NOT Live2D proof.
    """
    if operator_approved is not True:
        raise PermissionError('공식 Live2D Windows 창 실행의 명시적 승인이 필요합니다.')
    project = _project_from_readiness(readiness)
    _check_windows_native_dependencies()
    try:
        child = subprocess.Popen(native_viewer_command(project), close_fds=True)
    except OSError as exc:
        raise FrontendUnavailable('AISTING Windows Live2D 창을 시작할 수 없습니다.') from exc
    return child.pid > 0


def run_native_live2d_window(project: str | Path, *, operator_approved: bool = False) -> None:
    """Run official Live2D WebGL in a Windows native window in the child main thread.

    The official frontend manages its own upstream WebSocket conversation
    session, NOT the unrelated Tk AI text-chat session.
    """
    if operator_approved is not True:
        raise PermissionError('AISTING Live2D 전용 창 실행 승인이 필요합니다.')
    _check_windows_native_dependencies()
    # Child process checks the official local files and server again: no silent
    # switch to another project or blank network page between approval/start.
    probe_official_frontend(project, operator_approved=True)
    import webview
    webview.create_window('AISTING | 공식 Live2D 및 AI 대화', OFFICIAL_URL,
                          width=1100, height=760, min_size=(650, 480))
    webview.start(gui='edgechromium', debug=False, private_mode=True)
