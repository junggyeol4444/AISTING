"""29단계 Tk GUI 수동 검증 버튼 테스트 (가상 디스플레이)."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.response_records import ResponseRecord, ResponseRecordStore, ResponseSnapshot

def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'records.sqlite3'
        with patch('ai_broadcaster.desktop.load_settings', return_value=DEFAULTS), \
             patch('ai_broadcaster.desktop.response_records_path', return_value=path), \
             patch('socket.socket.connect', side_effect=AssertionError('network')):
            app = AistingApp()
            try:
                app.update()
                app._tab_nav.set('대화 연속성 검증')
                app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
                app.update()
                assert app._tabs.tab(app._tabs.select(), 'text') == '대화 연속성 검증'
                assert not path.exists()
                app._run_continuity()
                assert '검증 불가' in app._continuity_status.get()
                assert not path.exists()
                row = ResponseRecord('a'*32, 1, '가', '안녕', '반가워')
                ResponseRecordStore(path).save(ResponseSnapshot((row,), 1), confirmed=True)
                before = path.read_bytes()
                app._run_continuity()
                assert '통과' in app._continuity_status.get()
                assert before == path.read_bytes()
            finally:
                app._shutdown()
    print('29단계 GUI 수동 조회·연속성 검증 통과')
if __name__ == '__main__':
    main()
