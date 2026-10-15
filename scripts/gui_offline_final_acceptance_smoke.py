"""100 GUI acceptance dossier smoke; Linux virtual Tk only, no release approval."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_operator_maintenance import CHECK_IDS, STATUS_REVIEWED

with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(DEFAULTS)), \
     patch('ai_broadcaster.desktop.save_settings', side_effect=AssertionError('settings changed')), \
     patch('socket.socket.connect', side_effect=AssertionError('network')), \
     patch('subprocess.Popen', side_effect=AssertionError('external app')):
    app = AistingApp()
    try:
        app.update()
        name = '최종 기능 검수·승인 대기'
        assert name in app._tab_nav_widget.cget('values')
        app._tab_nav.set(name)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        original = deepcopy(app.settings)
        report = app._final_acceptance_report
        assert report.archived == () and report.can_release is False
        assert '검사 미실행' in app._final_acceptance_text.get('1.0', 'end')
        app._final_acceptance_inspect()
        assert app._final_acceptance_report.original_roadmap_pending
        assert len(app._final_acceptance_report.archived) == 6
        assert not app._final_acceptance_report.approval_granted
        assert 'ResourceWarning' in app._final_acceptance_text.get('1.0', 'end')
        # Modifying the old self-report cannot approve or prove device testing.
        for key in CHECK_IDS:
            app._maintenance.set_status(key, STATUS_REVIEWED)
        with TemporaryDirectory() as temp:
            dest = Path(temp) / 'dossier.json'
            with patch('ai_broadcaster.desktop.filedialog.asksaveasfilename', return_value=str(dest)):
                app._final_acceptance_export()
            saved = json.loads(dest.read_text(encoding='utf-8'))
            assert saved['operator_self_report_count'] == 12
            assert saved['can_release'] is False
            assert saved['approval_granted'] is False
            assert saved['hardware_verified'] is False
            assert saved['actual_broadcast_verified'] is False
            with patch('ai_broadcaster.desktop.filedialog.asksaveasfilename', return_value=str(dest)):
                app._final_acceptance_export()
            assert '실패' in app._final_acceptance_status.get()
            assert json.loads(dest.read_text(encoding='utf-8')) == saved
        assert app.settings == original
        assert app._final_acceptance_text.cget('state') == 'disabled'
    finally:
        app.destroy()
print('STAGE 100 GUI PASS: bundled final review, blocked release and approval')
