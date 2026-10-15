"""081 weekly local draft regression; no stream scheduler."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.offline_broadcast_schedule import (
    MAX_SLOTS, BroadcastScheduleDraft, WeeklyStartSlot, KST, parse_reference,
    schedule_path, save_schedule, load_schedule, delete_schedule, validate_schedule_record,
    _record,
)


class OfflineBroadcastScheduleTests(unittest.TestCase):
    def setUp(self):
        self.draft = BroadcastScheduleDraft().add(2, '19:30').add(0, '08:15')

    def test_empty_inactive(self):
        draft = BroadcastScheduleDraft()
        self.assertEqual(draft.slots, ())
        self.assertIn('자동 방송 시작 비활성', draft.description())

    def test_add_sort_and_immutable(self):
        self.assertEqual([s.label for s in self.draft.slots], ['월요일 08:15', '수요일 19:30'])
        self.assertEqual(BroadcastScheduleDraft().slots, ())
        with self.assertRaises((AttributeError, TypeError)):
            self.draft.slots = ()

    def test_weekday_invalid(self):
        for weekday in (-1, 7, True, '3', 3.0):
            with self.subTest(weekday=weekday), self.assertRaises(ValueError):
                WeeklyStartSlot(weekday, '19:30')

    def test_time_invalid(self):
        for time_text in ('24:00', '12:60', '9:00', '19:3', '-1:00', '19:30 ', '１２:00', '', None, 930):
            with self.subTest(time=time_text), self.assertRaises(ValueError):
                WeeklyStartSlot(0, time_text)

    def test_duplicate_is_not_silently_dropped(self):
        with self.assertRaises(ValueError):
            self.draft.add(0, '08:15')

    def test_remove_and_missing(self):
        reduced = self.draft.remove(2, '19:30')
        self.assertEqual(len(reduced.slots), 1)
        self.assertEqual(len(self.draft.slots), 2)
        with self.assertRaises(ValueError):
            reduced.remove(2, '19:30')

    def test_too_many(self):
        draft = BroadcastScheduleDraft()
        for minute in range(MAX_SLOTS):
            draft = draft.add(0, f'09:{minute:02d}')
        with self.assertRaises(ValueError):
            draft.add(0, '09:14')

    def test_unordered_record_rejected(self):
        with self.assertRaises(ValueError):
            BroadcastScheduleDraft(tuple(reversed(self.draft.slots)))

    def test_reference_strict(self):
        for s in ('2026-02-30 12:00', '2026-01-01 24:00', '2026-1-01 00:00',
                  '2026-01-01T00:00', '2026/01/01 00:00', '', '2026-01-01 ００:00'):
            with self.subTest(s=s), self.assertRaises(ValueError):
                parse_reference(s)
        self.assertEqual(parse_reference('2026-10-14 19:30').utcoffset(), timedelta(hours=9))

    def test_next_exact_boundary_strict_future(self):
        upcoming = self.draft.upcoming(parse_reference('2026-10-14 19:30'), 3)
        self.assertEqual([x.strftime('%Y-%m-%d %H:%M') for x in upcoming],
                         ['2026-10-19 08:15', '2026-10-21 19:30', '2026-10-26 08:15'])

    def test_next_before_boundary_includes_today(self):
        upcoming = self.draft.upcoming(parse_reference('2026-10-14 19:29'))
        self.assertEqual(upcoming[0].strftime('%Y-%m-%d %H:%M'), '2026-10-14 19:30')

    def test_sunday_to_monday_rollover(self):
        plan = BroadcastScheduleDraft().add(0, '00:00')
        self.assertEqual(plan.upcoming(parse_reference('2026-10-18 23:59'))[0].strftime('%Y-%m-%d %H:%M'),
                         '2026-10-19 00:00')

    def test_wrong_reference_timezone_rejected(self):
        for obj in (datetime(2026, 10, 14), datetime(2026, 10, 14, tzinfo=timezone.utc), '2026-10-14'):
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                self.draft.upcoming(obj)

    def test_limit_invalid(self):
        for lim in (0, 31, True, 1.0):
            with self.subTest(lim=lim), self.assertRaises(ValueError):
                self.draft.upcoming(parse_reference('2026-10-14 10:00'), lim)

    def test_empty_has_no_next(self):
        self.assertEqual(BroadcastScheduleDraft().upcoming(parse_reference('2026-10-14 10:00')), ())

    def test_manual_save_load_delete_and_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = schedule_path(Path(temp))
            unrelated = Path(temp) / 'settings.json'
            unrelated.write_text('ORIGINAL', encoding='utf-8')
            with self.assertRaises(PermissionError):
                save_schedule(path, self.draft)
            self.assertFalse(path.exists())
            self.assertIsNone(load_schedule(path))
            self.assertEqual(save_schedule(path, self.draft, operator_confirmed=True), path)
            self.assertEqual(load_schedule(path), self.draft)
            self.assertFalse(json.loads(path.read_text(encoding='utf-8'))['scheduled_execution'])
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'ORIGINAL')
            with self.assertRaises(PermissionError):
                delete_schedule(path)
            self.assertTrue(delete_schedule(path, operator_confirmed=True))
            self.assertFalse(delete_schedule(path, operator_confirmed=True))
            self.assertFalse(path.exists())
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'ORIGINAL')

    def test_corrupt_data_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            path = schedule_path(Path(temp))
            path.write_bytes(b'not json')
            with self.assertRaises(ValueError):
                load_schedule(path)
            path.write_bytes(b' ' * 4097)
            with self.assertRaises(ValueError):
                load_schedule(path)

    def test_no_auto_execute_or_authorization(self):
        original = _record(self.draft)
        for key in ('scheduled_execution', 'broadcasting_authorized', 'obs_connected', 'final_approval'):
            obj = dict(original)
            obj[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_schedule_record(obj)
        extra = dict(original, token='secret')
        with self.assertRaises(ValueError):
            validate_schedule_record(extra)
        malformed = dict(original, slots=[{'weekday': True, 'start_time': '20:00'}])
        with self.assertRaises(ValueError):
            validate_schedule_record(malformed)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            original = Path(temp) / 'target'
            original.write_text('ORIGINAL', encoding='utf-8')
            path = Path(temp) / 'link'
            path.symlink_to(original)
            with self.assertRaises((ValueError, OSError)):
                load_schedule(path)
            with self.assertRaises((ValueError, OSError)):
                save_schedule(path, self.draft, operator_confirmed=True)
            self.assertEqual(original.read_text(encoding='utf-8'), 'ORIGINAL')

    def test_no_io_or_network_during_calendar_math(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('time.sleep', side_effect=AssertionError('delay')), \
             patch('builtins.open', side_effect=AssertionError('io')):
            self.assertEqual(len(self.draft.upcoming(parse_reference('2026-10-14 10:00'))), 5)

    def test_explicit_save_has_no_network_or_process(self):
        with tempfile.TemporaryDirectory() as temp:
            path = schedule_path(Path(temp))
            with patch('socket.socket.connect', side_effect=AssertionError('network')), \
                 patch('subprocess.Popen', side_effect=AssertionError('process')), \
                 patch('time.sleep', side_effect=AssertionError('delay')):
                save_schedule(path, self.draft, operator_confirmed=True)
                self.assertEqual(load_schedule(path), self.draft)


if __name__ == '__main__':
    unittest.main()
