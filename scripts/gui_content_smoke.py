"""Tk 실제 선택 컨트롤/로컬 저장 확인. Linux Xvfb 또는 Windows GUI에서 수동 실행."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.offline_settings import CONTENTS, load_settings, save_settings
from ai_broadcaster.desktop import AistingApp


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'settings.json'
        with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(path)), \
             patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, path)), \
             patch('socket.create_connection') as network:
            app = AistingApp()
            try:
                app.update()
                assert app._content.get() == '미정', 'Content default must be undecided'
                for label, code in CONTENTS.items():
                    app._content.set(label)
                    app.update()
                    assert app._content_preview.get(), 'Content preview missing'
                    app._save()
                    setting = load_settings(path)
                    assert setting['content'] == code, 'Saved content mismatch'
                    assert not setting['streaming_enabled'], 'Content must not start stream'
                    assert not setting['scheduled_execution'], 'Content must not schedule'
                app._content.set('게임')
                app._platforms['chzzk'].set(True)
                app._platforms['youtube'].set(True)
                app._save()
                combined = load_settings(path)
                assert combined['content'] == 'game'
                assert combined['platforms'] == ['chzzk','youtube']
                network.assert_not_called()
                print('GUI 콘텐츠 미선택/수다/게임/둘 다/변경 및 복수 플랫폼 혼합: 통과')
            finally:
                app._shutdown()


if __name__ == '__main__':
    main()
