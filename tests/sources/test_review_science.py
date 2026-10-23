"""Review provenance, usable text and topic-level build restrictions."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("review_science", ROOT / "skills/review-science/scripts/finalize.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ScienceReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        snapshot = self.root / "storage/sources/src-test/v001/index.html"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text("<p>确定事实</p><p>未核定规则</p>", encoding="utf-8")
        self.extraction = snapshot.parent / "extractions/extract-001"
        asset = self.extraction / "assets/svg-001.svg"
        asset.parent.mkdir(parents=True)
        asset.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        source_ref = {"source_id": "src-test", "source_version": "v001", "sha256": MODULE.sha256(snapshot), "snapshot_path": snapshot.relative_to(self.root).as_posix()}
        content = {"source_ref": source_ref, "extraction_id": "extract-001", "text_blocks": [{"id": "block-001", "text": "确定事实"}, {"id": "block-002", "text": "未核定规则"}], "diagrams": [{"id": "svg-001", "path": "assets/svg-001.svg", "sha256": MODULE.sha256(asset)}]}
        knowledge = {"source_ref": source_ref, "extraction_id": "extract-001", "knowledge_points": [{"id": "kp-001", "title": "事实"}, {"id": "kp-002", "title": "规则"}], "review_items": [{"id": "review-001"}], "candidate_topics": [{"id": "topic-001", "title": "事实选题", "knowledge_point_ids": ["kp-001"]}, {"id": "topic-002", "title": "规则选题", "knowledge_point_ids": ["kp-002"]}]}
        write_json(self.extraction / "content.json", content)
        write_json(self.extraction / "knowledge.json", knowledge)
        self.review = {
            "schema_version": "1.0", "review_id": "review-001", "source_ref": source_ref,
            "extraction_id": "extract-001", "reviewed_at": "2026-10-16T08:00:00+00:00",
            "reviewer": {"type": "agent", "name": "Test agent"},
            "skill": {"name": "review-science", "version": "0.1.0", "instructions_sha256": MODULE.sha256(ROOT / "skills/review-science/SKILL.md")},
            "input_hashes": {"content_sha256": MODULE.sha256(self.extraction / "content.json"), "knowledge_sha256": MODULE.sha256(self.extraction / "knowledge.json")},
            "scope_notes": ["测试独立选题的可用性。"],
            "evidence": [{"id": "evidence-001", "title": "Example source", "publisher": "Example", "url": "https://example.org/source", "section": "Facts", "accessed_on": "2026-10-16", "note": "Fixture only."}],
            "claims": [
                {"id": "claim-001", "title": "事实", "original_text": "确定事实", "source_refs": ["block-001"], "knowledge_point_ids": ["kp-001"], "related_review_item_ids": [], "decision": "revise", "reason": "需修订措辞。", "recommended_text": "修订后的事实。", "evidence_ids": ["evidence-001"], "scope": "通用科普", "constraints": []},
                {"id": "claim-002", "title": "规则", "original_text": "未核定规则", "source_refs": ["block-002"], "knowledge_point_ids": ["kp-002"], "related_review_item_ids": ["review-001"], "decision": "unresolved", "reason": "缺少教材。", "recommended_text": None, "evidence_ids": [], "scope": "具体教材", "constraints": ["待提供版本。"]},
            ],
            "diagram_reviews": [{"diagram_id": "svg-001", "decision": "revise", "claim_ids": ["claim-001"], "requirements": ["修订替代文本。"]}],
            "topic_plans": [
                {"topic_id": "topic-001", "scope": "通用科普", "claim_ids": ["claim-001"], "diagram_ids": ["svg-001"], "constraints": []},
                {"topic_id": "topic-002", "scope": "具体教材", "claim_ids": ["claim-002"], "diagram_ids": [], "constraints": []},
            ],
        }
        self.review_path = self.extraction / "reviews/review-001/review.json"

    def finalize(self, review=None):
        write_json(self.review_path, review or self.review)
        return MODULE.finalize(self.root, self.extraction, self.review_path)

    def test_unresolved_topic_does_not_block_independent_topic(self):
        result = self.finalize()
        first, second = result["topics"]
        self.assertEqual(first["readiness"], "ready_for_build")
        self.assertEqual(first["statements"][0]["recommended_text"], "修订后的事实。")
        self.assertEqual(first["required_changes"][0]["instructions"], ["修订替代文本。"])
        self.assertEqual(second["readiness"], "blocked")
        self.assertEqual(second["statements"], [])
        self.assertTrue(result["requires_publication_approval"])
        self.assertEqual(result["status"], "completed_with_open_items")

    def test_usable_claim_requires_evidence(self):
        self.review["claims"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(ValueError, "Claim evidence"):
            self.finalize()

    def test_unresolved_claim_cannot_export_usable_text(self):
        self.review["claims"][1]["recommended_text"] = "未经核定的规则。"
        with self.assertRaisesRegex(ValueError, "Unresolved claim"):
            self.finalize()

    def test_changed_extraction_invalidates_review(self):
        with (self.extraction / "content.json").open("a") as handle:
            handle.write(" ")
        with self.assertRaisesRegex(ValueError, "input hash mismatch"):
            self.finalize()

    def test_missing_coverage_is_rejected(self):
        for field in ["claims", "diagram_reviews", "topic_plans"]:
            with self.subTest(field=field):
                candidate = deepcopy(self.review)
                candidate[field].pop()
                with self.assertRaises(ValueError):
                    self.finalize(candidate)

    def test_diagram_carries_unresolved_dependency_into_topic(self):
        self.review["diagram_reviews"][0]["claim_ids"] = ["claim-002"]
        result = self.finalize()
        self.assertEqual(result["topics"][0]["readiness"], "blocked")
        self.assertIn("claim-002", result["topics"][0]["blocking_claim_ids"])
        self.assertEqual(result["topics"][0]["statements"], [])

    def test_quote_must_be_locatable_in_source(self):
        self.review["claims"][0]["original_text"] = "原文不存在的句子"
        with self.assertRaisesRegex(ValueError, "quote not found"):
            self.finalize()

    def test_unknown_evidence_reference_is_rejected(self):
        self.review["claims"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "unknown references"):
            self.finalize()

    def test_rerun_is_stable_and_keeps_inputs(self):
        before = {name: MODULE.sha256(self.extraction / name) for name in ["content.json", "knowledge.json"]}
        first = self.finalize()
        second = self.finalize()
        self.assertEqual(first, second)
        self.assertEqual(before, {name: MODULE.sha256(self.extraction / name) for name in before})
        self.assertEqual(first["provenance"]["review_sha256"], MODULE.sha256(self.review_path))

    def test_changed_review_cannot_overwrite_finalized_outputs(self):
        self.finalize()
        output = self.review_path.parent / "reviewed-knowledge.json"
        before = output.read_bytes()
        self.review["claims"][0]["recommended_text"] = "另一份修订。"
        with self.assertRaisesRegex(ValueError, "Existing output differs"):
            self.finalize()
        self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
