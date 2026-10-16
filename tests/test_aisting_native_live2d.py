"""Tests for the existing Windows EXE's native Live2D window path (no real launch)."""
import sys
import tempfile
from pathlib import Path
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import original_plan_frontend as viewer


class NativeLive2DTests(unittest.TestCase):
    def setUp(self):
        viewer._native_viewer = None
        viewer._native_viewer_project = None
        viewer._native_bridge = None
        viewer._native_listener = None
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        (self.project / "frontend").mkdir()
        self.index = self.project / "frontend" / "index.html"
        self.index.write_text("<html></html>", encoding="utf-8")
        self.good = viewer.OfficialFrontendReadiness(
            viewer.OFFICIAL_URL, self.index, 200, "text/html")

    def test_explicit_consent_required(self):
        with self.assertRaises(PermissionError):
            viewer.open_prechecked_frontend(self.good)

    def test_remote_web_page_refused(self):
        other = viewer.OfficialFrontendReadiness(
            "https://example.org/", Path("x"), 200, "text/html")
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.open_prechecked_frontend(other, operator_approved=True)

    def test_redirect_refused(self):
        other = viewer.OfficialFrontendReadiness(
            viewer.OFFICIAL_URL, Path("x"), 301, "text/html")
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.open_prechecked_frontend(other, operator_approved=True)

    def test_windows_only(self):
        with patch.object(viewer, "inspect_installed_official_frontend", return_value=self.index), patch.object(viewer.sys, "platform", "linux"):
            with self.assertRaises(viewer.FrontendUnavailable):
                viewer.open_prechecked_frontend(self.good, operator_approved=True)

    def test_missing_viewer_not_installed_automatically(self):
        with patch.object(viewer, "inspect_installed_official_frontend", return_value=self.index), patch.object(viewer.sys, "platform", "win32"), patch.object(
            viewer.importlib.util, "find_spec", return_value=None
        ):
            with self.assertRaises(viewer.FrontendUnavailable):
                viewer.open_prechecked_frontend(self.good, operator_approved=True)

    def test_same_application_child_not_external_browser(self):
        from unittest.mock import MagicMock
        listener = MagicMock()
        address = r'\\.\pipe\aisting-live2d-' + 'a' * 32
        key = bytes.fromhex('22' * 32)
        with patch.object(viewer, "inspect_installed_official_frontend",
                          return_value=self.index), patch.object(
            viewer.sys, "platform", "win32"
        ), patch.object(viewer.importlib.util, "find_spec",
                       return_value=object()), patch.object(
            viewer, "native_viewer_command",
            return_value=["AISTING.exe", "--aisting-live2d-viewer", str(self.project)]
        ), patch.object(
            viewer, "_create_native_bridge", return_value=(listener, address, key)
        ), patch.object(
            viewer.threading, "Thread"
        ), patch.object(
            viewer.subprocess, "Popen", return_value=types.SimpleNamespace(pid=21)
        ) as popen:
            self.assertTrue(viewer.open_prechecked_frontend(self.good, operator_approved=True))
            popen.assert_called_once_with(
                ["AISTING.exe", "--aisting-live2d-viewer", str(self.project),
                 "--aisting-ipc", address, key.hex()],
                close_fds=True, stdin=viewer.subprocess.DEVNULL)

    def test_child_requires_approval(self):
        with self.assertRaises(PermissionError):
            viewer.run_native_live2d_window(self.project)

    def test_child_uses_native_edge_webview2(self):
        fake = types.SimpleNamespace(create_window=lambda *a, **k: None,
                                     start=lambda **k: None)
        with patch.object(viewer, "_check_windows_native_dependencies"), patch.object(
            viewer, "probe_official_frontend", return_value=self.good
        ) as probe, patch.dict(
            sys.modules, {"webview": fake}
        ), patch.object(fake, "create_window") as create, patch.object(
            fake, "start"
        ) as start:
            viewer.run_native_live2d_window(self.project, operator_approved=True)
            probe.assert_called_once_with(self.project, operator_approved=True)
            self.assertEqual(create.call_args.args[1], viewer.OFFICIAL_URL)
            start.assert_called_once_with(
                func=viewer._native_frontend_input_worker,
                args=(create.return_value, None, None),
                gui="edgechromium", debug=False, private_mode=True)


    def test_real_frontend_http_fingerprint_accepts_exact_disk_bytes(self):
        payload = self.index.read_bytes()
        with patch.object(viewer, "inspect_installed_official_frontend",
                          return_value=self.index), patch.object(
            viewer.http.client, "HTTPConnection"
        ) as http:
            response = http.return_value.getresponse.return_value
            response.status = 200
            response.getheader.side_effect = lambda name, default="": (
                "text/html; charset=utf-8" if name == "Content-Type" else default
            )
            response.read.return_value = payload
            checked = viewer.probe_official_frontend(
                self.project, operator_approved=True
            )
            self.assertEqual(checked.local_frontend, self.index)
            self.assertEqual(checked.http_status, 200)

    def test_real_frontend_http_fingerprint_rejects_different_page(self):
        with patch.object(viewer, "inspect_installed_official_frontend",
                          return_value=self.index), patch.object(
            viewer.http.client, "HTTPConnection"
        ) as http:
            response = http.return_value.getresponse.return_value
            response.status = 200
            response.getheader.side_effect = lambda name, default="": (
                "text/html" if name == "Content-Type" else default
            )
            response.read.return_value = b"<html>not official</html>"
            with self.assertRaises(viewer.FrontendUnavailable):
                viewer.probe_official_frontend(self.project, operator_approved=True)

    def test_same_session_refuses_without_explicit_approval(self):
        with self.assertRaises(PermissionError):
            viewer.send_to_native_live2d_session('안녕하세요')

    def test_same_session_refuses_without_authenticated_bridge(self):
        viewer._native_viewer = types.SimpleNamespace(poll=lambda: None)
        viewer._native_bridge = None
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.send_to_native_live2d_session('안녕하세요', operator_approved=True)

    def test_native_relay_reports_only_acknowledged_ui_input(self):
        import json
        from unittest.mock import MagicMock
        viewer._native_viewer = types.SimpleNamespace(poll=lambda: None)
        viewer._native_bridge = MagicMock()
        viewer._native_bridge.poll.return_value = True
        viewer._native_bridge.recv_bytes.return_value = (
            b'{"type":"input-result","accepted":true}'
        )
        self.assertTrue(viewer.send_to_native_live2d_session(
            '안녕하세요', operator_approved=True
        ))
        sent = json.loads(viewer._native_bridge.send_bytes.call_args.args[0])
        self.assertEqual(sent, {'type':'user-text','text':'안녕하세요'})
        viewer._native_bridge.recv_bytes.return_value = (
            b'{"type":"input-result","accepted":false}'
        )
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.send_to_native_live2d_session('다시 질문', operator_approved=True)

    def test_frontend_script_confirms_actual_official_ws_send(self):
        injection, submit, observed, cleanup = viewer._official_frontend_input_script(
            '한국어 "대화"', 'a' * 32
        )
        self.assertIn("HTMLTextAreaElement.prototype", injection)
        self.assertIn("dispatchEvent(new Event('input'", injection)
        self.assertIn("WebSocket.prototype.send", injection)
        self.assertIn("original.apply(this,arguments)", injection)
        self.assertIn("this.url==='ws://127.0.0.1:12393/client-ws'", injection)
        self.assertIn("packet.type==='text-input'", injection)
        self.assertIn("KeyboardEvent('keydown'", submit)
        self.assertIn("key.defaultPrevented", submit)
        self.assertIn("audit.observed===true", observed)
        self.assertIn("WebSocket.prototype.send=audit.original", cleanup)
        self.assertIn('한국어', injection)

    def test_frontend_script_refuses_bad_nonce_or_empty_question(self):
        for bad in ("", "x" * 32, "g" * 32):
            with self.subTest(nonce=bad), self.assertRaises(ValueError):
                viewer._official_frontend_input_script("안녕", bad)
        with self.assertRaises(ValueError):
            viewer._official_frontend_input_script("", "a" * 32)

    def test_native_worker_does_not_use_console_stdin(self):
        from pathlib import Path
        source = Path(viewer.__file__).read_text(encoding='utf-8')
        self.assertIn("Client(address, family='AF_PIPE'", source)
        self.assertNotIn("sys.stdin.buffer", source)

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows AF_PIPE only')
    def test_real_windows_named_pipe_round_trip_with_official_ui_handler(self):
        """One actual Windows pipe between parent and viewer worker; no LLM call."""
        import time
        import threading
        from unittest.mock import MagicMock
        viewer._native_viewer = types.SimpleNamespace(poll=lambda: None)
        listener, address, key = viewer._create_native_bridge()
        viewer._native_listener = listener
        parent = threading.Thread(
            target=viewer._receive_native_bridge, args=(listener, listener),
            daemon=True,
        )
        parent.start()
        fake = MagicMock()
        fake.events.loaded.wait.return_value = True
        fake.evaluate_js.side_effect = [True, True, True, True]
        child = threading.Thread(
            target=viewer._native_frontend_input_worker,
            args=(fake, address, key.hex()), daemon=True,
        )
        child.start()
        deadline = time.monotonic() + 5
        while viewer._native_bridge is None and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertIsNotNone(viewer._native_bridge)
        self.assertTrue(viewer.send_to_native_live2d_session(
            '안녕하세요', operator_approved=True
        ))
        self.assertEqual(fake.evaluate_js.call_count, 4)
        viewer._native_bridge.close()
        child.join(timeout=2)
        self.assertFalse(child.is_alive())

    def test_official_lipsync_readonly_probe_uses_actual_cubism_fields(self):
        script = viewer._official_live2d_probe_script()
        self.assertIn("window.getLive2DManager", script)
        self.assertIn("model._model.getParameterValueById", script)
        self.assertIn("wav.getRms()", script)
        self.assertIn("model?._lipsync===true", script)
        self.assertIn("getElementById('canvas')", script)
        self.assertNotIn("new Audio(", script)
        self.assertNotIn(".start(", script)

    def test_lipsync_evidence_requires_both_real_audio_and_mouth_motion(self):
        from ai_broadcaster.original_plan_frontend import OfficialLipSyncEvidence
        good = OfficialLipSyncEvidence(40, True, True, 1, .30, 12, .55, 8, 12, 5)
        self.assertTrue(good.verified_signal)
        self.assertFalse(OfficialLipSyncEvidence(40, True, True, 1, 0, 0, .55, 8).verified_signal)
        self.assertFalse(OfficialLipSyncEvidence(40, True, True, 1, .3, 12, 0, 0).verified_signal)
        self.assertFalse(OfficialLipSyncEvidence(40, True, True, 0, .3, 12, .55, 8, 12, 5).verified_signal)
        self.assertFalse(OfficialLipSyncEvidence(40, True, True, 1, .3, 12, .55, 8, 0, 0).verified_signal)
        self.assertFalse(OfficialLipSyncEvidence(40, True, True, 1, .3, 12, .55, 8, 12, 0).verified_signal)

    def test_lipsync_inspection_requires_user_consent_and_active_viewer(self):
        with self.assertRaises(PermissionError):
            viewer.inspect_native_live2d_lipsync()
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.inspect_native_live2d_lipsync(operator_approved=True)

    def test_lipsync_bridge_reports_real_signal_only_from_received_frames(self):
        import json
        from unittest.mock import MagicMock
        viewer._native_viewer = types.SimpleNamespace(poll=lambda: None)
        viewer._native_bridge = MagicMock()
        viewer._native_bridge.poll.return_value = True
        payload = {
            'type': 'lip-sync-result',
            'samples': 24,
            'model_seen': True,
            'canvas_seen': True,
            'lip_sync_ids': 1,
            'peak_rms': 0.42,
            'active_rms_samples': 9,
            'mouth_range': 0.31,
            'changing_mouth_samples': 5,
            'renderer_active_samples': 14,
            'overlapping_audio_mouth_samples': 5,
        }
        viewer._native_bridge.recv_bytes.return_value = json.dumps(payload).encode()
        report = viewer.inspect_native_live2d_lipsync(
            operator_approved=True, duration=2.0
        )
        self.assertTrue(report.verified_signal)
        sent = json.loads(viewer._native_bridge.send_bytes.call_args.args[0])
        self.assertEqual(sent, {'type': 'observe-lipsync', 'seconds': 2.0})
        payload['peak_rms'] = 0.0
        payload['active_rms_samples'] = 0
        payload['overlapping_audio_mouth_samples'] = 0
        viewer._native_bridge.recv_bytes.return_value = json.dumps(payload).encode()
        self.assertFalse(viewer.inspect_native_live2d_lipsync(
            operator_approved=True, duration=2.0
        ).verified_signal)

    def test_lipsync_probe_samples_real_viewer_values_not_random(self):
        from unittest.mock import MagicMock
        import json
        child = MagicMock()
        child.evaluate_js.side_effect = [
            json.dumps({'canvas': True,'model': True,'ids': 1,'lipsync':True,'rms': 0,'mouth': 0}),
            json.dumps({'canvas': True,'model': True,'ids': 1,'lipsync':True,'rms': .21,'mouth': .15}),
            json.dumps({'canvas': True,'model': True,'ids': 1,'lipsync':True,'rms': .43,'mouth': .55}),
        ]
        with patch.object(viewer.time, 'monotonic', side_effect=[0., .1, .2, .3, 1.1]), patch.object(
            viewer.time, 'sleep'
        ):
            report = viewer._observe_actual_live2d_model(child, 1)
        self.assertEqual(report['samples'], 3)
        self.assertAlmostEqual(report['peak_rms'], .43)
        self.assertAlmostEqual(report['mouth_range'], .55)
        self.assertEqual(report['changing_mouth_samples'], 2)
        self.assertEqual(report['active_rms_samples'], 2)
        self.assertEqual(report['renderer_active_samples'], 3)
        self.assertEqual(report['overlapping_audio_mouth_samples'], 2)

    def test_lipsync_requires_current_renderer_engine_enabled(self):
        import json
        from unittest.mock import MagicMock
        child = MagicMock()
        child.evaluate_js.side_effect = [
            json.dumps({'canvas':True,'model':True,'ids':1,'lipsync':False,'rms':.3,'mouth':0}),
            json.dumps({'canvas':True,'model':True,'ids':1,'lipsync':False,'rms':.5,'mouth':.6}),
        ]
        with patch.object(viewer.time,'monotonic',side_effect=[0.,.1,.2,1.1]), patch.object(viewer.time,'sleep'):
            result=viewer._observe_actual_live2d_model(child,1)
        self.assertEqual(result['active_rms_samples'],2)
        self.assertEqual(result['changing_mouth_samples'],1)
        self.assertEqual(result['renderer_active_samples'],0)
        self.assertEqual(result['overlapping_audio_mouth_samples'],0)

    def test_project_path_sent_to_child(self):
        command = viewer.native_viewer_command(self.project, frozen=True)
        self.assertEqual(command[-2:], ["--aisting-live2d-viewer", str(self.project)])

    def test_nonexisting_project_refused(self):
        with self.assertRaises(viewer.FrontendUnavailable):
            viewer.native_viewer_command(self.project / "nonexistent", frozen=True)

    def test_local_frontend_changed_after_probe(self):
        with patch.object(viewer, "inspect_installed_official_frontend",
                          return_value=self.project / "frontend" / "other.html"):
            with self.assertRaises(viewer.FrontendUnavailable):
                viewer._project_from_readiness(self.good)

    def test_child_failed_local_probe_never_opens_window(self):
        fake = types.SimpleNamespace(create_window=lambda *a, **k: None,
                                     start=lambda **k: None)
        with patch.object(viewer, "_check_windows_native_dependencies"), patch.object(
            viewer, "probe_official_frontend",
            side_effect=viewer.FrontendUnavailable("공식 서버 없음")
        ), patch.dict(sys.modules, {"webview": fake}), patch.object(
            fake, "create_window"
        ) as create:
            with self.assertRaises(viewer.FrontendUnavailable):
                viewer.run_native_live2d_window(self.project, operator_approved=True)
            create.assert_not_called()

if __name__ == "__main__":
    unittest.main()
