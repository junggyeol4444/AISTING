"""Original 042: manually declared audio-metadata plan, never actual audio access."""
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.voice_material_plan import (
    FILE_NAME, MAX_RECORD_BYTES, MaterialItem, VoiceMaterialDraft,
    parse_material_lines, material_plan_path, validate_plan_record,
    save_material_plan, load_material_plan, delete_material_plan,
)
from ai_broadcaster.voice_rights_review import VoiceRightsReview


class VoiceMaterialPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.path = self.folder / FILE_NAME

    def draft(self):
        return parse_material_lines('인사 샘플 | 12\n질문 샘플 | 24', 'own_recording', '개인정보 없는 메모')

    def test_empty_draft_preview_requires_no_file(self):
        draft = parse_material_lines('', 'undecided')
        self.assertEqual(draft.items, ())
        self.assertIn('출처 미정', draft.outline())
        self.assertFalse(self.path.exists())

    def test_parse_duration_and_order_and_korean_aliases(self):
        draft = self.draft()
        self.assertEqual(draft.total_declared_seconds, 36)
        self.assertEqual(tuple(item.alias for item in draft.items), ('인사 샘플', '질문 샘플'))
        self.assertIn('36초', draft.outline())

    def test_source_choices_not_automatically_approved(self):
        for source in ('undecided', 'windows_system', 'own_recording',
                       'consented_recording', 'licensed_recording'):
            with self.subTest(source=source):
                draft = VoiceMaterialDraft(source, (MaterialItem('샘플', 30),))
                self.assertIn('실물/권리/품질/학습 승인 대기', draft.outline())
        with self.assertRaises(ValueError):
            VoiceMaterialDraft('cloud_service')

    def test_rights_report_is_only_attestation(self):
        draft = self.draft()
        ok = VoiceRightsReview('own_recording', True, True, True, True)
        wrong = VoiceRightsReview('licensed_recording', True, True, True, True)
        self.assertIn('자체 신고 확인', draft.outline(ok))
        self.assertIn('법적 진위 미검증', draft.outline(ok))
        self.assertIn('출처 불일치', draft.outline(wrong))
        self.assertIn('미확인', draft.outline(VoiceRightsReview('own_recording')))

    def test_save_requires_operator_confirmation(self):
        with self.assertRaises(PermissionError):
            save_material_plan(self.path, self.draft())
        with self.assertRaises(PermissionError):
            save_material_plan(self.path, self.draft(), operator_confirmed=1)
        self.assertFalse(self.path.exists())

    def test_cannot_store_empty_draft(self):
        with self.assertRaises(ValueError):
            save_material_plan(self.path, VoiceMaterialDraft('own_recording'), operator_confirmed=True)
        self.assertFalse(self.path.exists())

    def test_save_read_roundtrip_keeps_false_authorizations(self):
        draft = self.draft()
        save_material_plan(self.path, draft, operator_confirmed=True)
        self.assertEqual(load_material_plan(self.path), draft)
        record = json.loads(self.path.read_text('utf-8'))
        self.assertIs(record['audio_files_stored'], False)
        self.assertIs(record['training_authorized'], False)
        self.assertIs(record['broadcast_authorized'], False)
        self.assertEqual(record['kind'], 'operator_metadata_only')
        self.assertNotIn('path', str(record).lower())

    def test_missing_read_does_not_create_anything(self):
        path = self.folder / 'absent-folder' / FILE_NAME
        self.assertIsNone(load_material_plan(path))
        self.assertFalse(path.parent.exists())

    def test_invalid_format_lengths_controls(self):
        for row in ('사본 | 0', '사본 | 601', '사본 | 3.4', '사본 | -4', '사본 | 2초',
                    '사본 | ３', '사본 2', '사본 | 5 | 2', ' | 10'):
            with self.subTest(row=row), self.assertRaises(ValueError):
                parse_material_lines(row, 'own_recording')
        for note in ('a' * 181, 'hello\nthere', '\t'):
            with self.assertRaises(ValueError):
                parse_material_lines('샘플 | 12', 'own_recording', note)

    def test_reject_paths_urls_control_and_duplicate_aliases(self):
        for alias in ('C:\\voice.wav', '../clip', 'https://audio.example', 'clip@x',
                      'a/b', 'a|b', 'a\x00b', 'a' * 49):
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                MaterialItem(alias, 10)
        with self.assertRaises(ValueError):
            parse_material_lines('인사 | 2\n인사 | 4', 'own_recording')
        with self.assertRaises(ValueError):
            parse_material_lines('hello | 2\n HELLO | 4', 'own_recording')

    def test_limits_exact_twenty_and_max_items_plus_one(self):
        valid = '\n'.join(f'별칭{i} | 600' for i in range(20))
        self.assertEqual(parse_material_lines(valid, 'own_recording').total_declared_seconds, 12000)
        with self.assertRaises(ValueError):
            parse_material_lines(valid + '\n초과 | 1', 'own_recording')

    def test_corrupt_unknown_fields_cannot_claim_approval(self):
        save_material_plan(self.path, self.draft(), operator_confirmed=True)
        valid = json.loads(self.path.read_text('utf-8'))
        for patch_fields in ({'schema_version': True}, {'schema_version': 10},
                             {'audio_files_stored': True}, {'training_authorized': True},
                             {'broadcast_authorized': True}, {'kind': 'trainer'},
                             {'extra': 'yes'}, {'source': 'cloud'}, {'items': {}},
                             {'note': None}):
            with self.subTest(fields=patch_fields), self.assertRaises(ValueError):
                validate_plan_record(dict(valid, **patch_fields))
        with self.assertRaises(ValueError):
            validate_plan_record({k: v for k, v in valid.items() if k != 'note'})

    def test_invalid_item_types(self):
        save_material_plan(self.path, self.draft(), operator_confirmed=True)
        valid = json.loads(self.path.read_text('utf-8'))
        for items in ([{'alias': 'x', 'declared_seconds': True}],
                      [{'alias': 'x', 'declared_seconds': 3, 'filepath': 'x'}],
                      ['audio.wav']):
            with self.subTest(items=items), self.assertRaises(ValueError):
                validate_plan_record(dict(valid, items=items))

    def test_oversized_or_corrupt_never_overwritten_automatically(self):
        self.path.write_bytes(b'Z' * (MAX_RECORD_BYTES + 1))
        with self.assertRaises(ValueError):
            load_material_plan(self.path)
        self.path.write_text('invalid json', 'utf-8')
        with self.assertRaises(ValueError):
            load_material_plan(self.path)
        self.assertEqual(self.path.read_text('utf-8'), 'invalid json')

    def test_target_not_allowed_symlink_and_directory(self):
        folder = self.folder / 'directory'
        folder.mkdir()
        with self.assertRaises(ValueError):
            save_material_plan(folder, self.draft(), operator_confirmed=True)
        with self.assertRaises(ValueError):
            load_material_plan(folder)
        link = self.folder / 'linked'
        try:
            link.symlink_to(folder, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        for action in (lambda: load_material_plan(link / FILE_NAME),
                       lambda: save_material_plan(link / FILE_NAME, self.draft(), operator_confirmed=True),
                       lambda: delete_material_plan(link / FILE_NAME, operator_confirmed=True)):
            with self.assertRaises(ValueError):
                action()

    def test_deletion_requires_explicit_confirmation(self):
        save_material_plan(self.path, self.draft(), operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_material_plan(self.path)
        self.assertTrue(self.path.exists())
        self.assertTrue(delete_material_plan(self.path, operator_confirmed=True))
        self.assertFalse(delete_material_plan(self.path, operator_confirmed=True))

    def test_settings_db_voice_rights_are_untouched(self):
        rights = self.folder / 'voice_rights_operator_review.json'
        settings = self.folder / 'settings.json'
        db = self.folder / 'conversation.sqlite3'
        for path in (rights, settings, db):
            path.write_bytes(b'preserve')
        save_material_plan(self.path, self.draft(), operator_confirmed=True)
        load_material_plan(self.path)
        delete_material_plan(self.path, operator_confirmed=True)
        for path in (rights, settings, db):
            self.assertEqual(path.read_bytes(), b'preserve')

    def test_no_external_access_or_pc_probe(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as network, \
             patch('sqlite3.connect', side_effect=AssertionError('db')) as db, \
             patch('subprocess.Popen', side_effect=AssertionError('process')) as proc, \
             patch('platform.system', side_effect=AssertionError('pc_probe')) as probe, \
             patch('time.sleep', side_effect=AssertionError('delay')) as delay:
            draft = self.draft()
            draft.outline()
            save_material_plan(self.path, draft, operator_confirmed=True)
            self.assertEqual(load_material_plan(self.path), draft)
            delete_material_plan(self.path, operator_confirmed=True)
            network.assert_not_called(); db.assert_not_called(); proc.assert_not_called()
            probe.assert_not_called(); delay.assert_not_called()


if __name__ == '__main__':
    unittest.main()
