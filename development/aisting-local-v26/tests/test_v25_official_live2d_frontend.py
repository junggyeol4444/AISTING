"""Local safety/contract checks; DO NOT claim official browser/Live2D operation."""
import queue
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload/src'))
from ai_broadcaster import original_plan_frontend as frontend
from ai_broadcaster import original_plan_studio as studio


class StubResponse:
    def __init__(self, status=200, content_type='text/html; charset=utf-8',
                 content=b'<!DOCTYPE html><html lang="en"></html>', headers=None):
        self.status = status
        self.ct = content_type
        self.content = content
        self.headers = headers or {}
    def getheader(self, key, default=''):
        return self.ct if key == 'Content-Type' else self.headers.get(key, default)
    def read(self, count):
        return self.content[:count]


class StubConnection:
    def __init__(self, response):
        self.response = response
        self.closed = False
        self.requested = None
    def request(self, verb, route, *, headers=None):
        self.requested = (verb, route, headers)
    def getresponse(self):
        return self.response
    def close(self):
        self.closed = True


class StubIndicator:
    def __init__(self):
        self.value = ''
    def set(self, v):
        self.value = v


class InlineThread:
    def __init__(self, *, target, **_kwargs):
        self.target = target
    def start(self):
        self.target()


class OfficialFrontendStageOneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('run_server.py', 'pyproject.toml', 'conf.yaml'):
            (self.root / name).write_text('existing official input', encoding='utf-8')
        (self.root / 'frontend').mkdir()
        (self.root / 'frontend/index.html').write_text(
            '<!DOCTYPE html><html><body>Official installed renderer</body></html>',
            encoding='utf-8')

    def test_real_installed_index_not_generated(self):
        f = frontend.inspect_installed_official_frontend(self.root)
        self.assertEqual(f, self.root / 'frontend/index.html')
        self.assertFalse((self.root / 'frontend/generated.html').exists())

    def test_missing_frontend_must_not_launch_upstream_submodule_download(self):
        (self.root / 'frontend/index.html').unlink()
        with self.assertRaises(frontend.FrontendUnavailable):
            frontend.inspect_installed_official_frontend(self.root)
        self.assertFalse((self.root / 'frontend/index.html').exists())

    def test_symlinked_frontend_is_rejected(self):
        (self.root / 'frontend/index.html').unlink()
        elsewhere = self.root / 'another.html'
        elsewhere.write_text('<html></html>')
        (self.root / 'frontend/index.html').symlink_to(elsewhere)
        with self.assertRaises(frontend.FrontendUnavailable):
            frontend.inspect_installed_official_frontend(self.root)

    def test_no_network_without_explicit_approval(self):
        with patch.object(frontend.http.client, 'HTTPConnection') as conn:
            with self.assertRaises(PermissionError):
                frontend.probe_official_frontend(self.root)
            conn.assert_not_called()

    def test_success_probes_exact_local_root_with_no_redirect(self):
        connection = StubConnection(StubResponse())
        with patch.object(frontend.http.client, 'HTTPConnection', return_value=connection) as constructor:
            ready = frontend.probe_official_frontend(self.root, operator_approved=True)
        self.assertEqual(ready.url, 'http://127.0.0.1:12393/')
        self.assertEqual(connection.requested[:2], ('GET', '/'))
        self.assertEqual(connection.requested[2]['Host'], '127.0.0.1:12393')
        self.assertTrue(connection.closed)
        constructor.assert_called_once_with('127.0.0.1', 12393, timeout=4.0)

    def test_http_redirect_is_never_followed(self):
        connection = StubConnection(StubResponse(status=302, headers={'Location':'https://example.org'}))
        with patch.object(frontend.http.client, 'HTTPConnection', return_value=connection):
            with self.assertRaises(frontend.FrontendUnavailable):
                frontend.probe_official_frontend(self.root, operator_approved=True)
        self.assertTrue(connection.closed)
        self.assertEqual(connection.requested[1], '/')

    def test_http_200_json_cannot_pass_as_official_rendering_html(self):
        connection = StubConnection(StubResponse(content_type='application/json',content=b'{"ok":true}'))
        with patch.object(frontend.http.client, 'HTTPConnection', return_value=connection):
            with self.assertRaises(frontend.FrontendUnavailable):
                frontend.probe_official_frontend(self.root, operator_approved=True)

    def test_http_200_empty_html_fails(self):
        connection = StubConnection(StubResponse(content=b'OK'))
        with patch.object(frontend.http.client, 'HTTPConnection', return_value=connection):
            with self.assertRaises(frontend.FrontendUnavailable):
                frontend.probe_official_frontend(self.root, operator_approved=True)

    def test_invalid_or_large_content_length_fails_closed(self):
        for invalid in ('bad', str(128 * 1024 + 1)):
            with self.subTest(invalid=invalid):
                connection = StubConnection(StubResponse(headers={'Content-Length':invalid}))
                with patch.object(frontend.http.client, 'HTTPConnection', return_value=connection):
                    with self.assertRaises(frontend.FrontendUnavailable):
                        frontend.probe_official_frontend(self.root, operator_approved=True)

    def test_browser_opens_only_specific_localhost_after_approval(self):
        ready = frontend.OfficialFrontendReadiness(frontend.OFFICIAL_URL,
            self.root / 'frontend/index.html', 200, 'text/html')
        with patch.object(frontend.webbrowser, 'open_new', return_value=True) as browser:
            with self.assertRaises(PermissionError):
                frontend.open_prechecked_frontend(ready)
            browser.assert_not_called()
            self.assertTrue(frontend.open_prechecked_frontend(ready,operator_approved=True))
            browser.assert_called_once_with(frontend.OFFICIAL_URL)

    def test_forged_remote_url_is_rejected(self):
        fake = frontend.OfficialFrontendReadiness('https://example.org',
            self.root / 'frontend/index.html', 200,'text/html')
        with patch.object(frontend.webbrowser, 'open_new') as browser:
            with self.assertRaises(frontend.FrontendUnavailable):
                frontend.open_prechecked_frontend(fake,operator_approved=True)
            browser.assert_not_called()

    def test_gui_refusal_does_not_spawn_worker_or_network(self):
        instance = SimpleNamespace(project_dir=SimpleNamespace(get=lambda: str(self.root)),
            state=StubIndicator(), parent=None, _events=queue.Queue())
        with (patch.object(studio.messagebox,'askyesno',return_value=False),
              patch.object(studio.threading,'Thread') as thread,
              patch.object(frontend.http.client,'HTTPConnection') as net):
            studio.OriginalPlanStudio._open(instance)
            thread.assert_not_called()
            net.assert_not_called()
            self.assertIn('승인 취소', instance.state.value)

    def test_gui_approval_puts_real_frontend_info_into_event_queue(self):
        instance = SimpleNamespace(project_dir=SimpleNamespace(get=lambda: str(self.root)),
            state=StubIndicator(), parent=None, _events=queue.Queue())
        expected = frontend.OfficialFrontendReadiness(frontend.OFFICIAL_URL,
            self.root/'frontend/index.html',200,'text/html')
        with (patch.object(studio.messagebox,'askyesno',return_value=True),
              patch.object(studio.threading,'Thread',InlineThread),
              patch.object(frontend,'probe_official_frontend',return_value=expected) as probe):
            studio.OriginalPlanStudio._open(instance)
        probe.assert_called_once_with(str(self.root), operator_approved=True)
        self.assertEqual(instance._events.get_nowait(),('official_frontend',('ready',expected)))

    def test_patch_and_windows_build_reference_new_module(self):
        self.assertIn('original_plan_frontend.py', (ROOT/'apply_to_existing_aisting.py').read_text())
        self.assertIn('original_plan_frontend.py', (ROOT/'build_existing_windows.ps1').read_text())
        self.assertIn('v25', (ROOT/'build_existing_windows.ps1').read_text())


if __name__ == '__main__':
    unittest.main()
