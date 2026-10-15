"""Original 039 Xvfb GUI: explicitly entered pending change requests only."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.operator_feedback import feedback_path, list_feedback

with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    settings = base / 'settings.json'
    records = feedback_path(base)
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda value: save_settings(value, settings)), \
         patch('ai_broadcaster.desktop.feedback_path', return_value=records), \
         patch('socket.socket.connect', side_effect=AssertionError('network')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('운영자 피드백 수정 준비')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '운영자 피드백 수정 준비'
            assert not records.exists() and not settings.exists()
            app._feedback_preview()
            assert '검증 실패' in app._feedback_status.get()
            app._feedback_observation.insert('1.0', '반응이 딱딱하게 느껴짐')
            app._feedback_request.insert('1.0', '편한 말투를 검토해 줘')
            app._feedback_preview()
            assert '검증 통과' in app._feedback_status.get()
            assert not records.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._feedback_add()
            assert not records.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._feedback_add()
            assert len(list_feedback(records)) == 1
            assert list_feedback(records)[0].observation == '반응이 딱딱하게 느껴짐'
            app._feedback_list()
            assert '#1' in app._feedback_result.get('1.0', 'end')
            app._feedback_sequence.set('1')
            app._feedback_category.set('채팅 반응')
            app._feedback_request.delete('1.0', 'end')
            app._feedback_request.insert('1.0', '더 구체적으로 설명')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._feedback_revise()
            assert list_feedback(records)[0].category == '말투'
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._feedback_revise()
            assert list_feedback(records)[0].category == '채팅 반응'
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._feedback_delete()
            assert len(list_feedback(records)) == 1
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, True]):
                app._feedback_delete()
            assert len(list_feedback(records)) == 0
            assert not settings.exists()
            assert not (base / 'conversation.sqlite3').exists()
            print('GUI stage 039 operator feedback: PASS')
        finally:
            app.destroy()
