"""AISTING 장시간 공개 채팅 재연결 회귀검사 (실제 계정/송출 없음)."""
import unittest
from unittest.mock import patch
from test_aisting_multiplatform_session_lifecycle import MockReader, module


class LongReconnectRegression(unittest.TestCase):
    def test_silent_return_reconnects(self):
        created, holder = [], {}
        class Reader(MockReader):
            def __init__(self, channel, callback, *args):
                super().__init__(channel, callback, *args)
                created.append(self)
            def run(self, *, max_seconds=None):
                if len(created) == 2:
                    holder["session"].stop()
        with patch.object(module, "TwitchReadOnlySession", Reader):
            session = module.MultiPlatformReadOnlySession(
                {"twitch": "testchannel"}, lambda *_: None)
            holder["session"] = session
            session._stop.wait = lambda timeout: False
            session.run()
        self.assertEqual(len(created), 2)

    def test_factory_error_does_not_reuse_old_reader(self):
        holder, calls = {}, []
        class Reader(MockReader):
            attempts = 0
            def __init__(self, channel, callback, *args):
                type(self).attempts += 1
                if type(self).attempts == 2:
                    raise OSError("생성 오류")
                super().__init__(channel, callback, *args)
                self.ordinal = type(self).attempts
            def run(self, *, max_seconds=None):
                calls.append(self.ordinal)
                if self.ordinal == 1:
                    raise ConnectionResetError("연결 오류")
                holder["session"].stop()
        with patch.object(module, "TwitchReadOnlySession", Reader):
            session = module.MultiPlatformReadOnlySession(
                {"twitch": "testchannel"}, lambda *_: None)
            holder["session"] = session
            session._stop.wait = lambda timeout: False
            session.run()
        self.assertEqual(Reader.attempts, 3)
        self.assertEqual(calls, [1, 3])


if __name__ == "__main__":
    unittest.main()
