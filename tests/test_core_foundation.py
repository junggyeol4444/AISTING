"""21단계 방송 코어 구조: 구성도/연결 계약/안전 경계 테스트."""
import copy
import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_broadcaster.core_foundation import (
    CORE_SCHEMA_VERSION, CORE_MODES, CoreBlueprint, CoreComponent,
    build_core_blueprint, validate_blueprint,
)
from ai_broadcaster.core_ports import CoreInput, CoreReply
from ai_broadcaster.offline_settings import DEFAULTS


class CoreFoundationTests(unittest.TestCase):
    def setUp(self):
        self.settings = copy.deepcopy(DEFAULTS)

    def test_default_seven_components(self):
        plan = build_core_blueprint(self.settings)
        self.assertEqual(plan.schema_version, CORE_SCHEMA_VERSION)
        self.assertEqual(len(plan.components), 7)
        self.assertEqual(plan.runtime_mode, "mock")

    def test_all_components_named(self):
        plan = build_core_blueprint(self.settings)
        self.assertEqual(tuple(p.key for p in plan.components),
                         ("input", "reply", "memory", "voice", "avatar", "broadcast", "orchestrator"))

    def test_no_broadcast_or_auto_start(self):
        plan = build_core_blueprint(self.settings)
        self.assertFalse(plan.streaming_enabled)
        self.assertFalse(plan.auto_start_enabled)
        self.assertFalse(plan.external_publish_enabled)

    def test_no_implemented_live_components(self):
        plan = build_core_blueprint(self.settings)
        self.assertEqual(plan.components[5].state, "not_implemented")
        self.assertEqual(plan.components[6].state, "not_implemented")

    def test_default_unselected_allowed(self):
        plan = build_core_blueprint(self.settings)
        self.assertEqual(plan.platforms, ())
        self.assertEqual(plan.avatar, "undecided")
        self.assertEqual(plan.voice, "undecided")

    def test_selected_platforms_order_preserved(self):
        self.settings["platforms"] = ["twitch", "chzzk", "youtube"]
        plan = build_core_blueprint(self.settings)
        self.assertEqual(plan.platforms, ("twitch", "chzzk", "youtube"))

    def test_content_and_persona_preserved(self):
        self.settings["content"] = "both"
        self.settings["persona_mode"] = "custom"
        self.settings["persona"]["name"] = "테스트"
        plan = build_core_blueprint(self.settings)
        self.assertEqual((plan.content, plan.persona_mode), ("both", "custom"))
        self.assertNotIn("테스트", plan.describe())  # no user private data in report

    def test_2d_sample_is_not_broadcast_avatar(self):
        self.settings["avatar"] = "2d"
        plan = build_core_blueprint(self.settings)
        self.assertEqual(plan.components[4].state, "manual_only")
        self.assertEqual(plan.components[5].state, "not_implemented")

    def test_3d_not_substituted_by_2d(self):
        self.settings["avatar"] = "3d"
        plan = build_core_blueprint(self.settings)
        self.assertEqual(plan.components[4].state, "not_implemented")
        self.assertIn("미구현", plan.describe())

    def test_windows_voice_manual_only(self):
        self.settings["voice"] = "windows_system"
        self.assertEqual(build_core_blueprint(self.settings).components[3].state, "manual_only")

    def test_other_voice_sources_not_implemented(self):
        for voice in ("undecided", "own_recording", "consented_recording", "licensed_recording"):
            with self.subTest(voice=voice):
                self.settings["voice"] = voice
                self.assertEqual(build_core_blueprint(self.settings).components[3].state, "not_implemented")

    def test_local_ollama_is_manual_and_not_called(self):
        plan = build_core_blueprint(self.settings, "local_ollama")
        self.assertEqual(plan.components[1].state, "manual_only")
        self.assertIn("미검증", plan.describe())

    def test_unknown_runtime_mode_rejected(self):
        for mode in ("cloud", "http://localhost", "", None, True):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                build_core_blueprint(self.settings, mode)

    def test_invalid_settings_rejected(self):
        self.settings["streaming_enabled"] = True
        with self.assertRaises(ValueError):
            build_core_blueprint(self.settings)

    def test_duplicate_platform_rejected(self):
        self.settings["platforms"] = ["youtube", "youtube"]
        with self.assertRaises(ValueError):
            build_core_blueprint(self.settings)

    def test_input_not_mutated(self):
        before = copy.deepcopy(self.settings)
        build_core_blueprint(self.settings)
        self.assertEqual(self.settings, before)

    def test_plan_does_not_follow_mutated_input(self):
        plan = build_core_blueprint(self.settings)
        self.settings["platforms"].append("youtube")
        self.assertEqual(plan.platforms, ())

    def test_dependency_graph_is_acyclic(self):
        plan = build_core_blueprint(self.settings)
        seen = set()
        for part in plan.components:
            self.assertTrue(set(part.depends_on) <= seen)
            seen.add(part.key)
        validate_blueprint(plan)

    def test_reject_dangling_dependency(self):
        plan = build_core_blueprint(self.settings)
        parts = list(plan.components)
        parts[2] = dataclasses.replace(parts[2], depends_on=("missing",))
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=tuple(parts)))

    def test_reject_cycle(self):
        plan = build_core_blueprint(self.settings)
        parts = list(plan.components)
        parts[0] = dataclasses.replace(parts[0], depends_on=("orchestrator",))
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=tuple(parts)))

    def test_reject_duplicate_component(self):
        plan = build_core_blueprint(self.settings)
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=plan.components[:-1] + (plan.components[-2],)))

    def test_reject_live_marked_implemented(self):
        plan = build_core_blueprint(self.settings)
        parts = list(plan.components)
        parts[5] = dataclasses.replace(parts[5], state="implemented")
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=tuple(parts)))

    def test_reject_core_marked_implemented(self):
        plan = build_core_blueprint(self.settings)
        parts = list(plan.components)
        parts[6] = dataclasses.replace(parts[6], state="implemented")
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=tuple(parts)))

    def test_reject_auto_start_and_external_publish(self):
        plan = build_core_blueprint(self.settings)
        for key in ("streaming_enabled", "auto_start_enabled", "external_publish_enabled"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_blueprint(dataclasses.replace(plan, **{key: True}))

    def test_reject_invalid_schema(self):
        plan = build_core_blueprint(self.settings)
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, schema_version=2))

    def test_reject_invalid_selected_platform(self):
        plan = build_core_blueprint(self.settings)
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, platforms=("fake",)))

    def test_reject_invalid_selected_voice(self):
        plan = build_core_blueprint(self.settings)
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, voice="unauthorized"))

    def test_reject_voice_state_forgery(self):
        plan = build_core_blueprint(self.settings)
        parts = list(plan.components)
        parts[3] = dataclasses.replace(parts[3], state="implemented")
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=tuple(parts)))

    def test_reject_avatar_state_forgery(self):
        plan = build_core_blueprint(self.settings)
        parts = list(plan.components)
        parts[4] = dataclasses.replace(parts[4], state="manual_only")
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=tuple(parts)))

    def test_reject_malformed_component_object(self):
        plan = build_core_blueprint(self.settings)
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=(None,) + plan.components[1:]))

    def test_reject_invalid_component_state(self):
        plan = build_core_blueprint(self.settings)
        parts = list(plan.components)
        parts[0] = dataclasses.replace(parts[0], state="ready_to_stream")
        with self.assertRaises(ValueError):
            validate_blueprint(dataclasses.replace(plan, components=tuple(parts)))

    def test_core_port_types_are_data_only(self):
        item = CoreInput("시청자", "안녕하세요")
        reply = CoreReply(item, "반가워요")
        self.assertEqual(reply.input, item)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            reply.text = "변경"

    def test_report_has_explicit_limitations(self):
        report = build_core_blueprint(self.settings).describe()
        for word in ("미구현", "승인", "외부 오픈소스", "9/100", "22단계"):
            self.assertIn(word, report)

    def test_build_has_no_network_subprocess_hardware_or_operator_files(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "operator"
            with patch("socket.create_connection", side_effect=AssertionError("network")) as net, \
                 patch("subprocess.Popen", side_effect=AssertionError("process")) as proc, \
                 patch("platform.system", side_effect=AssertionError("hardware")) as hw, \
                 patch.dict("os.environ", {"LOCALAPPDATA": str(base), "HOME": str(base)}):
                for mode in CORE_MODES:
                    build_core_blueprint(self.settings, mode).describe()
                net.assert_not_called()
                proc.assert_not_called()
                hw.assert_not_called()
            self.assertFalse(base.exists())


if __name__ == "__main__":
    unittest.main()
