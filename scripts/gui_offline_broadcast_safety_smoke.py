"""095 Tkinter safety audit smoke test, Linux Xvfb or GUI desktop only."""
from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS

with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(DEFAULTS)), \
     patch('ai_broadcaster.desktop.save_settings', side_effect=AssertionError('settings changed')), \
     patch('socket.socket.connect', side_effect=AssertionError('network')), \
     patch('subprocess.Popen', side_effect=AssertionError('process')):
    app = AistingApp()
    try:
        app.update()
        label = '방송 이상 감지·안전 제어 모의'
        assert label in app._tab_nav_widget.cget('values')
        app._tab_nav.set(label)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        before = deepcopy(app.settings)
        assert '대기' in app._broadcast_safety_status.get()
        app._broadcast_safety_run()
        app.update()
        assert '통과' in app._broadcast_safety_status.get(), app._broadcast_safety_status.get()
        body = app._broadcast_safety_text.get('1.0', 'end')
        for marker in ('[정상]', '[정체 감지]', '[수동 해제]', '[연결 끊김]', '[기록 손상]', '실제 장치 제어 없음'):
            assert marker in body, marker
        assert app.settings == before
        assert app._broadcast_safety_text.cget('state') == 'disabled'
    finally:
        app.destroy()
print('STAGE 095 GUI PASS: six synthetic safety states, no real broadcast or external I/O')
