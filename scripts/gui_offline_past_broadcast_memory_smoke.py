"""Stage 092 actual Tk screen: explicit selection; no secret collection / network."""
import tempfile
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_broadcast_journal import OfflineBroadcastJournal
from ai_broadcaster.offline_settings import DEFAULTS

with tempfile.TemporaryDirectory() as temp:
    journal_file = Path(temp) / 'prior-session.json'
    memory_file = Path(temp) / 'cards.json'
    journal = OfflineBroadcastJournal('오프라인 가상회차')
    journal.add_mock_event('operator_note', '지난 모의방송 요약')
    journal.export_json(journal_file)
    with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(DEFAULTS)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=AssertionError('settings write forbidden')), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('external process forbidden')):
        app = AistingApp()
        try:
            app.update()
            label = '과거 방송 기억 카드 (오프라인)'
            assert label in app._tab_nav_widget.cget('values')
            app._tab_nav.set(label)
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert len(app._past_memory.cards) == 0
            assert not memory_file.exists()
            with patch('tkinter.filedialog.askopenfilename', return_value=str(journal_file)):
                app._past_memory_import()
                app._past_memory_import()  # detect duplicate
            assert len(app._past_memory.cards) == 1
            assert '거부' in app._past_memory_status.get()
            assert '지난 모의방송 요약' in app._past_memory_text.get('1.0', 'end')
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(memory_file)):
                app._past_memory_export()
            assert memory_file.exists()
            memory_file.write_text('{"tampered":true}', encoding='utf-8')
            with patch('tkinter.filedialog.askopenfilename', return_value=str(memory_file)):
                app._past_memory_load()
            assert '거부' in app._past_memory_status.get()
            assert len(app._past_memory.cards) == 1
            app._past_memory_selected.set('1. 오프라인 가상회차')
            with patch('tkinter.messagebox.askyesno', return_value=True):
                app._past_memory_remove()
            assert not app._past_memory.cards
            assert not list(Path(temp).glob('settings*'))
        finally:
            app.destroy()
print('STAGE 092 GUI PASS: manual import, duplicate reject, export, corrupt restore reject, removal')
