"""Original 066: actual Tk GUI + 062/063/065 FIFO timing, no real network."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings

with tempfile.TemporaryDirectory() as temp:
    settings = Path(temp) / 'settings.json'
    sentinel = Path(temp) / 'keep.txt'
    sentinel.write_text('KEEP', encoding='utf8')
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda obj: save_settings(obj, settings)), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('subprocess.Popen', side_effect=AssertionError('process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('채팅 무지연 모의 시험')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '채팅 무지연 모의 시험'
            app._mock_latency_next()
            assert '중단' in app._mock_latency_status.get()
            app._platforms['chzzk'].set(True)
            app._platforms['youtube'].set(True)
            app._platform_chat_connect()
            app._mock_receive_attach()
            app._mock_receive_platform.set('chzzk')
            app._mock_receive_text.set('same')
            app._mock_receive_inject()
            app._mock_receive_inject()
            app._mock_receive_platform.set('youtube')
            app._mock_receive_inject()
            app._mock_order_sync()
            app._mock_latency_sync()
            app._mock_latency_next()
            assert [s.ordinal for s in app._mock_latency.snapshot().samples] == [1]
            app._mock_reactions_fail()
            assert app._mock_reactions.snapshot().blocked
            app._mock_latency_batch()
            assert len(app._mock_latency.snapshot().samples) == 1
            assert app._mock_latency.snapshot().pending == 2
            app._mock_reactions_resume()
            app._mock_latency_batch()
            report = app._mock_latency.snapshot()
            assert report.completed and [s.ordinal for s in report.samples] == [1, 2, 3]
            assert '실제 플랫폼 메시지/AI 모델 0건' in report.describe()
            assert '속도 합격 기준 없음' in report.describe()
            app._mock_receive_text.set('new')
            app._mock_receive_inject()
            app._mock_order_sync()
            app._mock_latency_sync()
            app._mock_reactions_next()  # stage-065 direct reply must NOT count as measured
            app._mock_latency_refresh()
            report = app._mock_latency.snapshot()
            assert report.unmeasured_ordinals == (4,)
            assert not report.completed
            assert not settings.exists() and sentinel.read_text(encoding='utf8') == 'KEEP'
            print('GUI stage 066 timed existing FIFO mock replies, fail/resume, untimed detection, no I/O: PASS')
        finally:
            app.destroy()
