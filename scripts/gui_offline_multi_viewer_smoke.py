"""068 real Tk smoke: interleaved mock viewers, explicit activation, fail/resume."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    settings = Path(temp) / 'settings.json'
    sentinel = Path(temp) / 'keep.txt'
    sentinel.write_text('KEEP', encoding='utf8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('여러 시청자 대화 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '여러 시청자 대화 모의'
            app._mock_multi_next()
            assert '활성화' in app._mock_multi_status.get()
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            for platform, sender, msg in (
                ('chzzk','alice','a1'), ('youtube','bob','b1'),
                ('chzzk','alice','a2'), ('youtube','bob','b2'),
                ('chzzk','carol','c1'),
            ):
                app._mock_receive_platform.set(platform)
                app._mock_receive_sender.set(sender)
                app._mock_receive_text.set(msg)
                app._mock_receive_inject()
            app._mock_multi_activate()
            app._mock_multi_sync()
            app._mock_multi_next()
            app._mock_multi_fail()
            report = app._mock_multi_viewer.snapshot()
            assert report.blocked and report.replied == 1 and report.pending == 4
            app._mock_multi_batch()
            assert app._mock_multi_viewer.snapshot().replied == 1
            app._mock_multi_resume()
            assert app._mock_multi_viewer.snapshot().replied == 1
            app._mock_multi_batch()
            report = app._mock_multi_viewer.snapshot()
            assert report.complete and report.replied == 5 and len(report.viewers) == 3
            assert [lane.replied_ordinals for lane in report.viewers] == [(1,3),(2,4),(5,)]
            assert app._mock_viewer_context.snapshot().enabled
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI original 068 multi-viewer interleaving + failure/resume + isolation: PASS')
        finally:
            app.destroy()
