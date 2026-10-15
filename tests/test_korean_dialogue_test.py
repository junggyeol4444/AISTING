"""25단계 한국어 대화 구조 시험: 모의 응답만, 파일/네트워크/PC 무접근."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.korean_dialogue_test import (
    SAMPLE_KOREAN_SCRIPT, MAX_KOREAN_SCRIPT, MAX_KOREAN_TURNS,
    _has_hangul, _valid_reply, run_korean_dialogue_test,
)
from ai_broadcaster.offline_settings import DEFAULTS


class StubPort:
    def __init__(self, responses=None, fail_at=None):
        self.responses = responses
        self.fail_at = fail_at
        self.seen = []

    def generate(self, item, history):
        self.seen.append((item, history))
        if self.fail_at == len(self.seen):
            raise RuntimeError("가짜 실패")
        if self.responses is not None:
            return self.responses[len(self.seen) - 1]
        return "한국어로 답변합니다."


class KoreanDialogueTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def test_sample_passes(self):
        result = run_korean_dialogue_test(self.settings)
        self.assertTrue(result.passed)
        self.assertEqual(result.total, 7)
        self.assertEqual(result.remaining, 0)
        self.assertEqual(result.passed_count, 7)

    def test_sample_contains_duplicates(self):
        result = run_korean_dialogue_test(self.settings)
        self.assertEqual(result.turns[0].input_text, result.turns[2].input_text)
        self.assertEqual(result.turns[0].sender, result.turns[2].sender)

    def test_sample_contains_mixed_and_emoji(self):
        result = run_korean_dialogue_test(self.settings)
        self.assertIn("🎮", result.turns[3].response)
        self.assertIn("hello 123", result.turns[5].response)

    def test_custom_fifo(self):
        result = run_korean_dialogue_test(self.settings, "가: 안녕\n나: 잘 지내?\n가: 안녕")
        self.assertTrue(result.passed)
        self.assertEqual([x.sender for x in result.turns], ["가", "나", "가"])

    def test_custom_user_input_not_modified(self):
        script = "  가: 안녕!\n나: 테스트?"
        original = script
        run_korean_dialogue_test(self.settings, script)
        self.assertEqual(script, original)

    def test_settings_not_modified(self):
        before = copy.deepcopy(self.settings)
        run_korean_dialogue_test(self.settings)
        self.assertEqual(self.settings, before)

    def test_ignores_local_model_selection(self):
        self.settings["content"] = "game"
        self.assertTrue(run_korean_dialogue_test(self.settings).passed)

    def test_two_runs_independent(self):
        a = run_korean_dialogue_test(self.settings, "가: 하나")
        b = run_korean_dialogue_test(self.settings, "나: 둘")
        self.assertEqual((a.total, b.total), (1, 1))
        self.assertEqual(b.turns[0].sender, "나")

    def test_no_implicit_network_or_sqlite_or_process(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network")) as net, \
             patch("sqlite3.connect", side_effect=AssertionError("sqlite")) as sql, \
             patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
             patch("platform.system", side_effect=AssertionError("pc info")) as pc:
            self.assertTrue(run_korean_dialogue_test(self.settings).passed)
            net.assert_not_called()
            sql.assert_not_called()
            proc.assert_not_called()
            pc.assert_not_called()

    def test_no_settings_save(self):
        with patch("ai_broadcaster.offline_settings.save_settings", side_effect=AssertionError("write")) as saver:
            self.assertTrue(run_korean_dialogue_test(self.settings).passed)
            saver.assert_not_called()

    def test_empty_script_rejected(self):
        with self.assertRaises(ValueError):
            run_korean_dialogue_test(self.settings, "")

    def test_script_wrong_type_rejected(self):
        for invalid in (None, "가: 안녕".encode("utf-8"), 123):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                run_korean_dialogue_test(self.settings, invalid)

    def test_script_too_large_rejected(self):
        with self.assertRaises(ValueError):
            run_korean_dialogue_test(self.settings, "가: " + "안" * MAX_KOREAN_SCRIPT)

    def test_max_turns_accepted(self):
        result = run_korean_dialogue_test(self.settings, "\n".join(f"가: 안녕{i}" for i in range(MAX_KOREAN_TURNS)))
        self.assertTrue(result.passed)
        self.assertEqual(result.total, MAX_KOREAN_TURNS)

    def test_too_many_turns_rejected(self):
        with self.assertRaises(ValueError):
            run_korean_dialogue_test(self.settings, "\n".join("가: 안녕" for _ in range(MAX_KOREAN_TURNS + 1)))

    def test_invalid_line_rejected(self):
        with self.assertRaises(ValueError):
            run_korean_dialogue_test(self.settings, "가: 안녕\n형식오류")

    def test_english_only_rejected(self):
        with self.assertRaises(ValueError):
            run_korean_dialogue_test(self.settings, "abc: hello")

    def test_english_mixed_allowed(self):
        result = run_korean_dialogue_test(self.settings, "a: hello\nb: 안녕")
        self.assertTrue(result.passed)

    def test_korean_nfd_recognized(self):
        import unicodedata
        nfd = unicodedata.normalize("NFD", "안녕")
        self.assertTrue(_has_hangul(nfd))
        self.assertTrue(run_korean_dialogue_test(self.settings, "가: " + nfd).passed)

    def test_invalid_settings_rejected(self):
        invalid = copy.deepcopy(self.settings)
        invalid["avatar"] = "illegal"
        with self.assertRaises(ValueError):
            run_korean_dialogue_test(invalid)

    def test_korean_answer_required(self):
        result = run_korean_dialogue_test(self.settings, "가: 안녕", reply_port=StubPort(["hello"]))
        self.assertFalse(result.passed)
        self.assertEqual(result.passed_count, 0)
        self.assertIn("한글", result.turns[0].reason)

    def test_replacement_character_rejected(self):
        result = run_korean_dialogue_test(self.settings, "가: 안녕", reply_port=StubPort(["안녕\ufffd"]))
        self.assertFalse(result.passed)

    def test_control_character_rejected(self):
        result = run_korean_dialogue_test(self.settings, "가: 안녕", reply_port=StubPort(["안녕\x00"]))
        self.assertFalse(result.passed)

    def test_newline_and_tab_allowed(self):
        self.assertTrue(_valid_reply("안녕\n반가워\t요"))

    def test_empty_answer_error_keeps_pending(self):
        result = run_korean_dialogue_test(self.settings, "가: 안녕", reply_port=StubPort([""]))
        self.assertFalse(result.passed)
        self.assertEqual(result.remaining, 1)
        self.assertIn("ValueError", result.error)

    def test_generator_error_keeps_pending(self):
        port = StubPort(fail_at=2)
        result = run_korean_dialogue_test(self.settings, "가: 안녕\n나: 반가워\n다: 좋아", reply_port=port)
        self.assertFalse(result.passed)
        self.assertEqual(result.passed_count, 1)
        self.assertEqual(result.remaining, 2)
        self.assertIn("RuntimeError", result.error)
        self.assertEqual(len(port.seen), 2)

    def test_previous_history_provided(self):
        port = StubPort()
        self.assertTrue(run_korean_dialogue_test(self.settings, "가: 안녕\n나: 잘 지내?", reply_port=port).passed)
        self.assertEqual(len(port.seen[0][1]), 0)
        self.assertEqual(len(port.seen[1][1]), 1)

    def test_oversized_response_failure(self):
        result = run_korean_dialogue_test(self.settings, "가: 안녕", reply_port=StubPort(["안" * 6001]))
        self.assertFalse(result.passed)
        self.assertEqual(result.remaining, 1)

    def test_report_explicitly_not_model_quality(self):
        text = run_korean_dialogue_test(self.settings).describe()
        self.assertIn("자연스러움", text)
        self.assertIn("실제 AI 품질", text)
        self.assertIn("9/100", text)

    def test_report_failure_not_success(self):
        text = run_korean_dialogue_test(self.settings, "가: 안녕", reply_port=StubPort(["english"])).describe()
        self.assertIn("구조 시험 실패", text)
        self.assertIn("0/1", text)

    def test_result_is_immutable(self):
        from dataclasses import FrozenInstanceError
        result = run_korean_dialogue_test(self.settings)
        with self.assertRaises(FrozenInstanceError):
            result.total = 999


if __name__ == "__main__":
    unittest.main()
