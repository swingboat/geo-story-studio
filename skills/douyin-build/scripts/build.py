#!/usr/bin/env python3
"""Build a versioned Douyin script and silent keyframe storyboard for review."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
from html import escape
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[3]
SKILL = Path(__file__).resolve().parents[1]
VERSION = "0.2.0"
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
STEPS = ["verify_review", "write_script", "design_storyboard", "preview_storyboard", "review_storyboard", "produce_audio", "animate", "render_video", "review_video", "approve", "publish"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inside(root, path):
    result = path.resolve()
    result.relative_to(root.resolve())
    return result


def text(value):
    return isinstance(value, str) and bool(value.strip())


def ids(values, allowed, label, empty=False):
    require(isinstance(values, list) and all(text(v) for v in values), label + ": expected IDs")
    require(len(values) == len(set(values)) and (empty or bool(values)) and set(values) <= set(allowed), label + ": invalid references")


def verify_material(root, path):
    path = inside(root, path)
    require(path.name == "reviewed-knowledge.json", "Expected reviewed-knowledge.json")
    extraction = path.parents[2]
    review_path = path.parent / "review.json"
    review, material = load(review_path), load(path)
    require(review_path == extraction / "reviews" / review["review_id"] / "review.json", "Review path mismatch")
    spec = importlib.util.spec_from_file_location("science_review_for_douyin", ROOT / "skills/review-science/scripts/finalize.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.compile_review(root, extraction, review, sha(review_path)) == material, "Reviewed material differs from its verified review")
    return material


def verify_svg(path):
    svg = ET.parse(path).getroot()
    require(svg.tag == f"{{{NS}}}svg" and svg.get("viewBox") == "0 0 1080 1920", "Storyboard SVG must use 1080×1920 viewBox")
    for node in svg.iter():
        require(node.tag.rsplit("}", 1)[-1] not in {"script", "foreignObject", "style", "image", "use"}, "Storyboard artwork must be self-contained vector SVG")
        for name, value in node.attrib.items():
            require(not name.lower().startswith("on"), "SVG event handler unsupported")
            require(name.rsplit("}", 1)[-1] != "href", "External SVG reference unsupported")
            require("url(" not in value or bool(re.fullmatch(r"url\(#[A-Za-z0-9_-]+\)", value)), "SVG external resource unsupported")


def validate(root, recipe, topic):
    require(recipe.get("schema_version") == "1.0", "Unsupported recipe schema")
    require(bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", recipe["build_id"])), "Invalid build ID")
    require(bool(re.fullmatch(r"v[0-9]{3,}", recipe["version"])), "Invalid build version")
    require(topic["readiness"] == "ready_for_build", "Topic is blocked by scientific review")
    require(text(recipe["title"]) and text(recipe["audience"]), "Title or audience missing")
    require(recipe["format"]["width"] == 1080 and recipe["format"]["height"] == 1920 and type(recipe["format"]["fps"]) is int and 1 <= recipe["format"]["fps"] <= 60, "Invalid planned video format")
    baseline = recipe["visual_baseline"]
    require(sha(inside(root, root / baseline["path"])) == baseline["sha256"], "Visual baseline hash mismatch")
    scenes, previous, seen, claims = recipe["scenes"], 0, set(), set()
    require(isinstance(scenes, list) and bool(scenes), "Storyboard scenes missing")
    for scene in scenes:
        key = scene["id"]
        require(bool(re.fullmatch(r"shot-[0-9]{2}", key)) and key not in seen, "Invalid or duplicate shot ID")
        seen.add(key)
        start, end = scene["start"], scene["end"]
        require(all(type(v) in {int, float} and math.isfinite(v) for v in [start, end]) and abs(start - previous) < 0.000001 and end > start, "Scene times must be finite, continuous and start at zero")
        previous = end
        for field in ["heading", "narration", "visual", "motion"]:
            require(text(scene[field]), "Missing scene " + field)
        require(isinstance(scene["subtitles"], list) and bool(scene["subtitles"]) and all(text(v) for v in scene["subtitles"]), "Missing draft subtitles")
        require("".join(scene["subtitles"]).replace("\n", "") == scene["narration"].replace("\n", ""), "Subtitle text must preserve full narration")
        require(isinstance(scene["on_screen_text"], list) and bool(scene["on_screen_text"]) and all(text(v) for v in scene["on_screen_text"]), "Missing on-screen text")
        ids(scene["claim_ids"], [c["id"] for c in topic["statements"]], "Scene claims")
        ids(scene["source_diagram_ids"], topic["diagram_ids"], "Scene diagrams")
        claims.update(scene["claim_ids"])
        art = scene["artwork"]
        require(all(text(art.get(f)) for f in ["path", "sha256", "alt", "credit", "rights_notes", "adaptation"]), "Artwork provenance missing")
        path = inside(root / "storage", root / art["path"])
        require(path.suffix == ".svg" and sha(path) == art["sha256"], "Artwork input integrity failure")
        verify_svg(path)
    mapping = {s["id"]: s for s in scenes}
    require(recipe["cover_plan"]["source_scene_id"] in mapping and all(text(recipe["cover_plan"].get(f)) for f in ["headline", "visual"]), "Invalid cover plan")
    expected = {(r["diagram_id"], instruction) for r in topic["required_changes"] for instruction in r["instructions"]}
    resolutions = recipe["change_resolutions"]
    require(len(resolutions) == len(expected) and {(r["diagram_id"], r["instruction"]) for r in resolutions} == expected, "Missing or duplicate review-change resolution")
    for resolution in resolutions:
        require(text(resolution["resolution"]), "Review-change explanation missing")
        ids(resolution["scene_ids"], mapping, "Review-change scenes")
        require(all(resolution["diagram_id"] in mapping[key]["source_diagram_ids"] for key in resolution["scene_ids"]), "Review change points to unrelated scene")
    editor = recipe["editorial_review"]
    require(editor["type"] in {"agent", "human"} and text(editor["name"]) and isinstance(editor["notes"], list) and bool(editor["notes"]) and all(text(v) for v in editor["notes"]), "Editorial review provenance missing")
    return claims


def timestamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def draft_cues(scene):
    weights = [len(v.replace("\n", "")) for v in scene["subtitles"]]
    total, elapsed, cues = sum(weights), 0, []
    for content, weight in zip(scene["subtitles"], weights):
        start = scene["start"] + (scene["end"] - scene["start"]) * elapsed / total
        elapsed += weight
        end = scene["start"] + (scene["end"] - scene["start"]) * elapsed / total
        cues.append({"start": round(start, 3), "end": round(end, 3), "text": content})
    return cues


def render(source, output, width, renderer):
    subprocess.run([renderer, "--width", str(width), "--output", str(output), str(source)], check=True, capture_output=True, timeout=30)
    require(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "SVG renderer did not produce PNG")


def sheet(scenes, outputs, renderer):
    columns = min(3, len(scenes)); rows = math.ceil(len(scenes) / columns)
    width, height = columns * 480 + 48, rows * 930 + 160
    svg = ET.Element(f"{{{NS}}}svg", {"viewBox": f"0 0 {width} {height}"})
    ET.SubElement(svg, f"{{{NS}}}rect", {"width": str(width), "height": str(height), "fill": "#f1f4f7"})
    def label(x, y, value, size, fill="#172d4a"):
        e = ET.SubElement(svg, f"{{{NS}}}text", {"x": str(x), "y": str(y), "font-family": "PingFang SC,Heiti SC,sans-serif", "font-size": str(size), "fill": fill}); e.text = value
    label(32, 55, "竖屏关键帧分镜", 36)
    label(32, 94, f'规划时长{scenes[-1]["end"]:g}秒 · 无声预演 · 科普示意', 23, "#52667a")
    for index, scene in enumerate(scenes):
        x, y = 32 + index % columns * 480, 135 + index // columns * 930
        data = base64.b64encode((outputs / scene["frame_path"]).read_bytes()).decode()
        ET.SubElement(svg, f"{{{NS}}}image", {"x": str(x), "y": str(y), "width": "432", "height": "768", "href": "data:image/png;base64," + data})
        label(x, y + 808, f'{scene["id"]} · {scene["start"]:g}—{scene["end"]:g}秒', 26)
        label(x, y + 848, scene["heading"], 27)
    path = outputs / "storyboard-contact-sheet.svg"
    ET.ElementTree(svg).write(path, encoding="utf-8", xml_declaration=True)
    render(path, path.with_suffix(".png"), 1440, renderer)


def build(root, material_path, recipe_path):
    root = root.resolve(); recipe = load(recipe_path)
    material = verify_material(root, material_path)
    topic = next((t for t in material["topics"] if t["id"] == recipe["topic_id"]), None)
    require(topic is not None, "Unknown topic")
    used_claims = validate(root, recipe, topic)
    workflow_path = root / "workflows/douyin.yaml"; workflow = load(workflow_path)
    require(workflow["platform"] == "douyin" and [s["id"] for s in workflow["steps"]] == STEPS, "Unexpected Douyin workflow")
    require(workflow["steps"][9].get("required") is True and workflow["steps"][9]["kind"] == "human_approval", "Final publication approval is mandatory")
    require(workflow["steps"][10].get("requires") == "approve" and workflow["steps"][10].get("implemented") is False, "Publishing is outside storyboard stage")
    provenance = {"name": "douyin-build", "version": VERSION, "instructions_sha256": sha(SKILL / "SKILL.md"), "script_sha256": sha(Path(__file__).resolve()), "asset_hashes": {p.relative_to(SKILL / "assets").as_posix(): sha(p) for p in sorted((SKILL / "assets").rglob("*")) if p.is_file()}, "reference_hashes": {p.relative_to(SKILL / "references").as_posix(): sha(p) for p in sorted((SKILL / "references").rglob("*")) if p.is_file()}}
    context = {"build_id": recipe["build_id"], "build_version": recipe["version"], "platform": "douyin", "stage": "storyboard", "source_ref": material["source_ref"], "review_ref": {"review_id": material["review_id"], "topic_id": topic["id"], "material_path": inside(root, material_path).relative_to(root).as_posix(), "material_sha256": sha(material_path), "review_sha256": material["provenance"]["review_sha256"]}, "skill": provenance, "workflow_ref": {"path": "workflows/douyin.yaml", "id": workflow["id"], "version": workflow["version"], "sha256": sha(workflow_path)}, "recipe_sha256": fingerprint(recipe), "visual_baseline": recipe["visual_baseline"]}
    destination = root / "storage/builds" / recipe["build_id"] / recipe["version"]
    if destination.exists():
        existing = load(destination / "manifest.json")
        require(all(existing[k] == v for k, v in context.items()), "Build version already exists with different inputs; use a new version")
        require(existing["status"] == "awaiting_storyboard_review" and existing["publication_approval_eligible"] is False and existing["requires_publication_approval"] is True, "Storyboard cannot grant publication approval")
        require(fingerprint({**context, "artifacts": existing["artifacts"]}) == existing["review_subject_sha256"], "Storyboard review fingerprint mismatch")
        for a in existing["artifacts"]:
            require(sha(inside(destination, destination / a["path"])) == a["sha256"], "Existing artifact integrity failure")
        return existing, destination
    renderer = shutil.which("rsvg-convert"); require(renderer is not None, "rsvg-convert required")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".storyboard-", dir=destination.parent))
    try:
        outputs, preview = temporary / "outputs", temporary / "preview"
        (outputs / "scenes").mkdir(parents=True); preview.mkdir()
        scenes, media, srt, number = [], [], [], 1
        lines = [f'# {recipe["title"]}', "", "阶段：脚本与分镜。无配音、无连续动画、无MP4；时间与字幕均为待配音校正的规划。", "", f'目标读者：{recipe["audience"]}', ""]
        for scene in recipe["scenes"]:
            svg = outputs / "scenes" / (scene["id"] + ".svg")
            shutil.copyfile(root / scene["artwork"]["path"], svg)
            render(svg, svg.with_suffix(".png"), 1080, renderer)
            render(svg, svg.with_name(scene["id"] + "-mobile.png"), 375, renderer)
            cues = draft_cues(scene)
            shot = {**scene, "frame_path": f'scenes/{scene["id"]}.png', "cues": cues, "timing_status": "estimated_pending_voice", "estimated_narration_cps": round(len(re.findall(r"[\u3400-\u9fff]", scene["narration"])) / (scene["end"] - scene["start"]), 2)}
            scenes.append(shot)
            media.append({"scene_id": scene["id"], **scene["artwork"], "input_path": scene["artwork"]["path"], "path": svg.relative_to(outputs).as_posix()})
            for cue in cues:
                srt.extend([str(number), f'{timestamp(cue["start"])} --> {timestamp(cue["end"])}', cue["text"], ""]); number += 1
            lines.extend([f'## {scene["id"]} · {scene["start"]:g}—{scene["end"]:g}秒 · {scene["heading"]}', "", "**旁白**：" + scene["narration"], "", "**画面**：" + scene["visual"], "", "**计划运动**：" + scene["motion"], "", "**画内文字**：" + "／".join(scene["on_screen_text"]), "", "**审校结论**：" + "、".join(scene["claim_ids"]), ""])
        statements = {s["id"]: s for s in topic["statements"]}
        used_evidence = {e for c in used_claims for e in statements[c]["evidence_ids"]}
        references = [r for r in material["references"] if r["id"] in used_evidence]
        lines.extend(["## 科学来源", ""] + [f'- [{r["title"]}]({r["url"]}) · {r["publisher"]}' for r in references])
        storyboard = {"title": recipe["title"], "stage": "storyboard", "format": recipe["format"], "duration": scenes[-1]["end"], "audio_status": "not_produced", "animation_status": "planned_only", "timing_status": "estimated_pending_voice", "scenes": scenes}
        dump(outputs / "storyboard.json", storyboard); dump(outputs / "cover-plan.json", recipe["cover_plan"])
        dump(outputs / "media.json", media); dump(outputs / "references.json", references)
        (outputs / "script.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (outputs / "narration.txt").write_text("\n\n".join(s["narration"] for s in scenes) + "\n", encoding="utf-8")
        (outputs / "subtitles-draft.srt").write_text("\n".join(srt), encoding="utf-8")
        sheet(scenes, outputs, renderer)
        data = {**storyboard, "audience": recipe["audience"], "version": recipe["version"], "references": references}
        template = (SKILL / "assets/preview.html").read_text(encoding="utf-8")
        html = template.replace("@@TITLE@@", escape(recipe["title"])).replace("@@STYLE@@", (SKILL / "assets/preview.css").read_text()).replace("@@DATA@@", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")).replace("@@SCRIPT@@", (SKILL / "assets/preview.js").read_text())
        (preview / "index.html").write_text(html, encoding="utf-8")
        dump(temporary / "recipe.json", recipe)
        statuses = ["completed"] * 4 + ["waiting"] + ["not_started"] * 6
        dump(temporary / "workflow-run.json", {"schema_version": "1.0", "run_id": recipe["build_id"] + "-" + recipe["version"], "platform": "douyin", "workflow_ref": context["workflow_ref"], "build_id": recipe["build_id"], "build_version": recipe["version"], "status": "waiting_for_storyboard_review", "steps": [{"id": k, "status": s} for k, s in zip(STEPS, statuses)]})
        with ZipFile(outputs / "storyboard-package.zip", "w") as archive:
            for path in sorted(outputs.rglob("*")):
                if path.is_file() and path.name != "storyboard-package.zip":
                    info = ZipInfo(path.relative_to(outputs).as_posix(), date_time=(1980, 1, 1, 0, 0, 0)); info.compress_type = ZIP_DEFLATED
                    archive.writestr(info, path.read_bytes())
        artifacts = [{"path": p.relative_to(temporary).as_posix(), "sha256": sha(p), "size_bytes": p.stat().st_size} for p in sorted(temporary.rglob("*")) if p.is_file()]
        manifest = {"schema_version": "1.0", **context, "title": recipe["title"], "status": "awaiting_storyboard_review", "requires_publication_approval": True, "publication_approval_eligible": False, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "parameters": {**recipe["format"], "duration_seconds": storyboard["duration"], "scene_count": len(scenes), "timing_status": "estimated_pending_voice"}, "artifacts": artifacts, "review_subject_sha256": fingerprint({**context, "artifacts": artifacts})}
        dump(temporary / "manifest.json", manifest); temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest, destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--material", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    args = parser.parse_args()
    try:
        m, path = build(args.root, args.root / args.material, args.root / args.recipe)
    except (OSError, KeyError, TypeError, ValueError, ET.ParseError, subprocess.SubprocessError) as e:
        parser.exit(1, f"Storyboard build failed: {e}\n")
    print(json.dumps({"build": str(path), "status": m["status"], "duration_seconds": m["parameters"]["duration_seconds"], "scene_count": m["parameters"]["scene_count"], "review_subject_sha256": m["review_subject_sha256"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
