"""099 Tk GUI smoke in virtual display, no actual user PC or broadcast tests."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_operator_maintenance import CHECKS, STATUS_PROBLEM, STATUS_REVIEWED

with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(DEFAULTS)), \
     patch('ai_broadcaster.desktop.save_settings', side_effect=AssertionError('settings changed')), \
     patch('socket.socket.connect', side_effect=AssertionError('network')), \
     patch('subprocess.Popen', side_effect=AssertionError('program execution')):
    app = AistingApp()
    try:
        app.update()
        label = '운영자 유지보수 수동 점검'
        assert label in app._tab_nav_widget.cget('values')
        app._tab_nav.set(label)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        before = deepcopy(app.settings)
        assert app._maintenance.report().pending == 12
        text = app._maintenance_text.get('1.0', 'end')
        assert 'ResourceWarning' in text and '미확인' in text
        app._maintenance_label.set(CHECKS[1][1])
        app._maintenance_item_selected()
        app._maintenance_mark.set(STATUS_PROBLEM)
        app._maintenance_record()
        assert app._maintenance.report().problems == 1
        assert not app._maintenance.report().can_release
        app._maintenance_label.set(CHECKS[0][1])
        app._maintenance_item_selected()
        app._maintenance_mark.set(STATUS_REVIEWED)
        app._maintenance_record()
        assert app._maintenance.report().reviewed == 1
        assert '승인 아님' in app._maintenance_status.get()
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / 'maintenance.json'
            with patch('ai_broadcaster.desktop.filedialog.asksaveasfilename', return_value=str(file)):
                app._maintenance_export()
            data = json.loads(file.read_text(encoding='utf-8'))
            assert data['can_release'] is False
            assert data['hardware_verified'] is False
            assert data['checklist'][1]['operator_status'] == STATUS_PROBLEM
            with patch('ai_broadcaster.desktop.filedialog.asksaveasfilename', return_value=str(file)):
                app._maintenance_export()
            assert '실패' in app._maintenance_status.get()
            assert json.loads(file.read_text(encoding='utf-8')) == data
        app._maintenance_reset()
        assert app._maintenance.report().pending == len(CHECKS)
        assert app.settings == before
        assert app._maintenance_text.cget('state') == 'disabled'
    finally:
        app.destroy()
print('STAGE 099 GUI PASS: operator-only maintenance review, no live approval')
