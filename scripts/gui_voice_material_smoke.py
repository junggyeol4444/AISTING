"""GUI smoke stage 042: operator metadata, explicit persistence and source isolation."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import VOICES, load_settings, save_settings
from ai_broadcaster.voice_material_plan import load_material_plan
from ai_broadcaster.voice_rights_review import VoiceRightsReview, save_rights_review

with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    plan_path = base / 'material.json'
    rights_path = base / 'rights.json'
    settings_path = base / 'settings.json'
    db_path = base / 'conversation.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_path)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings_path)), \
         patch('ai_broadcaster.desktop.material_plan_path', return_value=plan_path), \
         patch('ai_broadcaster.desktop.rights_review_path', return_value=rights_path), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('db')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('음성 자료 준비표')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '음성 자료 준비표'
            assert not plan_path.exists() and not settings_path.exists()
            app._preview_voice_material()
            assert '초안' in app._voice_material_result.get('1.0', 'end')
            app._voice_material_lines.insert('1.0', '테스트 인사 | 12\n테스트 응답 | 30')
            app._voice_material_note.insert(0, '메모')
            app._preview_voice_material()
            assert '42초' in app._voice_material_result.get('1.0', 'end')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._save_voice_material()
            assert not plan_path.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._save_voice_material()
            assert load_material_plan(plan_path).total_declared_seconds == 42
            assert not settings_path.exists() and not db_path.exists()
            original = app._voice.get()
            own = next(key for key, code in VOICES.items() if code == 'own_recording')
            app._voice.set(own)
            assert not app._voice_material_lines.get('1.0', 'end').strip()
            assert app._voice_material_note.get() == ''
            app._load_voice_material()
            assert '불일치' in app._voice_material_status.get()
            assert not app._voice_material_lines.get('1.0', 'end').strip()
            save_rights_review(rights_path, VoiceRightsReview('own_recording', True, True, True, True),
                               operator_confirmed=True)
            app._check_voice_material_rights()
            assert '자체 신고' in app._voice_material_status.get()
            app._voice_material_lines.insert('1.0', '기본 문장 | 15')
            app._preview_voice_material()
            assert '자체 신고 확인' in app._voice_material_result.get('1.0', 'end')
            assert '사용 승인 대기' not in app._voice_material_status.get() or '실물 검증' in app._voice_material_status.get()
            # A source change invalidates the imported attestation, too.
            app._voice.set(original)
            assert app._voice_material_rights is None
            app._load_voice_material()
            assert '불러오기' in app._voice_material_status.get()
            assert '테스트 인사' in app._voice_material_lines.get('1.0', 'end')
            app._voice_material_lines.insert('end', '\n내파일.wav | 0')
            app._preview_voice_material()
            assert '입력 확인 실패' in app._voice_material_status.get()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._delete_voice_material()
            assert plan_path.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._delete_voice_material()
            assert not plan_path.exists() and rights_path.exists()
            assert not settings_path.exists() and not db_path.exists()
            print('GUI stage 042 voice material metadata draft: PASS')
        finally:
            app.destroy()
