#!/usr/bin/env python3
"""Render a versioned, silent SVG animation draft from a reviewed storyboard."""

import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import build as base

ROOT, SKILL, NS = base.ROOT, base.SKILL, base.NS
VERSION = "0.2.0"


def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, timeout=60, **kwargs)


def verify_parent(root, reference):
    parent = base.inside(root / "storage/builds", root / reference["path"])
    manifest_path = parent / "manifest.json"
    base.require(base.sha(manifest_path) == reference["manifest_sha256"], "Storyboard manifest changed")
    manifest = base.load(manifest_path)
    base.require(manifest["platform"] == "douyin" and manifest["stage"] == "storyboard", "Expected Douyin storyboard")
    context = {key: manifest[key] for key in ("build_id", "build_version", "platform", "stage", "source_ref", "review_ref", "skill", "workflow_ref", "recipe_sha256", "visual_baseline")}
    base.require(base.fingerprint({**context, "artifacts": manifest["artifacts"]}) == manifest["review_subject_sha256"], "Storyboard fingerprint mismatch")
    for artifact in manifest["artifacts"]:
        base.require(base.sha(base.inside(parent, parent / artifact["path"])) == artifact["sha256"], "Storyboard artifact changed")
    material_path = root / manifest["review_ref"]["material_path"]
    base.require(base.sha(material_path) == manifest["review_ref"]["material_sha256"], "Reviewed material changed")
    material = base.verify_material(root, material_path)
    topic = next(t for t in material["topics"] if t["id"] == manifest["review_ref"]["topic_id"])
    base.validate(root, base.load(parent / "recipe.json"), topic)
    return parent, manifest, topic


def evaluate(track, time):
    points = track["keyframes"]
    if time <= points[0]["time"]:
        return points[0]["value"]
    for first, second in zip(points, points[1:]):
        if time <= second["time"]:
            p = (time - first["time"]) / (second["time"] - first["time"])
            if track.get("easing", "smooth") == "smooth":
                p = p * p * (3 - 2 * p)
            return [a + (b - a) * p for a, b in zip(first["value"], second["value"])]
    return points[-1]["value"]


def validate_tracks(svg, tracks, duration):
    targets = {n.get("id"): n for n in svg.iter() if n.get("id")}
    seen = set()
    dimensions = {"opacity": 1, "translate": 2, "scale": 3, "rotate": 3, "reveal": 1}
    for track in tracks:
        key, prop = track["target"], track["property"]
        base.require(key in targets and (key, prop) not in seen and prop in dimensions, "Invalid animation target or duplicate track")
        seen.add((key, prop))
        points = track["keyframes"]
        base.require(isinstance(points, list) and len(points) >= 2, "Animation needs two keyframes")
        previous = -1
        for point in points:
            time, values = point["time"], point["value"]
            base.require(type(time) in {int, float} and math.isfinite(time) and previous < time <= duration, "Invalid keyframe time")
            base.require(isinstance(values, list) and len(values) == dimensions[prop] and all(type(v) in {int, float} and math.isfinite(v) for v in values), "Invalid keyframe values")
            if prop in {"opacity", "reveal"}:
                base.require(0 <= values[0] <= 1, "Opacity or reveal outside range")
            if prop == "scale":
                base.require(values[0] > 0, "Scale must be positive")
            previous = time
        base.require(points[0]["time"] >= 0 and track.get("easing", "smooth") in {"smooth", "linear"}, "Invalid easing")


def frame_svg(scene, template, tracks, local_time, global_time):
    svg = deepcopy(template)
    targets = {n.get("id"): n for n in svg.iter() if n.get("id")}
    transforms = {}
    definitions = svg.find(f"{{{NS}}}defs")
    for index, track in enumerate(tracks):
        value = evaluate(track, local_time)
        key, prop = track["target"], track["property"]
        node = targets[key]
        if prop == "opacity":
            node.set("opacity", f"{value[0]:.5f}")
        elif prop == "reveal":
            clip = ET.SubElement(definitions, f"{{{NS}}}clipPath", {"id": f"motion-clip-{index}"})
            x, y, width, height = track["bounds"]
            ET.SubElement(clip, f"{{{NS}}}rect", {"x": str(x), "y": str(y), "width": str(width), "height": str(height * value[0])})
            node.set("clip-path", f"url(#motion-clip-{index})")
        else:
            transforms.setdefault(key, [])
            if prop == "translate":
                transforms[key].append(f"translate({value[0]:.4f} {value[1]:.4f})")
            elif prop == "rotate":
                transforms[key].append(f"rotate({value[0]:.4f} {value[1]:.4f} {value[2]:.4f})")
            else:
                scale, x, y = value
                transforms[key].append(f"translate({x} {y}) scale({scale:.5f}) translate({-x} {-y})")
    for key, values in transforms.items():
        node = targets[key]
        node.set("transform", " ".join(values) + " " + node.get("transform", ""))
    cue = next((c for c in scene["cues"] if c["start"] <= global_time < c["end"]), scene["cues"][-1])
    holder = targets["live-caption"]
    for line, content in enumerate(cue["text"].split("\n")):
        node = ET.SubElement(holder, f"{{{NS}}}text", {"x": "106", "y": str(1590 + 72 * line), "font-family": "PingFang SC,Heiti SC,sans-serif", "font-size": "54", "font-weight": "550", "fill": "#fff9ed"})
        node.text = content
    return ET.tostring(svg, encoding="utf-8")


def render_png(svg, width=1080):
    return command(["rsvg-convert", "--width", str(width)], input=svg).stdout


def video_frames(scenes, templates, animation, fps):
    for scene in scenes:
        start = round(scene["start"] * fps)
        stop = round(scene["end"] * fps)
        for frame in range(start, stop):
            time = frame / fps
            yield scene, templates[scene["id"]], animation[scene["id"]]["tracks"], time - scene["start"], time


def encode(path, scenes, templates, animation, fps, log):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin", "-y", "-f", "image2pipe", "-vcodec", "png", "-framerate", str(fps), "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-threads", "4", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)]
    jobs = iter(video_frames(scenes, templates, animation, fps))
    with log.open("wb") as errors, ThreadPoolExecutor(max_workers=4) as pool:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
        pending = deque()
        count = 0
        try:
            for _ in range(8):
                values = next(jobs, None)
                if values is not None:
                    pending.append(pool.submit(lambda args: render_png(frame_svg(*args)), values))
            while pending:
                process.stdin.write(pending.popleft().result())
                count += 1
                if count % (fps * 5) == 0:
                    print(f"Rendered {count // fps}/{scenes[-1]['end']:g} seconds", flush=True)
                values = next(jobs, None)
                if values is not None:
                    pending.append(pool.submit(lambda args: render_png(frame_svg(*args)), values))
            process.stdin.close()
            base.require(process.wait(timeout=60) == 0, "FFmpeg encode failed; see render.log")
        except BaseException:
            process.kill()
            process.wait()
            raise


def render_build(root, recipe_path):
    recipe = base.load(recipe_path)
    base.require(recipe["schema_version"] == "1.0" and recipe["mode"] == "silent_animation", "Expected silent animation recipe")
    base.require(recipe.get("delivery_target", "voiceover_pending") in {"voiceover_pending", "silent_video"}, "Unknown video delivery target")
    silent_delivery = recipe.get("delivery_target") == "silent_video"
    result_status = "awaiting_video_review" if silent_delivery else "awaiting_audio"
    timing_status = "planned_for_silent_reading" if silent_delivery else "estimated_pending_voice"
    parent, original, topic = verify_parent(root, recipe["storyboard_ref"])
    base.require(recipe["storyboard_review"]["decision"] == "proceed_with_production" and base.text(recipe["storyboard_review"]["user_instruction"]), "Production instruction missing")
    base.require(__import__('re').fullmatch(r"v[0-9]{3,}", recipe["version"]) and int(recipe["version"][1:]) > int(original["build_version"][1:]), "Use a new build version")
    storyboard = base.load(parent / "outputs/storyboard.json")
    animations = {a["scene_id"]: a for a in recipe["scenes"]}
    base.require(len(animations) == len(recipe["scenes"]) == len(storyboard["scenes"]) and set(animations) == {s["id"] for s in storyboard["scenes"]}, "Animation scene set mismatch")
    templates = {}
    for scene in storyboard["scenes"]:
        art = animations[scene["id"]]["artwork"]
        path = base.inside(root / "storage", root / art["path"])
        base.require(base.sha(path) == art["sha256"] and base.text(art["adaptation"]), "Animation source mismatch")
        base.verify_svg(path)
        svg = ET.parse(path).getroot()
        base.require(any(n.get("id") == "live-caption" for n in svg.iter()), "Caption layer missing")
        validate_tracks(svg, animations[scene["id"]]["tracks"], scene["end"] - scene["start"])
        templates[scene["id"]] = svg
    for tool in ("rsvg-convert", "ffmpeg", "ffprobe"):
        base.require(shutil.which(tool) is not None, tool + " required")
    workflow_path = root / "workflows/douyin.yaml"
    workflow = base.load(workflow_path)
    base.require([s["id"] for s in workflow["steps"]] == base.STEPS and workflow["steps"][9].get("required") is True and workflow["steps"][10].get("implemented") is False and workflow["steps"][10].get("requires") == "approve", "Unexpected approval workflow")
    hashes = {p.relative_to(SKILL).as_posix(): base.sha(p) for folder in ("assets", "references", "scripts") for p in sorted((SKILL / folder).rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
    context = {"build_id": original["build_id"], "build_version": recipe["version"], "platform": "douyin", "stage": "silent_animation", "source_ref": original["source_ref"], "review_ref": original["review_ref"], "storyboard_ref": recipe["storyboard_ref"], "skill": {"name": "douyin-build", "version": VERSION, "instructions_sha256": base.sha(SKILL / "SKILL.md"), "resource_hashes": hashes}, "workflow_ref": {"path": "workflows/douyin.yaml", "id": workflow["id"], "version": workflow["version"], "sha256": base.sha(workflow_path)}, "recipe_sha256": base.fingerprint(recipe)}
    destination = parent.parent / recipe["version"]
    if destination.exists():
        existing = base.load(destination / "manifest.json")
        base.require(all(existing[k] == v for k, v in context.items()), "Build version already exists; use a new version")
        base.require(base.fingerprint({**context, "artifacts": existing["artifacts"]}) == existing["review_subject_sha256"] and existing["publication_approval_eligible"] is False and existing["requires_publication_approval"] is True, "Animation draft state mismatch")
        for item in existing["artifacts"]:
            base.require(base.sha(base.inside(destination, destination / item["path"])) == item["sha256"], "Animation artifact changed")
        return destination
    temporary = Path(tempfile.mkdtemp(prefix=".animation-", dir=parent.parent))
    try:
        outputs, preview = temporary / "outputs", temporary / "preview"
        (outputs / "scenes").mkdir(parents=True)
        (outputs / "review-frames").mkdir()
        preview.mkdir()
        base.dump(temporary / "recipe.json", recipe)
        base.dump(temporary / "storyboard-review.json", {**recipe["storyboard_review"], "subject_sha256": original["review_subject_sha256"], "scope": "production_only", "publication_approved": False})
        for name in ("script.md", "narration.txt", "references.json", "subtitles-draft.srt", "cover-plan.json"):
            shutil.copyfile(parent / "outputs" / name, outputs / name)
        script = outputs / "script.md"
        stage_note = "阶段：无声视频。已生成连续动画MP4，字幕按无声观看和阅读节奏安排。" if silent_delivery else "阶段：无声动画审阅版。已生成连续动画MP4，尚无配音；时间与字幕仍为待配音校正的规划。"
        script.write_text(script.read_text().replace("阶段：脚本与分镜。无配音、无连续动画、无MP4；时间与字幕均为待配音校正的规划。", stage_note), encoding="utf-8")
        media = []
        for scene in storyboard["scenes"]:
            art = animations[scene["id"]]["artwork"]
            shutil.copyfile(root / art["path"], outputs / "scenes" / (scene["id"] + ".svg"))
            media.append({"scene_id": scene["id"], **art, "credit": scene["artwork"]["credit"], "rights_notes": scene["artwork"]["rights_notes"]})
        storyboard.update(stage="silent_animation", animation_status="rendered", audio_status="not_required" if silent_delivery else "blocked_environment", timing_status=timing_status)
        base.dump(outputs / "storyboard.json", storyboard)
        base.dump(outputs / "media.json", media)
        base.dump(outputs / "audio-status.json", recipe["audio_status"])
        fps = storyboard["format"]["fps"]
        encode(outputs / "animation-draft.mp4", storyboard["scenes"], templates, animations, fps, outputs / "render.log")
        probe = json.loads(command(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(outputs / "animation-draft.mp4")]).stdout)
        video = next(s for s in probe["streams"] if s["codec_type"] == "video")
        base.require(video["width"] == 1080 and video["height"] == 1920 and video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p" and int(video["nb_frames"]) == round(storyboard["duration"] * fps) and abs(float(probe["format"]["duration"]) - storyboard["duration"]) < .1, "Video format or duration mismatch")
        base.require(not any(s["codec_type"] == "audio" for s in probe["streams"]), "Silent draft has unexpected audio")
        base.dump(outputs / "video-info.json", probe)
        for scene in storyboard["scenes"]:
            for fraction in (.15, .65):
                local = (scene["end"] - scene["start"]) * fraction
                name = f'{scene["id"]}-{int(fraction * 100):02}.png'
                command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(scene["start"] + local), "-i", str(outputs / "animation-draft.mp4"), "-frames:v", "1", "-vf", "scale=375:-1", str(outputs / "review-frames" / name)])
        cover = base.inside(root / "storage", root / recipe["cover"]["path"])
        base.require(base.sha(cover) == recipe["cover"]["sha256"], "Cover changed")
        base.verify_svg(cover)
        shutil.copyfile(cover, outputs / "cover.svg")
        (outputs / "cover.png").write_bytes(render_png(cover.read_bytes()))
        base.dump(outputs / "publication-draft.json", recipe["publication_draft"])
        limitations = ["本项目交付无声视频，字幕按阅读节奏安排。", "本运行未进行浏览器交互检查，画面审阅另行记录。"] if silent_delivery else ["配音尚未生成；字幕按规划时间切换，待音频重新对齐。", "本运行未进行浏览器交互检查或完整人工试听。"]
        base.dump(outputs / "review-notes.json", {"type": "agent", "checks": ["source_review_hashes", "animation_sources", "h264_format", "frame_count", "duration", "actual_encoded_frames_exported"], "limitations": limitations, "requires_user_review": True})
        data = {"title": storyboard["title"], "duration": storyboard["duration"], "version": recipe["version"], "scenes": storyboard["scenes"]}
        html = (SKILL / "assets/video-preview.html").read_text().replace("@@TITLE@@", escape(storyboard["title"])).replace("@@STYLE@@", (SKILL / "assets/preview.css").read_text()).replace("@@DATA@@", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))
        if silent_delivery:
            html = html.replace("动画审阅版 · 等待配音", "无声视频 · 待审阅").replace("地理故事 / 视频工作台", "地理故事工坊 / 视频工作台")
            html = html.replace("60秒 · 1080×1920 · 30fps", f'{storyboard["duration"]:g}秒 · {storyboard["format"]["width"]}×{storyboard["format"]["height"]} · {fps}fps')
            html = html.replace("当前视频无声，字幕按分镜计划切换，配音后还会调整节奏。", "字幕按无声观看和阅读节奏切换。")
            html = html.replace("六镜头 · 可点击跳转", f'{len(storyboard["scenes"])}镜头 · 可点击跳转')
            html = html.replace("下一步：配音与节奏调整", "审阅画面与字幕").replace("本机语音合成未能输出有效音频。选定配音方式或提供音频后，再对齐字幕和镜头，进行成片审阅及发布Approve。", "本项目交付无声视频。请核对科学表述、画面和字幕阅读节奏；发布需另行确认。")
            html = html.replace("流星体、流星和陨石科普动画，无声审阅版", escape(storyboard["title"] + "，无声视频")).replace("看见流星，就有陨石吗？封面草稿", escape(storyboard["title"] + "封面"))
            html = html.replace("暂定字幕", "字幕文件").replace("旁白与镜头", "字幕与镜头").replace("旁白文本", "讲解文本")
        (preview / "index.html").write_text(html, encoding="utf-8")
        statuses = ["completed"] * 5 + (["not_required", "completed", "completed", "waiting_for_review", "not_started", "not_started"] if silent_delivery else ["blocked_environment", "completed", "completed", "waiting_for_audio", "not_started", "not_started"])
        base.dump(temporary / "workflow-run.json", {"schema_version": "1.0", "run_id": original["build_id"] + "-" + recipe["version"], "platform": "douyin", "workflow_ref": context["workflow_ref"], "build_id": original["build_id"], "build_version": recipe["version"], "status": result_status if silent_delivery else "waiting_for_audio", "steps": [{"id": k, "status": s} for k, s in zip(base.STEPS, statuses)]})
        artifacts = [{"path": p.relative_to(temporary).as_posix(), "sha256": base.sha(p), "size_bytes": p.stat().st_size} for p in sorted(temporary.rglob("*")) if p.is_file()]
        base.dump(temporary / "manifest.json", {"schema_version": "1.0", **context, "title": storyboard["title"], "status": result_status, "publication_approval_eligible": False, "requires_publication_approval": True, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "parameters": {**storyboard["format"], "duration_seconds": storyboard["duration"], "scene_count": len(storyboard["scenes"]), "timing_status": timing_status}, "artifacts": artifacts, "review_subject_sha256": base.fingerprint({**context, "artifacts": artifacts})})
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = render_build(ROOT, ROOT / args.recipe)
    except (OSError, KeyError, ValueError, TypeError, StopIteration, ET.ParseError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Animation render failed: {error}\n")
    print(json.dumps({"build": str(result), "status": base.load(result / "manifest.json")["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
