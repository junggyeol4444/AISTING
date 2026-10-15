"""Stage 072 real Tk offline canvas smoke, no external connection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import tkinter as tk
from ai_broadcaster.offline_broadcast_scene import BroadcastSceneDraft
from ai_broadcaster.avatar_layout import AvatarLayout
from ai_broadcaster.offline_avatar_screen_link import inspect_avatar_screen_link
root = tk.Tk()
root.withdraw()
canvas = tk.Canvas(root, width=640, height=360)
canvas.pack()
try:
    base = dict(platforms=(), content='chat', voice='windows_system', persona_name='아이스팅')
    two = inspect_avatar_screen_link(canvas, BroadcastSceneDraft(**base, avatar='2d', layout=AvatarLayout()))
    assert two.linked_sample, two
    three = inspect_avatar_screen_link(canvas, BroadcastSceneDraft(**base, avatar='3d'))
    assert not three.linked_sample
    assert 'aisting_sample_2d' not in {tag for item in canvas.find_all() for tag in canvas.gettags(item)}
    print('Stage 072 real Tk Canvas 2D link / 3D no-fallback: PASS')
finally:
    root.destroy()
