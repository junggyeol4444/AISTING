"""Stage 086 Tkinter offline mock display only; network/process blocked."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temporary:
    folder = Path(temporary)
    settings_file = folder / 'settings.json'
    sentinel = folder / 'sentinel.txt'
    sentinel.write_text('KEEP', encoding='utf-8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_file)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda x: save_settings(x, settings_file)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')):
        app = AistingApp()
        try:
            app.update()
            assert '방송 시작 공지 게시 모의' in app._tab_nav_widget.cget('values')
            app._notice_post_inspect()
            assert '거부' in app._notice_post_status.get()
            assert not app._notice_post_text.get('1.0', 'end').strip()
            # User manually registers Wednesday 19:30 and explicitly starts
            # a simulated broadcast, no timers or output device.
            app._schedule_weekday.set('수')
            app._schedule_start_time.set('19:30')
            app._schedule_add()
            app._schedule_reference.set('2026-10-14 19:30')
            app._notice_when.set('2026-10-14 19:30')
            app._notice_topic.set('로컬 안전 검증')
            app._notice_make()
            app._notice_post_inspect()
            assert 'not_started' in app._notice_post_status.get()
            app._start_control_simulate()
            assert 'mock_started' in app._start_control_status.get()
            app._notice_post_inspect()
            assert 'mock_ready' in app._notice_post_status.get()
            app._notice_post_simulate()
            assert 'mock_displayed' in app._notice_post_status.get()
            assert '로컬 안전 검증' in app._notice_post_text.get('1.0', 'end')
            app._notice_post_simulate()
            assert 'duplicate' in app._notice_post_status.get()
            assert not app._notice_post_text.get('1.0', 'end').strip()
            app._notice_topic.set('주제 변경')
            assert '무효' in app._notice_post_status.get()
            app._notice_post_simulate()
            assert '거부' in app._notice_post_status.get()
            app._notice_make()
            app._notice_post_simulate()
            assert 'duplicate' in app._notice_post_status.get()
            app._start_control_finish()
            app._notice_post_inspect()
            assert 'not_started' in app._notice_post_status.get()
            assert sentinel.read_text(encoding='utf-8') == 'KEEP'
            assert not settings_file.exists()
        finally:
            app.destroy()
print('GUI stage 086 PASS — virtual notice display only, no Discord or OBS activity')
