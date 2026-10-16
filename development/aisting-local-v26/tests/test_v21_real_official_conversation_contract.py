"""Protocol guards only; no fake AI replies and no network connections."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'payload' / 'src'))
from ai_broadcaster.original_plan_conversation import (
    ask_real_official_ai, extract_reply_segment, _send_masked, MAX_INPUT,
)

class OfficialConversationContract(unittest.TestCase):
    def test_never_connect_without_single_turn_approval(self):
        with patch('ai_broadcaster.original_plan_conversation.socket.create_connection') as con:
            with self.assertRaises(PermissionError):
                ask_real_official_ai('안녕')
            con.assert_not_called()

    def test_invalid_messages_rejected_before_network(self):
        with patch('ai_broadcaster.original_plan_conversation.socket.create_connection') as con:
            for text in ('', '   ', '가' * (MAX_INPUT + 1)):
                with self.assertRaises(ValueError):
                    ask_real_official_ai(text, operator_approved=True)
            con.assert_not_called()

    def test_extract_official_display_text_and_ignore_audio_bytes(self):
        self.assertEqual(extract_reply_segment({
            'type':'audio','display_text': {'name':'캐릭터','text':'안녕하세요'},
            'audio':'BASE64_PAYLOAD_MUST_NOT_PLAY'}), '안녕하세요')
        self.assertIsNone(extract_reply_segment({'type':'full-text','text':'Thinking...'}))
        self.assertIsNone(extract_reply_segment({'type':'audio','audio':'BASE64_PAYLOAD_MUST_NOT_PLAY'}))
        self.assertIsNone(extract_reply_segment({'type':'control','text':'conversation-chain-end'}))

    def test_client_frames_are_masked_and_utf8_json_is_preserved(self):
        class Sink:
            result = b''
            def sendall(self, data): self.result += data
        s=Sink()
        payload=json.dumps({'type':'text-input','text':'한국어 테스트'},ensure_ascii=False).encode()
        _send_masked(s, 1, payload)
        self.assertEqual(s.result[0], 0x81)
        self.assertEqual(s.result[1] & 0x80, 0x80)
        header_size = 2 if len(payload)<126 else 4
        masked=s.result[header_size+4:]
        mask=s.result[header_size:header_size+4]
        self.assertEqual(bytes(b ^ mask[i%4] for i,b in enumerate(masked)),payload)

    def test_module_has_no_speaker_or_broadcast_integration(self):
        src=(BASE / 'payload/src/ai_broadcaster/original_plan_conversation.py').read_text('utf-8')
        # This module only sends official text-input frames, not audio playback.
        self.assertNotIn('sounddevice',src)
        self.assertNotIn('start_stream',src)
        self.assertIn("'text-input'",src)
        self.assertIn("'conversation-chain-end'",src)

if __name__=='__main__': unittest.main()
