"""Stage 041: operator self-report only, never actual permission or cloning."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.offline_settings import VOICES
from ai_broadcaster.voice_rights_review import (
    FILE_NAME, MAX_FILE_BYTES, VoiceRightsReview, delete_rights_review,
    load_rights_review, rights_review_path, save_rights_review, validate_review_record,
)


class VoiceRightsReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / FILE_NAME

    def test_default_is_undecided_and_not_approved(self):
        review = VoiceRightsReview()
        self.assertFalse(review.checklist_complete)
        for fragment in ('미확인', '승인 대기', '진위 확인이 아닙니다', '음성 파일 수집'):
            self.assertIn(fragment, review.describe())
        self.assertFalse(self.path.exists())

    def test_recording_source_requires_all_operator_checks(self):
        for source in ('own_recording', 'consented_recording', 'licensed_recording'):
            with self.subTest(source=source):
                review = VoiceRightsReview(source, True, True, True, True)
                self.assertTrue(review.checklist_complete)
                self.assertIn('실제 음성 사용 승인 대기', review.describe())

    def test_windows_system_and_undecided_cannot_mark_training_readiness(self):
        for source in ('windows_system', 'undecided'):
            review = VoiceRightsReview(source, True, True, True, True)
            self.assertFalse(review.checklist_complete)
            self.assertIn('사용·학습 승인 대기', review.describe())

    def test_each_missing_flag_prevents_readiness(self):
        for index in range(4):
            flags = [True] * 4
            flags[index] = False
            self.assertFalse(VoiceRightsReview('own_recording', *flags).checklist_complete)

    def test_invalid_sources_and_strict_boolean_input_rejected(self):
        for source in ('', 'cloud_api', 'my recording', None, 123):
            with self.subTest(source=source), self.assertRaises(ValueError):
                VoiceRightsReview(source=source)
        for value in (1, 0, 'yes', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                VoiceRightsReview('own_recording', rights_checked=value)
        self.assertIn('windows_system', VOICES.values())

    def test_note_length_controls_and_unicode(self):
        self.assertIn('안녕', VoiceRightsReview(note='안녕').describe())
        for note in ('X'*241, 'hello\nworld', 'bad\x00name', 'bad\x7f', 4):
            with self.subTest(note=note), self.assertRaises(ValueError):
                VoiceRightsReview(note=note)

    def test_saving_requires_operator_confirmation(self):
        with self.assertRaises(PermissionError):
            save_rights_review(self.path, VoiceRightsReview())
        self.assertFalse(self.path.exists())
        with self.assertRaises(PermissionError):
            save_rights_review(self.path, VoiceRightsReview(), operator_confirmed=1)
        self.assertFalse(self.path.exists())

    def test_manual_save_load_roundtrip_with_no_training_authorization(self):
        review = VoiceRightsReview('consented_recording', True, True, False, True, '직접 확인')
        save_rights_review(self.path, review, operator_confirmed=True)
        self.assertEqual(load_rights_review(self.path), review)
        raw = json.loads(self.path.read_text('utf-8'))
        self.assertIs(raw['training_authorized'], False)
        self.assertIs(raw['streaming_authorized'], False)
        self.assertEqual(raw['source_tag'], 'operator_self_report')
        self.assertFalse(review.checklist_complete)

    def test_absent_load_does_not_create_folders(self):
        other = Path(self.temp.name) / 'no-folder' / FILE_NAME
        self.assertIsNone(load_rights_review(other))
        self.assertFalse(other.parent.exists())

    def test_duplicate_saves_replace_only_own_record(self):
        settings = Path(self.temp.name) / 'settings.json'
        memory = Path(self.temp.name) / 'conversation.sqlite3'
        settings.write_bytes(b'keep these settings')
        memory.write_bytes(b'keep these bytes')
        save_rights_review(self.path, VoiceRightsReview('own_recording'), operator_confirmed=True)
        save_rights_review(self.path, VoiceRightsReview('licensed_recording', note='새 메모'), operator_confirmed=True)
        self.assertEqual(load_rights_review(self.path).source, 'licensed_recording')
        self.assertEqual(settings.read_bytes(), b'keep these settings')
        self.assertEqual(memory.read_bytes(), b'keep these bytes')

    def test_corrupt_missing_extra_fields_cannot_fake_approval(self):
        save_rights_review(self.path, VoiceRightsReview(), operator_confirmed=True)
        original = json.loads(self.path.read_text('utf-8'))
        for patch_fields in ({'schema_version': 999}, {'training_authorized': True},
                             {'streaming_authorized': True}, {'source_tag': 'bot'},
                             {'rights_checked': 1}, {'voice_source': 'new-cloud'}):
            changed = dict(original, **patch_fields)
            with self.subTest(fields=patch_fields), self.assertRaises(ValueError):
                validate_review_record(changed)
        for extra in ({'unexpected': 'yes'}, {'note': None}):
            with self.assertRaises(ValueError):
                validate_review_record(dict(original, **extra))
        with self.assertRaises(ValueError):
            validate_review_record({k: v for k, v in original.items() if k != 'note'})

    def test_corruption_is_not_silently_overwritten(self):
        self.path.write_text('bad json', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_rights_review(self.path)
        self.assertEqual(self.path.read_text('utf-8'), 'bad json')

    def test_oversize_file_is_rejected(self):
        self.path.write_bytes(b'A' * (MAX_FILE_BYTES + 10))
        with self.assertRaises(ValueError):
            load_rights_review(self.path)

    def test_delete_requires_confirmation_and_is_idempotent(self):
        save_rights_review(self.path, VoiceRightsReview(), operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_rights_review(self.path)
        self.assertTrue(self.path.exists())
        self.assertTrue(delete_rights_review(self.path, operator_confirmed=True))
        self.assertFalse(delete_rights_review(self.path, operator_confirmed=True))

    def test_reject_directory_and_symlink_targets(self):
        folder = Path(self.temp.name) / 'another'
        folder.mkdir()
        with self.assertRaises(ValueError):
            save_rights_review(folder, VoiceRightsReview(), operator_confirmed=True)
        if hasattr(Path, 'symlink_to'):
            link = Path(self.temp.name) / 'linked'
            try:
                link.symlink_to(folder, target_is_directory=True)
            except OSError:
                return
            for action in (lambda: load_rights_review(link / FILE_NAME),
                           lambda: save_rights_review(link / FILE_NAME, VoiceRightsReview(), operator_confirmed=True),
                           lambda: delete_rights_review(link / FILE_NAME, operator_confirmed=True)):
                with self.assertRaises(ValueError):
                    action()

    def test_no_unrequested_network_db_process_inspection_or_delay(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as network, \
             patch('sqlite3.connect', side_effect=AssertionError('db')) as db, \
             patch('subprocess.Popen', side_effect=AssertionError('process')) as proc, \
             patch('platform.system', side_effect=AssertionError('inspect')) as sys, \
             patch('time.sleep', side_effect=AssertionError('delay')) as delay:
            review = VoiceRightsReview('own_recording', True, True, True, True)
            review.describe()
            save_rights_review(self.path, review, operator_confirmed=True)
            self.assertEqual(load_rights_review(self.path), review)
            delete_rights_review(self.path, operator_confirmed=True)
            network.assert_not_called(); db.assert_not_called(); proc.assert_not_called()
            sys.assert_not_called(); delay.assert_not_called()


if __name__ == '__main__':
    unittest.main()
