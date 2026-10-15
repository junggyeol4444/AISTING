import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.operator_boundaries import (
    review_boundaries, validate_boundaries, boundaries_path,
    save_boundaries, load_boundaries, delete_boundaries, MAX_LINES,
)
from ai_broadcaster.offline_settings import DEFAULTS


class OperatorBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = boundaries_path(Path(self.temp.name))

    def test_empty_no_invented_taboo(self):
        report = review_boundaries('default', DEFAULTS['persona'], [])
        self.assertTrue(report.passed)
        self.assertNotIn('금기·제한사항 (선택):', report.guidance)

    def test_custom_and_order(self):
        persona = {'name': '겨울', 'character': '차분함', 'style': '친근한 말투'}
        values = ['스포일러 언급하지 않기', '후원 금액 추측하지 않기']
        report = review_boundaries('custom', persona, values, '수다', '과장')
        self.assertTrue(report.passed)
        self.assertLess(report.guidance.index(values[0]), report.guidance.index(values[1]))
        for item in ('겨울', '차분함', '친근한 말투', '수다', '과장'):
            self.assertIn(item, report.guidance)
        self.assertEqual(values, ['스포일러 언급하지 않기', '후원 금액 추측하지 않기'])

    def test_input_rejection(self):
        invalid = [None, '문장', [''], [' \t'], ['a'*201], ['a\x00b'], ['a\nb'],
                   ['a', ' a '], ['x']*(MAX_LINES+1), [1], {'a': 'b'}]
        for case in invalid:
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate_boundaries(case)

    def test_save_requires_confirmation(self):
        with self.assertRaises(PermissionError):
            save_boundaries(self.path, ['원본 유지'])
        self.assertFalse(self.path.exists())

    def test_delete_requires_confirmation(self):
        save_boundaries(self.path, ['유지'], operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_boundaries(self.path)
        self.assertEqual(load_boundaries(self.path), ('유지',))

    def test_save_load_delete_roundtrip(self):
        values = ['실존인물 이름 언급 금지', '출처 없는 사실 단정 금지']
        save_boundaries(self.path, values, operator_confirmed=True)
        self.assertEqual(load_boundaries(self.path), tuple(values))
        self.assertTrue(delete_boundaries(self.path, operator_confirmed=True))
        self.assertIsNone(load_boundaries(self.path))
        self.assertFalse(delete_boundaries(self.path, operator_confirmed=True))

    def test_invalid_save_preserves_old(self):
        save_boundaries(self.path, ['원래 값'], operator_confirmed=True)
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            save_boundaries(self.path, ['a'*201], operator_confirmed=True)
        self.assertEqual(self.path.read_bytes(), original)

    def test_tampered_schema_rejected(self):
        for payload in ({'schema_version': True, 'source': 'operator_input', 'boundaries': []},
                        {'schema_version': 1, 'source': 'external', 'boundaries': []},
                        {'schema_version': 1, 'source': 'operator_input', 'boundaries': [], 'extra': 1},
                        {'schema_version': 1, 'source': 'operator_input', 'boundaries': 'x'}):
            with self.subTest(payload=payload):
                self.path.write_text(json.dumps(payload), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_boundaries(self.path)

    def test_malformed_and_oversize_rejected(self):
        for payload in (b'{oops', b'a'*10000, b'\xff'):
            self.path.write_bytes(payload)
            with self.assertRaises(ValueError):
                load_boundaries(self.path)

    def test_symlink_rejected(self):
        outside = Path(self.temp.name) / 'outside.json'
        outside.write_text('not boundaries', encoding='utf-8')
        try:
            self.path.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unsupported')
        with self.assertRaises(ValueError):
            load_boundaries(self.path)
        with self.assertRaises(ValueError):
            save_boundaries(self.path, ['우회'], operator_confirmed=True)
        with self.assertRaises(ValueError):
            delete_boundaries(self.path, operator_confirmed=True)
        self.assertEqual(outside.read_text(encoding='utf-8'), 'not boundaries')

    def test_no_unrequested_io(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')):
            report = review_boundaries('default', DEFAULTS['persona'], ['운영자 직접 입력'])
            self.assertTrue(report.passed)
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
