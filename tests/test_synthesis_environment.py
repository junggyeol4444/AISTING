"""Original roadmap 044: non-invasive Korean synthesis configuration draft."""
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.offline_settings import VOICES
from ai_broadcaster.synthesis_environment import (
    ENGINES, MAX_BYTES, SynthesisEnvironmentDraft, build_synthesis_environment,
    synthesis_environment_path, validate_synthesis_record, save_synthesis_environment,
    load_synthesis_environment, delete_synthesis_environment,
)


class SynthesisEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.file = self.folder / 'environment.json'
        self.profile = {'installed_voice_name': '샘플 (PC 설치 미확인)', 'rate': 0, 'volume': 85}
        self.draft = build_synthesis_environment('windows_system', self.profile)

    def test_all_sources_have_only_offline_engine(self):
        for source in VOICES.values():
            with self.subTest(source=source):
                draft = build_synthesis_environment(source, self.profile)
                self.assertEqual(draft.engine, ENGINES[source])
                self.assertEqual(draft.language, 'ko-KR')
                self.assertNotIn('승인 완료', draft.describe())
                if source != 'windows_system':
                    self.assertFalse(draft.voice_name)
                    self.assertIn('미', draft.describe())

    def test_windows_choice_is_only_configuration_not_execution(self):
        self.assertEqual(self.draft.voice_name, self.profile['installed_voice_name'])
        self.assertIn('사용자 PC에서 수동 확인 대기', self.draft.describe())
        self.assertIn('실제 실행 가능/사용권/품질', self.draft.describe())

    def test_empty_installed_voice_never_falls_back_to_other_name(self):
        d = build_synthesis_environment('windows_system', {**self.profile, 'installed_voice_name': ''})
        self.assertEqual(d.voice_name, '')
        self.assertIn('실행 가능 판정 불가', d.describe())

    def test_undecided_needs_no_prior_choice(self):
        d = build_synthesis_environment('undecided', self.profile)
        self.assertEqual(d.engine, 'not_selected')
        self.assertIn('나중에 선택', d.describe())

    def test_invalid_source_engine_language_rejected(self):
        for values in [('https://remote', 'not_selected', 'ko-KR'),
                       ('undecided', 'remote_api', 'ko-KR'),
                       ('windows_system', 'windows_system_speech', 'en-US'),
                       ('own_recording', 'windows_system_speech', 'ko-KR')]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                SynthesisEnvironmentDraft(*values, '', 0, 85)
        for bad in (None, 'cloud', True):
            with self.assertRaises(ValueError):
                build_synthesis_environment(bad, self.profile)

    def test_invalid_voice_profile_denied_no_mutation(self):
        for bad in ({**self.profile, 'rate': 5}, {**self.profile, 'volume': -1},
                    {**self.profile, 'rate': True}, {**self.profile, 'installed_voice_name': 'x\x00'},
                    {'volume': 85}):
            with self.subTest(bad=bad), self.assertRaises((ValueError, KeyError)):
                build_synthesis_environment('windows_system', bad)
        self.assertEqual(self.profile['rate'], 0)

    def test_unconfigured_engine_never_accepts_fake_installed_name(self):
        with self.assertRaises(ValueError):
            SynthesisEnvironmentDraft('own_recording', 'future_local_tts_unconfigured', 'ko-KR',
                                      'fake voice', 0, 85)

    def test_explicit_confirmation_required_and_existing_record_kept(self):
        for confirmed in (False, None, 1, 'yes'):
            with self.subTest(confirmed=confirmed), self.assertRaises(PermissionError):
                save_synthesis_environment(self.file, self.draft, operator_confirmed=confirmed)
        self.assertFalse(self.file.exists())
        save_synthesis_environment(self.file, self.draft, operator_confirmed=True)
        self.assertEqual(load_synthesis_environment(self.file, 'windows_system', self.profile), self.draft)

    def test_saved_schema_is_never_approval_or_probe(self):
        save_synthesis_environment(self.file, self.draft, operator_confirmed=True)
        obj = json.loads(self.file.read_text('utf-8'))
        for field in ('pc_probed', 'audio_accessed', 'model_installed', 'training_authorized',
                      'broadcast_authorized', 'environment_verified'):
            self.assertIs(obj[field], False)
        self.assertEqual(obj['language'], 'ko-KR')

    def test_stale_source_voice_rate_volume_deny_reuse(self):
        save_synthesis_environment(self.file, self.draft, operator_confirmed=True)
        old = self.file.read_bytes()
        for source, profile in [('own_recording', self.profile),
                                ('windows_system', {**self.profile, 'installed_voice_name': '변경'}),
                                ('windows_system', {**self.profile, 'rate': 2}),
                                ('windows_system', {**self.profile, 'volume': 40})]:
            with self.subTest(source=source, profile=profile), self.assertRaises(ValueError):
                load_synthesis_environment(self.file, source, profile)
        self.assertEqual(self.file.read_bytes(), old)

    def test_invalid_record_payload_denied(self):
        save_synthesis_environment(self.file, self.draft, operator_confirmed=True)
        obj = json.loads(self.file.read_text('utf-8'))
        mutations = [dict(obj, pc_probed=True), dict(obj, audio_accessed=True),
                     dict(obj, model_installed=True), dict(obj, training_authorized=True),
                     dict(obj, broadcast_authorized=True), dict(obj, environment_verified=True),
                     dict(obj, schema_version=True), dict(obj, schema_version=2),
                     dict(obj, language='en-US'), dict(obj, rate=True),
                     dict(obj, engine='cloud_api'), dict(obj, kind='ready'),
                     dict(obj, extra='x'), {k:v for k,v in obj.items() if k != 'voice_name'}]
        for entry in mutations:
            with self.subTest(value=entry), self.assertRaises((ValueError, KeyError)):
                validate_synthesis_record(entry)

    def test_missing_malformed_oversize_and_non_utf8(self):
        missing = self.folder / 'nested' / 'missing.json'
        self.assertIsNone(load_synthesis_environment(missing, 'windows_system', self.profile))
        self.assertFalse(missing.parent.exists())
        for raw in (b'{', b'\xff', b'!' * (MAX_BYTES + 1)):
            self.file.write_bytes(raw)
            with self.assertRaises(ValueError):
                load_synthesis_environment(self.file, 'windows_system', self.profile)
            self.assertEqual(self.file.read_bytes(), raw)

    def test_delete_requires_confirmation_and_is_idempotent(self):
        save_synthesis_environment(self.file, self.draft, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_synthesis_environment(self.file)
        self.assertTrue(self.file.exists())
        self.assertTrue(delete_synthesis_environment(self.file, operator_confirmed=True))
        self.assertFalse(delete_synthesis_environment(self.file, operator_confirmed=True))

    def test_directory_and_symlink_denied(self):
        folder = self.folder / 'folder'
        folder.mkdir()
        for fn in (lambda p: load_synthesis_environment(p, 'windows_system', self.profile),
                   lambda p: save_synthesis_environment(p, self.draft, operator_confirmed=True),
                   lambda p: delete_synthesis_environment(p, operator_confirmed=True)):
            with self.assertRaises(ValueError):
                fn(folder)
        link = self.folder / 'link'
        try:
            link.symlink_to(folder, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        for fn in (lambda p: load_synthesis_environment(p, 'windows_system', self.profile),
                   lambda p: save_synthesis_environment(p, self.draft, operator_confirmed=True),
                   lambda p: delete_synthesis_environment(p, operator_confirmed=True)):
            with self.assertRaises(ValueError):
                fn(link / 'env.json')

    def test_other_user_data_unchanged(self):
        names = ('settings.json','conversation.sqlite3','voice_material_draft.json',
                 'voice_quality_operator_review.json','voice_rights_operator_review.json')
        for name in names:
            (self.folder / name).write_bytes(b'preserve original')
        save_synthesis_environment(self.file, self.draft, operator_confirmed=True)
        load_synthesis_environment(self.file, 'windows_system', self.profile)
        delete_synthesis_environment(self.file, operator_confirmed=True)
        for name in names:
            self.assertEqual((self.folder / name).read_bytes(), b'preserve original')

    def test_no_network_process_audio_db_pc_info_probes(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) as net, \
             patch('subprocess.Popen', side_effect=AssertionError('process')) as proc, \
             patch('sqlite3.connect', side_effect=AssertionError('db')) as db, \
             patch('platform.system', side_effect=AssertionError('pc info')) as info:
            draft = build_synthesis_environment('windows_system', self.profile)
            draft.describe()
            save_synthesis_environment(self.file, draft, operator_confirmed=True)
            load_synthesis_environment(self.file, 'windows_system', self.profile)
            delete_synthesis_environment(self.file, operator_confirmed=True)
            net.assert_not_called(); proc.assert_not_called()
            db.assert_not_called(); info.assert_not_called()

    def test_default_path_declared_not_read(self):
        d = self.folder / 'custom'
        self.assertEqual(synthesis_environment_path(d).parent, d)
        self.assertFalse(d.exists())

if __name__ == '__main__':
    unittest.main()
