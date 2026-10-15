"""8단계: 미정·2D·3D 자유 선택, 표시의 정직성, PC 저장 및 승인 보호."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ai_broadcaster.avatar_choices import avatar_choice
from ai_broadcaster.avatar_renderer import draw_unavailable_3d
from ai_broadcaster.offline_settings import DEFAULTS, AVATARS, load_settings, save_settings, validate_settings
from ai_broadcaster.requirements import load_json, validate, status


class TestAvatarChoice(unittest.TestCase):
    def test_choice_labels_exactly_undecided_2d_3d(self):
        self.assertEqual(AVATARS,{'미정':'undecided','2D':'2d','3D':'3d'})

    def test_undecided_keeps_option_open_and_sample_is_only_demo(self):
        s=avatar_choice('undecided')
        self.assertTrue(s.sample_2d_visible)
        self.assertTrue(s.can_open_sample_window)
        self.assertIn('선택과 무관한',s.description)

    def test_2d_selected_has_sample_not_live2d_model(self):
        s=avatar_choice('2d')
        self.assertTrue(s.sample_2d_visible)
        self.assertTrue(s.can_open_sample_window)
        self.assertIn('미구현',s.description)
        self.assertIn('샘플',s.description)

    def test_3d_selected_does_not_fake_2d_as_3d(self):
        s=avatar_choice('3d')
        self.assertFalse(s.sample_2d_visible)
        self.assertFalse(s.can_open_sample_window)
        self.assertIn('VRM',s.description)
        self.assertIn('미설치',s.description)

    def test_unexpected_choice_is_rejected_no_silent_fallback(self):
        for code in ('4d','',None,2,[],{},True):
            with self.subTest(code=code),self.assertRaises(ValueError):
                avatar_choice(code)

    def test_render_3d_placeholder_does_not_draw_fake_2d_person(self):
        canvas=Mock()
        draw_unavailable_3d(canvas)
        canvas.delete.assert_called_once_with('all')
        self.assertEqual(canvas.create_oval.call_count,0)
        self.assertEqual(canvas.create_text.call_count,2)
        self.assertIn('VRM',str(canvas.create_text.call_args_list))

    def test_default_is_undecided(self):
        self.assertEqual(DEFAULTS['avatar'],'undecided')

    def test_all_choices_can_roundtrip_without_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch('socket.create_connection') as network:
            p=Path(tmp)/'settings.json'
            for code in AVATARS.values():
                value=copy.deepcopy(DEFAULTS)
                value['avatar']=code
                value['persona']['name']='수정 캐릭터'
                save_settings(value,p)
                restored=load_settings(p)
                self.assertEqual(restored['avatar'],code)
                self.assertEqual(restored['persona']['name'],'수정 캐릭터')
                self.assertFalse(restored['streaming_enabled'])
                self.assertFalse(restored['external_publish_enabled'])
            network.assert_not_called()

    def test_bad_avatar_value_is_rejected_without_overwriting_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'settings.json'
            save_settings(copy.deepcopy(DEFAULTS),p)
            before=p.read_bytes()
            value=copy.deepcopy(DEFAULTS)
            value['avatar']='unsupported'
            with self.assertRaises(ValueError):save_settings(value,p)
            self.assertEqual(p.read_bytes(),before)

    def test_v08_saved_settings_do_not_need_schema_migration(self):
        for code in AVATARS.values():
            old=copy.deepcopy(DEFAULTS)
            old['avatar']=code
            self.assertEqual(validate_settings(old)['avatar'],code)

    def test_gui_has_no_automatic_vrm_install_or_3d_claim(self):
        text=(ROOT/'src/ai_broadcaster/desktop.py').read_text('utf-8')
        self.assertIn('self._avatar.trace_add("write", self._avatar_changed)',text)
        self.assertIn('draw_unavailable_3d(self._canvas)',text)
        self.assertIn('can_open_sample_window',text)
        self.assertIn('command=self._open_avatar_capture',text)
        self.assertNotIn('StartStream',text)
        self.assertNotIn('subprocess.run(["vrm"',text)

    def test_renderer_never_connects_to_website(self):
        source=(ROOT/'src/ai_broadcaster/avatar_choices.py').read_text('utf-8')
        for forbidden in ('requests.get(', 'urlopen(', 'github.com', 'StartStream'):
            self.assertNotIn(forbidden,source)

    def test_stage8_completed_is_choice_only_not_3d_rendering(self):
        req=load_json(ROOT/'config/requirements.json')
        road=load_json(ROOT/'config/roadmap.json')
        self.assertEqual(validate(req,road),[])
        self.assertEqual((status(road)['completed'],status(road)['current']['number']),(9,10))
        self.assertEqual(road['steps'][7]['status'],'completed')
        self.assertIn('선택형',road['steps'][7]['title'])
        self.assertEqual(road['steps'][8]['status'],'completed')
        self.assertEqual(road['steps'][9]['status'],'pending')

    def test_validator_catches_stage8_gate_reintroduced(self):
        req=load_json(ROOT/'config/requirements.json')
        road=load_json(ROOT/'config/roadmap.json')
        road['steps'][7]['status']='pending'
        self.assertTrue(any('8단계' in e for e in validate(req,road)))

    def test_no_git_actions_or_scheduled_files(self):
        self.assertFalse((ROOT/'.git').exists())
        self.assertFalse((ROOT/'.github').exists())
        self.assertFalse((ROOT/'package.json').exists())
        self.assertFalse(any(ROOT.rglob('*.yml')))


if __name__=='__main__':
    unittest.main()
