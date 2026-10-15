"""Original roadmap 051: GUI manual avatar provenance draft, no real model access."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, load_settings, save_settings
from ai_broadcaster.avatar_preparation import load_preparation

with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    settings = base/'settings.json'
    preparation = base/'avatar_preparation_draft.json'
    database = base/'chat.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda d: save_settings(d, settings)), \
         patch('ai_broadcaster.desktop.preparation_path', return_value=preparation), \
         patch('socket.socket.connect', side_effect=AssertionError('network access forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('database access forbidden')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('아바타 모델 준비표')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '아바타 모델 준비표'
            assert not preparation.exists() and not settings.exists()
            app._avatar_prep_preview()
            assert '준비 초안' in app._avatar_prep_status.get()
            # No approved model when type is undecided.
            app._avatar_prep_alias.insert(0,'예시 모델')
            app._avatar_prep_preview()
            assert '입력 확인 실패' in app._avatar_prep_status.get()
            app._avatar_prep_alias.delete(0,'end')
            choice_2d = next(label for label, code in AVATARS.items() if code == '2d')
            choice_3d = next(label for label, code in AVATARS.items() if code == '3d')
            app._avatar.set(choice_2d)
            app.update()
            app._avatar_prep_origin.set('직접 제작')
            app._avatar_prep_alias.insert(0, '운영자 2D 별칭')
            for flag in app._avatar_prep_flags:
                flag.set(True)
            app._avatar_prep_note.insert(0, '자료는 아직 이 컴퓨터에서 읽지 않음')
            app._avatar_prep_preview()
            assert '실제 모델 사용 승인 대기' in app._avatar_prep_status.get()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._avatar_prep_save()
            assert not preparation.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._avatar_prep_save()
            draft = load_preparation(preparation, selected_avatar='2d')
            assert draft.checklist_ready and draft.alias == '운영자 2D 별칭'
            assert not settings.exists() and not database.exists()
            app._avatar.set(choice_3d)
            app.update()
            assert app._avatar_prep_alias.get() == ''
            assert not any(flag.get() for flag in app._avatar_prep_flags)
            app._avatar_prep_load()
            assert '불러오기 실패' in app._avatar_prep_status.get()
            assert app._avatar_prep_alias.get() == ''
            app._avatar.set(choice_2d)
            app._avatar_prep_load()
            assert app._avatar_prep_alias.get() == '운영자 2D 별칭'
            assert all(flag.get() for flag in app._avatar_prep_flags)
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._avatar_prep_delete()
            assert preparation.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._avatar_prep_delete()
            assert not preparation.exists() and not settings.exists() and not database.exists()
            print('GUI original stage 051 avatar preparation: PASS')
        finally:
            app.destroy()
