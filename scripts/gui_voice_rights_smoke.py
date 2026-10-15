"""Stage 041 GUI smoke: checked rights are merely operator self-report."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings, VOICES
from ai_broadcaster.voice_rights_review import load_rights_review

with tempfile.TemporaryDirectory() as temp:
    directory = Path(temp)
    settings = directory / 'settings.json'
    rights = directory / 'operator_voice_rights.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings)), \
         patch('ai_broadcaster.desktop.rights_review_path', return_value=rights), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('db')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('음성 권리·동의 확인')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '음성 권리·동의 확인'
            assert not rights.exists() and not settings.exists()
            app._preview_voice_rights()
            assert '미완료' in app._voice_rights_status.get()
            app._voice_rights_checks[0].set(True)
            app._voice_rights_note.insert(0, '운영자 직접 점검')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._save_voice_rights()
            assert not rights.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._save_voice_rights()
            assert load_rights_review(rights).rights_checked
            assert load_rights_review(rights).source == VOICES[app._voice.get()]
            assert not load_rights_review(rights).checklist_complete
            assert not settings.exists()
            # Different voice source must not borrow an old permission record.
            old_choice = app._voice.get()
            other = next(name for name, code in VOICES.items() if code != VOICES[old_choice])
            app._voice.set(other)
            assert app._voice_rights_checks[0].get() is False  # invalidated on change
            assert app._voice_rights_note.get() == ''  # no cross-source memo
            app._load_voice_rights()
            assert '불일치' in app._voice_rights_status.get()
            assert app._voice_rights_checks[0].get() is False
            app._voice.set(old_choice)
            app._load_voice_rights()
            assert '완료' in app._voice_rights_status.get()
            assert app._voice_rights_checks[0].get() is True
            # Verify checklist completed for recording; still no legal approval.
            own = next(name for name, code in VOICES.items() if code == 'own_recording')
            app._voice.set(own)
            for flag in app._voice_rights_checks:
                flag.set(True)
            app._preview_voice_rights()
            assert '자체 신고' in app._voice_rights_status.get()
            assert '실제 음성 사용 승인 대기' in app._voice_rights_result.get('1.0', 'end')
            app._voice_rights_note.insert('end', '\nnot allowed')
            app._preview_voice_rights()
            assert '입력 확인 실패' in app._voice_rights_status.get()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._delete_voice_rights()
            assert rights.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._delete_voice_rights()
            assert not rights.exists() and not settings.exists()
            assert not (directory / 'conversation.sqlite3').exists()
            print('GUI stage 041 voice rights review: PASS')
        finally:
            app.destroy()
