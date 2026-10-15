import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.conversation_continuity import check_continuity, check_saved_continuity
from ai_broadcaster.response_records import ResponseRecord, ResponseRecordStore, ResponseSnapshot

class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'records.sqlite3'
        self.store = ResponseRecordStore(self.path)
        self.rows = tuple(ResponseRecord('a'*32, i, '가', f'입력{i}', f'응답{i}') for i in range(1, 12))

    def test_no_automatic_file(self):
        self.assertFalse(self.path.exists())
        with self.assertRaises(ValueError):
            check_saved_continuity(self.store, '나: 안녕')
        self.assertFalse(self.path.exists())

    def test_window_and_duplicates(self):
        report = check_continuity(self.rows, '나: 반복\n나: 반복')
        self.assertTrue(report.passed)
        self.assertEqual([x[1] for x in report.checks], [8, 8])

    def test_save_then_read_only(self):
        self.store.save(ResponseSnapshot(self.rows, 11), confirmed=True)
        before = self.path.read_bytes()
        report = check_saved_continuity(self.store, '나: 새 대화')
        self.assertTrue(report.passed)
        self.assertEqual(report.saved_count, 11)
        self.assertEqual(before, self.path.read_bytes())

    def test_reject_mixed_sessions(self):
        with self.assertRaises(ValueError):
            check_continuity((self.rows[0], ResponseRecord('b'*32, 2, '가','a','b')), '나: hi')

    def test_reject_out_of_order(self):
        with self.assertRaises(ValueError):
            check_continuity((self.rows[1], self.rows[0]), '나: hi')

    def test_reject_empty_or_bad_script(self):
        for script in ('', 'invalid', 'x'*10001):
            with self.subTest(script=script[:10]), self.assertRaises(ValueError):
                check_continuity(self.rows, script)

    def test_latest_session_only(self):
        other = ResponseRecord('b'*32, 1, '다', '최근', '응답')
        self.store.save(ResponseSnapshot(self.rows + (other,), 11), confirmed=True)
        result = check_saved_continuity(self.store, '나: 다음')
        self.assertEqual(result.saved_count, 1)

if __name__ == '__main__':
    unittest.main()
