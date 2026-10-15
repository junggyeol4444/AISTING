"""Regression: a completed reply must not be lost to a late memory-save failure.

No external services, Windows machine, or real viewer data are used.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.offline_chat import ChatRehearsal, LocalMemory


class MemoryFailureReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'conversation.sqlite3'
        self.memory = LocalMemory(self.path)

    def test_replaced_db_after_delivery_is_preserved_and_reported(self):
        runner = ChatRehearsal(memory=self.memory)
        runner.add_script('가상시청자: 첫 질문\n가상시청자: 두 번째 질문')
        delivered = []

        def swap_after_delivery(answer):
            delivered.append(answer)
            if len(delivered) == 1:
                self.path.unlink()
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute('CREATE TABLE unrelated (secret TEXT)')
                    db.execute("INSERT INTO unrelated VALUES ('KEEP')")

        runner.process_next(swap_after_delivery)
        self.assertEqual(len(delivered), 1)
        self.assertEqual(len(runner.pending), 1)
        self.assertEqual(len(runner.completed), 1)
        self.assertEqual(len(runner.memory_errors), 1)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT secret FROM unrelated').fetchall(), [('KEEP',)])
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE name='history'").fetchall(), [])

    def test_sqlite_error_after_delivery_is_reported(self):
        runner = ChatRehearsal(memory=self.memory)
        runner.add_script('가상시청자: 질문')
        with patch.object(self.memory, 'append', side_effect=sqlite3.OperationalError('simulated write error')):
            answer = runner.process_next(lambda _: None)
        self.assertIsNotNone(answer)
        self.assertEqual(len(runner.completed), 1)
        self.assertEqual(len(runner.memory_errors), 1)

    def test_normal_save_has_no_error(self):
        runner = ChatRehearsal(memory=self.memory)
        runner.add_script('가상시청자: 정상 저장')
        runner.process_next(lambda _: None)
        self.assertEqual(runner.memory_errors, [])
        self.assertEqual(self.memory.recent()[0].original.text, '정상 저장')


if __name__ == '__main__':
    unittest.main()
