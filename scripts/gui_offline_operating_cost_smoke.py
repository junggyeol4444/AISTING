"""096 GUI smoke; a Tk/Xvfb screen, no devices, payments, network or writes."""
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
        label = '운영 비용 수동 예산 계산'
        assert label in app._tab_nav_widget.cget('values')
        app._tab_nav.set(label)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        before = deepcopy(app.settings)
        app._operating_cost_run()
        assert '미산정' in app._operating_cost_text.get('1.0', 'end')
        assert '미입력' in app._operating_cost_text.get('1.0', 'end')
        assert app._operating_cost_text.cget('state') == 'disabled'
        # All inputs manually supplied by operator; no provider rate defaults.
        for field in app._operating_cost_fields:
            app._operating_cost_fields[field].set('0')
        app._operating_cost_fields['server_usage'].set('4')
        app._operating_cost_fields['server_rate'].set('300')
        app._operating_cost_budget.set('1000')
        app._operating_cost_run()
        assert '초과' in app._operating_cost_text.get('1.0', 'end')
        assert '1,200.00원' in app._operating_cost_text.get('1.0', 'end')
        app._operating_cost_fields['server_usage'].set('-99')
        assert app._operating_cost_text.get('1.0', 'end').strip() == ''
        app._operating_cost_run()
        assert '거부' in app._operating_cost_status.get()
        assert app._operating_cost_text.get('1.0', 'end').strip() == ''
        assert app.settings == before
    finally:
        app.destroy()
print('STAGE 096 GUI PASS: manual estimate, budget warning, invalidation, no external I/O')
