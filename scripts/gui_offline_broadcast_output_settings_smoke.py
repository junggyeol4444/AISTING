"""Original 075 GUI check: offline review-only output settings bridge."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'settings.json'
    untouched = Path(tmp) / 'sentinel.txt'
    untouched.write_text('DO NOT TOUCH', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('db')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('방송 화면 구성 미리보기')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._broadcast_delivery_prepare()
            assert app._scene_delivery_contract is None
            assert '실패' in app._scene_delivery_status.get()
            app._broadcast_scene_preview()
            app._broadcast_delivery_prepare()
            assert app._scene_delivery_contract is None
            app._broadcast_output_check()
            app._broadcast_delivery_prepare()
            c = app._scene_delivery_contract
            assert c is not None
            assert c.review_mapping()['outputs']['streaming_enabled'] is False
            assert '실제 연결 0건' in app._scene_delivery_status.get()
            app._broadcast_delivery_view()
            app.update()
            assert app._scene_delivery_window is not None
            app._broadcast_delivery_close()
            assert app._scene_delivery_window is None
            app._broadcast_delivery_view()
            assert app._scene_delivery_window is not None
            app._voice_volume.set('0')
            assert app._scene_delivery_contract is None
            assert app._scene_delivery_window is None
            app._broadcast_output_check()
            app._broadcast_delivery_prepare()
            assert app._scene_delivery_contract.nominal_volume == 0
            app._scene_canvas.delete('aisting_scene_watermark')
            app._broadcast_delivery_prepare()
            assert app._scene_delivery_contract is None
            app._broadcast_scene_preview()
            app._broadcast_output_check()
            app._broadcast_delivery_prepare()
            assert app._scene_delivery_contract is not None
            app._avatar.set('3D')
            assert app._scene_delivery_contract is None
            app._broadcast_scene_preview()
            app._broadcast_output_check()
            app._broadcast_delivery_prepare()
            assert app._scene_delivery_contract.scene.avatar == '3d'
            assert not app._scene_canvas.find_withtag('aisting_sample_2d')
            assert not path.exists() and untouched.read_text(encoding='utf-8') == 'DO NOT TOUCH'
            print('Stage 075 Tk offline settings binding/audit/stale/mute/3D/no IO: PASS')
        finally:
            app.destroy()
