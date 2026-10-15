"""Roadmap 043: no audio access, operator-only manual quality notes."""
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.voice_material_plan import (
    MaterialItem, VoiceMaterialDraft, save_material_plan,
)
from ai_broadcaster.voice_quality_review import (
    CRITERIA, ASSESSMENTS, QualityItem, QualityReview, MAX_FILE_BYTES,
    manifest_digest, blank_quality_review, set_quality_item, quality_review_path,
    save_quality_review, load_quality_review, delete_quality_review,
    validate_quality_record,
)


class VoiceQualityReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.path = self.folder / 'quality.json'
        self.plan = VoiceMaterialDraft('own_recording',
                                       (MaterialItem('첫 문장', 12), MaterialItem('반응', 30)))

    def review(self):
        return blank_quality_review(self.plan)

    def test_blank_contains_only_unreviewed(self):
        r = self.review()
        self.assertTrue(r.matches(self.plan))
        self.assertEqual(len(r.items), 2)
        self.assertTrue(all(v == 'unreviewed' for i in r.items for v in i.assessments))
        self.assertIn('실제 음성 분석 아님', r.summarize(self.plan))

    def test_quality_labels_and_full_review_still_no_auto_approval(self):
        r = set_quality_item(self.review(), self.plan, '첫 문장', ('operator_ok',)*4, '직접 관찰')
        self.assertIn('실제 파일 품질', r.summarize(self.plan))
        self.assertIn('실제 검증 아님', r.items[0].review_state)
        save_quality_review(self.path, r, self.plan, operator_confirmed=True)
        obj = json.loads(self.path.read_text('utf-8'))
        self.assertIs(obj['audio_analyzed'], False)
        self.assertIs(obj['training_authorized'], False)
        self.assertIs(obj['broadcast_authorized'], False)
        self.assertEqual(load_quality_review(self.path, self.plan), r)

    def test_one_item_update_preserves_other_and_order(self):
        r = set_quality_item(self.review(), self.plan, '반응',
                             ('needs_rework','operator_ok','unreviewed','unreviewed'))
        self.assertEqual([i.alias for i in r.items], ['첫 문장','반응'])
        self.assertEqual(r.items[0].assessments, ('unreviewed',)*4)
        self.assertIn('보완 필요', r.items[1].review_state)

    def test_unknown_alias_rejected(self):
        with self.assertRaises(ValueError):
            set_quality_item(self.review(), self.plan, '제3자', ('unreviewed',)*4)

    def test_invalid_assessment_rejected(self):
        for wrong in ((True,)*4, (1,)*4, ('ok',)*4, ('unreviewed',)*3, ['unreviewed']*4):
            with self.subTest(value=wrong), self.assertRaises(ValueError):
                QualityItem('첫 문장', wrong)

    def test_note_format_controlled(self):
        for wrong in (2, 'Z'*161, '줄\n바꿈', '경로/C', 'https://a', 'x\\y', 'mail@domain', '..'):
            with self.subTest(value=wrong), self.assertRaises(ValueError):
                QualityItem('첫 문장', note=wrong)
        self.assertEqual(QualityItem('첫 문장', note='간단 메모').note, '간단 메모')

    def test_manifest_digest_changes_with_length_alias_order_and_source(self):
        base = manifest_digest(self.plan)
        changes = [VoiceMaterialDraft('own_recording', (MaterialItem('첫 문장', 13), MaterialItem('반응', 30))),
                   VoiceMaterialDraft('own_recording', (MaterialItem('반응', 30), MaterialItem('첫 문장', 12))),
                   VoiceMaterialDraft('consented_recording', self.plan.items),
                   VoiceMaterialDraft('own_recording', (MaterialItem('첫 문장', 12), MaterialItem('다른 이름', 30)))]
        for p in changes:
            with self.subTest(p=p):
                self.assertNotEqual(base, manifest_digest(p))
                self.assertFalse(self.review().matches(p))

    def test_deny_save_without_explicit_confirmation(self):
        for confirmed in (False, 1, 'yes', None):
            with self.subTest(confirmed=confirmed), self.assertRaises(PermissionError):
                save_quality_review(self.path, self.review(), self.plan, operator_confirmed=confirmed)
        self.assertFalse(self.path.exists())

    def test_empty_manifest_denies_save(self):
        blank = VoiceMaterialDraft('own_recording')
        with self.assertRaises(ValueError):
            save_quality_review(self.path, blank_quality_review(blank), blank, operator_confirmed=True)

    def test_loading_absent_does_not_create_directories(self):
        p = self.folder / 'missing' / 'q.json'
        self.assertIsNone(load_quality_review(p, self.plan))
        self.assertFalse(p.parent.exists())

    def test_stale_plan_rejected_and_file_untouched(self):
        r = self.review()
        save_quality_review(self.path, r, self.plan, operator_confirmed=True)
        raw = self.path.read_bytes()
        changed = VoiceMaterialDraft('own_recording', (MaterialItem('첫 문장', 100), MaterialItem('반응', 30)))
        with self.assertRaises(ValueError):
            load_quality_review(self.path, changed)
        with self.assertRaises(ValueError):
            save_quality_review(self.path, r, changed, operator_confirmed=True)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_malformed_json_and_unknown_fields_blocked(self):
        save_quality_review(self.path, self.review(), self.plan, operator_confirmed=True)
        valid = json.loads(self.path.read_text('utf-8'))
        variants = [dict(valid, audio_analyzed=True), dict(valid, training_authorized=True),
                    dict(valid, broadcast_authorized=True), dict(valid, schema_version=True),
                    dict(valid, kind='auto_pass'), dict(valid, extra='wrong'),
                    dict(valid, items={'oops':'dict'}), dict(valid, plan_digest='Z'*64),
                    {k:v for k,v in valid.items() if k != 'kind'},
                    dict(valid, items=[{'alias': '첫 문장','assessments':['operator_ok']*4,'note':'','extra':'x'}])]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                validate_quality_record(variant)
        self.path.write_bytes(b'invalid json')
        with self.assertRaises(ValueError):
            load_quality_review(self.path, self.plan)
        self.assertEqual(self.path.read_bytes(), b'invalid json')

    def test_oversize_rejected(self):
        self.path.write_bytes(b'!'*(MAX_FILE_BYTES+1))
        with self.assertRaises(ValueError):
            load_quality_review(self.path, self.plan)

    def test_duplicate_aliases_invalid(self):
        with self.assertRaises(ValueError):
            QualityReview('own_recording', manifest_digest(self.plan),
                          (QualityItem('한'), QualityItem('한')))

    def test_symlink_and_directories_denied(self):
        folder = self.folder / 'dir'
        folder.mkdir()
        with self.assertRaises(ValueError):
            save_quality_review(folder, self.review(), self.plan, operator_confirmed=True)
        with self.assertRaises(ValueError):
            load_quality_review(folder, self.plan)
        link = self.folder / 'link'
        try:
            link.symlink_to(folder, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        for fn in (lambda: load_quality_review(link/'quality.json', self.plan),
                   lambda: save_quality_review(link/'quality.json', self.review(), self.plan, operator_confirmed=True),
                   lambda: delete_quality_review(link/'quality.json', operator_confirmed=True)):
            with self.subTest(fn=fn), self.assertRaises(ValueError):
                fn()

    def test_double_confirmation_in_gui_and_backend_delete_guard(self):
        save_quality_review(self.path, self.review(), self.plan, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_quality_review(self.path)
        self.assertTrue(self.path.exists())
        self.assertTrue(delete_quality_review(self.path, operator_confirmed=True))
        self.assertFalse(delete_quality_review(self.path, operator_confirmed=True))

    def test_previous_data_is_unchanged(self):
        files = [self.folder/name for name in ('settings.json','conversation.sqlite3',
                 'voice_material_draft.json','voice_rights_operator_review.json')]
        for f in files: f.write_bytes(b'untouched')
        save_quality_review(self.path, self.review(), self.plan, operator_confirmed=True)
        load_quality_review(self.path, self.plan)
        delete_quality_review(self.path, operator_confirmed=True)
        self.assertTrue(all(f.read_bytes() == b'untouched' for f in files))

    def test_no_network_process_db_pc_probe_or_sleep(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as net, \
             patch('sqlite3.connect', side_effect=AssertionError('db')) as db, \
             patch('subprocess.Popen', side_effect=AssertionError('proc')) as proc, \
             patch('platform.system', side_effect=AssertionError('pc_probe')) as probe, \
             patch('time.sleep', side_effect=AssertionError('delay')) as sleep:
            r = self.review()
            r.summarize(self.plan)
            save_quality_review(self.path, r, self.plan, operator_confirmed=True)
            load_quality_review(self.path, self.plan)
            delete_quality_review(self.path, operator_confirmed=True)
            net.assert_not_called(); db.assert_not_called(); proc.assert_not_called()
            probe.assert_not_called(); sleep.assert_not_called()

if __name__ == '__main__':
    unittest.main()
