"""Original roadmap 048: manual emotion expression inspection notes, no audio access."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.emotion_expression_review import (
    MAX_FILE_BYTES, EmotionItem, EmotionReview, blank_review, update_item,
    review_path, save_review, load_review, delete_review,
)

PROFILE = {'installed_voice_name': '사용자 수동 선택 음성', 'rate': -1, 'volume': 80}
SOURCE = 'windows_system'
PHRASES = ('정말 반가워요!', '헉, 진짜요?', '정말 반가워요!')


class EmotionExpressionReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.path = self.folder / 'emotion.json'

    def blank(self):
        return blank_review(SOURCE, PROFILE, PHRASES)

    def test_blank_is_unreviewed_and_does_not_claim_expression(self):
        r = self.blank()
        self.assertEqual(len(r.items), 3)
        self.assertTrue(all(not x.intended_emotion and x.verdict == 'unreviewed' for x in r.items))
        self.assertIn('실제 음성 재생·감정 분석·모델 연결 없음', r.describe())

    def test_duplicates_preserve_per_item_identity_and_order(self):
        r = update_item(self.blank(), 2, '기쁨', 'needs_adjustment', '좀 더 밝게')
        self.assertEqual([x.phrase for x in r.items], list(PHRASES))
        self.assertEqual(r.items[0].verdict, 'unreviewed')
        self.assertEqual(r.items[2].verdict, 'needs_adjustment')
        self.assertIn('좀 더 밝게', r.describe())

    def test_intent_is_manual_not_inferred_or_encoded_as_tts_instruction(self):
        r = update_item(self.blank(), 0, '운영자 지정 기쁨', 'unreviewed')
        self.assertEqual(r.items[0].intended_emotion, '운영자 지정 기쁨')
        self.assertTrue(all(v.verdict == 'unreviewed' for v in r.items))

    def test_cannot_mark_appropriate_without_intended_emotion(self):
        for value in ('operator_ok', 'needs_adjustment'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                update_item(self.blank(), 0, '', value)

    def test_save_requires_exact_explicit_confirmation(self):
        for val in (False, None, 1, 'yes'):
            with self.subTest(val=val), self.assertRaises(PermissionError):
                save_review(self.path, self.blank(), SOURCE, PROFILE, PHRASES, operator_confirmed=val)
        self.assertFalse(self.path.exists())

    def test_positive_assessment_never_sets_audio_or_broadcast_authorization(self):
        r = update_item(self.blank(), 1, '놀람', 'operator_ok', '실제 청취 후 운영자가 기재')
        save_review(self.path, r, SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        raw = json.loads(self.path.read_text('utf-8'))
        for name in ('audio_analyzed', 'audio_played', 'emotion_generated',
                     'training_authorized', 'broadcast_authorized'):
            self.assertIs(raw[name], False)
        self.assertEqual(load_review(self.path, SOURCE, PROFILE, PHRASES), r)

    def test_missing_read_does_not_create_directory(self):
        p = self.folder / 'none' / 'review.json'
        self.assertIsNone(load_review(p, SOURCE, PROFILE, PHRASES))
        self.assertFalse(p.parent.exists())

    def test_voice_settings_and_sentence_changes_invalidate_context(self):
        save_review(self.path, self.blank(), SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        before = self.path.read_bytes()
        variants = [
            (SOURCE, dict(PROFILE, installed_voice_name='변경됨'), PHRASES),
            (SOURCE, dict(PROFILE, rate=2), PHRASES),
            (SOURCE, dict(PROFILE, volume=70), PHRASES),
            ('own_recording', PROFILE, PHRASES),
            (SOURCE, PROFILE, ((PHRASES[1], PHRASES[0], PHRASES[2]))),
            (SOURCE, PROFILE, PHRASES[:-1]),
        ]
        for source, profile, phrases in variants:
            with self.subTest(variant=(source, profile, phrases)):
                with self.assertRaises(ValueError):
                    load_review(self.path, source, profile, phrases)
                with self.assertRaises(ValueError):
                    save_review(self.path, self.blank(), source, profile, phrases, operator_confirmed=True)
                self.assertEqual(self.path.read_bytes(), before)

    def test_non_windows_unused_os_voice_does_not_affect_context(self):
        a = blank_review('own_recording', PROFILE, PHRASES)
        b = blank_review('own_recording', {'installed_voice_name':'', 'rate':0, 'volume':100}, PHRASES)
        self.assertEqual(a.context, b.context)

    def test_invalid_and_undecided_voice_source_rejected(self):
        for src in ('undecided', 'cloud', '', None):
            with self.subTest(src=src), self.assertRaises(ValueError):
                blank_review(src, PROFILE, PHRASES)

    def test_voice_profile_validation(self):
        for p in (dict(PROFILE, installed_voice_name=''), dict(PROFILE, rate=True),
                  dict(PROFILE, volume=101), {}):
            with self.subTest(p=p), self.assertRaises(ValueError):
                blank_review(SOURCE, p, PHRASES)

    def test_bad_phrases_or_limits(self):
        for values in ((), ('',), ('a'*161,), tuple('안녕' for _ in range(13)),
                       ('https://bad',), ('C:\\Users',), ('a@b',), ('안녕/경로',)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                blank_review(SOURCE, PROFILE, values)

    def test_invalid_emotion_direction_and_note(self):
        for value in ('x'*61, 'https://bad', 'C:\\secret', 'a@b', '사람/경로', '\n'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                update_item(self.blank(), 0, value, 'unreviewed')
        for value in ('x'*161, 'https://bad', '사람/정보', '\n', None):
            with self.subTest(note=value), self.assertRaises(ValueError):
                update_item(self.blank(), 0, '기쁨', 'unreviewed', value)

    def test_unknown_verdict_and_index_rejected(self):
        for verdict in ('yes', 1, True, None):
            with self.subTest(verdict=verdict), self.assertRaises(ValueError):
                update_item(self.blank(), 0, '기쁨', verdict)
        for index in (-1, 3, '0', True):
            with self.subTest(index=index), self.assertRaises(ValueError):
                update_item(self.blank(), index, '기쁨', 'operator_ok')

    def test_tamper_unknown_fields_and_fake_permission_flags_rejected(self):
        save_review(self.path, self.blank(), SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        data = json.loads(self.path.read_text('utf-8'))
        variants = [dict(data, unexpected='yes'), dict(data, kind='training'),
                    dict(data, schema_version=True), dict(data, items='bad')]
        for key in ('audio_analyzed', 'audio_played', 'emotion_generated',
                    'training_authorized', 'broadcast_authorized'):
            variants.append(dict(data, **{key: True}))
        changed = dict(data)
        changed['items'] = [dict(data['items'][0], path='bad')]
        variants.append(changed)
        for d in variants:
            self.path.write_text(json.dumps(d), encoding='utf8')
            with self.subTest(data=d), self.assertRaises(ValueError):
                load_review(self.path, SOURCE, PROFILE, PHRASES)

    def test_invalid_utf8_json_or_large_file_rejected(self):
        for raw in (b'{', b'\xff', b'x'*(MAX_FILE_BYTES+1)):
            self.path.write_bytes(raw)
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                load_review(self.path, SOURCE, PROFILE, PHRASES)

    def test_delete_requires_confirmation_and_is_idempotent(self):
        save_review(self.path, self.blank(), SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_review(self.path)
        self.assertTrue(self.path.exists())
        self.assertTrue(delete_review(self.path, operator_confirmed=True))
        self.assertFalse(delete_review(self.path, operator_confirmed=True))

    def test_symlinks_blocked_for_all_file_actions(self):
        other = self.folder / 'protected.json'
        other.write_text('original', 'utf8')
        self.path.symlink_to(other)
        with self.assertRaises(ValueError):
            save_review(self.path, self.blank(), SOURCE, PROFILE, PHRASES, operator_confirmed=True)
        with self.assertRaises(ValueError):
            load_review(self.path, SOURCE, PROFILE, PHRASES)
        with self.assertRaises(ValueError):
            delete_review(self.path, operator_confirmed=True)
        self.assertEqual(other.read_text('utf8'), 'original')

    def test_preview_has_no_network_process_audio_or_memory_access(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('sqlite3.connect', side_effect=AssertionError('SQLite')):
            text = update_item(self.blank(), 0, '기쁨', 'unreviewed').describe()
            self.assertIn('기쁨', text)
            self.assertFalse(self.path.exists())

    def test_storage_separate_from_settings_and_memory(self):
        name = review_path(self.folder).name
        self.assertEqual(name, 'emotion_expression_operator_notes.json')
        self.assertNotIn('settings', name)
        self.assertNotIn('memory', name)


if __name__ == '__main__':
    unittest.main()
