"""35단계 단독 탭: 수동 저장·불러오기·취소·삭제 확인 (가상 화면)."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import load_settings, save_settings
from ai_broadcaster.operator_boundaries import load_boundaries

with tempfile.TemporaryDirectory() as temp:
    settings = Path(temp) / 'settings.json'
    boundaries = Path(temp) / 'operator_boundaries.json'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings)), \
         patch('ai_broadcaster.desktop.boundaries_path', return_value=boundaries), \
         patch('socket.socket.connect', side_effect=AssertionError('network')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('금기·제한사항 설정')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '금기·제한사항 설정'
            assert not boundaries.exists() and not settings.exists()
            app._boundary_input.insert('1.0', '스포일러 금지\n추측 사실 단정 금지')
            app._preview_boundaries()
            assert '구조 검사 통과' in app._boundary_status.get()
            assert '스포일러 금지' in app._boundary_result.get('1.0', 'end')
            assert not boundaries.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._save_boundaries()
            assert not boundaries.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._save_boundaries()
            assert load_boundaries(boundaries) == ('스포일러 금지', '추측 사실 단정 금지')
            app._boundary_input.delete('1.0', 'end')
            app._load_boundaries()
            assert '스포일러 금지' in app._boundary_input.get('1.0', 'end')
            app._boundary_input.insert('end', '\n' + '가'*201)
            app._preview_boundaries()
            assert '입력 확인 실패' == app._boundary_status.get()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._delete_boundaries()
            assert boundaries.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._delete_boundaries()
            assert not boundaries.exists() and not settings.exists()
            print('GUI stage35 operator boundaries smoke: PASS')
        finally:
            app.destroy()
