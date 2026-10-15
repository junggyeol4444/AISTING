"""10단계 최종 개발 기준 검토: 자동 승인, GitHub 접근, 예약/송출 없음."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.development_review import (
    CriteriaReview, approval_path, approval_status, bundled_project_root, evaluate_review,
    load_review_sources, record_approval, revoke_approval,
)
from ai_broadcaster.offline_settings import DEFAULTS


class TestStageTenDevelopmentReview(unittest.TestCase):
    def setUp(self):
        self.req, self.road = load_review_sources(ROOT)
        self.settings = copy.deepcopy(DEFAULTS)
        self.review = evaluate_review(self.req, self.road, self.settings)

    def test_baseline_review_is_ready_but_not_approved(self):
        self.assertTrue(self.review.ready)
        self.assertEqual((self.review.completed_steps, self.review.pending_step), (9, 10))
        self.assertEqual(len(self.review.checks), 8)
        self.assertEqual(len(self.review.fingerprint), 64)
        self.assertIn("방송", self.review.describe())
        self.assertEqual(self.road["steps"][9]["status"], "pending")

    def test_review_is_pure_and_offline(self):
        before=(copy.deepcopy(self.req),copy.deepcopy(self.road),copy.deepcopy(self.settings))
        with patch("socket.create_connection") as network, patch("subprocess.Popen") as popen:
            fresh=evaluate_review(self.req,self.road,self.settings)
            network.assert_not_called()
            popen.assert_not_called()
        self.assertEqual(fresh,self.review)
        self.assertEqual((self.req,self.road,self.settings),before)

    def test_missing_receipt_does_not_create_data_dir(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"absent"/"approval.json"
            self.assertEqual(approval_status(self.review,path)[0],False)
            self.assertFalse(path.parent.exists())

    def test_approval_requires_explicit_operator_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"data"/"approval.json"
            with self.assertRaises(PermissionError):
                record_approval(self.review,path)
            self.assertFalse(path.parent.exists())

    def test_approval_round_trip_and_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            path=approval_path(Path(temp))
            record_approval(self.review,path,operator_confirmed=True)
            self.assertTrue(approval_status(self.review,path)[0])
            data=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["method"],"manual_operator_confirmed")
            self.assertEqual(data["decision"],"approved")
            self.assertIn("not_streaming",data["scope"])
            self.assertNotIn("name",data)
            self.assertNotIn("password",data)

    def test_approval_invalidated_after_local_persona_change(self):
        with tempfile.TemporaryDirectory() as temp:
            path=approval_path(Path(temp))
            record_approval(self.review,path,operator_confirmed=True)
            settings=copy.deepcopy(self.settings)
            settings["persona_mode"]="custom"
            settings["persona"]["name"]="내 방송 캐릭터"
            newer=evaluate_review(self.req,self.road,settings)
            self.assertNotEqual(newer.fingerprint,self.review.fingerprint)
            self.assertFalse(approval_status(newer,path)[0])
            self.assertTrue(path.exists())

    def test_approval_invalidated_after_plan_change(self):
        changed=copy.deepcopy(self.req)
        changed["goal"]="임의 수정된 개발 목표"
        changed_review=evaluate_review(changed,self.road,self.settings)
        self.assertNotEqual(self.review.fingerprint,changed_review.fingerprint)

    def test_unsafe_permissions_block_approval(self):
        for field in (
            "install_without_operator_approval", "charge_without_operator_approval",
            "publish_without_operator_approval", "broadcast_enabled_by_default",
            "clone_voice_without_permission",
        ):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temp:
                req=copy.deepcopy(self.req)
                req["control"][field]=True
                bad=evaluate_review(req,self.road,self.settings)
                self.assertFalse(bad.ready)
                with self.assertRaises(ValueError):
                    record_approval(bad,Path(temp)/"approval.json",operator_confirmed=True)
                self.assertEqual(list(Path(temp).iterdir()),[])

    def test_changed_default_streaming_is_blocked(self):
        settings=copy.deepcopy(self.settings)
        settings["streaming_enabled"]=True
        bad=evaluate_review(self.req,self.road,settings)
        self.assertFalse(bad.ready)
        self.assertFalse(next(c for c in bad.checks if c.code=="local_only").passed)

    def test_platform_preselection_gate_is_rejected(self):
        req=copy.deepcopy(self.req)
        req["operator_decisions"]["broadcast_platform"]="choose_one_before_dev"
        bad=evaluate_review(req,self.road,self.settings)
        self.assertFalse(bad.ready)
        self.assertFalse(next(c for c in bad.checks if c.code=="free_selection").passed)

    def test_prior_stage_incomplete_blocks(self):
        road=copy.deepcopy(self.road)
        road["steps"][8]["status"]="pending"
        self.assertFalse(evaluate_review(self.req,road,self.settings).ready)

    def test_premature_auto_completion_of_stage_ten_blocks(self):
        road=copy.deepcopy(self.road)
        road["steps"][9]["status"]="completed"
        self.assertFalse(evaluate_review(self.req,road,self.settings).ready)

    def test_roadmap_mutation_has_different_digest(self):
        road=copy.deepcopy(self.road)
        road["steps"][88]["title"]="특정 단계 변경"
        self.assertNotEqual(self.review.fingerprint,evaluate_review(self.req,road,self.settings).fingerprint)

    def test_corrupt_receipt_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"approval.json"
            file.write_text("corrupt json",encoding="utf-8")
            self.assertFalse(approval_status(self.review,file)[0])
            file.write_text(json.dumps({"schema_version":1,"decision":"approved"}),encoding="utf-8")
            self.assertFalse(approval_status(self.review,file)[0])

    def test_revoke_requires_confirmation_preserves_other_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path=approval_path(Path(temp))
            keep=Path(temp)/"settings.json"
            keep.write_text("original config",encoding="utf-8")
            record_approval(self.review,path,operator_confirmed=True)
            with self.assertRaises(PermissionError):
                revoke_approval(path)
            self.assertTrue(path.exists())
            revoke_approval(path,operator_confirmed=True)
            self.assertFalse(path.exists())
            self.assertEqual(keep.read_text(encoding="utf-8"),"original config")

    def test_sources_read_from_project_root(self):
        self.assertEqual(bundled_project_root(),ROOT)
        req,road=load_review_sources(ROOT)
        self.assertEqual(road["total_steps"],100)
        self.assertEqual(req["operator_decisions"]["hosting_option"],"local_pc")

    def test_approval_uses_bundled_source_when_exe(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)
            (source/"config").mkdir()
            (source/"config"/"requirements.json").write_text(
                json.dumps(self.req,ensure_ascii=False),encoding="utf-8")
            (source/"config"/"roadmap.json").write_text(
                json.dumps(self.road,ensure_ascii=False),encoding="utf-8")
            with patch.object(sys,"_MEIPASS",str(source),create=True):
                self.assertEqual(bundled_project_root(),source)
                loaded=load_review_sources()
                self.assertTrue(evaluate_review(*loaded,self.settings).ready)

    def test_windows_exe_packaging_includes_required_local_files(self):
        batch=(ROOT/"build_exe_windows.bat").read_text(encoding="utf-8")
        self.assertIn('--add-data "config;config"',batch)
        self.assertIn('--add-data "docs;docs"',batch)
        self.assertNotIn('git clone',batch.lower())
        self.assertNotIn('pip install',batch.lower())

    def test_gui_requires_manual_action_and_has_revocation(self):
        desktop=(ROOT/"src/ai_broadcaster/desktop.py").read_text(encoding="utf-8")
        self.assertIn('(review, "개발 기준 검토")',desktop)
        self.assertIn('command=self._approve_review',desktop)
        self.assertIn('command=self._revoke_review',desktop)
        self.assertIn('if not self._review_confirmation.get()',desktop)
        self.assertIn('messagebox.askyesno(',desktop)
        self.assertNotIn('self._approve_review()',desktop)


if __name__ == "__main__":
    unittest.main()
