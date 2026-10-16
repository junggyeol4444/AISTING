"""Local protocol contract checks only; does not verify actual speech or LLM."""
import base64
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload/src'))
from ai_broadcaster import original_plan_conversation as chat


def actual_wav_container():
    memory = io.BytesIO()
    with wave.open(memory, 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b'\0\0' * 160)
    return memory.getvalue()


class AudioEvidenceContract(unittest.TestCase):
    def test_actual_valid_wav_container(self):
        payload = actual_wav_container()
        data = {'type': 'audio', 'audio': base64.b64encode(payload).decode(),
                'display_text': {'text': '한국어 응답', 'name': 'AI'}}
        self.assertEqual(chat.inspect_upstream_audio_event(data), ('wav', len(payload)))
        self.assertEqual(chat.extract_reply_segment(data), '한국어 응답')

    def test_actual_silent_audio_does_not_count_as_speech(self):
        self.assertEqual(chat.inspect_upstream_audio_event({'type':'audio','audio':None}), ('silent', 0))
        self.assertIsNone(chat.inspect_upstream_audio_event({'type':'full-text','text':'Thinking...'}))

    def test_invalid_base64_is_not_reported_as_valid_wav(self):
        self.assertEqual(chat.inspect_upstream_audio_event({'type':'audio','audio':'not@base64!'}), ('invalid', 0))

    def test_header_only_is_not_evidence(self):
        raw = b'RIFF' + (4).to_bytes(4,'little') + b'WAVE'
        self.assertEqual(chat.inspect_upstream_audio_event({'type':'audio','audio':base64.b64encode(raw).decode()}), ('invalid',0))

    def test_truncated_data_chunk_is_not_evidence(self):
        raw = bytearray(actual_wav_container())
        i = raw.index(b'data')
        raw[i+4:i+8] = (999999).to_bytes(4, 'little')
        self.assertEqual(chat.inspect_upstream_audio_event({'type':'audio','audio':base64.b64encode(raw).decode()}), ('invalid', 0))

    def test_non_pcm_is_not_evidence(self):
        raw = bytearray(actual_wav_container())
        i = raw.index(b'fmt ')
        raw[i+8:i+10] = (999).to_bytes(2,'little')
        self.assertEqual(chat.inspect_upstream_audio_event({'type':'audio','audio':base64.b64encode(raw).decode()}), ('invalid',0))

    def test_oversize_encoded_payload_is_not_decoded(self):
        with patch.object(chat,'MAX_INCOMING_FRAME',12):
            self.assertEqual(chat.inspect_upstream_audio_event({'type':'audio','audio':'A'*20}), ('invalid',0))

    def test_counts_actual_wav_and_invalid_and_silent_without_playback(self):
        from test_v22_upstream_session_reuse import LocalSocketFixture, init, end
        f = LocalSocketFixture()
        wav = actual_wav_container()
        events = [init(),
                  {'type':'audio','audio':base64.b64encode(wav).decode(), 'display_text':{'text':'실제 응답'}},
                  {'type':'audio','audio':None,'display_text':{'text':' 보충'}},
                  {'type':'audio','audio':'bad@@','display_text':{'text':' 문장'}}, end()]
        with (patch.object(chat.socket,'create_connection',return_value=f),
              patch.object(chat,'_read_http_upgrade',return_value=bytearray()),
              patch.object(chat,'_read_upstream_json',side_effect=events),
              patch.object(chat,'_send_masked')):
            with chat.OfficialConversationSession() as session:
                result = session.ask('질문',operator_approved=True)
        self.assertEqual(result.text,'실제 응답 보충 문장')
        self.assertEqual((result.wav_packets,result.wav_audio_bytes),(1,len(wav)))
        self.assertEqual((result.silent_audio_packets,result.invalid_audio_packets),(1,1))

if __name__ == '__main__':
    unittest.main()
