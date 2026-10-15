"""Stage 048 GUI test under virtual display. No OS voice enumeration or external I/O."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.emotion_expression_review import load_review, LABELS

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    settings = root/'settings.json'
    notes = root/'emotion.json'
    memory = root/'memory.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('ai_broadcaster.desktop.emotion_review_path', return_value=notes), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('SQLite')), \
         patch('subprocess.Popen', side_effect=AssertionError('process/audio')), \
         patch('subprocess.run', side_effect=AssertionError('OS lookup')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('감정 표현 수동 평가')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '감정 표현 수동 평가'
            app._emotion_create()
            assert '실패' in app._emotion_status.get()   # no voice source chosen
            assert not notes.exists()
            app._voice.set('내 목소리 (추후 직접 녹음)')
            app._emotion_create()
            assert app._emotion_review is not None
            assert len(app._emotion_review.items) == 3
            assert all(not x.intended_emotion and x.verdict == 'unreviewed' for x in app._emotion_review.items)
            app._emotion_index.set(app._emotion_index_widget['values'][1])
            app._emotion_select()
            app._emotion_verdict.set(LABELS['operator_ok'])
            app._emotion_apply()
            assert '오류' in app._emotion_status.get() # cannot assess without intent
            app._emotion_intent.insert(0, '놀람')
            app._emotion_note.insert(0, '운영자가 감정 방향 확인')
            app._emotion_apply()
            assert app._emotion_review.items[1].intended_emotion == '놀람'
            assert app._emotion_review.items[1].verdict == 'operator_ok'
            assert app._emotion_review.items[0].verdict == 'unreviewed'
            assert '실제 음성 재생' in app._emotion_result.get('1.0', 'end')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._emotion_save()
            assert not notes.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._emotion_save()
            source, profile, phrases = app._emotion_context()
            assert load_review(notes, source, profile, phrases) == app._emotion_review
            assert not settings.exists() and not memory.exists()
            app._emotion_invalidate()
            assert app._emotion_review is None
            app._emotion_load()
            assert app._emotion_review.items[1].verdict == 'operator_ok'
            app._emotion_text.insert('end', '\n새로운 문장')
            app.update()
            assert app._emotion_review is None
            app._emotion_load()
            assert '차단' in app._emotion_status.get()
            app._emotion_text.delete('1.0', 'end')
            app._emotion_text.insert('1.0', '오늘 와줘서 정말 반가워요!\n헉, 진짜 그렇게 됐어요?\n오늘은 조금 차분하게 이야기해볼게요.')
            app.update()
            app._emotion_load()
            assert app._emotion_review.items[1].intended_emotion == '놀람'
            app._voice.set('동의받은 목소리 (추후 확보)')
            assert app._emotion_review is None
            app._emotion_load()
            assert '차단' in app._emotion_status.get()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._emotion_delete()
            assert notes.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._emotion_delete()
            assert not notes.exists()
            assert not settings.exists() and not memory.exists()
            print('GUI stage048 manual emotion-expression review: PASS')
        finally:
            app.destroy()
