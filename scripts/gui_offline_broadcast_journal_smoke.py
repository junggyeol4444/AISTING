"""Stage 091 actual Tk/Xvfb smoke - explicit synthetic-only journal actions."""
import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.offline_chat_receiver import MockReceivedChat, ReceiveSnapshot

with tempfile.TemporaryDirectory() as temp:
    filename = Path(temp) / '가상회차.json'
    with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(DEFAULTS)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=AssertionError('no settings write')), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            assert '방송 대화·사건 기록 (오프라인)' in app._tab_nav_widget.cget('values')
            app._tab_nav.set('방송 대화·사건 기록 (오프라인)')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert not filename.exists()
            app._journal_note.set('운영자가 적은 가상 게임 사건')
            app._journal_add()
            assert len(app._journal.entries) == 1
            snapshot = ReceiveSnapshot((MockReceivedChat(1, 'youtube', '가상시청자', '안녕'),
                                        MockReceivedChat(2, 'youtube', '가상시청자', '안녕')), False, 2)
            with patch.object(app._mock_receiver, 'snapshot', return_value=snapshot):
                app._journal_import_chats()
                app._journal_import_chats()  # no duplicates on repeated click
            assert len(app._journal.entries) == 3
            assert '안녕' in app._journal_preview.get('1.0', 'end')
            assert not filename.exists(), 'implicit record save occurred'
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(filename)):
                app._journal_export()
            data = json.loads(filename.read_text(encoding='utf-8'))
            assert len(data['entries']) == 3
            assert data['actual_broadcast_verified'] is False
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(filename)):
                app._journal_export()
            assert '실패' in app._journal_status.get()
            assert len(json.loads(filename.read_text(encoding='utf-8'))['entries']) == 3
            app._journal_label.set('새 회차')
            with patch('tkinter.messagebox.askyesno', return_value=True):
                app._journal_reset()
            assert len(app._journal.entries) == 0
            with patch('tkinter.filedialog.askopenfilename', return_value=str(filename)):
                app._journal_load()
            assert len(app._journal.entries) == 3
            filename.write_text('{"bad":"data"}', encoding='utf-8')
            with patch('tkinter.filedialog.askopenfilename', return_value=str(filename)):
                app._journal_load()
            assert len(app._journal.entries) == 3
            assert '거부' in app._journal_status.get()
            assert not list(Path(temp).glob('settings*'))
        finally:
            app.destroy()
print('GUI stage 091 PASS: manual event, mock chats, no duplicate, explicit export, load fail-closed')
