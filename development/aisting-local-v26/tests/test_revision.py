"""Local source-patch sanity checks. NOT real voice/avatar/OBS verification."""
import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / 'payload' / 'src'))
import apply_to_existing_aisting as apply
from ai_broadcaster.original_plan_studio import (
    StageOneUnavailable, check_official_project, update_official_persona,
    launch_official_server, prepare_official_launch, save_official_persona,
)

UPSTREAM_CONF = '''system_config:
  host: 'localhost'
character_config:
  conf_name: 'mao_pro'
  conf_uid: 'mao_pro_001'
  live2d_model_name: 'mao_pro'
  character_name: 'Mao'
  avatar: 'mao.png'
  persona_prompt: |
    default upstream persona
  agent_config:
    conversation_agent_choice: 'basic_memory_agent'
  tts_config:
    tts_model: 'edge_tts'
'''
IDENTITY = {'name':'내방송인', 'style':'자연스럽게', 'character':'호기심 많은 성격'}


class OriginalRevisionChecks(TestCase):
    def test_actual_upstream_conf_persona_preserves_all_unrelated_fields(self):
        revised=update_official_persona(UPSTREAM_CONF,IDENTITY)
        self.assertIn("character_name: '내방송인'",revised)
        self.assertIn('캐릭터 성격: 호기심 많은 성격',revised)
        self.assertIn('한국어 말투: 자연스럽게',revised)
        self.assertIn("live2d_model_name: 'mao_pro'",revised)
        self.assertIn("tts_model: 'edge_tts'",revised)
        self.assertNotIn('default upstream persona',revised)
        self.assertEqual(revised,update_official_persona(revised,IDENTITY))

    def test_actual_upstream_conf_is_backed_up(self):
        with TemporaryDirectory() as t:
            root=Path(t)
            (root/'run_server.py').write_text('',encoding='utf8')
            (root/'pyproject.toml').write_text('',encoding='utf8')
            (root/'conf.yaml').write_text(UPSTREAM_CONF,encoding='utf8')
            modified,backup=save_official_persona(root,IDENTITY)
            self.assertEqual(backup.read_text('utf8'),UPSTREAM_CONF)
            self.assertIn('내방송인',modified.read_text('utf8'))

    def test_unknown_config_rejected(self):
        self.assertRaises(ValueError,update_official_persona,'something else',IDENTITY)
        self.assertRaises(ValueError,update_official_persona,UPSTREAM_CONF.replace('character_name:','custom_name:'),IDENTITY)
        self.assertRaises(ValueError,update_official_persona,UPSTREAM_CONF,dict(IDENTITY, name='a\n'+'foo: bar'))

    def test_official_server_no_install_or_fake_backend(self):
        with TemporaryDirectory() as t:
            root=Path(t)
            (root/'run_server.py').write_text('',encoding='utf8')
            (root/'pyproject.toml').write_text('',encoding='utf8')
            (root/'frontend').mkdir()
            (root/'frontend/index.html').write_text('actual frontend', encoding='utf8')
            (root/'conf.yaml').write_text(UPSTREAM_CONF,encoding='utf8')
            self.assertEqual(root, prepare_official_launch(root))
            self.assertRaises(StageOneUnavailable, launch_official_server, root)
            with patch('ai_broadcaster.original_plan_studio.shutil.which',return_value='/usr/bin/uv'), \
                 patch('ai_broadcaster.original_plan_studio.subprocess.Popen') as popen:
                launch_official_server(root, operator_authorized_side_effects=True)
                args=popen.call_args.args[0]
                self.assertEqual(args,['/usr/bin/uv','run','--offline','--no-sync','run_server.py'])
                self.assertIn('UV_OFFLINE',popen.call_args.kwargs['env'])
                self.assertIn('UV_NO_SYNC',popen.call_args.kwargs['env'])
            self.assertRaises(StageOneUnavailable,check_official_project,root/'missing')

    def test_original_desktop_edit_has_valid_unique_anchors(self):
        # Validate exactly one intended substitution for each source pattern.
        # The real upstream main baseline's 20 anchors were separately checked
        # read-only from GitHub; this local fixture checks transformation order.
        mod=ast.parse((BASE/'apply_to_existing_aisting.py').read_text('utf-8'))
        values=[]
        for node in ast.walk(mod):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='r':
                if len(node.args)>=3 and isinstance(node.args[1],ast.Constant):
                    values.append(node.args[1].value)
        self.assertGreaterEqual(len(values),20)
        synthetic='\n#### UNIQUE ANCHOR ####\n'.join(values)
        revised=apply.modify_existing_desktop(synthetic)
        self.assertIn('OriginalPlanStudio(studio, self)',revised)
        self.assertIn('def _save_character_identity(self)',revised)
        self.assertIn('"방송인 홈"',revised)
        self.assertIn('data["persona_mode"] = self.settings["persona_mode"]',revised)
        self.assertEqual(len(revised.split('#### UNIQUE ANCHOR ####')),len(values))

if __name__=='__main__':main()
