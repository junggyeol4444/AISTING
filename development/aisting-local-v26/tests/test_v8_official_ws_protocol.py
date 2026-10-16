"""Unit tests of upstream wire-format parsing only (NOT real AI/live proof)."""
import base64
import hashlib
from pathlib import Path
import socket
import sys
import time
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'payload' / 'src'))
from ai_broadcaster.original_plan_ws import (  # noqa: E402
    _extract_initialization, _next_text_frame, _read_http_upgrade,
    OfficialWsProbeError, probe_official_ws_initialization,
)


class OfficialWsWireFormatTests(unittest.TestCase):
    def test_rejects_probe_without_explicit_consent(self):
        with self.assertRaises(PermissionError):
            probe_official_ws_initialization()

    def test_rejects_invalid_timeout_before_network(self):
        with self.assertRaises(ValueError):
            probe_official_ws_initialization(operator_approved=True, timeout=0)

    def test_valid_upstream_init_message_is_metadata_only(self):
        msg = {'type': 'set-model-and-conf', 'conf_name': 'default',
               'client_uid': 'id', 'model_info': {
                   'name': 'mao_pro',
                   'url': '/live2d-models/mao_pro/runtime/mao_pro.model3.json'}}
        result = _extract_initialization(msg, 3)
        self.assertEqual(result.model_name, 'mao_pro')
        self.assertEqual(result.messages_observed, 3)
        self.assertFalse(hasattr(result, 'ai_answer'))
        self.assertFalse(hasattr(result, 'audio_generated'))

    def test_unrelated_messages_are_not_success(self):
        self.assertIsNone(_extract_initialization({'type': 'full-text', 'text': 'Connection established'}, 1))
        self.assertIsNone(_extract_initialization({'type': 'control', 'text': 'start-mic'}, 2))

    def test_rejects_missing_or_external_model_reference(self):
        base = {'type': 'set-model-and-conf', 'conf_name': 'default', 'client_uid': 'id'}
        for info in ({}, {'name': 'mao', 'url': 'https://example.com/model3.json'},
                     {'name': 'mao', 'url': '/tmp/model3.json'}):
            with self.subTest(info=info), self.assertRaises(OfficialWsProbeError):
                _extract_initialization({**base, 'model_info': info}, 1)

    def test_parses_actual_wire_frame_shape(self):
        a, b = socket.socketpair()
        try:
            payload = b'{"type":"full-text","text":"Connection established"}'
            b.sendall(bytes([0x81, len(payload)]) + payload)
            result = _next_text_frame(a, bytearray(), time.monotonic() + 2)
            self.assertIn('Connection established', result)
        finally:
            a.close(); b.close()

    def test_rejects_masked_server_frame(self):
        a, b = socket.socketpair()
        try:
            b.sendall(b'\x81\x80\x00\x00\x00\x00')
            with self.assertRaises(OfficialWsProbeError):
                _next_text_frame(a, bytearray(), time.monotonic() + 2)
        finally:
            a.close(); b.close()

    def test_rejects_binary_initialization_frame(self):
        a, b = socket.socketpair()
        try:
            b.sendall(b'\x82\x01\x00')
            with self.assertRaises(OfficialWsProbeError):
                _next_text_frame(a, bytearray(), time.monotonic() + 2)
        finally:
            a.close(); b.close()

    def test_accepts_protocol_correct_upgrade_only(self):
        key = base64.b64encode(b'0123456789abcdef').decode('ascii')
        accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        a, b = socket.socketpair()
        try:
            b.sendall(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n'
                       'Connection: keep-alive, Upgrade\r\nSec-WebSocket-Accept: '
                       + accept + '\r\n\r\n').encode('ascii') + b'\x81\x02OK')
            pending = _read_http_upgrade(a, key, time.monotonic() + 2)
            self.assertEqual(_next_text_frame(a, pending, time.monotonic() + 2), 'OK')
        finally:
            a.close(); b.close()

    def test_rejects_wrong_accept_hash(self):
        a, b = socket.socketpair()
        try:
            b.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n'
                      b'Connection: Upgrade\r\nSec-WebSocket-Accept: invalid\r\n\r\n')
            with self.assertRaises(OfficialWsProbeError):
                _read_http_upgrade(a, 'any-key', time.monotonic() + 2)
        finally:
            a.close(); b.close()


if __name__ == '__main__':
    unittest.main()
