"""Roadmap 047 UI integration, virtual Linux display; no OS/audio/network access."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.pronunciation_review import load_review, LABELS

with tempfile.TemporaryDirectory() as temp:
    folder = Path(temp)
    settings = folder / 'settings.json'
    notes = folder / 'notes.json'
    db = folder / 'memory.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('ai_broadcaster.desktop.pronunciation_review_path', return_value=notes), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('SQLite')), \
         patch('subprocess.Popen', side_effect=AssertionError('OS/audio')), \
         patch('subprocess.run', side_effect=AssertionError('OS queried')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('발음·억양 수동 검토')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '발음·억양 수동 검토'
            app._pron_create()
            assert '실패' in app._pron_status.get()  # voice undecided
            assert not notes.exists()
            app._voice.set('내 목소리 (추후 직접 녹음)')
            app._pron_create()
            assert app._pron_review is not None
            assert len(app._pron_review.items) == 3
            app._pron_index.set(app._pron_index_widget['values'][1])
            app._pron_select()
            app._pron_pronunciation.set(LABELS['needs_adjustment'])
            app._pron_intonation.set(LABELS['operator_ok'])
            app._pron_note.insert(0, '강세 재검토')
            app._pron_apply()
            assert app._pron_review.items[1].pronunciation == 'needs_adjustment'
            assert app._pron_review.items[0].pronunciation == 'unreviewed'
            assert '실제 음성' in app._pron_result.get('1.0', 'end')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._pron_save()
            assert not notes.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._pron_save()
            source, profile, phrases = app._pron_context()
            assert load_review(notes, source, profile, phrases) == app._pron_review
            assert not settings.exists() and not db.exists()
            app._pron_invalidate()
            assert app._pron_review is None
            app._pron_load()
            assert app._pron_review.items[1].intonation == 'operator_ok'
            app._pron_text.insert('end', '\n새로 추가한 대화')
            app.update()
            assert app._pron_review is None
            app._pron_load()
            assert '차단' in app._pron_status.get()
            app._pron_text.delete('1.0', 'end')
            app._pron_text.insert('1.0', '안녕하세요, 오늘 방송에 와 주셔서 고마워요.\n정말요? 그다음 이야기도 들려주세요!\nㅋㅋㅋ 너무 재미있네요.')
            app.update()
            app._pron_load()
            assert app._pron_review is not None
            app._voice.set('동의받은 목소리 (추후 확보)')
            assert app._pron_review is None
            app._pron_load()
            assert '차단' in app._pron_status.get()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._pron_delete()
            assert notes.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._pron_delete()
            assert not notes.exists()
            assert not settings.exists() and not db.exists()
            print('GUI 047 manual pronunciation + intonation: PASS')
        finally:
            app.destroy()
