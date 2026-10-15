"""28단계: 응답 기록의 수동 동의·중복 방지·비파괴 SQLite·오프라인 회귀."""
from __future__ import annotations

import copy
from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.core_execution import OfflineCoreSession, CoreBatchError
from ai_broadcaster.offline_settings import DEFAULTS
from ai_broadcaster.response_records import (
    APP_ID, MAX_READ, ResponseRecord, ResponseRecordStore, ResponseSnapshot,
    snapshot_core_responses, response_records_path,
)


class FailingPort:
    def __init__(self):
        self.calls = 0

    def generate(self, item, history):
        self.calls += 1
        if self.calls == 2:
            raise TimeoutError("private token")
        return "정상 답변"


class ResponseRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "user" / "core_response_records.sqlite3"
        self.store = ResponseRecordStore(self.path)
        self.settings = copy.deepcopy(DEFAULTS)
        self.session = OfflineCoreSession(self.settings)

    def prepare(self, script="가: 안녕\n가: 안녕\n나: 반가워"):
        self.session.enqueue(script)
        self.session.run_batch()
        return snapshot_core_responses(self.session)

    def test_construct_store_no_files(self):
        self.assertFalse(self.path.parent.exists())
        self.assertFalse(self.path.exists())

    def test_path_computation_no_folder_creation(self):
        with patch("ai_broadcaster.response_records.data_dir", return_value=self.path.parent):
            self.assertEqual(response_records_path(), self.path.parent / "core_response_records.sqlite3")
        self.assertFalse(self.path.parent.exists())

    def test_no_automatic_snapshot_on_core_execution(self):
        self.session.enqueue("가: 안녕")
        self.session.run_batch()
        self.assertIsNone(self.session._response_recording_key)
        self.assertFalse(self.path.exists())

    def test_snapshot_only_successful_fifo_duplicates(self):
        snapshot = self.prepare()
        self.assertEqual([x.sender for x in snapshot.records], ["가", "가", "나"])
        self.assertEqual([x.turn_no for x in snapshot.records], [1, 2, 3])
        self.assertEqual(snapshot.records[0].input_text, snapshot.records[1].input_text)
        self.assertEqual(snapshot.total_processed, 3)
        self.assertFalse(self.path.exists())

    def test_snapshot_empty_refused_without_side_effects(self):
        with self.assertRaises(ValueError):
            snapshot_core_responses(self.session)
        self.assertIsNone(self.session._response_recording_key)
        self.assertFalse(self.path.exists())

    def test_snapshot_invalid_session(self):
        for obj in (None, "test", object()):
            with self.subTest(obj=obj), self.assertRaises(TypeError):
                snapshot_core_responses(obj)

    def test_snapshot_description_is_preview_only(self):
        snap = self.prepare()
        self.assertIn("아직 파일 생성 없음", snap.describe())
        self.assertIn("실패·대기", snap.describe())
        self.assertFalse(self.path.exists())

    def test_snapshot_over_five_truncates_preview_not_data(self):
        snap = self.prepare("\n".join(f"가: {i}" for i in range(10)))
        self.assertEqual(len(snap.records), 10)
        self.assertIn("이하 5건", snap.describe())
        self.assertFalse(self.path.exists())

    def test_confirm_strict_true(self):
        snap = self.prepare()
        for confirmed in (False, 1, "yes", None):
            with self.subTest(confirmed=confirmed), self.assertRaises(PermissionError):
                self.store.save(snap, confirmed=confirmed)
        self.assertFalse(self.path.parent.exists())

    def test_persist_reopen_korean(self):
        snap = self.prepare()
        result = self.store.save(snap, confirmed=True)
        self.assertEqual((result.inserted, result.already_saved, result.total_in_file), (3, 0, 3))
        reopened = ResponseRecordStore(self.path).recent(10)
        self.assertEqual(reopened, tuple(reversed(snap.records)))

    def test_repeated_save_idempotent(self):
        snap = self.prepare()
        self.store.save(snap, confirmed=True)
        result = self.store.save(snap, confirmed=True)
        self.assertEqual((result.inserted, result.already_saved, result.total_in_file), (0, 3, 3))

    def test_incremental_save_only_new_rows(self):
        self.session.enqueue("가: 첫 번째")
        self.session.run_batch()
        first = snapshot_core_responses(self.session)
        self.store.save(first, confirmed=True)
        self.session.enqueue("가: 첫 번째\n나: 두 번째")
        self.session.run_batch()
        second = snapshot_core_responses(self.session)
        result = self.store.save(second, confirmed=True)
        self.assertEqual((result.inserted, result.already_saved, result.total_in_file), (2, 1, 3))

    def test_failed_pending_not_archived(self):
        session = OfflineCoreSession(self.settings, FailingPort())
        session.enqueue("가: 성공\n나: 실패\n다: 대기")
        with self.assertRaises(CoreBatchError):
            session.run_batch()
        snap = snapshot_core_responses(session)
        self.assertEqual([x.input_text for x in snap.records], ["성공"])
        self.store.save(snap, confirmed=True)
        self.assertEqual([x.input_text for x in self.store.recent()], ["성공"])
        self.assertEqual(session.pending_count, 2)

    def test_snapshot_after_reset_new_key(self):
        first = self.prepare("가: 동일")
        self.store.save(first, confirmed=True)
        self.session.reset()
        self.session.enqueue("가: 동일")
        self.session.run_batch()
        second = snapshot_core_responses(self.session)
        self.assertNotEqual(first.records[0].session_key, second.records[0].session_key)
        self.assertEqual(self.store.save(second, confirmed=True).total_in_file, 2)

    def test_session_selection_changes_preserved(self):
        snap = self.prepare("가: 처음")
        self.settings["platforms"] = ["youtube", "twitch"]
        self.settings["content"] = "game"
        self.settings["avatar"] = "3d"
        self.session.update_selection(self.settings)
        self.assertEqual(snapshot_core_responses(self.session), snap)
        self.store.save(snap, confirmed=True)
        self.assertEqual(self.session.blueprint.platforms, ("youtube", "twitch"))
        self.assertEqual(self.session.blueprint.avatar, "3d")

    def test_original_settings_not_changed(self):
        original = copy.deepcopy(self.settings)
        self.store.save(self.prepare(), confirmed=True)
        self.assertEqual(self.settings, original)

    def test_no_existing_file_read_does_not_create(self):
        self.assertEqual(self.store.recent(), ())
        self.assertFalse(self.path.parent.exists())

    def test_recent_invalid_limit_no_io(self):
        for n in (-1, 0, 101, 1.0, True, "5"):
            with self.subTest(n=n), self.assertRaises(ValueError):
                self.store.recent(n)
        self.assertFalse(self.path.parent.exists())

    def test_recent_limit_and_descending(self):
        self.store.save(self.prepare(), confirmed=True)
        self.assertEqual([x.turn_no for x in self.store.recent(2)], [3, 2])
        self.assertEqual(len(self.store.recent(MAX_READ)), 3)

    def test_unknown_file_not_overwritten(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b"my precious notes")
        before = self.path.read_bytes()
        with self.assertRaises((ValueError, sqlite3.DatabaseError)):
            self.store.save(self.prepare(), confirmed=True)
        self.assertEqual(self.path.read_bytes(), before)

    def test_existing_foreign_sqlite_not_modified(self):
        self.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE user_data (value TEXT)")
            db.execute("INSERT INTO user_data VALUES ('important')")
        with self.assertRaises(ValueError):
            self.store.save(self.prepare(), confirmed=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute("SELECT value FROM user_data").fetchone(), ("important",))
            self.assertEqual(db.execute("PRAGMA application_id").fetchone()[0], 0)

    def test_sqlite_handles_closed_after_save_read_and_clear(self):
        # sqlite3.Connection.__exit__ commits/rolls back, but DOES NOT close.
        # Track real connections to prove all production operations close them.
        real_connect = sqlite3.connect
        observed = []

        def track(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            observed.append(connection)
            return connection

        with patch("ai_broadcaster.response_records.sqlite3.connect", side_effect=track):
            self.store.save(self.prepare(), confirmed=True)
            self.store.recent()
            self.store.clear(confirmed=True)
        self.assertGreaterEqual(len(observed), 3)
        for connection in observed:
            with self.subTest(connection=repr(connection)):
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute("SELECT 1")

    def test_readonly_pragma_error_closes_connection(self):
        self.store.save(self.prepare(), confirmed=True)
        class FailedPragma:
            closed = False
            def execute(self, *_args, **_kwargs):
                raise sqlite3.OperationalError("simulated pragma failure")
            def close(self):
                self.closed = True

        connection = FailedPragma()
        with patch("ai_broadcaster.response_records.sqlite3.connect", return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError, "simulated pragma failure"):
                self.store.recent()
        self.assertTrue(connection.closed)

    def test_symlink_file_refused(self):
        self.path.parent.mkdir(parents=True)
        target = self.path.parent / "other.sqlite3"
        target.write_bytes(b"untouched")
        try:
            self.path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links unavailable")
        with self.assertRaises(ValueError):
            self.store.save(self.prepare(), confirmed=True)
        self.assertEqual(target.read_bytes(), b"untouched")

    def test_symlink_parent_refused(self):
        real = Path(self.tmp.name) / "real"
        real.mkdir()
        alias = Path(self.tmp.name) / "alias"
        try:
            alias.symlink_to(real, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links unavailable")
        store = ResponseRecordStore(alias / "data.sqlite3")
        with self.assertRaises(ValueError):
            store.save(self.prepare(), confirmed=True)
        self.assertEqual(list(real.iterdir()), [])

    def test_directory_target_refused(self):
        self.path.mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.store.save(self.prepare(), confirmed=True)

    def test_conflicting_same_key_rejected_without_overwrite(self):
        snap = self.prepare()
        self.store.save(snap, confirmed=True)
        changed = replace(snap.records[1], reply_text="조작")
        corrupted = replace(snap, records=(snap.records[0], changed, snap.records[2]))
        with self.assertRaises(ValueError):
            self.store.save(corrupted, confirmed=True)
        self.assertEqual(self.store.recent(), tuple(reversed(snap.records)))

    def test_conflict_rolls_back_earlier_insert(self):
        snap = self.prepare()
        self.store.save(snap, confirmed=True)
        additional = replace(snap.records[0], turn_no=4)
        conflict = replace(snap.records[1], reply_text="changed")
        batch = ResponseSnapshot((additional, conflict), 4)
        with self.assertRaises(ValueError):
            self.store.save(batch, confirmed=True)
        self.assertEqual(len(self.store.recent()), 3)

    def test_duplicate_snapshot_turn_refused(self):
        snap = self.prepare()
        with self.assertRaises(ValueError):
            self.store.save(replace(snap, records=(snap.records[0], snap.records[0])), confirmed=True)
        self.assertFalse(self.path.exists())

    def test_invalid_snapshot_shape_refused(self):
        snap = self.prepare()
        for value in (None, "bad", replace(snap, records=()),
                      replace(snap, records=list(snap.records)),
                      replace(snap, total_processed=True)):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                self.store.save(value, confirmed=True)
        self.assertFalse(self.path.exists())

    def test_invalid_record_fields_refused(self):
        snap = self.prepare()
        examples = (
            replace(snap.records[0], session_key="bad"),
            replace(snap.records[0], turn_no=0),
            replace(snap.records[0], turn_no=True),
            replace(snap.records[0], sender=""),
            replace(snap.records[0], sender="x" * 101),
            replace(snap.records[0], input_text="x" * 4001),
            replace(snap.records[0], reply_text="x" * 6001),
            replace(snap.records[0], reply_text="bad\x00data"),
        )
        for row in examples:
            with self.subTest(row=row.turn_no), self.assertRaises(ValueError):
                self.store.save(replace(snap, records=(row,)), confirmed=True)
        self.assertFalse(self.path.exists())

    def test_limit_refuses_without_auto_prune(self):
        snap = self.prepare()
        with patch("ai_broadcaster.response_records.MAX_RECORDS", 2):
            with self.assertRaises(ValueError):
                self.store.save(snap, confirmed=True)
        self.assertEqual(self.store.recent(), ())
        self.assertEqual(self.store.save(snap, confirmed=True).inserted, 3)

    def test_clear_requires_exact_confirmation(self):
        snap = self.prepare()
        self.store.save(snap, confirmed=True)
        for confirm in (False, None, 1, "yes"):
            with self.subTest(confirm=confirm), self.assertRaises(PermissionError):
                self.store.clear(confirmed=confirm)
        self.assertEqual(len(self.store.recent()), 3)

    def test_clear_then_new_save(self):
        snap = self.prepare()
        self.store.save(snap, confirmed=True)
        self.assertEqual(self.store.clear(confirmed=True), 3)
        self.assertEqual(self.store.recent(), ())
        self.assertEqual(self.store.clear(confirmed=True), 0)
        self.assertEqual(self.store.save(snap, confirmed=True).inserted, 3)

    def test_clear_missing_does_not_create(self):
        self.assertEqual(self.store.clear(confirmed=True), 0)
        self.assertFalse(self.path.parent.exists())

    def test_foreign_db_clear_refused(self):
        self.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE other (name TEXT)")
        with self.assertRaises(ValueError):
            self.store.clear(confirmed=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE name='other'").fetchone(), ("other",))

    def test_corrupted_table_schema_refused(self):
        self.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(f"PRAGMA application_id={APP_ID}")
            db.execute("CREATE TABLE core_response_records (id INTEGER PRIMARY KEY)")
        with self.assertRaises(ValueError):
            self.store.save(self.prepare(), confirmed=True)
        with self.assertRaises(ValueError):
            self.store.recent()

    def test_no_network_process_pc_info_or_other_db(self):
        snap = self.prepare()
        with patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("PC info")) as pc:
            self.store.save(snap, confirmed=True)
            self.store.recent()
            self.store.clear(confirmed=True)
            net.assert_not_called()
            proc.assert_not_called()
            pc.assert_not_called()

    def test_snapshot_after_history_cap_preserves_original_indices(self):
        for chunk in range(11):
            lines = "\n".join(f"가: {chunk * 50 + i}" for i in range(50))
            self.session.enqueue(lines)
            self.session.run_batch()
        snap = snapshot_core_responses(self.session)
        self.assertEqual(len(snap.records), 500)
        self.assertEqual((snap.records[0].turn_no, snap.records[-1].turn_no), (51, 550))
        self.assertEqual(self.store.save(snap, confirmed=True).inserted, 500)


if __name__ == "__main__":
    unittest.main()
