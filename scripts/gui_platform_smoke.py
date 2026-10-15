"""Xvfb/Windows에서 플랫폼 0~3개를 수동 GUI 설정처럼 선택하고 저장한다.

OBS, 실제 방송, GitHub, 외부 채팅 플랫폼에 연결하지 않는다.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.offline_settings import load_settings, save_settings, PLATFORMS
from ai_broadcaster.desktop import AistingApp


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        settings_path = Path(tmp) / 'settings.json'
        # 앱 UI가 실제 로컬 설정 파일을 읽고 쓸 수 있게 경로만 임시 격리.
        with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings_path)), \
             patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings_path)):
            app = AistingApp()
            try:
                app.update()
                assert len(app._platforms) == 3
                assert all(not flag.get() for flag in app._platforms.values())

                for code in ('chzzk', 'twitch'):
                    app._platforms[code].set(True)
                app._save()
                assert load_settings(settings_path)['platforms'] == ['chzzk', 'twitch']
                assert not load_settings(settings_path)['streaming_enabled']

                app._platforms['chzzk'].set(False)
                app._platforms['twitch'].set(False)
                app._platforms['youtube'].set(True)
                app._save()
                assert load_settings(settings_path)['platforms'] == ['youtube']

                app._platforms['youtube'].set(False)
                app._save()
                assert load_settings(settings_path)['platforms'] == []
                app.update()
                print('GUI 플랫폼 미선택/복수 선택/변경/해제 및 로컬 저장: 통과')
            finally:
                app._shutdown()


if __name__ == '__main__':
    main()
