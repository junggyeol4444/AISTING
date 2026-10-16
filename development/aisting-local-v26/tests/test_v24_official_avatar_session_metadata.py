"""Offline contract fixture only: actual upstream event schema, NO real rendering."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'payload/src'))
from ai_broadcaster import original_plan_conversation as chat
from test_v22_upstream_session_reuse import LocalSocketFixture, answer, end, init


class AvatarSessionProvenance(unittest.TestCase):
    def test_real_upstream_model_name_and_url_exposed_without_faking_render(self):
        sock = LocalSocketFixture()
        with (patch.object(chat.socket, 'create_connection', return_value=sock),
              patch.object(chat, '_read_http_upgrade', return_value=bytearray()),
              patch.object(chat, '_read_upstream_json', side_effect=[init(),answer('응답'),end()]),
              patch.object(chat, '_send_masked')):
            with chat.OfficialConversationSession() as session:
                result = session.ask('승인 요청',operator_approved=True)
        self.assertEqual(result.model_name, 'real-configured-model')
        self.assertEqual(result.model_url, '/live2d-models/mao_pro/runtime/mao_pro.model3.json')
        self.assertEqual(result.text, '응답')

    def test_gui_contains_real_model_metadata_reference(self):
        source=(BASE/'payload/src/ai_broadcaster/original_plan_studio.py').read_text('utf-8')
        self.assertIn('response.model_url',source)
        self.assertIn('response.model_name',source)
        self.assertIn('command=self._open_real_live2d_choice',source)

if __name__ == '__main__':
    unittest.main()
