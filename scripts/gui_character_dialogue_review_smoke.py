"""Stage 040 standalone GUI smoke. Run via Xvfb; NEVER starts a real stream."""
from pathlib import Path
import tempfile
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    settings_path = Path(temp) / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda v: save_settings(v, settings_path)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('캐릭터 대화 1차 검증')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '캐릭터 대화 1차 검증'
            assert app._character_dialogue_report is None and not settings_path.exists()
            app._mark_character_dialogue()
            assert '거부' in app._character_dialogue_status.get()
            app._run_character_dialogue_review()
            assert app._character_dialogue_report.structure_passed
            assert len(app._character_dialogue_ratings) == 6
            assert '평가 대기' in app._character_dialogue_status.get()
            app._character_dialogue_verdict.set('수정 필요')
            app._character_dialogue_note.insert(0, '운영자 검토 의견')
            app._mark_character_dialogue()
            assert app._character_dialogue_ratings[0] == '수정 필요'
            assert '운영자 검토 의견' in app._character_dialogue_result.get('1.0', 'end')
            app._character_dialogue_index.set('99')
            app._mark_character_dialogue()
            assert '거부' in app._character_dialogue_status.get()
            app._character_dialogue_index.set('2')
            app._character_dialogue_script.insert('end', '\n새봄: 대본 변경')
            app._mark_character_dialogue()
            assert app._character_dialogue_report is None  # stale operator assessments cleared
            assert not settings_path.exists()
            app._run_character_dialogue_review()
            assert len(app._character_dialogue_ratings) == 7
            app._reset_character_dialogue_review()
            assert app._character_dialogue_report is None
            assert not settings_path.exists()
            assert not (Path(temp) / 'conversation.sqlite3').exists()
            print('GUI stage 040 character dialogue review: PASS')
        finally:
            app.destroy()
