"""Stage 052: UI actions, candidate selection, no external device/model access."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import AVATARS, load_settings, save_settings
from ai_broadcaster.avatar_runtime_environment import load_runtime_environment

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    destination = folder/'avatar_runtime_environment_draft.json'
    settings = folder/'settings.json'
    database = folder/'chat.sqlite3'
    old_prep = folder/'avatar_preparation_draft.json'
    old_prep.write_bytes(b'unchanged previous record')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda value: save_settings(value, settings)), \
         patch('ai_broadcaster.desktop.runtime_environment_path', return_value=destination), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
         patch('sqlite3.connect', side_effect=AssertionError('DB forbidden')), \
         patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('아바타 실행 환경 준비')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '아바타 실행 환경 준비'
            app._avatar_env_preview()
            assert '호환성' not in app._avatar_env_status.get() or not destination.exists()
            choice_2d = next(k for k, v in AVATARS.items() if v == '2d')
            choice_3d = next(k for k, v in AVATARS.items() if v == '3d')
            app._avatar.set(choice_2d)
            app.update()
            app._avatar_env_renderer.set('외부 VRM 후보 (미연결)')
            app._avatar_env_preview()
            assert '호환성 검사 실패' in app._avatar_env_status.get()
            app._avatar_env_renderer.set('내장 2D 샘플 (기존 Tk 미리보기)')
            app._avatar_env_background.set('초록색 배경')
            app._avatar_env_note.insert(0, '샘플만 미리보기')
            app._avatar_env_preview()
            assert '실제 구동' in app._avatar_env_status.get() or '실제 모델 아님' in app._avatar_env_result.get('1.0', 'end')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._avatar_env_save()
            assert not destination.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._avatar_env_save()
            saved = load_runtime_environment(destination, selected_avatar='2d')
            assert saved.background == '초록색 배경' and saved.has_existing_preview
            assert not settings.exists() and not database.exists()
            app._avatar.set(choice_3d)
            app.update()
            assert app._avatar_env_renderer.get() == '미정'
            assert app._avatar_env_note.get() == ''
            app._avatar_env_load()
            assert '불러오기 실패' in app._avatar_env_status.get()
            app._avatar_env_renderer.set('외부 VRM 후보 (미연결)')
            app._avatar_env_preview()
            assert '미확인' in app._avatar_env_result.get('1.0', 'end')
            app._avatar.set(choice_2d)
            app._avatar_env_load()
            assert app._avatar_env_renderer.get() == '내장 2D 샘플 (기존 Tk 미리보기)'
            assert app._avatar_env_background.get() == '초록색 배경'
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._avatar_env_delete()
            assert destination.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._avatar_env_delete()
            assert not destination.exists()
            assert old_prep.read_bytes() == b'unchanged previous record'
            assert not settings.exists() and not database.exists()
            print('GUI 052 avatar offline runtime environment: PASS')
        finally:
            app.destroy()
