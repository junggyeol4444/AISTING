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
import hmac
import http.client
import json
import secrets
import threading
import time
from multiprocessing.connection import Client, Listener
from pathlib import Path
import re
import importlib.util
import subprocess
import sys

OFFICIAL_HOST = '127.0.0.1'
OFFICIAL_PORT = 12393
OFFICIAL_URL = f'http://{OFFICIAL_HOST}:{OFFICIAL_PORT}/'
_MAX_HTML = 128 * 1024
_native_viewer: subprocess.Popen | None = None
_native_viewer_project: Path | None = None
_native_bridge = None
_native_listener = None
_native_send_lock = threading.Lock()


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
        if not hmac.compare_digest(hashlib.sha256(raw).digest(),
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


def _create_native_bridge() -> tuple[object, str, bytes]:
    """Windows named-pipe listener, not a web server or browser backend."""
    if sys.platform != 'win32':
        raise FrontendUnavailable('공식 Live2D 앱 간 통신은 Windows에서만 지원합니다.')
    address = r'\\.\pipe\aisting-live2d-' + secrets.token_hex(16)
    authkey = secrets.token_bytes(32)
    try:
        listener = Listener(address=address, family='AF_PIPE', authkey=authkey)
    except (OSError, ValueError) as exc:
        raise FrontendUnavailable('Windows Live2D 전용 보안 파이프를 만들지 못했습니다.') from exc
    return listener, address, authkey


def _receive_native_bridge(listener: object, generation: object) -> None:
    """Accept only the authenticated child of this existing AISTING.exe."""
    global _native_bridge
    conn = None
    try:
        conn = listener.accept()
        if not conn.poll(15):
            return
        ready = json.loads(conn.recv_bytes(1024).decode('utf-8'))
        if ready != {'type': 'ready'}:
            return
        if generation is _native_listener:
            _native_bridge = conn
            conn = None
    except (OSError, EOFError, UnicodeError, ValueError):
        pass
    finally:
        if conn is not None:
            conn.close()
        listener.close()


def open_prechecked_frontend(readiness: OfficialFrontendReadiness, *,
                             operator_approved: bool = False) -> bool:
    """Spawn SAME AISTING.exe native WebView2 plus authenticated Windows pipe.

    No new web backend, browser, auto-download, voice/model inference, or stream.
    """
    if operator_approved is not True:
        raise PermissionError('공식 Live2D Windows 창 실행의 명시적 승인이 필요합니다.')
    project = _project_from_readiness(readiness)
    _check_windows_native_dependencies()
    global _native_viewer, _native_viewer_project, _native_bridge, _native_listener
    if _native_viewer is not None and _native_viewer.poll() is None:
        if _native_viewer_project != project:
            raise FrontendUnavailable('다른 공식 프로젝트 Live2D 창이 이미 열려 있습니다.')
        return True
    _native_bridge = None
    listener, address, key = _create_native_bridge()
    try:
        child = subprocess.Popen(
            native_viewer_command(project) +
            ['--aisting-ipc', address, key.hex()],
            close_fds=True, stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        listener.close()
        raise FrontendUnavailable('AISTING Windows Live2D 창을 시작할 수 없습니다.') from exc
    _native_listener = listener
    _native_viewer, _native_viewer_project = child, project
    threading.Thread(
        target=_receive_native_bridge, args=(listener, listener),
        name='aisting-official-live2d-ipc', daemon=True,
    ).start()
    return child.pid > 0


def send_to_native_live2d_session(text: str, *, operator_approved: bool = False) -> bool:
    """Only report successful forwarding if official React key handler consumed it.

    An acknowledgement proves the official browser WebSocket sent text, NOT AI, TTS, Live2D
    motion, audio delivery, or broadcast. All external execution is user-approved.
    """
    if operator_approved is not True:
        raise PermissionError('공식 Live2D 실제 AI 세션 질문은 매번 승인이 필요합니다.')
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
        raise FrontendUnavailable('공식 Live2D 질문은 1~4000글자여야 합니다.')
    child = _native_viewer
    if child is None or child.poll() is not None:
        raise FrontendUnavailable('AISTING에서 먼저 공식 Live2D 창을 열어주세요.')
    conn = _native_bridge
    if conn is None:
        raise FrontendUnavailable('공식 Live2D 창의 입력 통신이 아직 연결되지 않았습니다.')
    with _native_send_lock:
        try:
            conn.send_bytes(json.dumps({'type': 'user-text', 'text': text.strip()},
                                       ensure_ascii=False).encode('utf-8'))
            if not conn.poll(9):
                raise FrontendUnavailable('공식 Live2D 화면 입력 처리 응답을 받지 못했습니다.')
            reply = json.loads(conn.recv_bytes(2048).decode('utf-8'))
            if not isinstance(reply, dict) or reply.get('type') != 'input-result':
                raise FrontendUnavailable('공식 Live2D 응답 형식이 올바르지 않습니다.')
            if reply.get('accepted') is not True:
                raise FrontendUnavailable('공식 Live2D 입력창의 전송 이벤트가 처리되지 않았습니다.')
        except (EOFError, BrokenPipeError, OSError, UnicodeError, ValueError) as exc:
            raise FrontendUnavailable('공식 Live2D Windows 창 입력 통신에 실패했습니다.') from exc
    return True




def send_to_native_live2d_session_with_observation(
        text: str, *, operator_approved: bool = False,
        duration: float = 8.0) -> "OfficialLipSyncEvidence":
    """One approved official text turn followed immediately by read-only RMS sampling.

    Existing child pipe dispatches both parts in one request, so observation
    cannot block the associated prompt. No other AI session or forced audio.
    """
    if operator_approved is not True:
        raise PermissionError('공식 Live2D 실제 질문·입 움직임 확인 승인이 필요합니다.')
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
        raise FrontendUnavailable('공식 AI 질문은 1~4000글자여야 합니다.')
    if type(duration) not in (int, float) or not 1 <= duration <= 12:
        raise ValueError('립싱크 관찰 기간은 1~12초여야 합니다.')
    child, conn = _native_viewer, _native_bridge
    if child is None or child.poll() is not None or conn is None:
        raise FrontendUnavailable('공식 Live2D Windows 창과 연결되어 있지 않습니다.')
    with _native_send_lock:
        try:
            request = {'type': 'user-text-with-lipsync', 'text': text.strip(),
                       'seconds': float(duration)}
            conn.send_bytes(json.dumps(request, ensure_ascii=False).encode('utf-8'))
            if not conn.poll(float(duration) + 9):
                raise FrontendUnavailable(
                    '공식 질문·립싱크 검사 응답 시간 초과 · 자동 재시도하지 않습니다.'
                )
            reply = json.loads(conn.recv_bytes(4096).decode('utf-8'))
        except (OSError, EOFError, UnicodeError, ValueError) as exc:
            raise FrontendUnavailable(
                '공식 Live2D 질문·립싱크 전달 오류 · 중복 전송 방지를 위해 자동 재시도하지 않습니다.'
            ) from exc
    if not isinstance(reply, dict) or reply.get('type') != 'input-with-lipsync-result':
        raise FrontendUnavailable('공식 Live2D 질문 전송 또는 관찰이 확인되지 않았습니다.')
    if reply.get('accepted') is not True:
        raise FrontendUnavailable('공식 Live2D 질문의 실제 WebSocket 전송이 확인되지 않았습니다.')
    return _parse_official_lipsync_evidence(reply.get('evidence'))




@dataclass(frozen=True)
class OfficialLipSyncEvidence:
    """Real official WebView2 model observations; never simulated samples."""
    samples: int
    model_seen: bool
    canvas_seen: bool
    lip_sync_ids: int
    peak_rms: float
    active_rms_samples: int
    mouth_range: float
    changing_mouth_samples: int
    renderer_active_samples: int = 0
    overlapping_audio_mouth_samples: int = 0

    @property
    def verified_signal(self) -> bool:
        # Model/canvas presence alone is NOT audio-driven mouth motion.
        return (self.model_seen and self.canvas_seen and self.lip_sync_ids > 0
                and self.peak_rms > 0.01 and self.active_rms_samples > 0
                and self.mouth_range > 0.02 and self.changing_mouth_samples > 0
                and self.renderer_active_samples > 0
                and self.overlapping_audio_mouth_samples > 0)


def inspect_native_live2d_lipsync(*, operator_approved: bool = False,
                                   duration: float = 8.0) -> OfficialLipSyncEvidence:
    """Read actual original Cubism RMS and mouth parameter while the AI speaks.

    Never synthesize, mutate the model, start any audio, send an AI prompt,
    change OBS, or claim a sound was heard. This needs a running real voice.
    """
    if operator_approved is not True:
        raise PermissionError('실제 Live2D 립싱크 관찰 승인이 필요합니다.')
    if type(duration) not in (float, int) or not 1 <= duration <= 12:
        raise ValueError('Live2D 관찰 기간은 1~12초여야 합니다.')
    child = _native_viewer
    conn = _native_bridge
    if child is None or child.poll() is not None or conn is None:
        raise FrontendUnavailable('현재 공식 Live2D Windows 창이 연결되어 있지 않습니다.')
    with _native_send_lock:
        try:
            conn.send_bytes(json.dumps({
                'type': 'observe-lipsync', 'seconds': float(duration)
            }).encode('utf-8'))
            if not conn.poll(float(duration) + 6):
                raise FrontendUnavailable('Live2D 실제 입 움직임 검사 결과가 도착하지 않았습니다.')
            reply = json.loads(conn.recv_bytes(4096).decode('utf-8'))
        except (EOFError, OSError, ValueError, UnicodeError) as exc:
            raise FrontendUnavailable('Live2D 실시간 관찰 IPC 연결 실패') from exc
    return _parse_official_lipsync_evidence(reply)


def _parse_official_lipsync_evidence(reply: dict) -> OfficialLipSyncEvidence:
    if not isinstance(reply, dict) or reply.get('type') != 'lip-sync-result':
        raise FrontendUnavailable('공식 Live2D 검사 응답 형식이 올바르지 않습니다.')
    try:
        vals = tuple(reply[field] for field in (
            'samples', 'model_seen', 'canvas_seen', 'lip_sync_ids',
            'peak_rms', 'active_rms_samples', 'mouth_range',
            'changing_mouth_samples', 'renderer_active_samples',
            'overlapping_audio_mouth_samples',
        ))
        (samples, model_seen, canvas_seen, ids, rms, active, mouth, changes,
         renderer_active, overlapping) = vals
        if (type(samples) is not int or not 1 <= samples <= 500
                or type(model_seen) is not bool or type(canvas_seen) is not bool
                or type(ids) is not int or not 0 <= ids <= 50
                or type(active) is not int or not 0 <= active <= samples
                or type(changes) is not int or not 0 <= changes <= samples
                or type(renderer_active) is not int or not 0 <= renderer_active <= samples
                or type(overlapping) is not int or not 0 <= overlapping <= samples
                or overlapping > min(active, changes, renderer_active)
                or type(rms) not in (int, float) or not 0 <= rms <= 10
                or type(mouth) not in (int, float) or not 0 <= mouth <= 20):
            raise ValueError('관측값 범위 오류')
        return OfficialLipSyncEvidence(
            samples, model_seen, canvas_seen, ids, float(rms), active,
            float(mouth), changes, renderer_active, overlapping
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise FrontendUnavailable('공식 Live2D 검사 결과에 유효하지 않은 데이터가 있습니다.') from exc


def _official_live2d_probe_script() -> str:
    """One read-only observation of official Open-LLM-VTuber Cubism internals."""
    return (
        "(() => {"
        "if(location.origin!=='http://127.0.0.1:12393')return null;"
        "const canvas=document.getElementById('canvas');"
        "const visible=!!(canvas&&canvas.width>0&&canvas.height>0);"
        "const manager=window.getLive2DManager?.()||"
        "window.LAppLive2DManager?.getInstance?.();"
        "const model=manager?.getModel?.(0);"
        "const wav=model?._wavFileHandler;"
        "const ids=model?._lipSyncIds;"
        "const count=ids?.getSize?.()||0;"
        "let mouth=null;"
        "try{if(count>0&&model?._model?.getParameterValueById)"
        "mouth=model._model.getParameterValueById(ids.at(0));"
        "}catch(_error){}"
        "let rms=null;"
        "try{if(wav?.getRms)rms=wav.getRms();}catch(_error){}"
        "return JSON.stringify({canvas:visible,model:!!model,ids:count,"
        "lipsync:model?._lipsync===true,"
        "rms:(Number.isFinite(rms)?rms:null),"
        "mouth:(Number.isFinite(mouth)?mouth:null)});"
        "})()"
    )


def _observe_actual_live2d_model(window, seconds: float) -> dict:
    """Sample real renderer state; no generated/sample/placeholder values."""
    samples = 0
    model_seen = canvas_seen = False
    ids = active = changing = renderer_active = overlapping = 0
    peak_rms = 0.0
    low = high = previous = None
    deadline = time.monotonic() + seconds
    script = _official_live2d_probe_script()
    while time.monotonic() < deadline and samples < 500:
        try:
            raw = window.evaluate_js(script)
            item = json.loads(raw) if isinstance(raw, str) else None
            if isinstance(item, dict):
                samples += 1
                model_seen = model_seen or item.get('model') is True
                canvas_seen = canvas_seen or item.get('canvas') is True
                count = item.get('ids')
                if type(count) is int and 0 <= count <= 50:
                    ids = max(ids, count)
                lipsync_enabled = item.get('lipsync') is True
                if lipsync_enabled:
                    renderer_active += 1
                rms = item.get('rms')
                if type(rms) in (int, float) and 0 <= rms <= 10:
                    peak_rms = max(peak_rms, float(rms))
                    if rms > 0.01:
                        active += 1
                mouth = item.get('mouth')
                if type(mouth) in (int, float) and -10 <= mouth <= 10:
                    m = float(mouth)
                    low = m if low is None else min(low, m)
                    high = m if high is None else max(high, m)
                    if previous is not None and abs(m - previous) > 0.01:
                        changing += 1
                        if (lipsync_enabled and type(rms) in (int, float)
                                and 0.01 < rms <= 10):
                            overlapping += 1
                    previous = m
        except (ValueError, TypeError, OSError):
            pass
        time.sleep(0.08)
    return {
        'type': 'lip-sync-result',
        'samples': samples,
        'model_seen': model_seen, 'canvas_seen': canvas_seen,
        'lip_sync_ids': ids,
        'peak_rms': round(peak_rms, 6),
        'active_rms_samples': active,
        'mouth_range': round((high - low) if low is not None else 0.0, 6),
        'changing_mouth_samples': changing,
        'renderer_active_samples': renderer_active,
        'overlapping_audio_mouth_samples': overlapping,
    }


def _official_frontend_input_script(value: str, nonce: str) -> tuple[str, str, str, str]:
    """Observe ONLY the official frontend's same-session WS text send.

    A one-shot hook delegates to the browser's original WebSocket.send without
    changing outgoing payloads. It is removed after each attempt. Seeing the
    genuine send proves the browser submitted text through its own established
    connection; it does not prove server receipt, LLM result, TTS or lip sync.
    """
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 4000:
        raise ValueError('공식 AI 질문 길이가 올바르지 않습니다.')
    if not isinstance(nonce, str) or len(nonce) != 32 or any(
            ch not in '0123456789abcdef' for ch in nonce):
        raise ValueError('공식 화면 요청 식별자가 올바르지 않습니다.')
    encoded = json.dumps(value, ensure_ascii=False)
    marker = json.dumps(nonce)
    input_script = (
        "(() => {"
        "if(location.origin!=='http://127.0.0.1:12393')return false;"
        "if(typeof WebSocket==='undefined'||!WebSocket.prototype.send)return false;"
        "if(window.__aistingSendAudit)return false;"
        "const nodes=Array.from(document.querySelectorAll('textarea'))"
        ".filter(x=>!x.disabled&&x.offsetParent!==null);"
        "if(nodes.length!==1)return false;"
        "const el=nodes[0];const value=" + encoded + ";"
        "const nonce=" + marker + ";"
        "const original=WebSocket.prototype.send;"
        "const audit={nonce:nonce,observed:false,original:original,wrapper:null};"
        "audit.wrapper=function(data){"
        "const result=original.apply(this,arguments);"
        "try{"
        "if(this.readyState===WebSocket.OPEN&&"
        "this.url==='ws://127.0.0.1:12393/client-ws'&&"
        "typeof data==='string'){"
        "const packet=JSON.parse(data);"
        "if(packet.type==='text-input'&&packet.text===value)"
        "audit.observed=true;"
        "}}catch(_err){}"
        "return result;};"
        "window.__aistingSendAudit=audit;"
        "WebSocket.prototype.send=audit.wrapper;"
        "const setter=Object.getOwnPropertyDescriptor("
        "HTMLTextAreaElement.prototype,'value').set;"
        "setter.call(el,value);"
        "el.dispatchEvent(new Event('input',{bubbles:true}));"
        "return el.value===value;"
        "})()"
    )
    submit_script = (
        "(() => {"
        "if(location.origin!=='http://127.0.0.1:12393')return false;"
        "const audit=window.__aistingSendAudit;"
        "if(!audit||audit.nonce!==" + marker + ")return false;"
        "const nodes=Array.from(document.querySelectorAll('textarea'))"
        ".filter(x=>!x.disabled&&x.offsetParent!==null);"
        "if(nodes.length!==1)return false;"
        "const el=nodes[0];"
        "if(el.value!==" + encoded + ")return false;"
        "const key=new KeyboardEvent('keydown',"
        "{key:'Enter',code:'Enter',bubbles:true,cancelable:true});"
        "return el.dispatchEvent(key)===false&&key.defaultPrevented;"
        "})()"
    )
    observed_script = (
        "(() => {"
        "if(location.origin!=='http://127.0.0.1:12393')return false;"
        "const audit=window.__aistingSendAudit;"
        "return !!(audit&&audit.nonce===" + marker + "&&audit.observed===true);"
        "})()"
    )
    cleanup_script = (
        "(() => {"
        "const audit=window.__aistingSendAudit;"
        "if(!audit||audit.nonce!==" + marker + ")return false;"
        "if(WebSocket.prototype.send===audit.wrapper)"
        "WebSocket.prototype.send=audit.original;"
        "delete window.__aistingSendAudit;return true;"
        "})()"
    )
    return input_script, submit_script, observed_script, cleanup_script


def _submit_original_live2d_text(window, value: str) -> bool:
    """Run official React input handler and observe its real WS text-input send."""
    accepted = False
    request_nonce = secrets.token_hex(16)
    scripts = _official_frontend_input_script(value.strip(), request_nonce)
    input_script, submit_script, observed_script, cleanup_script = scripts
    try:
        input_seen = window.evaluate_js(input_script) is True
        if input_seen:
            time.sleep(0.1)
            handled = window.evaluate_js(submit_script) is True
            if handled:
                deadline = time.monotonic() + 6.0
                while time.monotonic() < deadline:
                    if window.evaluate_js(observed_script) is True:
                        accepted = True
                        break
                    time.sleep(0.05)
    except Exception:
        accepted = False
    finally:
        try:
            window.evaluate_js(cleanup_script)
        except Exception:
            pass
    return accepted


def _native_frontend_input_worker(window, address: str | None = None,
                                  auth_hex: str | None = None) -> None:
    """Connect authenticated Windows pipe even in PyInstaller --windowed mode.

    Never use sys.stdin: a --windowed EXE can have no Python stdin despite a
    Popen PIPE. Each request is handled in the official WebView React UI.
    """
    if not address or not auth_hex or sys.platform != 'win32':
        return
    conn = None
    try:
        if not window.events.loaded.wait(timeout=30):
            return
        conn = Client(address, family='AF_PIPE', authkey=bytes.fromhex(auth_hex))
        conn.send_bytes(b'{"type":"ready"}')
        while True:
            raw = conn.recv_bytes(24_000)
            try:
                request = json.loads(raw.decode('utf-8'))
            except (UnicodeError, ValueError):
                # Reject only the malformed request; keep the authenticated pipe alive.
                conn.send_bytes(b'{"type":"input-invalid"}')
                continue
            if isinstance(request, dict) and request.get('type') == 'observe-lipsync':
                period = request.get('seconds')
                if type(period) not in (int, float) or not 1 <= period <= 12:
                    conn.send_bytes(b'{"type":"lip-sync-invalid"}')
                    continue
                result = _observe_actual_live2d_model(window, float(period))
                conn.send_bytes(json.dumps(result).encode('utf-8'))
                continue
            accepted = False
            if isinstance(request, dict) and request.get('type') in ('user-text', 'user-text-with-lipsync'):
                value = request.get('text')
                if request.get('type') == 'user-text-with-lipsync':
                    period = request.get('seconds')
                    if type(period) not in (int, float) or not 1 <= period <= 12:
                        conn.send_bytes(b'{"type":"input-with-lipsync-invalid"}')
                        continue
                if isinstance(value, str) and 1 <= len(value.strip()) <= 4000:
                    accepted = _submit_original_live2d_text(window, value)
                    if accepted and request.get('type') == 'user-text-with-lipsync':
                        evidence = _observe_actual_live2d_model(window, float(period))
                        conn.send_bytes(json.dumps({
                            'type': 'input-with-lipsync-result', 'accepted': True,
                            'evidence': evidence,
                        }).encode('utf-8'))
                        continue
            conn.send_bytes(json.dumps(
                {'type': 'input-result', 'accepted': accepted}
            ).encode('utf-8'))
    except (OSError, EOFError, UnicodeError, ValueError):
        return
    finally:
        if conn is not None:
            conn.close()


def run_native_live2d_window(project: str | Path, *, operator_approved: bool = False,
                             ipc_address: str | None = None,
                             ipc_auth: str | None = None) -> None:
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
    window = webview.create_window('AISTING | 공식 Live2D 및 AI 대화', OFFICIAL_URL,
                          width=1100, height=760, min_size=(650, 480))
    webview.start(func=_native_frontend_input_worker,
                  args=(window, ipc_address, ipc_auth),
                  gui='edgechromium', debug=False, private_mode=True)
