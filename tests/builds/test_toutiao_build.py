"""Versioned article output and review/approval boundaries."""

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = import_file("toutiao_build", ROOT / "skills/toutiao-build/scripts/build.py")
REVIEW = import_file("science_review", ROOT / "skills/review-science/scripts/finalize.py")


class ToutiaoBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        snapshot = self.root / "storage/sources/src-test/v001/index.html"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text("<p>已核对事实</p><p>待核对规则</p>", encoding="utf-8")
        self.extraction = snapshot.parent / "extractions/extract-001"
        diagram = self.extraction / "assets/svg-001.svg"
        diagram.parent.mkdir(parents=True)
        diagram.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" aria-label="旧燃烧标签"><style>.kf{fill:var(--card)}</style><circle class="kf" cx="50" cy="50" r="30"/></svg>', encoding="utf-8")
        source = {"source_id": "src-test", "source_version": "v001", "sha256": BUILD.sha(snapshot), "snapshot_path": snapshot.relative_to(self.root).as_posix()}
        content = {"source_ref": source, "extraction_id": "extract-001", "text_blocks": [{"id": "block-001", "text": "已核对事实"}, {"id": "block-002", "text": "待核对规则"}], "diagrams": [{"id": "svg-001", "path": "assets/svg-001.svg", "sha256": BUILD.sha(diagram)}]}
        knowledge = {"source_ref": source, "extraction_id": "extract-001", "knowledge_points": [{"id": "kp-001", "title": "事实"}, {"id": "kp-002", "title": "规则"}], "review_items": [{"id": "item-001"}], "candidate_topics": [{"id": "topic-001", "title": "可用选题", "knowledge_point_ids": ["kp-001"]}, {"id": "topic-002", "title": "等待选题", "knowledge_point_ids": ["kp-002"]}]}
        BUILD.dump(self.extraction / "content.json", content)
        BUILD.dump(self.extraction / "knowledge.json", knowledge)
        review = {
            "schema_version": "1.0", "review_id": "review-001", "source_ref": source, "extraction_id": "extract-001", "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "reviewer": {"type": "agent", "name": "Fixture"}, "skill": {"name": "review-science", "version": "0.1.0", "instructions_sha256": BUILD.sha(ROOT / "skills/review-science/SKILL.md")},
            "input_hashes": {"content_sha256": BUILD.sha(self.extraction / "content.json"), "knowledge_sha256": BUILD.sha(self.extraction / "knowledge.json")},
            "scope_notes": ["结构与状态测试。"],
            "evidence": [{"id": "evidence-001", "title": "Fixture", "publisher": "Fixture", "url": "https://example.org/fixture", "section": "Fixture", "accessed_on": datetime.now(timezone.utc).date().isoformat(), "note": "测试数据。"}],
            "claims": [
                {"id": "claim-001", "title": "事实", "original_text": "已核对事实", "source_refs": ["block-001"], "knowledge_point_ids": ["kp-001"], "related_review_item_ids": [], "decision": "supported", "reason": "Fixture", "recommended_text": "已核对事实。", "evidence_ids": ["evidence-001"], "scope": "Fixture", "constraints": []},
                {"id": "claim-002", "title": "规则", "original_text": "待核对规则", "source_refs": ["block-002"], "knowledge_point_ids": ["kp-002"], "related_review_item_ids": ["item-001"], "decision": "unresolved", "reason": "缺少教材", "recommended_text": None, "evidence_ids": [], "scope": "Fixture", "constraints": []}
            ],
            "diagram_reviews": [{"diagram_id": "svg-001", "decision": "revise", "claim_ids": ["claim-001"], "requirements": ["更新替代文本"]}],
            "topic_plans": [
                {"topic_id": "topic-001", "scope": "Fixture", "claim_ids": ["claim-001"], "diagram_ids": ["svg-001"], "constraints": []},
                {"topic_id": "topic-002", "scope": "Fixture", "claim_ids": ["claim-002"], "diagram_ids": [], "constraints": []}
            ]
        }
        review_path = self.extraction / "reviews/review-001/review.json"
        BUILD.dump(review_path, review)
        REVIEW.finalize(self.root, self.extraction, review_path)
        self.material_path = review_path.parent / "reviewed-knowledge.json"
        self.material = BUILD.load(self.material_path)
        workflow = self.root / "workflows/toutiao.yaml"
        workflow.parent.mkdir()
        shutil.copyfile(ROOT / "workflows/toutiao.yaml", workflow)
        self.recipe = {
            "schema_version": "1.0", "build_id": "toutiao-test", "version": "v001", "topic_id": "topic-001", "titles": ["测试正文"], "selected_title": 0,
            "summary": "摘要", "tags": ["测试"], "audience": "读者",
            "cover": {"lines": ["测试", "封面"], "subtitle": "测试", "source_diagram_ids": ["svg-001"], "claim_ids": ["claim-001"], "alt": "已修订图示"},
            "sections": [{"heading": "事实", "paragraphs": [{"text": "已核对事实。", "claim_ids": ["claim-001"]}], "figure_id": "figure-01"}],
            "figures": [{"id": "figure-01", "kind": "single", "title": "图示", "source_diagram_ids": ["svg-001"], "labels": [{"title": "已修订", "subtitle": "测试"}], "caption": "图注", "alt": "已修订图示", "claim_ids": ["claim-001"]}],
            "change_resolutions": [{"diagram_id": "svg-001", "instruction": "更新替代文本", "resolution": "重写根级替代文本", "figure_ids": ["figure-01"]}],
            "editorial_review": {"type": "agent", "name": "Fixture", "notes": ["已核对事实引用。"]}
        }
        self.recipe_path = self.root / "recipe.json"

    def run_build(self, recipe=None):
        BUILD.dump(self.recipe_path, recipe or self.recipe)
        return BUILD.build(self.root, self.material_path, self.recipe_path)

    def test_blocked_topic_cannot_be_built(self):
        self.recipe["topic_id"] = "topic-002"
        with self.assertRaisesRegex(ValueError, "blocked by scientific review"):
            self.run_build()
        self.assertFalse((self.root / "storage/builds").exists())

    def test_forged_ready_status_is_rejected(self):
        material = deepcopy(self.material)
        material["topics"][1]["readiness"] = "ready_for_build"
        BUILD.dump(self.material_path, material)
        with self.assertRaisesRegex(ValueError, "differs from its verified review"):
            self.run_build()

    def test_unreviewed_claim_is_rejected(self):
        self.recipe["sections"][0]["paragraphs"][0]["claim_ids"] = ["claim-002"]
        with self.assertRaisesRegex(ValueError, "outside reviewed scope"):
            self.run_build()

    def test_unresolved_diagram_changes_cannot_be_omitted(self):
        self.recipe["change_resolutions"] = []
        with self.assertRaisesRegex(ValueError, "required diagram-change"):
            self.run_build()

    def test_workflow_cannot_disable_approval(self):
        path = self.root / "workflows/toutiao.yaml"
        workflow = BUILD.load(path)
        workflow["steps"][4]["required"] = False
        BUILD.dump(path, workflow)
        with self.assertRaisesRegex(ValueError, "mandatory approval"):
            self.run_build()

    @unittest.skipUnless(shutil.which("rsvg-convert"), "PNG integration requires rsvg-convert")
    def test_output_is_versioned_and_waits_for_approval(self):
        manifest, path = self.run_build()
        self.assertEqual(manifest["status"], "awaiting_approval")
        self.assertTrue(manifest["requires_publication_approval"])
        self.assertEqual(BUILD.load(path / "workflow-run.json")["steps"][-2]["status"], "waiting")
        self.assertTrue((path / "outputs/content-package.zip").is_file())
        self.assertNotIn("燃烧", (path / "outputs/assets/figure-01.svg").read_text())
        self.assertNotIn("var(", (path / "outputs/assets/figure-01.svg").read_text())
        first_subject = manifest["approval_subject_sha256"]
        repeated, repeated_path = self.run_build()
        self.assertEqual(manifest, repeated)
        self.assertEqual(path, repeated_path)
        updated = deepcopy(self.recipe)
        updated["version"] = "v002"
        updated["titles"] = ["修订标题"]
        second, second_path = self.run_build(updated)
        self.assertNotEqual(first_subject, second["approval_subject_sha256"])
        self.assertEqual(BUILD.load(path / "manifest.json")["title"], "测试正文")
        self.assertEqual(second_path.name, "v002")

    @unittest.skipUnless(shutil.which("rsvg-convert"), "PNG integration requires rsvg-convert")
    def test_changed_recipe_cannot_overwrite_same_version(self):
        self.run_build()
        self.recipe["titles"] = ["改过的标题"]
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.run_build()

    @unittest.skipUnless(shutil.which("rsvg-convert"), "PNG integration requires rsvg-convert")
    def test_modified_artifact_is_detected(self):
        _, path = self.run_build()
        (path / "outputs/article.md").write_text("修改过的成品", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact integrity"):
            self.run_build()

    @unittest.skipUnless(shutil.which("rsvg-convert"), "PNG integration requires rsvg-convert")
    def test_manifest_cannot_fake_publication_approval(self):
        _, path = self.run_build()
        manifest = BUILD.load(path / "manifest.json")
        manifest["status"] = "approved"
        BUILD.dump(path / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "cannot grant publication approval"):
            self.run_build()


if __name__ == "__main__":
    unittest.main()
