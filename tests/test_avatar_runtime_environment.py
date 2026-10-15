"""Stage 052 operator-only renderer candidate, no machine/model access."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_broadcaster.avatar_runtime_environment import (
    AvatarRuntimeDraft, RENDERERS, COMPATIBLE, MAX_BYTES,
    runtime_environment_path, validate_runtime_record,
    save_runtime_environment, load_runtime_environment, delete_runtime_environment,
)


class AvatarRuntimeEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.target = runtime_environment_path(self.folder)
        self.draft = AvatarRuntimeDraft('2d', 'builtin_2d', '초록색 배경', '운영자 후보')

    def test_default_no_renderer_and_no_permission(self):
        draft = AvatarRuntimeDraft('undecided')
        self.assertFalse(draft.has_existing_preview)
        self.assertIn('미확인', draft.describe())

    def test_builtin_2d_preview_only(self):
        self.assertTrue(self.draft.has_existing_preview)
        self.assertIn('실제 모델 아님', self.draft.describe())
        self.assertNotIn('설치 확인 완료', self.draft.describe())

    def test_external_renderers_explicit_unconnected(self):
        for avatar, renderer in (('2d', 'external_live2d'), ('3d', 'external_vrm')):
            with self.subTest(avatar=avatar):
                draft = AvatarRuntimeDraft(avatar, renderer)
                self.assertFalse(draft.has_existing_preview)
                self.assertIn('미확인', draft.describe())

    def test_renderer_compatibility(self):
        for avatar in COMPATIBLE:
            for renderer in RENDERERS.values():
                if renderer in COMPATIBLE[avatar]:
                    AvatarRuntimeDraft(avatar, renderer)
                else:
                    with self.subTest(avatar=avatar, renderer=renderer), self.assertRaises(ValueError):
                        AvatarRuntimeDraft(avatar, renderer)

    def test_reject_invalid_input_types(self):
        for invalid in ('VRM', '', 2, None, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                AvatarRuntimeDraft(invalid)
        for renderer in (None, 5, 'run_command'):
            with self.assertRaises(ValueError):
                AvatarRuntimeDraft('2d', renderer)

    def test_sample_background_only(self):
        self.assertEqual(AvatarRuntimeDraft('2d', 'builtin_2d', '초록색 배경').background, '초록색 배경')
        for invalid in ('#fffff', '', None, True, 123):
            with self.assertRaises(ValueError):
                AvatarRuntimeDraft('2d', 'builtin_2d', invalid)
        with self.assertRaises(ValueError):
            AvatarRuntimeDraft('3d', 'external_vrm', '초록색 배경')

    def test_note_controls_length(self):
        for bad in ('a' * 201, 'line\nbreak', '\t', 3, None):
            with self.assertRaises(ValueError):
                AvatarRuntimeDraft('2d', note=bad)

    def test_save_explicit_confirmation_only(self):
        for value in (None, False, 1, 'yes'):
            with self.subTest(value=value), self.assertRaises(PermissionError):
                save_runtime_environment(self.target, self.draft, operator_confirmed=value)
        self.assertFalse(self.target.exists())

    def test_save_load_and_permissions_false(self):
        save_runtime_environment(self.target, self.draft, operator_confirmed=True)
        self.assertEqual(load_runtime_environment(self.target, selected_avatar='2d'), self.draft)
        data = json.loads(self.target.read_text('utf-8'))
        for flag in ('pc_inspected', 'model_accessed', 'software_installed',
                     'external_process_launched', 'renderer_connected', 'license_verified',
                     'streaming_authorized', 'final_approval'):
            self.assertIs(data[flag], False)
        for prohibited in ('path', 'url', 'command', 'model_bytes'):
            self.assertNotIn(prohibited, data)

    def test_missing_load_has_no_side_effects(self):
        path = self.folder/'missing'/'draft.json'
        self.assertIsNone(load_runtime_environment(path, selected_avatar='2d'))
        self.assertFalse(path.parent.exists())

    def test_cross_avatar_load_rejected_without_loss(self):
        save_runtime_environment(self.target, self.draft, operator_confirmed=True)
        with self.assertRaisesRegex(ValueError, '다른 기록'):
            load_runtime_environment(self.target, selected_avatar='3d')
        self.assertEqual(load_runtime_environment(self.target, selected_avatar='2d'), self.draft)

    def test_reject_any_privilege_escalation(self):
        save_runtime_environment(self.target, self.draft, operator_confirmed=True)
        data = json.loads(self.target.read_text('utf-8'))
        for flag in ('pc_inspected', 'model_accessed', 'software_installed',
                     'external_process_launched', 'renderer_connected', 'license_verified',
                     'streaming_authorized', 'final_approval'):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                validate_runtime_record({**data, flag: True})

    def test_reject_unknown_keys_and_schema(self):
        save_runtime_environment(self.target, self.draft, operator_confirmed=True)
        data = json.loads(self.target.read_text('utf-8'))
        for bad in ({**data, 'launch': 'now'}, {**data, 'kind': 'approved'},
                    {**data, 'schema_version': True}, {**data, 'schema_version': 999}):
            with self.assertRaises(ValueError):
                validate_runtime_record(bad)

    def test_reject_malformed_and_corrupt_record(self):
        for raw in (b'{', b'\xff', b'0', b'x'*(MAX_BYTES + 1)):
            self.target.write_bytes(raw)
            with self.subTest(raw=raw[:4]), self.assertRaises(ValueError):
                load_runtime_environment(self.target, selected_avatar='2d')

    def test_invalid_save_preserves_prior_bytes(self):
        save_runtime_environment(self.target, self.draft, operator_confirmed=True)
        before = self.target.read_bytes()
        with self.assertRaises(ValueError):
            save_runtime_environment(self.target, object(), operator_confirmed=True)
        self.assertEqual(self.target.read_bytes(), before)

    def test_symlink_rejected(self):
        real = self.folder/'source.json'
        real.write_text('SAFE', encoding='utf-8')
        link = self.folder/'link.json'
        try:
            link.symlink_to(real)
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            save_runtime_environment(link, self.draft, operator_confirmed=True)
        with self.assertRaises(ValueError):
            load_runtime_environment(link, selected_avatar='2d')
        with self.assertRaises(ValueError):
            delete_runtime_environment(link, operator_confirmed=True)
        self.assertEqual(real.read_text('utf-8'), 'SAFE')

    def test_delete_requires_confirmation(self):
        save_runtime_environment(self.target, self.draft, operator_confirmed=True)
        with self.assertRaises(PermissionError):
            delete_runtime_environment(self.target)
        self.assertTrue(self.target.exists())
        self.assertTrue(delete_runtime_environment(self.target, operator_confirmed=True))
        self.assertFalse(delete_runtime_environment(self.target, operator_confirmed=True))

    def test_no_network_or_database_or_process(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network')) , \
             patch('sqlite3.connect', side_effect=AssertionError('sqlite')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            save_runtime_environment(self.target, self.draft, operator_confirmed=True)
            self.assertEqual(load_runtime_environment(self.target, selected_avatar='2d'), self.draft)
            self.assertTrue(delete_runtime_environment(self.target, operator_confirmed=True))

    def test_not_saved_to_existing_preparation_file(self):
        original = self.folder/'avatar_preparation_draft.json'
        original.write_bytes(b'PREVIOUS USER DATA')
        save_runtime_environment(self.target, self.draft, operator_confirmed=True)
        self.assertEqual(original.read_bytes(), b'PREVIOUS USER DATA')


if __name__ == '__main__':
    unittest.main()
