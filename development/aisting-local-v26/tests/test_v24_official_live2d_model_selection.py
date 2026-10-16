"""Synthetic local fixture checks of REAL upstream conf/model_dict layouts only.
No model download, rendering, AI response, web access or actual broadcast.
"""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload' / 'src'))
from ai_broadcaster.original_plan_avatar import (
    _change_model_scalar, apply_official_live2d_choice,
    inspect_official_live2d_options,
)
from ai_broadcaster.original_plan_studio import StageOneUnavailable


class RealUpstreamModelFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'run_server.py').write_text('# existing official marker', encoding='utf-8')
        (self.root / 'pyproject.toml').write_text('[project]\nname="Open-LLM-VTuber"\n', encoding='utf-8')
        self.config = self.root / 'conf.yaml'
        self.original = ('character_config:\r\n  character_name: "사람"\r\n'
                         '  live2d_model_name: "Old" # 내 메모\r\n'
                         '  persona_prompt: |\r\n    기존 성격 보존\r\n'
                         '  tts_config:\r\n    tts_model: edge_tts\r\n'
                         'system_config:\r\n  arbitrary_setting: true\r\n')
        self.config.write_bytes(b'\xef\xbb\xbf' + self.original.encode('utf-8'))
        self.models = [
            {'name': 'Old', 'url': '/live2d-models/Old/runtime/Old.model3.json', 'kScale': 0.5},
            {'name': '새 모델', 'url': '/live2d-models/New/runtime/New.model3.json', 'kScale': 0.7},
        ]
        (self.root / 'model_dict.json').write_text(json.dumps(self.models, ensure_ascii=False), encoding='utf-8')
        for prefix in ('Old', 'New'):
            loc = self.root / 'live2d-models' / prefix / 'runtime'
            loc.mkdir(parents=True)
            (loc / f'{prefix}.model3.json').write_text(json.dumps({
                'Version': 3,
                'FileReferences': {'Moc': f'{prefix}.moc3', 'Textures': [f'{prefix}.png']},
            }), encoding='utf-8')
            (loc / f'{prefix}.moc3').write_bytes(b'existing-Cubism-asset-placeholder')
            (loc / f'{prefix}.png').write_bytes(b'existing-file-placeholder')

    def test_read_only_listing_contains_real_existing_asset_refs(self):
        before = self.config.read_bytes()
        result = inspect_official_live2d_options(self.root)
        self.assertEqual(result.selected_name, 'Old')
        self.assertEqual([c.name for c in result.choices], ['Old', '새 모델'])
        self.assertEqual([c.asset_files for c in result.choices], [2, 2])
        self.assertTrue(all(c.available for c in result.choices))
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse(list(self.root.glob('*.bak')))

    def test_explicit_approval_required_without_file_change(self):
        before = self.config.read_bytes()
        snap = inspect_official_live2d_options(self.root)
        with self.assertRaises(PermissionError):
            apply_official_live2d_choice(self.root, '새 모델', expected_config_sha256=snap.config_sha256)
        self.assertEqual(self.config.read_bytes(), before)

    def test_approved_change_only_updates_model_and_private_backup(self):
        original = self.config.read_bytes()
        snap = inspect_official_live2d_options(self.root)
        config, backup = apply_official_live2d_choice(self.root, '새 모델',
            expected_config_sha256=snap.config_sha256, operator_approved=True)
        self.assertEqual(config, self.config)
        self.assertIsNotNone(backup)
        self.assertEqual(backup.read_bytes(), original)
        written = self.config.read_bytes()
        self.assertTrue(written.startswith(b'\xef\xbb\xbf'))
        expected = self.original.replace('live2d_model_name: "Old"', "live2d_model_name: '새 모델'")
        self.assertEqual(written, b'\xef\xbb\xbf' + expected.encode('utf-8'))
        self.assertEqual(inspect_official_live2d_options(self.root).selected_name, '새 모델')

    def test_existing_choice_no_write_or_backup(self):
        before = self.config.read_bytes()
        snap = inspect_official_live2d_options(self.root)
        _config, backup = apply_official_live2d_choice(self.root, 'Old',
            expected_config_sha256=snap.config_sha256, operator_approved=True)
        self.assertIsNone(backup)
        self.assertEqual(self.config.read_bytes(), before)

    def test_outdated_window_cannot_overwrite_current_config(self):
        snap = inspect_official_live2d_options(self.root)
        self.config.write_bytes(self.config.read_bytes() + b'# concurrent change\r\n')
        current = self.config.read_bytes()
        with self.assertRaisesRegex(StageOneUnavailable, '변경'):
            apply_official_live2d_choice(self.root, '새 모델',
                expected_config_sha256=snap.config_sha256, operator_approved=True)
        self.assertEqual(self.config.read_bytes(), current)
        self.assertFalse(list(self.root.glob('*.bak')))

    def test_missing_asset_blocks_selection_without_changes(self):
        (self.root / 'live2d-models/New/runtime/New.moc3').unlink()
        snap = inspect_official_live2d_options(self.root)
        self.assertFalse(snap.choices[1].available)
        before = self.config.read_bytes()
        with self.assertRaises(StageOneUnavailable):
            apply_official_live2d_choice(self.root, '새 모델',
                expected_config_sha256=snap.config_sha256, operator_approved=True)
        self.assertEqual(self.config.read_bytes(), before)

    def test_directory_escape_refused_without_change(self):
        self.models[1]['url'] = '/live2d-models/../private/New.model3.json'
        (self.root / 'model_dict.json').write_text(json.dumps(self.models, ensure_ascii=False))
        snap = inspect_official_live2d_options(self.root)
        self.assertFalse(snap.choices[1].available)

    def test_missing_mandatory_upstream_scale_blocks_model(self):
        self.models[1].pop('kScale')
        (self.root / 'model_dict.json').write_text(json.dumps(self.models, ensure_ascii=False))
        snap = inspect_official_live2d_options(self.root)
        self.assertFalse(snap.choices[1].available)
        self.assertIn('kScale', snap.choices[1].issue)

    def test_unlisted_model_name_cannot_be_written(self):
        snap = inspect_official_live2d_options(self.root)
        with self.assertRaises(StageOneUnavailable):
            apply_official_live2d_choice(self.root, 'nonexistent',
                expected_config_sha256=snap.config_sha256, operator_approved=True)
        self.assertEqual(self.config.read_bytes(), b'\xef\xbb\xbf' + self.original.encode('utf-8'))

    def test_duplicate_model_name_is_ambiguous_and_rejected(self):
        self.models.append(self.models[1])
        (self.root / 'model_dict.json').write_text(json.dumps(self.models, ensure_ascii=False))
        with self.assertRaisesRegex(StageOneUnavailable, '중복'):
            inspect_official_live2d_options(self.root)

    def test_malformed_nested_scalar_refused(self):
        with self.assertRaises(StageOneUnavailable):
            _change_model_scalar('character_config:\n  live2d_model_name:\n    nested: illegal\n', 'Old')

    def test_quoted_hash_and_comment_preserved(self):
        src = "character_config:\n  live2d_model_name: 'Old #1'  # 메모\n"
        transformed = _change_model_scalar(src, "New'Name")
        self.assertEqual(transformed, "character_config:\n  live2d_model_name: 'New''Name'  # 메모\n")


if __name__ == '__main__':
    unittest.main()
