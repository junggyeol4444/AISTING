"""Original 051: avatar model metadata is never real authorization."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.avatar_preparation import (
    AvatarPreparation, ORIGINS, preparation_path, save_preparation,
    load_preparation, delete_preparation, validate_preparation_record, MAX_BYTES,
)


class AvatarPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = preparation_path(self.root)
        self.draft = AvatarPreparation('2d', 'self_created', '내 아바타', True, True, True, '권리 직접 확인')

    def test_empty_selection_is_pending(self):
        d = AvatarPreparation('undecided')
        self.assertFalse(d.checklist_ready)
        self.assertIn('미정', d.describe())

    def test_two_types_have_distinct_drafts(self):
        for code in ('2d', '3d'):
            d = AvatarPreparation(code, 'licensed', '모델 A', True, True, True)
            self.assertTrue(d.checklist_ready)
            self.assertIn('실제 사용 승인 대기', d.describe())

    def test_no_automatic_license_verification(self):
        self.assertNotIn('법적 진위가 확인', self.draft.describe())
        self.assertIn('법적 진위', self.draft.describe())

    def test_missing_flags_never_ready(self):
        for flags in ((False, True, True), (True, False, True), (True, True, False)):
            self.assertFalse(AvatarPreparation('3d', 'licensed', '모델', *flags).checklist_ready)
        self.assertFalse(AvatarPreparation('2d', 'undecided', '모델', True, True, True).checklist_ready)
        self.assertFalse(AvatarPreparation('2d', 'self_created', '', True, True, True).checklist_ready)

    def test_reject_invalid_type_origin(self):
        for val in ('vrm', 'VRM', '', None, 2):
            with self.subTest(val=val), self.assertRaises(ValueError):
                AvatarPreparation(val)
        for val in ('server', None, 4):
            with self.subTest(val=val), self.assertRaises(ValueError):
                AvatarPreparation('2d', val)

    def test_reject_undecided_with_attestations(self):
        for kwargs in ({'origin':'self_created'}, {'alias':'모델'}, {'rights_reviewed':True},
                       {'display_permission_reviewed': True}, {'evidence_reviewed':True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                AvatarPreparation('undecided', **kwargs)

    def test_reject_paths_urls_and_control_alias(self):
        for alias in ('C:\\model.vrm', '/home/model', '../x', 'https://example.net',
                      'a|b', 'x@y', 'a\nb', 'q' * 49):
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                AvatarPreparation('3d', alias=alias)

    def test_reject_note_controls_and_invalid_flags(self):
        for note in ('hello\nworld', '\t', 'a'*201):
            with self.assertRaises(ValueError):
                AvatarPreparation('2d', note=note)
        for val in (1, 'true', None):
            with self.assertRaises(ValueError):
                AvatarPreparation('2d', rights_reviewed=val)

    def test_save_requires_explicit_bool(self):
        for val in (False, None, 1, 'yes'):
            with self.assertRaises(PermissionError):
                save_preparation(self.file, self.draft, operator_confirmed=val)
        self.assertFalse(self.file.exists())

    def test_round_trip_and_permission_fields_false(self):
        save_preparation(self.file, self.draft, operator_confirmed=True)
        self.assertEqual(load_preparation(self.file, selected_avatar='2d'), self.draft)
        record = json.loads(self.file.read_text('utf-8'))
        for key in ('model_file_accessed', 'license_verified', 'rendering_authorized',
                    'broadcast_authorized', 'pc_inspected'):
            self.assertIs(record[key], False)
        self.assertNotIn('model_path', record)

    def test_load_missing_creates_no_directory(self):
        path = self.root / 'uncreated' / 'draft.json'
        self.assertIsNone(load_preparation(path, selected_avatar='2d'))
        self.assertFalse(path.parent.exists())

    def test_reject_cross_avatar_reuse(self):
        save_preparation(self.file, self.draft, operator_confirmed=True)
        with self.assertRaisesRegex(ValueError, '다릅니다'):
            load_preparation(self.file, selected_avatar='3d')
        with self.assertRaises(ValueError):
            load_preparation(self.file, selected_avatar='bad')
        self.assertTrue(self.file.exists())

    def test_reject_modified_privilege_flag(self):
        save_preparation(self.file, self.draft, operator_confirmed=True)
        data = json.loads(self.file.read_text('utf-8'))
        for field in ('model_file_accessed', 'license_verified', 'rendering_authorized',
                      'broadcast_authorized', 'pc_inspected'):
            modified = dict(data, **{field: True})
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_preparation_record(modified)

    def test_reject_unknown_keys_or_wrong_schema(self):
        save_preparation(self.file, self.draft, operator_confirmed=True)
        data = json.loads(self.file.read_text('utf-8'))
        for change in (dict(data, surprise='yes'), dict(data, schema_version=True),
                       dict(data, kind='approved')):
            with self.assertRaises(ValueError):
                validate_preparation_record(change)

    def test_reject_invalid_record_without_overwrite(self):
        save_preparation(self.file, self.draft, operator_confirmed=True)
        before = self.file.read_bytes()
        with self.assertRaises(ValueError):
            save_preparation(self.file, AvatarPreparation('2d', note='x\n'), operator_confirmed=True)
        self.assertEqual(self.file.read_bytes(), before)

    def test_corrupt_oversized_and_invalid_utf8(self):
        for raw in (b'{', b'\xff\xfe', b'x'*(MAX_BYTES+1)):
            with self.subTest(raw=raw[:4]):
                self.file.write_bytes(raw)
                with self.assertRaises(ValueError):
                    load_preparation(self.file, selected_avatar='2d')

    def test_safe_symlink_rejection(self):
        real = self.root/'target.json'
        real.write_text('safe', encoding='utf-8')
        link = self.root/'link.json'
        try:
            link.symlink_to(real)
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            save_preparation(link, self.draft, operator_confirmed=True)
        with self.assertRaises(ValueError):
            load_preparation(link, selected_avatar='2d')
        with self.assertRaises(ValueError):
            delete_preparation(link, operator_confirmed=True)
        self.assertEqual(real.read_text('utf-8'), 'safe')

    def test_delete_needs_confirm(self):
        save_preparation(self.file, self.draft, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_preparation(self.file)
        self.assertTrue(self.file.exists())
        self.assertTrue(delete_preparation(self.file, operator_confirmed=True))
        self.assertFalse(delete_preparation(self.file, operator_confirmed=True))

    def test_no_network_or_db_access(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')):
            self.assertFalse(AvatarPreparation('3d').checklist_ready)
            save_preparation(self.file, self.draft, operator_confirmed=True)
            self.assertEqual(load_preparation(self.file, selected_avatar='2d'), self.draft)


if __name__ == '__main__':
    unittest.main()
