"""Read-only concurrent chat regression (fake transports; no live accounts)."""
import sys
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.multi_platform_session import MultiPlatformReadOnlySession
from ai_broadcaster.multiplatform_readonly import PlatformChat
from ai_broadcaster.twitch_readonly import TwitchChatLine


class MultiChatTests(unittest.TestCase):
    def test_2000_fifo_and_duplicates(self):
        channels = {"twitch":"tester", "chzzk":"a"*32,
                    "soop":"streamer/123", "youtube":"livechat"}
        events = []
        class Reader:
            def __init__(self, channel, emit, api_key=None):
                self.channel, self.emit = channel, emit
            def run(self, *, max_seconds=None):
                code = next(k for k,v in channels.items() if v==self.channel)
                for i in range(500):
                    item = (TwitchChatLine(self.channel,"viewer",str(i))
                            if code=="twitch" else
                            PlatformChat(self.channel,"viewer",str(i),code))
                    self.emit("chat", item)
            def stop(self):
                pass
        mod="ai_broadcaster.multi_platform_session."
        with patch(mod+"TwitchReadOnlySession",Reader), patch(
             mod+"ChzzkReadOnlySession",Reader), patch(
             mod+"SoopReadOnlySession",Reader), patch(
             mod+"YouTubeReadOnlySession",Reader):
            MultiPlatformReadOnlySession(
                channels,lambda k,v:events.append((k,v)),
                youtube_api_key="k"*39).run(max_seconds=2)
        grouped=defaultdict(list)
        for kind,value in events:
            if kind=="chat":
                grouped[value.platform].append(value.text)
        self.assertEqual(set(grouped),set(channels))
        for code in channels:
            self.assertEqual(grouped[code],list(map(str,range(500))))

    def test_invalid_and_replay(self):
        with self.assertRaises(ValueError):
            MultiPlatformReadOnlySession({},lambda *_:None)
        class Reader:
            def __init__(self, channel, emit):
                pass
            def run(self, *, max_seconds=None):
                pass
            def stop(self):
                pass
        with patch("ai_broadcaster.multi_platform_session.TwitchReadOnlySession",Reader):
            s=MultiPlatformReadOnlySession({"twitch":"tester"},lambda *_:None)
            s.run(max_seconds=1)
            with self.assertRaises(RuntimeError):
                s.run(max_seconds=1)
