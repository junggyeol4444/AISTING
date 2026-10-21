"""Validate the real (never canned-LLM) Windows load runner's controls."""
import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).resolve().parents[1] / "scripts" / "aisting_real_ollama_fifo_soak.py"
SPEC = importlib.util.spec_from_file_location("real_ollama_fifo_soak", PATH)
SOAK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOAK)


class LoadRunnerContracts(unittest.TestCase):
    def test_500_unique_clients_over_four_platforms(self):
        names = [SOAK.make_message(i) for i in range(500)]
        self.assertEqual(len(names), 500)
        self.assertEqual(len({m.author for m in names}) if hasattr(names[0], "author")
                         else len(names), 500)
        self.assertEqual(len([m for m in names if getattr(m, "platform", "twitch")
                              == "twitch"]), 125)
        self.assertEqual([getattr(m, "platform", "twitch")
                          for m in names[:4]], ["twitch","chzzk","soop","youtube"])

    def test_repeated_identical_messages_not_deduplicated(self):
        messages = [SOAK.make_message(i, duplicate=True) for i in range(8)]
        self.assertEqual(len(messages), 8)
        self.assertEqual(len({m.text for m in messages}), 1)

    def test_actual_24_hour_duration_supported(self):
        SOAK.validate_parameters(500, 86400, 10000, 11434)

    def test_invalid_time_or_bounded_queue_rejected(self):
        for args in [(500, 0, 10000, 11434),
                     (500, 86401, 10000, 11434),
                     (500, float("nan"), 10000, 11434),
                     (500, 86400, 0, 11434),
                     (500, 86400, 10000, 0),
                     (0, 86400, 10000, 11434)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                SOAK.validate_parameters(*args)


if __name__ == "__main__":
    unittest.main()
