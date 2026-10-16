"""Local contract checks; never count as an actual core/voice/live test."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
from unittest import TestCase
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'payload' / 'src'))

from ai_broadcaster.original_plan_studio import (
    StageOneUnavailable, launch_official_server, prepare_official_launch,
    update_official_persona,
)
from ai_broadcaster.original_plan_obs import OfficialObsWebsocket

UPSTREAM_FRAGMENT = '''character_config:
  character_name: 'Mao'
  persona_prompt: |
    Old persona

  # =================== LLM Backend Settings ===================
  agent_config:
    conversation_agent_choice: 'basic_memory_agent'
'''
IDENTITY = {'name': '방송인', 'style': '친근함', 'character': '밝음'}


class UpstreamSideEffectProtection(TestCase):
    def make_project(self, root: Path):
        (root / 'run_server.py').write_text('upstream script', encoding='utf8')
        (root / 'pyproject.toml').write_text('upstream project', encoding='utf8')

    def test_denies_launch_without_new_explicit_approval(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_project(root)
            with patch('ai_broadcaster.original_plan_studio.subprocess.Popen') as spawn:
                with self.assertRaisesRegex(StageOneUnavailable, '승인'):
                    launch_official_server(root)
                spawn.assert_not_called()

    def test_missing_frontend_blocks_implicit_git_download_even_if_confirmed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_project(root)
            (root / 'conf.yaml').write_text(UPSTREAM_FRAGMENT, encoding='utf8')
            with patch('ai_broadcaster.original_plan_studio.subprocess.Popen') as spawn:
                with self.assertRaisesRegex(StageOneUnavailable, '서브모듈'):
                    launch_official_server(root, operator_authorized_side_effects=True)
                spawn.assert_not_called()

    def test_missing_conf_blocks_upstream_auto_settings_creation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_project(root)
            (root / 'frontend').mkdir()
            (root / 'frontend/index.html').write_text('upstream frontend', encoding='utf8')
            with self.assertRaisesRegex(StageOneUnavailable, 'conf.yaml'):
                prepare_official_launch(root)

    def test_upstream_comments_not_removed_by_identity_change(self):
        result = update_official_persona(UPSTREAM_FRAGMENT, IDENTITY)
        self.assertIn('# =================== LLM Backend Settings', result)
        self.assertIn("conversation_agent_choice: 'basic_memory_agent'", result)
        self.assertNotIn('Old persona', result)
        self.assertEqual(result, update_official_persona(result, IDENTITY))

    def test_obs_scene_change_requires_separate_env_authorization(self):
        client = OfficialObsWebsocket('locally-entered-password')
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(PermissionError):
                client.set_scene('Actual On-Air Scene', operator_confirmed=True)

    def test_obs_stop_requires_separate_env_authorization(self):
        client = OfficialObsWebsocket('locally-entered-password')
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(PermissionError):
                client.stop_stream(operator_confirmed=True)
