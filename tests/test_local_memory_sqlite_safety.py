"""Offline regression: legacy memory stays usable; unrelated SQLite files stay untouched."""
from __future__ import annotations

from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_broadcaster.offline_chat import Answer, ChatMessage, LocalMemory


class LocalMemorySqliteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "memory" / "conversation.sqlite3"
        self.path.parent.mkdir()

    def _db(self, sql):
        with closing(sqlite3.connect(self.path)) as db, db:
            for statement in sql:
                db.execute(statement)

    def test_foreign_database_is_not_modified(self):
        self._db(["CREATE TABLE other_data (value TEXT)",
                  "INSERT INTO other_data VALUES ('keep')"])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            LocalMemory(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT value FROM other_data").fetchall(), [('keep',)])
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'").fetchall(), [])

    def test_malformed_history_schema_rejected_without_modification(self):
        self._db(["CREATE TABLE history (id INTEGER PRIMARY KEY, wrong TEXT)",
                  "INSERT INTO history(wrong) VALUES ('keep')"])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            LocalMemory(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_same_column_names_but_wrong_types_are_rejected(self):
        self._db(["CREATE TABLE history (id INTEGER PRIMARY KEY, sender BLOB, question TEXT, answer TEXT)"])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            LocalMemory(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_nonzero_sqlite_application_id_rejected(self):
        self._db(["CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL)",
                  "PRAGMA application_id=12345"])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            LocalMemory(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_extra_foreign_tables_rejected_without_modification(self):
        self._db(["CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL)",
                  "CREATE TABLE private_data (value TEXT)",
                  "INSERT INTO private_data VALUES ('keep')"])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            LocalMemory(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_existing_legacy_history_kept_and_append_works(self):
        self._db(["CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL)",
                  "INSERT INTO history(sender,question,answer) VALUES ('옛시청자','기존질문','기존답변')"])
        memory = LocalMemory(self.path)
        self.assertEqual(memory.recent()[0].reply, '기존답변')
        memory.append(Answer(ChatMessage('새시청자', '새질문'), '새답변'))
        self.assertEqual([x.reply for x in LocalMemory(self.path).recent()], ['기존답변', '새답변'])

    def test_symlinked_database_refused_without_target_changes(self):
        real = self.path.parent / 'real.sqlite3'
        with closing(sqlite3.connect(real)) as db, db:
            db.execute("CREATE TABLE keep (value TEXT)")
        before = real.read_bytes()
        try:
            self.path.symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            LocalMemory(self.path)
        self.assertEqual(real.read_bytes(), before)

    def test_symlinked_parent_refused_without_creating_database(self):
        actual = Path(self.temp.name) / 'actual'
        actual.mkdir()
        alias = Path(self.temp.name) / 'alias'
        try:
            alias.symlink_to(actual, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            LocalMemory(alias / 'conversation.sqlite3')
        self.assertEqual(list(actual.iterdir()), [])

    def test_missing_file_after_initialization_is_not_recreated(self):
        memory = LocalMemory(self.path)
        self.path.unlink()
        with self.assertRaises(sqlite3.OperationalError):
            memory.recent()
        self.assertFalse(self.path.exists())

    def test_foreign_database_swapped_after_initialization_is_not_modified(self):
        memory = LocalMemory(self.path)
        self.path.unlink()
        self._db(["CREATE TABLE operator_private (secret TEXT)",
                  "INSERT INTO operator_private VALUES ('keep')"])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            memory.append(Answer(ChatMessage('가', '질문'), '답변'))
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_initialization_cleans_only_new_database(self):
        from unittest.mock import patch
        with patch('ai_broadcaster.offline_chat.sqlite3.connect',
                   side_effect=sqlite3.OperationalError('simulated open failure')):
            with self.assertRaisesRegex(sqlite3.OperationalError, 'simulated open failure'):
                LocalMemory(self.path)
        self.assertFalse(self.path.exists())

    def test_new_database_and_operations_still_work(self):
        memory = LocalMemory(self.path)
        self.assertEqual(memory.recent(), [])
        memory.append(Answer(ChatMessage('가', '질문'), '답변'))
        self.assertEqual([x.reply for x in memory.recent()], ['답변'])
        memory.clear()
        self.assertEqual(memory.recent(), [])


if __name__ == '__main__':
    unittest.main()
