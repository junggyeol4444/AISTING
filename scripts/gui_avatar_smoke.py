"""화면이 있는 로컬 환경에서 아바타 창 수명/렌더를 검증한다.

OBS, 인터넷, PowerShell, 외부 채팅 플랫폼에 접근하지 않는다.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.avatar_renderer import BACKGROUND_COLORS


def main():
    app=AistingApp()
    try:
        app.update()
        assert app._avatar_capture_window is None
        assert app._avatar_capture_status.get() == '별도 창: 닫힘'
        app._open_avatar_capture()
        app.update()
        win=app._avatar_capture_window
        assert win is not None and win.winfo_exists()
        assert app._avatar_capture_canvas is not None
        assert app._avatar_capture_status.get() == '별도 창: 열림'

        # 두 번 눌러도 별도 창은 한 개만 생성된다.
        app._open_avatar_capture()
        assert win is app._avatar_capture_window

        app._avatar_demo.set(True)
        app._avatar_frame=3
        app._draw_avatar_canvases()
        app.update_idletasks()
        assert app._canvas.find_all()
        assert app._avatar_capture_canvas.find_all()
        app._avatar_demo.set(False)

        app._avatar_capture_background.set('초록색 배경')
        app._draw_avatar_canvases()
        assert app._avatar_capture_canvas.cget('bg') == BACKGROUND_COLORS['초록색 배경']
        assert app._canvas.cget('bg') == BACKGROUND_COLORS['남색 스튜디오']

        app._close_avatar_capture()
        app.update()
        assert app._avatar_capture_window is None
        assert app._avatar_capture_canvas is None
        assert app._avatar_capture_status.get() == '별도 창: 닫힘'
        assert app.winfo_exists() and app._canvas.winfo_exists()

        app._open_avatar_capture()
        assert app._avatar_capture_window.winfo_exists()
        app._shutdown()
        try:
            assert not app.winfo_exists()
        except tk.TclError:
            # destroy() 후 Tk 명령 전체가 해제된 상태도 정상.
            pass
        print('GUI별도창/중복방지/동기화/배경전환/독립닫기/전체종료: 통과')
    finally:
        try:
            if app.winfo_exists():
                app.destroy()
        except Exception:
            pass


if __name__=='__main__':
    main()
