"""097 Tk offline accelerated 1h/3h virtual smoke (no real broadcasting)."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import sys

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
        tab = '장시간 무인 방송 모의 안정성'
        assert tab in app._tab_nav_widget.cget('values')
        app._tab_nav.set(tab)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        before = deepcopy(app.settings)
        assert '대기' in app._unattended_status.get()
        app._unattended_run()
        app.update()
        assert '통과' in app._unattended_status.get(), app._unattended_status.get()
        assert '3,601틱' not in app._unattended_text.get('1.0', 'end')  # ungrouped count
        assert '3601틱' in app._unattended_text.get('1.0', 'end')
        app._unattended_hours.set('3')
        assert app._unattended_text.get('1.0', 'end').strip() == ''
        app._unattended_run()
        app.update()
        assert '10801틱' in app._unattended_text.get('1.0', 'end')
        assert '실제 경과시간' in app._unattended_text.get('1.0', 'end')
        app._unattended_hours.set('4')  # synthetic invalid value; cannot be selected in readonly widget
        app._unattended_run()
        assert '미통과' in app._unattended_status.get()
        assert app._unattended_text.get('1.0', 'end').strip() == ''
        assert app._unattended_text.cget('state') == 'disabled'
        assert app.settings == before
    finally:
        app.destroy()
print('STAGE 097 GUI PASS: accelerated virtual 1h/3h, no OBS/network/setting write')
