"""v20 regression checks against SHA-pinned REAL offline_settings.py.

All official-project fixtures are local text files. NO live AI/TTS/Live2D/OBS
operation, broadcast, installation or network request is performed.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'payload/src'))
from apply_to_existing_aisting import BASELINE_OFFLINE_SHA, git_blob_sha, modify_existing_offline_settings
from ai_broadcaster.original_plan_studio import OriginalPlanStudio
from ai_broadcaster.original_plan_persona_store import commit_character_identity


class Var:
    def __init__(self, value=''):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class DiskConfirmedPersonaOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'settings.json'
        baseline = ROOT / 'evidence/original_readonly/offline_settings_main_20261016.py'
        source = baseline.read_bytes()
        self.assertEqual(git_blob_sha(source), BASELINE_OFFLINE_SHA)
        patched = modify_existing_offline_settings(source.decode('utf-8'))
        spec = importlib.util.spec_from_loader('ai_broadcaster.offline_settings', loader=None)
        module = importlib.util.module_from_spec(spec)
        exec(compile(patched, str(baseline), 'exec'), module.__dict__)
        module.settings_file = lambda: self.path
        replacement = patch.dict(sys.modules, {'ai_broadcaster.offline_settings': module})
        replacement.start()
        self.addCleanup(replacement.stop)
        self.settings = module
        self.identity = {'name': '새로 확정한 이름', 'style': '새 말투', 'character': '새 성격'}
        self.draft = {'name': '확정하지 않은 이름', 'style': '초안 말투', 'character': '초안 성격'}
        self.studio = object.__new__(OriginalPlanStudio)
        self.studio.app = type('App', (), {})()
        self.studio.app.settings = deepcopy(module.DEFAULTS)
        self.studio.saved_persona = Var()
        self.studio.persona_sync_status = Var()
        self.studio.project_dir = Var(self.tmp.name)
        self.studio.state = Var()
        self.studio.parent = object()

    def save_and_confirm(self):
        self.settings.save_settings(deepcopy(self.settings.DEFAULTS), self.path)
        return commit_character_identity(self.settings.DEFAULTS, 'custom', self.identity, path=self.path)

    def test_refresh_reads_newer_confirmation_without_using_draft(self):
        self.save_and_confirm()
        self.studio.app.settings['persona'] = deepcopy(self.draft)
        self.studio._refresh_persona()
        self.assertIn(self.identity['name'], self.studio.saved_persona.get())
        self.assertNotIn(self.draft['name'], self.studio.saved_persona.get())
        self.assertEqual(self.studio.app.settings['persona'], self.identity)
        self.assertEqual(self.studio.app.settings['persona_mode'], 'custom')

    def test_refresh_preserves_unrelated_unsaved_broadcast_editor_state(self):
        self.save_and_confirm()
        self.studio.app.settings['content'] = 'chat'
        self.studio._refresh_persona()
        self.assertEqual(self.studio.app.settings['content'], 'chat')
        self.assertEqual(self.settings.load_settings(self.path)['content'], 'undecided')

    def test_missing_file_not_misreported_as_confirmed_default(self):
        self.studio._refresh_persona()
        self.assertIn('복원 불가', self.studio.saved_persona.get())
        self.assertFalse(self.path.exists())

    def test_corrupt_file_not_overwritten(self):
        self.path.write_bytes(b'{broken')
        self.studio._refresh_persona()
        self.assertIn('복원 불가', self.studio.saved_persona.get())
        self.assertEqual(self.path.read_bytes(), b'{broken')

    def test_changed_file_during_read_does_not_use_stale_identity(self):
        self.save_and_confirm()
        original_loader = self.settings.load_settings
        def racing_loader(path):
            loaded = original_loader(path)
            changed = deepcopy(loaded)
            changed['persona']['name'] = '다른 창에서 변경됨'
            path.write_text(__import__('json').dumps(changed, ensure_ascii=False), encoding='utf-8')
            return loaded
        with patch.object(self.settings, 'load_settings', side_effect=racing_loader):
            self.studio._refresh_persona()
        self.assertIn('복원 불가', self.studio.saved_persona.get())
        self.assertNotEqual(self.studio.app.settings['persona']['name'], '다른 창에서 변경됨')

    def test_apply_rechecks_identity_after_operator_confirmation(self):
        self.save_and_confirm()
        calls = []
        newer = {'name': '다른 창 확정', 'style': '새 스타일', 'character': '다른 성격'}
        def approve(*_args, **_kwargs):
            commit_character_identity(self.settings.load_settings(self.path), 'custom', newer, path=self.path)
            return True
        with patch('ai_broadcaster.original_plan_studio.check_official_project', return_value=Path(self.tmp.name)), \
             patch('ai_broadcaster.original_plan_studio.messagebox.askyesno', side_effect=approve), \
             patch('ai_broadcaster.original_plan_studio.save_official_persona', side_effect=lambda *a: calls.append(a)):
            self.studio._apply_official_identity()
        self.assertEqual(calls, [])
        self.assertIn('변경되었습니다', self.studio.state.get())
        self.assertEqual(self.settings.load_settings(self.path)['persona'], newer)

    def test_apply_uses_only_persisted_persona(self):
        self.save_and_confirm()
        self.studio.app.settings['persona'] = deepcopy(self.draft)
        applied = []
        with patch('ai_broadcaster.original_plan_studio.check_official_project', return_value=Path(self.tmp.name)), \
             patch('ai_broadcaster.original_plan_studio.messagebox.askyesno', return_value=True), \
             patch('ai_broadcaster.original_plan_studio.save_official_persona', side_effect=lambda project, fields: (applied.append(fields), (Path('conf.yaml'), None))[1]):
            self.studio._apply_official_identity()
        self.assertEqual(applied, [self.identity])
        self.assertNotIn(self.draft['name'], self.studio.state.get())

    def test_apply_with_no_confirmed_file_is_blocked(self):
        with patch('ai_broadcaster.original_plan_studio.check_official_project', return_value=Path(self.tmp.name)), \
             patch('ai_broadcaster.original_plan_studio.messagebox.askyesno') as approval:
            self.studio._apply_official_identity()
        approval.assert_not_called()
        self.assertIn('확정 저장된', self.studio.state.get())


if __name__ == '__main__':
    unittest.main()
