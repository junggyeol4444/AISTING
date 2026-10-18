"""Live2D authenticated pipe recovery regression tests (no live broadcast)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster import original_plan_frontend as frontend


class PipeRecoveryTests(unittest.TestCase):
    def tearDown(self):
        frontend._native_bridge = None

    def test_invalidated_pipe_is_not_reused(self):
        conn = MagicMock()
        frontend._native_bridge = conn
        frontend._invalidate_untrusted_native_bridge(conn)
        self.assertIsNone(frontend._native_bridge)
        conn.close.assert_called_once()

    def test_old_pipe_does_not_replace_new_pipe(self):
        old = MagicMock()
        current = MagicMock()
        frontend._native_bridge = current
        frontend._invalidate_untrusted_native_bridge(old)
        self.assertIs(frontend._native_bridge, current)
        old.close.assert_called_once()
        current.close.assert_not_called()


if __name__ == "__main__":
    unittest.main()
