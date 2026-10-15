"""Stage 090 Tk UI: isolated Canvas virtual audit, no network/process/real playback."""
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings


with tempfile.TemporaryDirectory() as temp:
    location = Path(temp) / 'settings.json'
    settings = deepcopy(DEFAULTS)
    settings.update(platforms=['youtube'], content='chat', avatar='undecided', voice='windows_system')
    with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, location)), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            assert '방송 자동화 전체 모의 감사' in app._tab_nav_widget.cget('values')
            app._tab_nav.set('방송 자동화 전체 모의 감사')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            app._automation_audit_when.set('2026-10-14 19:30')
            app._automation_audit_run()
            assert '미통과' in app._automation_audit_status.get(), app._automation_audit_status.get()
            # Existing operator schedule is a draft; do not persist it.
            app._schedule_draft = app._schedule_draft.add(2, '19:30')
            app._schedule_refresh('GUI mock schedule')
            app._automation_audit_run()
            assert '통과' in app._automation_audit_status.get() and '미통과' not in app._automation_audit_status.get(), app._automation_audit_status.get()
            assert '15/15' in app._automation_audit_status.get()
            checked = app._automation_audit_details.get('1.0', 'end-1c')
            assert checked.count('통과 · ') == 15
            assert app._automation_audit_canvas.find_withtag('aisting_scene_voice')
            app._automation_audit_topic.set('변경')
            assert '무효' in app._automation_audit_status.get()
            assert not app._automation_audit_canvas.find_withtag('aisting_scene_voice')
            app._automation_audit_run()
            assert '15/15' in app._automation_audit_status.get()
            app._automation_audit_when.set('2026-10-14 19:31')
            app._automation_audit_run()
            assert '미통과' in app._automation_audit_status.get()
            app._automation_audit_when.set('2026-10-14 19:30')
            app._voice_volume.set('0')
            assert '무효' in app._automation_audit_status.get()
            app._automation_audit_run()
            assert '15/15' in app._automation_audit_status.get()
            assert not location.exists(), 'GUI audit saved user settings without consent'
        finally:
            app.destroy()
print('GUI stage 090 PASS - 15 checks, blocked/start, Canvas, invalidation, no I/O')
