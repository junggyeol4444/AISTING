"""Stage 076 real Tk smoke in Xvfb; no actual private broadcast/OBS/audio."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as tmp:
    config_path = Path(tmp) / 'settings.json'
    untouched = Path(tmp) / 'unchanged.txt'
    untouched.write_text('PRESERVED', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(config_path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, config_path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._private_broadcast_rehearse()
            assert app._scene_private_rehearsal is None
            assert '실패' in app._scene_private_status.get()
            app._broadcast_scene_preview()
            app._broadcast_output_check()
            app._private_broadcast_rehearse()
            assert app._scene_private_rehearsal is None
            app._broadcast_delivery_prepare()
            app._private_broadcast_rehearse()
            report = app._scene_private_rehearsal
            assert report is not None and report.passed
            assert not report.streaming_performed and not report.private_visibility_verified
            assert len(report.phases) == 5
            assert '비공개 공개범위 확인 0건' in app._scene_private_status.get()
            app._broadcast_delivery_prepare()
            assert app._scene_private_rehearsal is None
            app._private_broadcast_rehearse()
            assert app._scene_private_rehearsal.passed
            app._voice_volume.set('0')
            assert app._scene_private_rehearsal is None
            app._broadcast_output_check()
            app._broadcast_delivery_prepare()
            app._private_broadcast_rehearse()
            assert app._scene_private_rehearsal.passed
            assert '음소거' in app._scene_private_status.get()
            app._scene_canvas.delete('aisting_scene_watermark')
            app._private_broadcast_rehearse()
            assert app._scene_private_rehearsal is None
            app._broadcast_scene_preview()
            app._broadcast_output_check()
            app._broadcast_delivery_prepare()
            app._private_broadcast_rehearse()
            assert app._scene_private_rehearsal.passed
            app._avatar.set('3D')
            assert app._scene_private_rehearsal is None
            app._broadcast_scene_preview()
            app._broadcast_output_check()
            app._broadcast_delivery_prepare()
            app._private_broadcast_rehearse()
            assert app._scene_private_rehearsal.passed
            assert not app._scene_canvas.find_withtag('aisting_sample_2d')
            assert app._scene_delivery_contract.scene.avatar == '3d'
            assert not config_path.exists()
            assert untouched.read_text(encoding='utf-8') == 'PRESERVED'
            print('Stage 076 Tk private procedure rehearsal/invalidations/3D/no streams/no IO: PASS')
        finally:
            app.destroy()
