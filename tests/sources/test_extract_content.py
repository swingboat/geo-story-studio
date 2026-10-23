"""Observable source-version and extraction behavior; standard-library tests."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("extract_content", ROOT / "skills/extract-content/scripts/extract.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

HTML = '''<meta charset="utf-8"><title>图鉴</title>
<style>:root{--ink:#132B57}.k{stroke:var(--ink)}</style>
<main><header><h1>天体</h1><p>保留 <b>原文</b>。</p></header>
<section><h2>判断</h2>
<svg viewBox="0 0 100 100"><circle class="k" cx="50" cy="50" r="20"/><text>图 &amp; 字</text></svg>
<button aria-expanded="false">月球<span>是天体</span></button>
</section></main>'''


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "input.html"
        self.source.write_text(HTML, encoding="utf-8")

    def run_extract(self, **options):
        arguments = {"root": self.root, "source": self.source, "source_id": "src-test", "book": "必修第一册", "extraction_id": "extract-001"}
        arguments.update(options)
        return MODULE.register_and_extract(**arguments)

    def test_repeat_import_reuses_version_and_preserves_knowledge(self):
        manifest, output, content = self.run_extract()
        (output / "knowledge.json").write_text('{"human_note": "keep"}', encoding="utf-8")
        registry_before = (self.root / "storage/state/source-registry.json").read_bytes()
        second_manifest, second_output, second_content = self.run_extract()
        self.assertEqual((manifest, output, content), (second_manifest, second_output, second_content))
        self.assertEqual(registry_before, (self.root / "storage/state/source-registry.json").read_bytes())
        self.assertEqual(json.loads((output / "knowledge.json").read_text()), {"human_note": "keep"})
        self.assertEqual(self.source.read_text(), HTML)

    def test_changed_input_creates_new_version_without_changing_old_snapshot(self):
        first_manifest, _, _ = self.run_extract()
        first = json.loads(first_manifest.read_text())
        old_snapshot = self.root / first["snapshot_path"]
        self.source.write_text(HTML.replace("保留", "更新"), encoding="utf-8")
        next_manifest, _, _ = self.run_extract()
        second = json.loads(next_manifest.read_text())
        self.assertEqual(first["source_version"], "v001")
        self.assertEqual(second["source_version"], "v002")
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(old_snapshot.read_text(), HTML)

    def test_svg_has_styles_and_namespace_and_original_is_preserved(self):
        _, output, content = self.run_extract()
        self.assertEqual(len(content["diagrams"]), 1)
        diagram = content["diagrams"][0]
        svg = ET.parse(output / diagram["path"]).getroot()
        self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(svg.attrib["viewBox"], "0 0 100 100")
        style = svg.find("{http://www.w3.org/2000/svg}style")
        self.assertIn("--ink:#132B57", style.text)
        self.assertIn('<circle class="k"', (output / diagram["raw_path"]).read_text())
        self.assertEqual(content["interactions"][0]["text"], "月球是天体")
        self.assertIn("保留 原文。", [block["text"] for block in content["text_blocks"]])

    def test_local_dependencies_are_marked_incomplete(self):
        self.source.write_text(HTML + '<img src="assets/example.png"><style>@import "theme.css";</style>', encoding="utf-8")
        manifest, _, content = self.run_extract()
        self.assertFalse(json.loads(manifest.read_text())["snapshot_complete"])
        self.assertEqual({item["url"] for item in content["dependencies"]}, {"assets/example.png", "theme.css"})
        self.assertTrue(all(item["availability"] == "not_copied" for item in content["dependencies"]))

    def test_modified_snapshot_is_detected_on_repeat(self):
        manifest, _, _ = self.run_extract()
        snapshot = self.root / json.loads(manifest.read_text())["snapshot_path"]
        snapshot.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity check"):
            self.run_extract()

    def test_ids_cannot_escape_storage_directory(self):
        with self.assertRaises(ValueError):
            self.run_extract(source_id="../outside")
        with self.assertRaises(ValueError):
            self.run_extract(extraction_id="../outside")
        self.assertFalse((self.root / "storage").exists())

    def test_source_id_cannot_be_reassigned_to_another_input(self):
        self.run_extract()
        other = self.root / "other.html"
        other.write_text(HTML, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "another input path"):
            self.run_extract(source=other)


if __name__ == "__main__":
    unittest.main()
