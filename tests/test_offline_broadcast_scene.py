"""Original 071: scene composition contract and safety, no broadcast."""
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_broadcaster.offline_broadcast_scene import BroadcastSceneDraft, draw_broadcast_scene
from ai_broadcaster.avatar_layout import AvatarLayout
from ai_broadcaster.offline_settings import PLATFORMS, CONTENTS, AVATARS, VOICES


class FakeCanvas:
    def __init__(self):
        self.calls = []

    def __getattr__(self, method):
        if method in ('configure', 'delete', 'create_oval', 'create_arc',
                      'create_line', 'create_text', 'create_rectangle',
                      'scale', 'move', 'tag_lower'):
            def record(*args, **kwargs):
                self.calls.append((method, args, kwargs))
                return len(self.calls)
            return record
        raise AttributeError(method)

    def tags(self):
        return [tag for _, _, kwargs in self.calls for tag in kwargs.get('tags', ())]


def make(**overrides):
    args = dict(platforms=('chzzk',), content='chat', avatar='2d',
                voice='windows_system', persona_name='아이스팅',
                layout=AvatarLayout(), show_title=True, show_chat=True)
    args.update(overrides)
    return BroadcastSceneDraft(**args)


class SceneTests(unittest.TestCase):
    def test_default_valid_and_report_is_explicit(self):
        draft = make()
        text = draft.describe()
        for marker in ('원본 071', '640×360', '16:9', '오프라인', 'OBS', '송출',
                       'Windows', '사용자 최종 승인'):
            self.assertIn(marker, text)
        self.assertIn('치지직', text)

    def test_zero_platform_allowed_without_auto_selection(self):
        draft = make(platforms=())
        self.assertIn('플랫폼 미선택', draft.describe())
        self.assertEqual(draft.platforms, ())

    def test_all_platform_combinations_preserved(self):
        for platforms in (('youtube',), ('twitch', 'chzzk'),
                          ('chzzk', 'youtube', 'twitch')):
            with self.subTest(platforms=platforms):
                self.assertEqual(make(platforms=platforms).platforms, platforms)

    def test_reject_duplicate_platform(self):
        with self.assertRaises(ValueError):
            make(platforms=('chzzk', 'chzzk'))

    def test_reject_invalid_platforms(self):
        for platforms in ('chzzk', ['chzzk'], ('other',), (1,), (None,),
                          ('chzzk', 'youtube', 'twitch', 'other')):
            with self.subTest(platforms=platforms), self.assertRaises(ValueError):
                make(platforms=platforms)

    def test_content_modes(self):
        for code in CONTENTS.values():
            with self.subTest(code=code):
                self.assertIn('콘텐츠', make(content=code).describe())

    def test_invalid_content(self):
        for code in (None, 1, 'stream'):
            with self.assertRaises(ValueError):
                make(content=code)

    def test_avatar_modes_no_2d_fallback(self):
        for avatar in ('undecided', '3d'):
            draft = make(avatar=avatar, layout=None)
            self.assertIn('2D 자동 대체 없음', draft.describe())
            canvas = FakeCanvas()
            draw_broadcast_scene(canvas, draft)
            self.assertIn('aisting_scene_avatar_placeholder', canvas.tags())
            self.assertNotIn('aisting_sample_2d', canvas.tags())

    def test_2d_requires_existing_layout(self):
        with self.assertRaises(ValueError):
            make(layout=None)

    def test_3d_must_not_accept_2d_layout(self):
        with self.assertRaises(ValueError):
            make(avatar='3d')

    def test_invalid_avatar(self):
        with self.assertRaises(ValueError):
            make(avatar='4d', layout=None)

    def test_all_voice_choices_are_descriptive_only(self):
        for voice in VOICES.values():
            with self.subTest(voice=voice):
                self.assertIn('음성 출력/믹싱 미연결', make(voice=voice).describe())

    def test_invalid_voice(self):
        with self.assertRaises(ValueError):
            make(voice='cloud')

    def test_persona_validation(self):
        for name in ('', ' ', 'a'*201, 'bad\nname', 'bad\x00name'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                make(persona_name=name)

    def test_no_type_coercion_for_overlay_flags(self):
        for kw in ({'show_title': 1}, {'show_chat': 'true'}):
            with self.assertRaises(ValueError):
                make(**kw)

    def test_immutable_draft(self):
        with self.assertRaises(FrozenInstanceError):
            make().avatar = '3d'

    def test_2d_reuses_existing_layout_renderer(self):
        canvas = FakeCanvas()
        draw_broadcast_scene(canvas, make())
        self.assertIn('aisting_sample_2d', canvas.tags())
        self.assertIn('aisting_scene_content', canvas.tags())
        self.assertIn('aisting_scene_watermark', canvas.tags())
        self.assertTrue(any(name == 'scale' for name, _, _ in canvas.calls))
        self.assertTrue(any(name == 'tag_lower' for name, _, _ in canvas.calls))

    def test_undecided_content_draws_placeholder(self):
        canvas = FakeCanvas()
        draw_broadcast_scene(canvas, make(content='undecided'))
        self.assertTrue(any('콘텐츠 미정' in str(kwargs.get('text')) for name, _, kwargs in canvas.calls if name == 'create_text'))

    def test_game_does_not_capture_screen(self):
        canvas = FakeCanvas()
        draw_broadcast_scene(canvas, make(content='game'))
        self.assertTrue(any('캡처 없음' in str(kwargs.get('text')) for name, _, kwargs in canvas.calls if name == 'create_text'))

    def test_both_content_panels_and_chat_visibility(self):
        for show in (True, False):
            canvas = FakeCanvas()
            draw_broadcast_scene(canvas, make(content='both', show_chat=show))
            self.assertTrue(any('채팅 UI' in str(kwargs.get('text')) for name, _, kwargs in canvas.calls if name == 'create_text'))

    def test_title_toggle(self):
        for show in (True, False):
            canvas = FakeCanvas()
            draw_broadcast_scene(canvas, make(show_title=show))
            self.assertEqual('aisting_scene_title' in canvas.tags(), show)

    def test_expression_validation(self):
        with self.assertRaises(ValueError):
            draw_broadcast_scene(FakeCanvas(), make(), expression='auto')

    def test_bad_draft_type(self):
        with self.assertRaises(ValueError):
            draw_broadcast_scene(FakeCanvas(), object())

    def test_overlapping_avatar_is_warning_not_forced_move(self):
        draft = make(layout=AvatarLayout(horizontal=0, vertical=0, size=100))
        self.assertTrue(any('겹칠' in w for w in draft.warnings))
        self.assertEqual(draft.layout.horizontal, 0)

    def test_no_disk_network_process_or_device_access(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('sqlite3.connect', side_effect=AssertionError('database')):
            draft = make()
            draft.describe()
            draw_broadcast_scene(FakeCanvas(), draft)

    def test_no_mutation_of_operator_input(self):
        platforms = ('chzzk', 'youtube')
        layout = AvatarLayout(horizontal=55, vertical=40, size=90)
        draft = make(platforms=platforms, layout=layout)
        draw_broadcast_scene(FakeCanvas(), draft)
        self.assertEqual(draft.platforms, platforms)
        self.assertIs(draft.layout, layout)

    def test_all_selection_code_sets_match_original_options(self):
        self.assertEqual(set(PLATFORMS.values()), {'chzzk', 'youtube', 'twitch', 'soop'})
        self.assertEqual(set(AVATARS.values()), {'undecided', '2d', '3d'})
        self.assertEqual(set(CONTENTS.values()), {'undecided', 'chat', 'game', 'both'})


if __name__ == '__main__':
    unittest.main()
