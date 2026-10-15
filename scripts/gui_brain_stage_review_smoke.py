"""30단계 가상 GUI 점검. 외부 연결 차단."""
import sys
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS

def main():
    with patch('ai_broadcaster.desktop.load_settings', return_value=DEFAULTS), \
         patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('AI 두뇌 1차 점검')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == 'AI 두뇌 1차 점검'
            assert '미실행' in app._brain_review_status.get()
            app._run_brain_review()
            assert '통과' in app._brain_review_status.get()
            assert '미검증' in app._brain_review_text.get('1.0', 'end')
        finally:
            app._shutdown()
    print('30단계 GUI 모의 점검 통과')
if __name__ == '__main__': main()
