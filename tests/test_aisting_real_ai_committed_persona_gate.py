"""Read-only unit checks for the EXISTING Windows AISTING real AI send guard.

No AI calls, no user settings writes, no OBS, and no GUI launch.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ai_broadcaster import original_plan_studio as studio


class ConfirmedPersonaBeforeRealAiTests(unittest.TestCase):
    def setUp(self):
        self.obj = object.__new__(studio.OriginalPlanStudio)
        self.confirmed = {'name': '디스크확정', 'style': '존댓말', 'character': '친절함'}
        self.obj.project_dir = SimpleNamespace(get=lambda: 'C:/Open-LLM-VTuber')
        self.obj._read_confirmed_persona_from_disk = lambda: dict(self.confirmed)

    def test_uses_only_disk_confirmed_persona(self):
        self.obj.app = SimpleNamespace(settings={'persona': {'name': '미확정초안'}})
        with patch.object(studio, 'inspect_saved_persona_alignment', return_value=True) as inspected:
            self.assertEqual(self.obj._require_confirmed_persona_for_real_ai(), self.confirmed)
            inspected.assert_called_once_with('C:/Open-LLM-VTuber', self.confirmed)

    def test_official_conf_mismatch_blocks(self):
        with patch.object(studio, 'inspect_saved_persona_alignment', return_value=False):
            with self.assertRaises(studio.StageOneUnavailable):
                self.obj._require_confirmed_persona_for_real_ai()

    def test_missing_committed_persona_blocks_without_probing(self):
        def fail():
            raise studio.StageOneUnavailable('저장한 캐릭터 없음')
        self.obj._read_confirmed_persona_from_disk = fail
        with patch.object(studio, 'inspect_saved_persona_alignment') as inspected:
            with self.assertRaises(studio.StageOneUnavailable):
                self.obj._require_confirmed_persona_for_real_ai()
            inspected.assert_not_called()

    def test_reads_newer_confirmation_instead_of_draft(self):
        current = {'name': '이후확정', 'style': '새말투', 'character': '새성격'}
        self.obj._read_confirmed_persona_from_disk = lambda: dict(current)
        with patch.object(studio, 'inspect_saved_persona_alignment', return_value=True) as inspected:
            self.obj._require_confirmed_persona_for_real_ai()
        self.assertEqual(inspected.call_args.args[1], current)

    def test_submit_guard_before_and_after_approval(self):
        import inspect
        source = inspect.getsource(studio.OriginalPlanStudio._open_real_ai_chat)
        block = ast.parse(source.lstrip() if not source.startswith(' ') else
                          __import__('textwrap').dedent(source))
        send = next(n for n in ast.walk(block)
                    if isinstance(n, ast.FunctionDef) and n.name == 'send')
        guard = [n.lineno for n in ast.walk(send)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == '_require_confirmed_persona_for_real_ai']
        approve = [n.lineno for n in ast.walk(send)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == 'askyesno']
        self.assertEqual(len(guard), 2)
        self.assertEqual(len(approve), 1)
        self.assertLess(min(guard), approve[0])
        self.assertLess(approve[0], max(guard))


if __name__ == '__main__':
    unittest.main()
