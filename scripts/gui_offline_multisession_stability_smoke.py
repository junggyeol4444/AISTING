"""098 isolated GUI multi-broadcast virtual rehearsal, no device/platform/OBS."""
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
        label = '다회차 방송 안정성 모의 검증'
        assert label in app._tab_nav_widget.cget('values')
        app._tab_nav.set(label)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        before = deepcopy(app.settings)
        assert '대기' in app._multisession_status.get()
        app._multisession_run()
        app.update()
        assert '통과' in app._multisession_status.get(), app._multisession_status.get()
        content = app._multisession_text.get('1.0', 'end')
        assert '3회차 × 가상 1시간' in content, content
        assert '10803' in content
        app._multisession_rounds.set('5')
        app._multisession_hours.set('3')
        assert not app._multisession_text.get('1.0', 'end').strip()
        app._multisession_run()
        app.update()
        content = app._multisession_text.get('1.0', 'end')
        assert '5회차 × 가상 3시간' in content, content
        assert '54005' in content
        assert '미검증' in content
        app._multisession_rounds.set('6')
        app._multisession_run()
        assert '미통과' in app._multisession_status.get()
        assert not app._multisession_text.get('1.0', 'end').strip()
        assert app._multisession_text.cget('state') == 'disabled'
        assert app.settings == before
    finally:
        app.destroy()
print('STAGE 098 GUI PASS: bounded 3/5 virtual episodes, no external IO')
