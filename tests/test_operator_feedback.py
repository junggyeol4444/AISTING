"""Stage 039, explicitly operator-authored pending changes; no auto application."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.operator_feedback import (
    CATEGORIES, MAX_ENTRIES, MAX_TEXT, MAX_BYTES, draft_feedback,
    feedback_path, add_feedback, revise_feedback, delete_feedback, list_feedback,
)


class OperatorFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = feedback_path(Path(self.temp.name))
        self.draft = draft_feedback('말투', '모의 응답이 너무 딱딱했음', '더 편안한 문장으로 변경 요청')

    def test_no_auto_io_on_draft_or_preview(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')):
            self.assertIn('검토 대기', self.draft.describe())
            self.assertEqual(self.draft.sequence, 0)
            self.assertEqual(list_feedback(self.path), ())
        self.assertFalse(self.path.exists())

    def test_categories_and_exact_trim(self):
        for category in CATEGORIES:
            record = draft_feedback(category, '  상황  ', '  요청  ')
            self.assertEqual((record.category, record.observation, record.requested_change),
                             (category, '상황', '요청'))
        self.assertIn('아직', self.draft.describe())

    def test_invalid_inputs(self):
        for category, obs, wanted in [(None, 'x', 'y'), ('자체판단', 'x', 'y'),
                                      ('말투', '', 'y'), ('말투', 'x', '  '),
                                      ('말투', 'a'*(MAX_TEXT+1), 'y'),
                                      ('말투', 'x', 'a\nb'), ('말투', 'x', 'y\x00z'),
                                      ('말투', ['x'], 'y'), ('말투', 'x', False)]:
            with self.subTest(category=category, obs=obs, wanted=wanted):
                with self.assertRaises(ValueError):
                    draft_feedback(category, obs, wanted)

    def test_manual_confirmation_required(self):
        with self.assertRaises(PermissionError):
            add_feedback(self.path, self.draft)
        with self.assertRaises(PermissionError):
            revise_feedback(self.path, 1, self.draft)
        with self.assertRaises(PermissionError):
            delete_feedback(self.path, 1)
        self.assertFalse(self.path.exists())

    def test_add_revise_delete_order_and_nonreuse(self):
        first = add_feedback(self.path, self.draft, operator_confirmed=True)
        second = add_feedback(self.path, self.draft, operator_confirmed=True)
        self.assertEqual((first.sequence, second.sequence), (1, 2))
        revision = draft_feedback('채팅 반응', '너무 짧음', '더 구체적으로')
        changed = revise_feedback(self.path, 1, revision, operator_confirmed=True)
        self.assertEqual((changed.sequence, changed.category), (1, '채팅 반응'))
        self.assertEqual([record.sequence for record in list_feedback(self.path)], [1, 2])
        self.assertEqual(list_feedback(self.path)[1], second)
        self.assertTrue(delete_feedback(self.path, 1, operator_confirmed=True))
        self.assertFalse(delete_feedback(self.path, 1, operator_confirmed=True))
        third = add_feedback(self.path, self.draft, operator_confirmed=True)
        self.assertEqual(third.sequence, 3)
        self.assertEqual([record.sequence for record in list_feedback(self.path)], [2, 3])
        self.assertFalse((Path(self.temp.name) / 'settings.json').exists())
        self.assertFalse((Path(self.temp.name) / 'conversation.sqlite3').exists())

    def test_unknown_revision_does_not_modify(self):
        add_feedback(self.path, self.draft, operator_confirmed=True)
        original = self.path.read_bytes()
        for seq in (0, -1, 5, True, '1'):
            with self.subTest(seq=seq), self.assertRaises(ValueError):
                revise_feedback(self.path, seq, self.draft, operator_confirmed=True)
            self.assertEqual(self.path.read_bytes(), original)

    def test_add_invalid_draft_does_not_modify(self):
        add_feedback(self.path, self.draft, operator_confirmed=True)
        original = self.path.read_bytes()
        for item in ('foo', None, self.draft.__class__(9, '말투', '문제', '변경')):
            with self.subTest(item=item), self.assertRaises(ValueError):
                add_feedback(self.path, item, operator_confirmed=True)
            self.assertEqual(self.path.read_bytes(), original)

    def test_capacity_and_rejected_oversize_preserve(self):
        for _ in range(MAX_ENTRIES):
            add_feedback(self.path, self.draft, operator_confirmed=True)
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            add_feedback(self.path, self.draft, operator_confirmed=True)
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual(len(list_feedback(self.path)), MAX_ENTRIES)

    def test_corrupt_schema_rejected_no_overwrite(self):
        original_cases = [
            {'schema_version': True, 'next_sequence': 1, 'requests': []},
            {'schema_version': 2, 'next_sequence': 1, 'requests': []},
            {'schema_version': 1, 'next_sequence': True, 'requests': []},
            {'schema_version': 1, 'next_sequence': 1, 'requests': [
                {'sequence': 1, 'category': '말투', 'observation': 'x', 'requested_change': 'y'}]},
            {'schema_version': 1, 'next_sequence': 3, 'requests': [
                {'sequence': 2, 'category': '말투', 'observation': 'x', 'requested_change': 'y'},
                {'sequence': 1, 'category': '말투', 'observation': 'x', 'requested_change': 'y'}]},
            {'schema_version': 1, 'next_sequence': 1, 'requests': [], 'extra': 'x'},
        ]
        for value in original_cases:
            content = json.dumps(value).encode()
            self.path.write_bytes(content)
            with self.subTest(value=value), self.assertRaises(ValueError):
                list_feedback(self.path)
            with self.assertRaises(ValueError):
                add_feedback(self.path, self.draft, operator_confirmed=True)
            self.assertEqual(self.path.read_bytes(), content)

    def test_corruption_and_size_limit(self):
        for raw in (b'\xff', b'{', b'x' * (MAX_BYTES + 1)):
            with self.subTest(raw=raw[:5]):
                self.path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    list_feedback(self.path)
                self.assertEqual(raw, self.path.read_bytes())

    def test_symlink_refusal(self):
        outside = Path(self.temp.name) / 'outside.txt'
        outside.write_text('keep', encoding='utf-8')
        try:
            self.path.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unsupported')
        for operation in (lambda: list_feedback(self.path),
                          lambda: add_feedback(self.path, self.draft, operator_confirmed=True),
                          lambda: delete_feedback(self.path, 1, operator_confirmed=True)):
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual(outside.read_text(encoding='utf-8'), 'keep')

    def test_no_network_or_pc_inspection(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('PC process')):
            one = add_feedback(self.path, self.draft, operator_confirmed=True)
            self.assertEqual(list_feedback(self.path), (one,))
            self.assertTrue(delete_feedback(self.path, 1, operator_confirmed=True))


if __name__ == '__main__':
    unittest.main()
