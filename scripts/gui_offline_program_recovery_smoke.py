"""Tk desktop smoke for stage 094. No network, device, user files or OBS."""
from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS

with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(DEFAULTS)), \
     patch('ai_broadcaster.desktop.save_settings', side_effect=AssertionError('settings modified')), \
     patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
     patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
    app = AistingApp()
    try:
        app.update()
        label = '프로그램 오류 복구 모의 감사'
        assert label in app._tab_nav_widget.cget('values')
        app._tab_nav.set(label)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        assert '대기' in app._program_recovery_status.get()
        before = deepcopy(app.settings)
        app._program_recovery_run()
        app.update()
        assert '통과' in app._program_recovery_status.get(), app._program_recovery_status.get()
        text = app._program_recovery_text.get('1.0', 'end')
        assert '[4]' in text and '자동 차단 해제 True' in text
        assert '실제 프로세스/Windows/AI/OBS' in text
        assert before == app.settings
    finally:
        app.destroy()
print('STAGE 094 GUI PASS: guarded mock recovery, settings retained, no external actions')
