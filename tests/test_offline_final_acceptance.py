"""Stage 100: final review evidence is NOT live device testing or approval."""
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ai_broadcaster.offline_final_acceptance import (
    ALLOWED_FILES, REVIEW_ITEMS, EXPECTED_ORIGINAL_SHA256, ArchivedFile,
    build_final_acceptance, inspect_bundled_project, export_final_acceptance,
)
from ai_broadcaster.offline_operator_maintenance import (
    OfflineOperatorMaintenance, CHECK_IDS, STATUS_REVIEWED, STATUS_PROBLEM,
)

ROOT = Path(__file__).resolve().parents[1]


class FinalAcceptanceTests(TestCase):
    def test_missing_evidence_defaults_to_blocked(self):
        r = build_final_acceptance()
        self.assertFalse(r.can_release)
        self.assertFalse(r.approval_granted)
        self.assertFalse(r.hardware_verified)
        self.assertFalse(r.actual_broadcast_verified)
        self.assertIn('검사 미실행', r.describe())

    def test_baseline_original_sha(self):
        self.assertEqual(EXPECTED_ORIGINAL_SHA256, 'd4482d539bf733fddc65263566b436e2547d64d43545ac3279581bc21c58180c')

    def test_exact_six_bundled_files(self):
        self.assertEqual(len(ALLOWED_FILES), 6)
        self.assertEqual(len(ALLOWED_FILES), len(set(ALLOWED_FILES)))
        self.assertTrue(all('..' not in s and not s.startswith('/') for s in ALLOWED_FILES))

    def test_review_items_are_not_deceptive(self):
        self.assertEqual(len(REVIEW_ITEMS), 14)
        self.assertEqual(len(set(x[0] for x in REVIEW_ITEMS)), len(REVIEW_ITEMS))
        self.assertIn('실기기 미검증', str(REVIEW_ITEMS))
        self.assertIn('승인 대기', str(REVIEW_ITEMS))

    def test_actual_project_archive_presence_only(self):
        found, pending = inspect_bundled_project(ROOT)
        self.assertEqual(len(found), len(ALLOWED_FILES))
        self.assertTrue(all(x.status.startswith('보관 파일 존재') for x in found))
        self.assertTrue(pending)
        self.assertTrue(all(len(x.digest) == 64 for x in found))

    def test_real_archive_does_not_grant_release(self):
        files, pending = inspect_bundled_project(ROOT)
        r = build_final_acceptance(files, pending)
        self.assertFalse(r.can_release)
        self.assertFalse(r.approval_granted)
        self.assertFalse(r.actual_broadcast_verified)
        self.assertIn('ResourceWarning', r.describe())
        self.assertIn('보관된 파일', r.describe())

    def test_no_real_device_hardware_claim_even_if_everything_checked(self):
        op = OfflineOperatorMaintenance()
        for key in CHECK_IDS:
            op.set_status(key, STATUS_REVIEWED)
        files, pending = inspect_bundled_project(ROOT)
        r = build_final_acceptance(files, pending, op.report())
        self.assertEqual(r.operator_claims, 12)
        self.assertFalse(r.can_release)
        self.assertFalse(r.approval_granted)
        self.assertFalse(r.hardware_verified)

    def test_operator_problem_remains_no_release(self):
        op = OfflineOperatorMaintenance()
        op.set_status('obs', STATUS_PROBLEM)
        r = build_final_acceptance(operator_report=op.report())
        self.assertEqual(r.operator_claims, 0)
        self.assertFalse(r.can_release)

    def test_invalid_operator_report_rejected(self):
        with self.assertRaises(TypeError):
            build_final_acceptance(operator_report={})

    def test_invalid_archive_structure_rejected(self):
        for bad in ([], ({'path': 'fake'},), None, 'x'):
            with self.subTest(bad=bad), self.assertRaises(TypeError):
                build_final_acceptance(bad)

    def test_invalid_pending_type_rejected(self):
        for bad in (1, 0, 'pending', None):
            with self.subTest(bad=bad), self.assertRaises(TypeError):
                build_final_acceptance((), bad)

    def test_missing_project_files_block(self):
        with TemporaryDirectory() as temp:
            files, pending = inspect_bundled_project(Path(temp))
            self.assertFalse(pending)
            self.assertTrue(all('검토 불가' in x.status for x in files))
            self.assertIn('누락', build_final_acceptance(files, pending).describe())

    def test_changed_original_blocked(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs').mkdir()
            (root / 'docs' / 'ORIGINAL_PLAN.txt').write_text('변경된 임의 원본')
            files, _ = inspect_bundled_project(root)
            self.assertEqual(files[0].status, '원본 기획안 해시 불일치')
            self.assertIn('동봉 프로젝트 파일 누락/변경', build_final_acceptance(files).describe())

    def test_changed_roadmap_detected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'config').mkdir()
            (root / 'config' / 'roadmap.json').write_text(json.dumps({'steps': []}))
            files, pending = inspect_bundled_project(root)
            self.assertFalse(pending)
            self.assertEqual(files[2].status, '로드맵 원본 해시 불일치')

    def test_truncated_roadmap_json_does_not_crash(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'config').mkdir()
            (root / 'config' / 'roadmap.json').write_text('{invalid')
            _, pending = inspect_bundled_project(root)
            self.assertFalse(pending)

    def test_symlink_evidence_is_refused(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs').mkdir()
            (root / 'docs' / 'ORIGINAL_PLAN.txt').symlink_to(ROOT / 'docs/ORIGINAL_PLAN.txt')
            files, _ = inspect_bundled_project(root)
            self.assertIn('심볼릭', files[0].status)

    def test_oversize_is_refused_without_read(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs').mkdir()
            f = root / 'docs/ORIGINAL_PLAN.txt'
            with f.open('wb') as out:
                out.truncate(2_000_001)
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('oversized file read')):
                files, _ = inspect_bundled_project(root)
            self.assertIn('용량 초과', files[0].status)

    def test_no_network_process_access_when_inspecting(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) , \
             patch('subprocess.Popen', side_effect=AssertionError('subprocess')):
            files, pending = inspect_bundled_project(ROOT)
            self.assertTrue(pending)
            build_final_acceptance(files, pending)

    def test_no_reads_for_report_construction(self):
        with patch('builtins.open', side_effect=AssertionError('filesystem')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')):
            r = build_final_acceptance(operator_report=OfflineOperatorMaintenance().report())
            self.assertFalse(r.can_release)
            self.assertTrue(r.describe())

    def test_report_frozen(self):
        r = build_final_acceptance()
        with self.assertRaises(FrozenInstanceError):
            r.approval_granted = True

    def test_export_has_no_approval_field_true(self):
        r = build_final_acceptance()
        d = r.safe_export()
        for field in ('can_release', 'hardware_verified', 'actual_broadcast_verified',
                      'approval_granted', 'external_posted', 'user_pc_autocollected'):
            self.assertIs(d[field], False)
        self.assertEqual(d['type'], 'unapproved_offline_review_only')

    def test_export_requires_explicit_valid_path(self):
        with self.assertRaises(TypeError):
            export_final_acceptance(build_final_acceptance(), 'wrong.json')
        with self.assertRaises(ValueError):
            export_final_acceptance(build_final_acceptance(), Path('bad.txt'))

    def test_manual_export_round_trip_no_private_data(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'final.json'
            r = build_final_acceptance()
            export_final_acceptance(r, path)
            saved = json.loads(path.read_text())
            self.assertEqual(saved['type'], 'unapproved_offline_review_only')
            self.assertEqual(len(saved['review_items']), len(REVIEW_ITEMS))
            self.assertIn('SQLite', ' '.join(saved['blockers']))
            self.assertFalse(saved['can_release'])
            self.assertNotIn('token', saved)

    def test_export_does_not_overwrite(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'review.json'
            path.write_text('KEEP', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                export_final_acceptance(build_final_acceptance(), path)
            self.assertEqual(path.read_text(encoding='utf-8'), 'KEEP')

    def test_forged_release_flag_is_rejected(self):
        for field in ('can_release', 'approval_granted', 'hardware_verified', 'actual_broadcast_verified'):
            with TemporaryDirectory() as temp:
                path = Path(temp) / 'review.json'
                forged = replace(build_final_acceptance(), **{field: True})
                with self.subTest(field=field), self.assertRaises(ValueError):
                    export_final_acceptance(forged, path)
                self.assertFalse(path.exists())

    def test_forged_missing_sqlite_blocker_rejected(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'review.json'
            forged = replace(build_final_acceptance(), blockers=('인위적 승인',))
            with self.assertRaises(ValueError):
                export_final_acceptance(forged, path)
            self.assertFalse(path.exists())

    def test_isolated_operator_snapshots(self):
        op = OfflineOperatorMaintenance()
        r = build_final_acceptance(operator_report=op.report())
        op.set_status('voice', STATUS_REVIEWED)
        self.assertEqual(r.operator_claims, 0)
        self.assertEqual(build_final_acceptance(operator_report=op.report()).operator_claims, 1)

    def test_digest_is_only_archive_not_execution(self):
        files, pending = inspect_bundled_project(ROOT)
        r = build_final_acceptance(files, pending)
        self.assertIn('테스트 재실행', r.describe())
        self.assertFalse(r.can_release)
