"""GUI stage 049; no speaker, OS query, network, SQLite or real AI."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as folder:
    settings = Path(folder) / 'settings.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('SQLite')), \
         patch('subprocess.Popen', side_effect=AssertionError('audio/process')), \
         patch('subprocess.run', side_effect=AssertionError('OS lookup')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('AI 대사·음성 연결 모의')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == 'AI 대사·음성 연결 모의'
            app._link_start()
            assert app._link_session is None  # undecided voice source
            assert '오류' in app._link_status.get()
            app._voice.set('Windows 무료 음성')
            app._link_start()
            assert app._link_session is not None
            assert len(app._link_session.status().pending) == 3
            app._link_step()
            assert len(app._link_session.status().completed) == 1
            app._link_batch()
            assert len(app._link_session.status().completed) == 3
            assert len(app._link_session.status().pending) == 0
            result = app._link_result.get('1.0', 'end')
            assert '모의 AI 대사' in result
            assert '실제 음성 출력 없음' in result
            app._link_mode.set('두번째 채팅 중단')
            assert app._link_session is None
            app._link_start()
            app._link_batch()
            assert len(app._link_session.status().completed) == 1
            assert len(app._link_session.status().pending) == 2
            assert 'interrupted' in app._link_status.get()
            app._link_mode.set('없음')
            assert app._link_session is None
            app._link_start()
            app._voice_rate.set('2')
            assert app._link_session is None
            app._link_start()
            assert app._link_session.rate == 2
            app._link_script.insert('end', '\n새사람: 반가워요')
            app.update()
            assert app._link_session is None
            app._link_start()
            assert len(app._link_session.status().pending) == 4
            app._link_voice_name.set('')
            app._link_start()
            assert app._link_session is None
            assert not settings.exists()
            print('GUI stage 049 PASS: mock dialogue -> virtual speech FIFO, duplicate, interrupt, no side effects')
        finally:
            app._shutdown()
