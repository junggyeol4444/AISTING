"""실제 GUI 창 없이 설정 선택/안전 정책을 검증한다."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ai_broadcaster.desktop_state import (
    AVATAR_LABELS, CONTENT_LABELS, VOICE_LABELS, PERSONA_LABELS,
    from_screen, label_for,
)
from ai_broadcaster.operator_settings import default_settings, save_settings, load_settings

def opts(**kwargs):
    sample = {
        "platforms": ["치지직", "유튜브"],
        "content": "수다 + 게임",
        "persona_mode": "기본값 사용",
        "persona_fields": {"name":"예시", "gender":"미정", "traits":"호기심", "speech_style":"한국어"},
        "voice":"나중에 선택",
        "avatar":"나중에 선택",
    }
    sample.update(kwargs)
    return sample

class TestNativeDesktop(unittest.TestCase):
    def test_platform_multi_select(self):
        data=from_screen(default_settings(), **opts())
        self.assertEqual(data["platforms"],["chzzk","youtube"])

    def test_can_leave_platform_undecided(self):
        data=from_screen(default_settings(),**opts(platforms=[]))
        self.assertEqual(data["platforms"],[])

    def test_every_content_choice(self):
        for label,expected in CONTENT_LABELS.items():
            with self.subTest(label=label):
                self.assertEqual(from_screen(default_settings(),**opts(content=label))["content"],expected)

    def test_every_voice_choice(self):
        for label,expected in VOICE_LABELS.items():
            self.assertEqual(from_screen(default_settings(),**opts(voice=label))["voice"],expected)

    def test_every_avatar_choice(self):
        for label,expected in AVATAR_LABELS.items():
            self.assertEqual(from_screen(default_settings(),**opts(avatar=label))["avatar"],expected)

    def test_custom_persona(self):
        data=from_screen(default_settings(),**opts(
            persona_mode="직접 만들기",
            persona_fields={"name":"나만의 AI","gender":"미정","traits":"차분","speech_style":"자연스러운 한국어"},
        ))
        self.assertEqual(data["persona"]["name"],"나만의 AI")
        self.assertEqual(data["persona"]["mode"],"custom")

    def test_default_persona(self):
        data=from_screen(default_settings(),**opts(persona_mode="기본값 사용"))
        self.assertEqual(data["persona"]["name"],"아이스팅")

    def test_local_pc_no_payment_no_broadcast(self):
        data=from_screen(default_settings(),**opts())
        op=data["operation"]
        self.assertEqual(op["host"],"local_pc")
        self.assertEqual(op["budget_mode"],"free_only")
        self.assertFalse(op["allow_paid_api"])
        self.assertFalse(op["allow_external_broadcast"])

    def test_invalid_platform_rejected(self):
        with self.assertRaises(ValueError):
            from_screen(default_settings(),**opts(platforms=["알 수 없는 플랫폼"]))

    def test_duplicate_platform_rejected(self):
        with self.assertRaises(ValueError):
            from_screen(default_settings(),**opts(platforms=["치지직","치지직"]))

    def test_unknown_dropdown_rejected(self):
        with self.assertRaises(ValueError):
            from_screen(default_settings(),**opts(content="임의의 내용"))

    def test_character_field_required(self):
        with self.assertRaises(ValueError):
            from_screen(default_settings(),**opts(persona_mode="직접 만들기",persona_fields={}))

    def test_save_and_load_unchanged(self):
        result=from_screen(default_settings(),**opts())
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"data"/"settings.json"
            save_settings(result,path)
            self.assertEqual(load_settings(path),result)

    def test_reverse_label_lookup(self):
        for choices in (CONTENT_LABELS,VOICE_LABELS,AVATAR_LABELS,PERSONA_LABELS):
            for label,code in choices.items():
                self.assertEqual(label_for(choices,code),label)
