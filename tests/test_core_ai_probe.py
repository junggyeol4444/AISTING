"""24단계: 네트워크 없이 로컬 Ollama 응답 계약과 승인 게이트를 검증."""
from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.core_ai_connection import build_core_ai_plan
from ai_broadcaster.core_ai_probe import (
    MAX_RESPONSE_BYTES, ConnectionCheckResult, evaluate_tags, probe_local_model,
    simulate_connection_test, _fetch_loopback_tags,
)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_core_ai_plan("local_ollama", "gemma3:4b")

    def check(self, code=200, body=b'{"models":[{"name":"gemma3:4b"}]}', content_type="application/json"):
        return evaluate_tags(self.plan, code, body, content_type)

    def test_valid_model(self):
        result = self.check()
        self.assertTrue(result.model_available)
        self.assertEqual(result.status, "model_available")
        self.assertIn("가상", result.describe())

    def test_exact_match_only(self):
        for value in ("gemma3", "gemma3:4b-more", "GEMMA3:4B", "gemma3:4b "):
            with self.subTest(value=value):
                self.assertEqual(self.check(body=json.dumps({"models": [{"name": value}]}).encode()).status,
                                 "model_missing")

    def test_empty_list(self):
        self.assertEqual(self.check(body=b'{"models":[]}').status, "model_missing")

    def test_multiple_models(self):
        body = json.dumps({"models": [{"name": "other"}, {"name": "gemma3:4b"}]}).encode()
        self.assertTrue(self.check(body=body).model_available)

    def test_json_content_type_with_charset(self):
        self.assertTrue(self.check(content_type="application/json; charset=utf-8").model_available)

    def test_non_json_content_type_rejected(self):
        for value in ("text/html", "application/javascript", "", None):
            with self.subTest(value=value):
                self.assertEqual(self.check(content_type=value).status, "invalid_response")

    def test_http_errors_not_success(self):
        for code in (301, 302, 307, 400, 401, 404, 500, True, "200"):
            with self.subTest(code=code):
                self.assertEqual(self.check(code=code).status, "http_error")

    def test_invalid_json(self):
        for value in (b"", b"{", b"\xff", b"[]", b"null", b'{"unexpected":1}', b'{"models":{}}'):
            with self.subTest(value=value):
                self.assertEqual(self.check(body=value).status, "invalid_response")

    def test_invalid_model_entries(self):
        for record in ({"models": ["abc"]}, {"models": [{}]}, {"models": [{"name": 123}]},
                       {"models": [{"name": "x" * 201}]}, {"models": [{}] * 1025}):
            with self.subTest(record=str(record)[:30]):
                self.assertEqual(self.check(body=json.dumps(record).encode()).status, "invalid_response")

    def test_oversized_body(self):
        self.assertEqual(self.check(body=b" " * (MAX_RESPONSE_BYTES + 1)).status, "invalid_response")

    def test_nonbytes_body(self):
        self.assertEqual(self.check(body='{"models":[]}').status, "invalid_response")

    def test_forged_plan_rejected(self):
        for changed in (replace(self.plan, host="external.example"),
                        replace(self.plan, network_enabled=True),
                        replace(self.plan, port=80)):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    self.check_plan(changed)

    def check_plan(self, plan):
        return evaluate_tags(plan, 200, b'{"models":[]}')

    def test_mock_never_claims_model(self):
        result = evaluate_tags(build_core_ai_plan(), 200, b'{"models":[{"name":"x"}]}')
        self.assertEqual(result.status, "mock_mode")
        self.assertFalse(result.model_available)

    def test_simulated_scenarios(self):
        for scenario, status in (("available", "model_available"), ("missing", "model_missing"),
                                 ("invalid", "invalid_response"), ("http_error", "http_error")):
            with self.subTest(scenario=scenario):
                result = simulate_connection_test(self.plan, scenario)
                self.assertTrue(result.simulated)
                self.assertEqual(result.status, status)

    def test_unknown_simulated_scenario_rejected(self):
        with self.assertRaises(ValueError):
            simulate_connection_test(self.plan, "real")

    def test_simulation_no_system_access(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("pc")) as pc:
            simulate_connection_test(self.plan)
        net.assert_not_called()
        proc.assert_not_called()
        pc.assert_not_called()


class ManualProbeTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_core_ai_plan("local_ollama", "gemma3:4b")
        self.transport = Mock(return_value=(200, b'{"models":[{"name":"gemma3:4b"}]}', "application/json"))

    def test_explicit_confirmation_required(self):
        with self.assertRaises(PermissionError):
            probe_local_model(self.plan, transport=self.transport)
        self.transport.assert_not_called()

    def test_false_confirmation_required(self):
        with self.assertRaises(PermissionError):
            probe_local_model(self.plan, operator_confirmed=False, transport=self.transport)
        self.transport.assert_not_called()

    def test_truthy_but_not_boolean_approval_rejected(self):
        for value in (1, "yes", [True]):
            with self.subTest(value=value), self.assertRaises(PermissionError):
                probe_local_model(self.plan, operator_confirmed=value, transport=self.transport)
        self.transport.assert_not_called()

    def test_true_confirmation_uses_transport_once(self):
        result = probe_local_model(self.plan, operator_confirmed=True, transport=self.transport)
        self.assertTrue(result.model_available)
        self.assertFalse(result.simulated)
        self.transport.assert_called_once_with()

    def test_mock_does_not_call_transport_even_with_approval(self):
        result = probe_local_model(build_core_ai_plan(), operator_confirmed=True, transport=self.transport)
        self.assertEqual(result.status, "mock_mode")
        self.transport.assert_not_called()

    def test_forged_plan_rejected_before_transport(self):
        with self.assertRaises(ValueError):
            probe_local_model(replace(self.plan, host="remote"), operator_confirmed=True,
                              transport=self.transport)
        self.transport.assert_not_called()

    def test_network_failure_is_not_success(self):
        self.transport.side_effect = ConnectionRefusedError("refused")
        result = probe_local_model(self.plan, operator_confirmed=True, transport=self.transport)
        self.assertEqual(result.status, "connection_error")
        self.assertFalse(result.model_available)
        self.assertNotIn("refused", result.describe())

    def test_timeout_is_not_success(self):
        self.transport.side_effect = TimeoutError("timeout")
        self.assertEqual(probe_local_model(self.plan, operator_confirmed=True,
                                           transport=self.transport).status, "connection_error")

    def test_missing_model_is_not_success(self):
        self.transport.return_value = (200, b'{"models":[]}', "application/json")
        self.assertFalse(probe_local_model(self.plan, operator_confirmed=True,
                                           transport=self.transport).model_available)

    def test_redirect_is_not_followed(self):
        self.transport.return_value = (302, b"", "text/html")
        self.assertEqual(probe_local_model(self.plan, operator_confirmed=True,
                                           transport=self.transport).status, "http_error")

    def test_real_transport_fixed_target_and_size_limit(self):
        response = Mock(status=200)
        response.read.return_value = b'{"models":[]}'
        response.getheader.return_value = "application/json"
        connection = Mock()
        connection.getresponse.return_value = response
        with patch("ai_broadcaster.core_ai_probe.http.client.HTTPConnection", return_value=connection) as factory:
            code, body, content_type = _fetch_loopback_tags()
        factory.assert_called_once_with("127.0.0.1", 11434, timeout=2.0)
        connection.request.assert_called_once_with(
            "GET", "/api/tags", headers={"Accept": "application/json", "Connection": "close"})
        response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)
        connection.close.assert_called_once()
        self.assertEqual((code, body, content_type), (200, b'{"models":[]}', "application/json"))

    def test_close_connection_on_failure(self):
        connection = Mock()
        connection.request.side_effect = OSError("offline")
        with patch("ai_broadcaster.core_ai_probe.http.client.HTTPConnection", return_value=connection):
            with self.assertRaises(OSError):
                _fetch_loopback_tags()
        connection.close.assert_called_once()

    def test_result_status_validation(self):
        with self.assertRaises(ValueError):
            ConnectionCheckResult("unknown", "x", False).describe()


if __name__ == "__main__":
    unittest.main()
