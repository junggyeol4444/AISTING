"""Original roadmap 047: operator notes only, not a playback or TTS quality test."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.pronunciation_review import (
    MAX_FILE_BYTES, PronunciationItem, PronunciationReview, parse_phrases,
    context_digest, blank_review, update_item, review_path, save_review,
    load_review, delete_review,
)

PROFILE = {'installed_voice_name': '직접 선택한 음성', 'rate': -1, 'volume': 75}
SOURCE = 'windows_system'
PHRASES = ('안녕하세요.', 'ㅋㅋㅋ 진짜요?', '안녕하세요.')


class PronunciationReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.path = self.folder / 'review.json'

    def review(self):
        return blank_review(SOURCE, PROFILE, PHRASES)

    def test_blank_does_not_pretend_quality_pass(self):
        review = self.review()
        self.assertEqual(len(review.items), 3)
        self.assertTrue(all(x.pronunciation == 'unreviewed' and x.intonation == 'unreviewed' for x in review.items))
        self.assertIn('실제 음성 재생/분석 없음', review.describe())

    def test_unicode_and_duplicate_phrases_preserved(self):
        review = self.review()
        self.assertEqual(tuple(x.phrase for x in review.items), PHRASES)
        self.assertEqual(parse_phrases('\n'.join(PHRASES)), PHRASES)

    def test_manual_update_changes_one_index_only(self):
        review = update_item(self.review(), 2, 'needs_adjustment', 'operator_ok', '톤 점검')
        self.assertEqual(review.items[0], review.items[1].__class__(PHRASES[0]))
        self.assertEqual(review.items[2].pronunciation, 'needs_adjustment')
        self.assertEqual(review.items[1].intonation, 'unreviewed')
        self.assertIn('수정 필요', review.describe())

    def test_positive_entries_not_technical_approval(self):
        r = update_item(self.review(), 0, 'operator_ok', 'operator_ok', '운영자 기재')
        save_review(self.path, r, SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        payload = json.loads(self.path.read_text('utf-8'))
        for key in ('audio_analyzed', 'audio_played', 'training_authorized', 'broadcast_authorized'):
            self.assertIs(payload[key], False)
        self.assertIn('실제 음성 품질', r.describe())
        self.assertEqual(load_review(self.path, SOURCE, PROFILE, PHRASES), r)

    def test_no_save_before_explicit_operator_confirmation(self):
        for value in (False, None, 1, 'true'):
            with self.subTest(value=value), self.assertRaises(PermissionError):
                save_review(self.path, self.review(), SOURCE, PROFILE, PHRASES, operator_confirmed=value)
        self.assertFalse(self.path.exists())

    def test_missing_read_does_not_create_file_or_directory(self):
        p = self.folder / 'no-dir' / 'review.json'
        self.assertIsNone(load_review(p, SOURCE, PROFILE, PHRASES))
        self.assertFalse(p.parent.exists())

    def test_context_changes_reject_read_and_write_and_preserve_file(self):
        r = self.review()
        save_review(self.path, r, SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        previous = self.path.read_bytes()
        variants = [(SOURCE, dict(PROFILE, rate=0), PHRASES),
                    (SOURCE, dict(PROFILE, volume=76), PHRASES),
                    (SOURCE, dict(PROFILE, installed_voice_name='다른 음성'), PHRASES),
                    ('own_recording', PROFILE, PHRASES),
                    (SOURCE, PROFILE, (PHRASES[1], PHRASES[0], PHRASES[2])),
                    (SOURCE, PROFILE, ('안녕하세요.', 'ㅋㅋㅋ 진짜요?'))]
        for source, profile, phrases in variants:
            with self.subTest((source, profile, phrases)):
                with self.assertRaises(ValueError):
                    save_review(self.path, r, source, profile, phrases, operator_confirmed=True)
                with self.assertRaises(ValueError):
                    load_review(self.path, source, profile, phrases)
                self.assertEqual(self.path.read_bytes(), previous)

    def test_same_source_nonwindows_ignores_unused_os_voice(self):
        a = context_digest('own_recording', PROFILE)
        b = context_digest('own_recording', {'installed_voice_name': '', 'rate': 1, 'volume': 60})
        self.assertEqual(a, b)

    def test_unknown_and_unselected_sources_rejected(self):
        for source in ('undecided', 'cloud', '', None):
            with self.subTest(source=source), self.assertRaises(ValueError):
                context_digest(source, PROFILE)

    def test_windows_voice_must_be_manually_named(self):
        with self.assertRaises(ValueError):
            context_digest(SOURCE, dict(PROFILE, installed_voice_name=''))

    def test_invalid_voice_profile_rejected(self):
        for profile in (dict(PROFILE, rate=True), dict(PROFILE, volume=101), {}):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                context_digest(SOURCE, profile)

    def test_script_limits_and_privacy(self):
        for script in ('', '\n안녕', '가'*161, '가\n'*13, 'https://example.com', 'C:\\Users', '전화@test', '경로/자료'):
            with self.subTest(script=script), self.assertRaises(ValueError):
                parse_phrases(script)

    def test_invalid_note_and_assessments(self):
        for value in ('unknown', 1, None, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PronunciationItem('안녕하세요', pronunciation=value)
        for value in ('자료/경로', 'x'*161, 'a\nb', 'https://example.com'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PronunciationItem('안녕하세요', note=value)

    def test_invalid_indices_rejected(self):
        for index in (-1, True, 3, '0'):
            with self.subTest(index=index), self.assertRaises(ValueError):
                update_item(self.review(), index, 'operator_ok', 'operator_ok')

    def test_tampering_rejects_permissions_and_unknown_fields(self):
        save_review(self.path, self.review(), SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        data = json.loads(self.path.read_text('utf-8'))
        variants = [dict(data, audio_played=True), dict(data, audio_analyzed=True),
                    dict(data, broadcast_authorized=True), dict(data, training_authorized=True),
                    dict(data, schema_version=True), dict(data, kind='authorization'),
                    dict(data, unexpected=True)]
        bad_item = dict(data)
        bad_item['items'] = [dict(data['items'][0], extra='x')]
        variants.append(bad_item)
        for entry in variants:
            with self.subTest(entry=entry):
                self.path.write_text(json.dumps(entry), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_review(self.path, SOURCE, PROFILE, PHRASES)

    def test_invalid_json_and_large_payload(self):
        for raw in (b'{', b'\xff', b'x'*(MAX_FILE_BYTES+1)):
            self.path.write_bytes(raw)
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                load_review(self.path, SOURCE, PROFILE, PHRASES)

    def test_delete_requires_confirmation_twice_handled_by_ui(self):
        save_review(self.path, self.review(), SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_review(self.path)
        self.assertTrue(self.path.exists())
        self.assertTrue(delete_review(self.path, operator_confirmed=True))
        self.assertFalse(delete_review(self.path, operator_confirmed=True))

    def test_symlink_target_blocked(self):
        other = self.folder / 'other.json'
        other.write_text('protected', 'utf-8')
        self.path.symlink_to(other)
        with self.assertRaises(ValueError):
            save_review(self.path, self.review(), SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        with self.assertRaises(ValueError):
            load_review(self.path, SOURCE, PROFILE, PHRASES)
        with self.assertRaises(ValueError):
            delete_review(self.path, operator_confirmed=True)
        self.assertEqual(other.read_text('utf-8'), 'protected')

    def test_no_unapproved_io_or_network_for_preview(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('OS process')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')):
            review = self.review()
            self.assertIn('발음', review.describe())
            self.assertFalse(self.path.exists())

    def test_path_is_separate_from_settings_and_memory(self):
        self.assertEqual(review_path(self.folder).name, 'pronunciation_intonation_operator_notes.json')
        self.assertNotIn('settings', str(review_path(self.folder)))
        self.assertNotIn('memory', str(review_path(self.folder)))


if __name__ == '__main__':
    unittest.main()
