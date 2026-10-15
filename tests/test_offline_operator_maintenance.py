"""099 operator-only maintenance claims, not device evidence or approvals."""
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ai_broadcaster.offline_operator_maintenance import (
    CHECKS, CHECK_IDS, KNOWN_UNRESOLVED, STATUSES, MaintenanceItem,
    OfflineOperatorMaintenance, STATUS_PENDING, STATUS_REVIEWED,
    STATUS_PROBLEM, export_maintenance_snapshot,
)


class OperatorMaintenanceTests(TestCase):
    def setUp(self):
        self.session = OfflineOperatorMaintenance()

    def test_all_items_present_ordered_unique(self):
        self.assertEqual(len(CHECKS), 12)
        self.assertEqual(len(set(CHECK_IDS)), len(CHECK_IDS))
        self.assertEqual(tuple(x.key for x in self.session.report().items), CHECK_IDS)

    def test_default_all_pending_and_unapproved(self):
        r = self.session.report()
        self.assertEqual((r.pending, r.reviewed, r.problems), (12, 0, 0))
        self.assertFalse(r.hardware_verified)
        self.assertFalse(r.actual_stream_verified)
        self.assertFalse(r.can_release)
        self.assertFalse(r.final_approval_granted)

    def test_known_unresolved_always_present(self):
        self.assertEqual(self.session.report().unresolved, KNOWN_UNRESOLVED)
        self.assertIn('ResourceWarning', self.session.report().describe())

    def test_mark_reviewed_self_report_only(self):
        self.session.set_status('voice', STATUS_REVIEWED)
        r = self.session.report()
        self.assertEqual((r.pending, r.reviewed, r.problems), (11, 1, 0))
        self.assertFalse(r.can_release)
        self.assertIn('자기보고', r.describe())

    def test_problem_is_recorded(self):
        self.session.set_status('chat', STATUS_PROBLEM)
        self.assertEqual(self.session.report().problems, 1)
        self.assertIn('[문제 발견]', self.session.report().describe())

    def test_status_replace_not_double_counted(self):
        self.session.set_status('chat', STATUS_PROBLEM)
        self.session.set_status('chat', STATUS_REVIEWED)
        self.assertEqual((self.session.report().reviewed, self.session.report().problems), (1, 0))

    def test_invalid_key_rejected_without_mutation(self):
        before = self.session.report()
        for key in ('', 'sqlite', 'WINDOWS', None, True, 1):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.session.set_status(key, STATUS_REVIEWED)
        self.assertEqual(self.session.report(), before)

    def test_invalid_status_rejected_without_mutation(self):
        before = self.session.report()
        for mark in ('완료', '승인', '통과', '', None, True, 0, 1):
            with self.subTest(mark=mark), self.assertRaises(ValueError):
                self.session.set_status('windows', mark)
        self.assertEqual(self.session.report(), before)

    def test_all_reviewed_still_never_releases(self):
        for key in CHECK_IDS:
            self.session.set_status(key, STATUS_REVIEWED)
        r = self.session.report()
        self.assertEqual(r.reviewed, len(CHECK_IDS))
        self.assertEqual(r.pending, 0)
        self.assertFalse(r.can_release)
        self.assertFalse(r.final_approval_granted)
        self.assertFalse(r.hardware_verified)
        self.assertFalse(r.actual_stream_verified)

    def test_reset(self):
        self.session.set_status('chat', STATUS_PROBLEM)
        self.session.set_status('windows', STATUS_REVIEWED)
        self.session.clear()
        self.assertEqual(self.session.report().pending, len(CHECKS))
        self.assertIn('ResourceWarning', self.session.report().describe())

    def test_snapshot_immutable_and_not_aliased(self):
        old = self.session.report()
        self.session.set_status('voice', STATUS_PROBLEM)
        self.assertEqual(old.pending, len(CHECKS))
        self.assertEqual(self.session.report().problems, 1)
        with self.assertRaises(FrozenInstanceError):
            old.can_release = True
        with self.assertRaises(FrozenInstanceError):
            old.items[0].status = STATUS_PROBLEM

    def test_snapshot_safe_schema(self):
        obj = self.session.report().safe_export()
        self.assertEqual(obj['schema'], 'aisting_operator_maintenance_v1')
        self.assertFalse(obj['hardware_verified'])
        self.assertFalse(obj['can_release'])
        self.assertFalse(obj['autocollected_pc_data'])
        self.assertNotIn('token', str(obj).lower())

    def test_snapshot_contains_exact_unresolved_item(self):
        self.assertEqual(self.session.report().safe_export()['known_unresolved'], list(KNOWN_UNRESOLVED))

    def test_safe_export_returns_independent_structure(self):
        obj = self.session.report().safe_export()
        obj['checklist'][0]['operator_status'] = STATUS_PROBLEM
        self.assertEqual(self.session.report().items[0].status, STATUS_PENDING)

    def test_export_only_explicit_write_and_round_trip(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'operator.json'
            self.assertFalse(dest.exists())
            result = export_maintenance_snapshot(self.session.report(), dest)
            self.assertEqual(result, dest)
            data = json.loads(dest.read_text(encoding='utf-8'))
            self.assertEqual(len(data['checklist']), len(CHECKS))
            self.assertEqual(data['evidence_kind'], 'operator_self_report_only')

    def test_export_never_overwrites_file(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'operator.json'
            dest.write_text('SENTINEL', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                export_maintenance_snapshot(self.session.report(), dest)
            self.assertEqual(dest.read_text(encoding='utf-8'), 'SENTINEL')

    def test_export_rejects_path_types(self):
        with TemporaryDirectory() as tmp:
            for value in ('foo.json', None, 5):
                with self.subTest(value=value), self.assertRaises(TypeError):
                    export_maintenance_snapshot(self.session.report(), value)
            with self.assertRaises(ValueError):
                export_maintenance_snapshot(self.session.report(), Path(tmp) / 'file.txt')

    def test_export_refuses_forged_approval(self):
        with TemporaryDirectory() as tmp:
            for changes in ({'can_release': True}, {'hardware_verified': True},
                            {'actual_stream_verified': True}, {'final_approval_granted': True},
                            {'user_claims_only': False}, {'unresolved': ()},
                            {'items': self.session.report().items[1:]}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    export_maintenance_snapshot(replace(self.session.report(), **changes),
                                                Path(tmp) / 'forged.json')
            self.assertFalse((Path(tmp) / 'forged.json').exists())

    def test_export_refuses_corrupt_labels_or_status(self):
        report = self.session.report()
        for row in (replace(report.items[0], label='fake'),
                    replace(report.items[0], status='승인')):
            with TemporaryDirectory() as tmp:
                forged = replace(report, items=(row,) + report.items[1:])
                with self.assertRaises(ValueError):
                    export_maintenance_snapshot(forged, Path(tmp) / 'wrong.json')

    def test_export_rejects_untrusted_report(self):
        with self.assertRaises(TypeError):
            export_maintenance_snapshot({}, Path('fake.json'))

    def test_no_external_io_on_mark_or_report(self):
        with patch('builtins.open', side_effect=AssertionError('read/write')), \
             patch('socket.socket.connect', side_effect=AssertionError('net')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.session.set_status('cost', STATUS_PROBLEM)
            r = self.session.report()
            self.assertIn('문제', r.describe())
            self.session.clear()

    def test_no_hidden_pc_collection_in_statuses(self):
        self.assertEqual(STATUSES, ('대기', '운영자 확인 입력', '문제 발견'))
        self.assertNotIn('출시 준비 완료', self.session.report().describe())
        self.assertIn('실제', self.session.report().describe())

    def test_concurrent_independent_operator_sessions(self):
        other = OfflineOperatorMaintenance()
        self.session.set_status('voice', STATUS_PROBLEM)
        self.assertEqual(other.report().pending, len(CHECKS))

    def test_operator_report_never_marks_live_verified_after_many_changes(self):
        for _ in range(5):
            for key in CHECK_IDS:
                self.session.set_status(key, STATUS_REVIEWED)
            self.assertFalse(self.session.report().can_release)
            self.session.clear()
        self.assertFalse(self.session.report().actual_stream_verified)
