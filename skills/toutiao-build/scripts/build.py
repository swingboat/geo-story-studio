#!/usr/bin/env python3
"""Create a versioned Toutiao article package that waits for publication approval."""

import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from html import escape
import importlib.util
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


TOOL_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = Path(__file__).resolve().parents[1]
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
SKILL_VERSION = "0.3.0"
WORKFLOW_STEPS = ["verify_review", "compose", "export_assets", "preview", "approve", "publish"]


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
    path = path.resolve()
    path.relative_to(root.resolve())
    return path


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_ids(values, available, label, allow_empty=False):
    require(isinstance(values, list) and all(nonempty(value) for value in values), f"{label}: expected IDs")
    require(len(values) == len(set(values)), f"{label}: duplicate IDs")
    require(allow_empty or bool(values), f"{label}: empty references")
    require(set(values) <= set(available), f"{label}: references outside reviewed scope")


def verify_material(root, material_path):
    material_path = inside(root, material_path)
    extraction = material_path.parents[2]
    require(material_path.name == "reviewed-knowledge.json", "Expected reviewed-knowledge.json")
    review_path = material_path.parent / "review.json"
    review, material = load(review_path), load(material_path)
    require(review_path == extraction / "reviews" / review["review_id"] / "review.json", "Review path mismatch")
    module_path = TOOL_ROOT / "skills/review-science/scripts/finalize.py"
    spec = importlib.util.spec_from_file_location("science_review_for_build", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rebuilt = module.compile_review(root, extraction, review, sha(review_path))
    require(rebuilt == material, "Reviewed material differs from its verified review")
    return extraction, material


def validate_recipe(recipe, topic):
    require(recipe.get("schema_version") == "1.0", "Unsupported recipe schema")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", recipe["build_id"]), "Invalid build ID")
    require(re.fullmatch(r"v[0-9]{3,}", recipe["version"]), "Invalid build version")
    require(topic["readiness"] == "ready_for_build", "Topic is blocked by scientific review")
    require(recipe["topic_id"] == topic["id"], "Topic ID mismatch")
    claims = {item["id"] for item in topic["statements"]}
    require(bool(claims), "No reviewed statements available")
    require(isinstance(recipe["titles"], list) and bool(recipe["titles"]) and all(nonempty(value) for value in recipe["titles"]), "Missing titles")
    require(type(recipe["selected_title"]) is int and 0 <= recipe["selected_title"] < len(recipe["titles"]), "Invalid selected title")
    require(all(nonempty(recipe.get(key)) for key in ["summary", "audience"]), "Recipe summary or audience missing")
    require(isinstance(recipe["tags"], list) and all(nonempty(tag) for tag in recipe["tags"]), "Invalid tags")
    cover = recipe["cover"]
    require(isinstance(cover["lines"], list) and len(cover["lines"]) == 2 and all(nonempty(line) for line in cover["lines"]), "Cover requires two title lines")
    require(nonempty(cover["subtitle"]) and nonempty(cover["alt"]), "Cover description missing")
    validate_ids(cover["source_diagram_ids"], topic["diagram_ids"], "Cover diagram")
    require(len(cover["source_diagram_ids"]) <= 3, "Cover supports at most three source diagrams")
    validate_ids(cover["claim_ids"], claims, "Cover claim")
    figures = {}
    for figure in recipe["figures"]:
        require(re.fullmatch(r"figure-[0-9]{2}", figure["id"]), "Invalid figure ID")
        require(figure["id"] not in figures, "Duplicate figure ID")
        figures[figure["id"]] = figure
        require(figure["kind"] in {"single", "comparison", "asset"}, "Unknown figure layout")
        require(all(nonempty(figure.get(key)) for key in ["title", "caption", "alt"]), "Missing figure text")
        validate_ids(figure["source_diagram_ids"], topic["diagram_ids"], "Figure diagram", allow_empty=figure["kind"] == "asset")
        validate_ids(figure["claim_ids"], claims, "Figure claim")
        if figure["kind"] != "asset":
            expected = 1 if figure["kind"] == "single" else 3
            require(len(figure["source_diagram_ids"]) == len(figure["labels"]) == expected, "Figure layout input mismatch")
        else:
            require(nonempty(figure.get("asset_id")) and not figure["labels"], "Asset figure requires asset_id and empty labels")
            require(nonempty(figure.get("purpose")), "Asset figure needs an explanation purpose")
        require(all(nonempty(label.get("title")) and nonempty(label.get("subtitle")) for label in figure["labels"]), "Figure labels missing")
    require(bool(figures), "Article requires figures")
    used_figures, used_claims = [], set(cover["claim_ids"])
    require(isinstance(recipe["sections"], list) and bool(recipe["sections"]), "Article sections missing")
    for section in recipe["sections"]:
        require(nonempty(section["heading"]) and bool(section["paragraphs"]), "Section missing content")
        for paragraph in section["paragraphs"]:
            require(nonempty(paragraph["text"]), "Empty paragraph")
            validate_ids(paragraph["claim_ids"], claims, "Paragraph claim")
            used_claims.update(paragraph["claim_ids"])
        if section["figure_id"] is not None:
            require(section["figure_id"] in figures, "Section references unknown figure")
            used_figures.append(section["figure_id"])
    require(len(used_figures) == len(set(used_figures)) and set(used_figures) == set(figures), "Figures must each appear once in article")
    for figure in figures.values():
        used_claims.update(figure["claim_ids"])
    for instruction in topic["required_changes"]:
        for text in instruction["instructions"]:
            matches = [item for item in recipe["change_resolutions"] if item["diagram_id"] == instruction["diagram_id"] and item["instruction"] == text]
            require(len(matches) == 1, "Missing or duplicate required diagram-change resolution")
            resolution = matches[0]
            require(nonempty(resolution["resolution"]), "Diagram resolution missing")
            validate_ids(resolution["figure_ids"], figures, "Change-resolution figure")
            require(all(instruction["diagram_id"] in figures[key]["source_diagram_ids"] for key in resolution["figure_ids"]), "Change resolution points to unrelated figure")
    permitted_changes = {(item["diagram_id"], text) for item in topic["required_changes"] for text in item["instructions"]}
    require({(item["diagram_id"], item["instruction"]) for item in recipe["change_resolutions"]} == permitted_changes, "Unexpected change resolution")
    editor = recipe["editorial_review"]
    require(editor["type"] in {"agent", "human"} and nonempty(editor["name"]), "Editor provenance missing")
    require(isinstance(editor["notes"], list) and bool(editor["notes"]) and all(nonempty(note) for note in editor["notes"]), "Editorial notes missing")
    return figures, used_claims


def verify_media(root, recipe):
    """Bind local images and their editorial provenance to the recipe fingerprint."""
    media = {}
    for item in recipe.get("media", []):
        key = item["id"]
        require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", key) and key not in media, "Invalid or duplicate media ID")
        require(item["kind"] in {"photograph", "illustration", "composition"}, "Invalid media kind")
        for field in ["path", "sha256", "credit", "rights_notes", "adaptation", "verified_at"]:
            require(nonempty(item.get(field)), f"Media {key}: missing {field}")
        path = inside(root / "storage", root / item["path"])
        require(path.suffix.lower() in {".svg", ".jpg", ".jpeg", ".png"}, "Unsupported local media format")
        require(sha(path) == item["sha256"], f"Media {key}: input hash mismatch")
        if item["kind"] == "photograph":
            require(all(nonempty(item.get(f)) and item[f].startswith("https://") for f in ["source_url", "rights_url"]), "Photograph requires source and usage-policy URLs")
        if path.suffix.lower() == ".svg":
            svg = ET.parse(path).getroot()
            require(svg.tag == f"{{{NS}}}svg" and bool(svg.get("viewBox")), "Invalid artwork SVG")
            for node in svg.iter():
                require(node.tag.rsplit("}", 1)[-1] not in {"script", "foreignObject", "style"}, "Artwork SVG must use presentation attributes without executable or external content")
                for name, value in node.attrib.items():
                    require(not name.lower().startswith("on"), "SVG event handlers are not supported")
                    if name.rsplit("}", 1)[-1] == "href":
                        require(value.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "#")), "SVG references must be embedded images or local fragment IDs")
                    require("url(" not in value or re.fullmatch(r"url\(#[A-Za-z0-9_-]+\)", value), "SVG external resource reference")
        media[key] = {**item, "local_path": path}
    for item in media.values():
        parents = item.get("derived_from", [])
        require(isinstance(parents, list) and set(parents) <= set(media) and item["id"] not in parents, "Unknown media dependency")
    cover = recipe["cover"]
    if "show_in_article" in cover:
        require(type(cover["show_in_article"]) is bool, "Invalid cover placement")
    if cover.get("asset_id"):
        require(cover["asset_id"] in media and media[cover["asset_id"]]["kind"] != "photograph", "Cover requires a composed local artwork")
        require(nonempty(cover.get("purpose")) and nonempty(cover.get("caption")), "Cover needs purpose and caption")
    for figure in recipe["figures"]:
        if figure["kind"] == "asset":
            require(figure["asset_id"] in media, "Unknown figure media")
            require(media[figure["asset_id"]]["kind"] == "photograph" or bool(figure["source_diagram_ids"]), "Illustrations require reviewed diagram references")
    return media


def svg_text(parent, x, y, value, cls, **attrs):
    node = ET.SubElement(parent, f"{{{NS}}}text", {"x": str(x), "y": str(y), "class": cls, **{key: str(value) for key, value in attrs.items()}})
    node.text = value
    return node


def canvas(width, height, alt, dark=False):
    root = ET.Element(f"{{{NS}}}svg", {"width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}", "role": "img", "aria-label": alt})
    ET.SubElement(root, f"{{{NS}}}title").text = alt
    ET.SubElement(root, f"{{{NS}}}style").text = (SKILL_DIR / "assets/figure.css").read_text(encoding="utf-8")
    ET.SubElement(root, f"{{{NS}}}rect", {"width": str(width), "height": str(height), "fill": "#132b4d" if dark else "#f3f6fb"})
    return root


def insert_diagram(parent, source, x, y, width, height):
    original = ET.parse(source).getroot()
    viewbox = original.attrib.get("viewBox", "").split()
    require(len(viewbox) == 4, "Source diagram must have a viewBox")
    vx, vy, vw, vh = map(float, viewbox)
    require(vw > 0 and vh > 0, "Invalid source viewBox")
    scale = min(width / vw, height / vh)
    tx, ty = x + (width - vw * scale) / 2 - vx * scale, y + (height - vh * scale) / 2 - vy * scale
    group = ET.SubElement(parent, f"{{{NS}}}g", {"transform": f"translate({tx:g},{ty:g}) scale({scale:g})"})
    for node in list(original):
        if node.tag.rsplit("}", 1)[-1] not in {"style", "title", "desc", "script"}:
            group.append(deepcopy(node))


def export_svg(svg, path, renderer):
    ET.ElementTree(svg).write(path, encoding="utf-8", xml_declaration=True)
    png = path.with_suffix(".png")
    subprocess.run([renderer, "--format", "png", "--width", "1440", "--keep-aspect-ratio", "--output", str(png), str(path)], check=True, capture_output=True, timeout=30)
    data = png.read_bytes()
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "Renderer did not produce a PNG")
    return struct.unpack(">II", data[16:24])


def media_svg(item, alt):
    path = item["local_path"]
    if path.suffix.lower() == ".svg":
        root = ET.parse(path).getroot()
        root.set("role", "img")
        root.set("aria-label", alt)
        return root
    width, height = item["width"], item["height"]
    require(type(width) is int and type(height) is int and width > 0 and height > 0, "Photograph dimensions missing")
    root = ET.Element(f"{{{NS}}}svg", {"viewBox": f"0 0 {width} {height}", "role": "img", "aria-label": alt})
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    ET.SubElement(root, f"{{{NS}}}image", {"width": str(width), "height": str(height), "href": f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()})
    return root


def make_images(recipe, extraction, diagrams, output, renderer, media=None):
    assets = output / "assets"
    assets.mkdir(parents=True)
    dimensions = {}
    source_path = lambda key: inside(extraction, extraction / diagrams[key]["path"])
    cover = recipe["cover"]
    if cover.get("asset_id"):
        dimensions["cover"] = export_svg(media_svg(media[cover["asset_id"]], cover["alt"]), assets / "cover.svg", renderer)
    else:
        dimensions["cover"] = make_legacy_cover(cover, source_path, assets, renderer)
    for figure in recipe["figures"]:
        if figure["kind"] == "asset":
            dimensions[figure["id"]] = export_svg(media_svg(media[figure["asset_id"]], figure["alt"]), assets / f"{figure['id']}.svg", renderer)
        else:
            dimensions[figure["id"]] = make_legacy_figure(figure, source_path, assets, renderer)
    return dimensions


def make_legacy_cover(cover, source_path, assets, renderer):
    root = canvas(1200, 675, cover["alt"], dark=True)
    svg_text(root, 70, 78, "GEO STORY  /  天体图解", "cover-kicker")
    svg_text(root, 70, 198, cover["lines"][0], "cover-title")
    svg_text(root, 70, 302, cover["lines"][1], "cover-title")
    svg_text(root, 74, 369, cover["subtitle"], "cover-subtitle")
    for index, key in enumerate(cover["source_diagram_ids"][:3]):
        insert_diagram(root, source_path(key), 65 + index * 375, 400, 320, 205)
    svg_text(root, 74, 640, "必修一 · 宇宙中的地球", "cover-label")
    return export_svg(root, assets / "cover.svg", renderer)


def make_legacy_figure(figure, source_path, assets, renderer):
    height = 900 if figure["kind"] == "single" else 1240
    root = canvas(1200, height, figure["alt"])
    svg_text(root, 64, 110, figure["title"], "title")
    if figure["kind"] == "single":
        insert_diagram(root, source_path(figure["source_diagram_ids"][0]), 210, 175, 780, 500)
        svg_text(root, 64, 742, figure["labels"][0]["title"], "row-title")
        svg_text(root, 64, 810, figure["labels"][0]["subtitle"], "subtitle")
    else:
        for index, (key, label) in enumerate(zip(figure["source_diagram_ids"], figure["labels"])):
            y = 155 + index * 330
            ET.SubElement(root, f"{{{NS}}}rect", {"x": "44", "y": str(y), "width": "1112", "height": "302", "rx": "12", "fill": "#fff", "stroke": "#d4deeb"})
            insert_diagram(root, source_path(key), 65, y + 38, 320, 215)
            svg_text(root, 424, y + 116, label["title"], "row-title")
            svg_text(root, 424, y + 186, label["subtitle"], "row-subtitle")
    svg_text(root, 64, height - 26, "示意图 · 大小、轨道与距离不按比例", "footer")
    return export_svg(root, assets / f"{figure['id']}.svg", renderer)


def article_outputs(recipe, references, statements, dimensions):
    title = recipe["titles"][recipe["selected_title"]]
    evidence_ids = list(references)
    ref_number = {key: index for index, key in enumerate(evidence_ids, 1)}
    figures = {item["id"]: item for item in recipe["figures"]}
    media = {item["id"]: item for item in recipe.get("media", [])}
    esc = escape
    css = (SKILL_DIR / "assets/article.css").read_text(encoding="utf-8")
    title_parts = title.split("：", 1)
    title_markup = esc(title) if len(title_parts) == 1 else f'<span class="title-line">{esc(title_parts[0])}：</span><span class="title-line">{esc(title_parts[1])}</span>'
    body = [f'<article class="article"><div class="eyebrow">地理故事 · 天体图解</div><h1>{title_markup}</h1><p class="deck">{esc(recipe["summary"])}</p>']
    markdown = [f"# {title}", "", recipe["summary"], ""]
    if recipe["cover"].get("show_in_article", True):
        body.append(f'<img class="cover" src="assets/cover.png" width="{dimensions["cover"][0]}" height="{dimensions["cover"][1]}" alt="{esc(recipe["cover"]["alt"], quote=True)}">')
        markdown.extend([f'![{recipe["cover"]["alt"]}](assets/cover.png)', ""])
    for section in recipe["sections"]:
        body.append(f'<section><h2>{esc(section["heading"])}</h2>')
        markdown.extend([f'## {section["heading"]}', ""])
        for paragraph in section["paragraphs"]:
            refs = list(dict.fromkeys(key for claim in paragraph["claim_ids"] for key in statements[claim]["evidence_ids"]))
            cites = "".join(f'<a href="#ref-{ref_number[key]}" aria-label="参考资料{ref_number[key]}">[{ref_number[key]}]</a>' for key in refs)
            body.append(f'<p>{esc(paragraph["text"])}<sup>{cites}</sup></p>')
            markdown.extend([paragraph["text"] + " " + "".join(f'[{ref_number[key]}]' for key in refs), ""])
        if section["figure_id"]:
            figure = figures[section["figure_id"]]
            key = figure["id"]
            width, height = dimensions[key]
            source = media.get(figure.get("asset_id"), {}).get("source_url")
            source_link = f' <a href="{esc(source, quote=True)}">原图来源</a>' if source else ""
            body.append(f'<figure><img src="assets/{key}.png" width="{width}" height="{height}" loading="lazy" alt="{esc(figure["alt"], quote=True)}"><figcaption>{esc(figure["caption"])}{source_link}</figcaption></figure>')
            markdown.extend([f'![{figure["alt"]}](assets/{key}.png)', "", figure["caption"] + (f" [原图来源]({source})" if source else ""), ""])
        body.append("</section>")
    body.append('<section class="references"><h2>参考资料</h2><ol>')
    markdown.extend(["## 参考资料", ""])
    for key, evidence in references.items():
        number = ref_number[key]
        body.append(f'<li id="ref-{number}"><a href="{esc(evidence["url"], quote=True)}">{esc(evidence["title"])}</a> · {esc(evidence["publisher"])}</li>')
        markdown.append(f'{number}. [{evidence["title"]}]({evidence["url"]}) · {evidence["publisher"]}')
    body.append("</ol></section></article>")
    body = "\n".join(body)
    head = f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{css}</style></head><body>'
    return title, head + body + "</body></html>", "\n".join(markdown) + "\n", body, css


def preview_html(recipe, title, body, css, topic):
    actions = '<a href="visuals.html">封面与配图</a><a href="../outputs/article.md" download>下载正文</a><a href="../outputs/content-package.zip" download>下载图文包</a><a href="../outputs/article.html">阅读成品</a>'
    details = [f'<p>选题范围：{escape(topic["scope"])}</p><p>制作人：{escape(recipe["editorial_review"]["name"])}（代理核对）。</p><h2>审校要求的落实</h2><ul>']
    details.extend(f'<li>{escape(item["diagram_id"])}：{escape(item["resolution"])}</li>' for item in recipe["change_resolutions"])
    details.append("</ul><h2>备选标题</h2><ul>")
    details.extend(f"<li>{escape(item)}</li>" for item in recipe["titles"])
    details.append("</ul>")
    styles = css + "\n" + (SKILL_DIR / "assets/preview.css").read_text(encoding="utf-8")
    article = body.replace('src="assets/', 'src="../outputs/assets/')
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>审阅 · {escape(title)}</title><style>{styles}</style></head><body><header class="review-bar"><span class="review-brand">Geo Story Studio</span><nav class="review-actions" aria-label="作品文件"><span class="status">等待 Approve</span>{actions}</nav></header><p class="review-note">今日头条 · 图文构建 · {escape(recipe["version"])}。请核对标题、正文与配图，在对话中批准或提出修改。</p><details class="review-details"><summary>查看审校范围、配图处理和备选标题</summary>{"".join(details)}</details><main class="preview-sheet">{article}</main><footer class="preview-footer">当前为本地审阅版本，工作流停在 Approve。修改后的作品使用新版本保存。</footer></body></html>'


def visual_review_html(recipe, media):
    esc = escape
    css = (SKILL_DIR / "assets/article.css").read_text() + (SKILL_DIR / "assets/preview.css").read_text()
    cover = recipe["cover"]
    cards = []
    for name, cls in [("原图 · 16:9", "wide"), ("居中裁切 · 4:3", "standard"), ("居中裁切 · 1:1", "square")]:
        cards.append(f'<figure class="crop {cls}"><img src="../outputs/assets/cover.png" alt="{esc(cover["alt"], quote=True)}"><figcaption>{name}</figcaption></figure>')
    figures = "".join(f'<section><h2>{esc(f["title"])}</h2><p>{esc(f.get("purpose", f["caption"]))}</p><img class="visual-asset" src="../outputs/assets/{f["id"]}.png" alt="{esc(f["alt"], quote=True)}"><p>{esc(f["caption"])}</p></section>' for f in recipe["figures"])
    sources = []
    for item in media.values():
        links = "".join(f'<a href="{esc(item[key], quote=True)}">{label}</a> ' for key, label in [("source_url", "来源页面"), ("rights_url", "使用依据")] if item.get(key))
        sources.append(f'<li><strong>{esc(item["id"])}</strong> · {esc(item["credit"])}<br>{esc(item["rights_notes"])}<br>处理：{esc(item["adaptation"])}<br>{links}</li>')
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>题图审阅 · {esc(recipe["titles"][recipe["selected_title"]])}</title><style>{css}</style></head><body><header class="review-bar"><span class="review-brand">封面与配图 · {esc(recipe["version"])}</span><nav class="review-actions"><span class="status">等待 Approve</span><a href="index.html">审阅正文</a><a href="../outputs/visual-plan.json">图片清单</a></nav></header><main class="visual-review"><h1>先看封面，再看解释图</h1><p>读者：{esc(recipe["audience"])}</p><p>{esc(cover.get("purpose", "封面帮助辨认文章主题。"))}</p><div class="crop-grid">{"".join(cards)}</div><p>{esc(cover.get("caption", cover["alt"]))}</p><p>裁切为本地检查情形，实际发布规格与裁切位置以平台编辑器为准。封面是否进入正文由构建单独记录。</p>{figures}<section><h2>素材来源与使用范围</h2><ul>{"".join(sources)}</ul><p>上述来源只说明原始素材；文章与图解由本项目整理，未获得来源机构对本作品的审核或背书。</p></section></main></body></html>'


def build(root, material_path, recipe_path):
    root = root.resolve()
    recipe = load(recipe_path)
    extraction, material = verify_material(root, material_path)
    topic = next((item for item in material["topics"] if item["id"] == recipe["topic_id"]), None)
    require(topic is not None, "Unknown reviewed topic")
    figures, used_claims = validate_recipe(recipe, topic)
    media = verify_media(root, recipe)
    material_path = inside(root, material_path)
    skill = {
        "name": "toutiao-build",
        "version": SKILL_VERSION,
        "instructions_sha256": sha(SKILL_DIR / "SKILL.md"),
        "script_sha256": sha(Path(__file__).resolve()),
        "asset_hashes": {path.relative_to(SKILL_DIR / "assets").as_posix(): sha(path) for path in sorted((SKILL_DIR / "assets").rglob("*")) if path.is_file()},
        "reference_hashes": {path.relative_to(SKILL_DIR / "references").as_posix(): sha(path) for path in sorted((SKILL_DIR / "references").rglob("*")) if path.is_file()},
    }
    workflow_path = root / "workflows/toutiao.yaml"
    workflow = load(workflow_path)
    require(workflow["platform"] == "toutiao" and [item["id"] for item in workflow["steps"]] == WORKFLOW_STEPS, "Unsupported Toutiao workflow")
    require(workflow["steps"][4].get("kind") == "human_approval" and workflow["steps"][4].get("required") is True, "Workflow requires a mandatory approval step")
    require(workflow["steps"][5].get("requires") == "approve" and workflow["steps"][5].get("implemented") is False, "Publishing is not implemented in this build stage")
    workflow_ref = {"path": "workflows/toutiao.yaml", "id": workflow["id"], "version": workflow["version"], "sha256": sha(workflow_path)}
    review_ref = {"review_id": material["review_id"], "extraction_id": material["extraction_id"], "topic_id": topic["id"], "material_path": material_path.relative_to(root).as_posix(), "material_sha256": sha(material_path), "review_sha256": material["provenance"]["review_sha256"]}
    recipe_hash = fingerprint(recipe)
    destination = root / "storage/builds" / recipe["build_id"] / recipe["version"]
    if destination.exists():
        existing = load(destination / "manifest.json")
        require(existing["recipe_sha256"] == recipe_hash and existing["review_ref"] == review_ref and existing["skill"] == skill and existing["workflow_ref"] == workflow_ref, "Build version already exists with different inputs; use a new version")
        require(existing["status"] == "awaiting_approval" and existing["requires_publication_approval"] is True, "Build status cannot grant publication approval")
        subject = {key: existing[key] for key in ["build_id", "build_version", "platform", "source_ref", "review_ref", "skill", "workflow_ref", "recipe_sha256", "artifacts"]}
        require(fingerprint(subject) == existing["approval_subject_sha256"], "Build approval-subject integrity failure")
        require(existing["title"] == recipe["titles"][recipe["selected_title"]], "Build title mismatch")
        for artifact in existing["artifacts"]:
            require(sha(inside(destination, destination / artifact["path"])) == artifact["sha256"], "Existing build artifact integrity failure")
        return existing, destination
    renderer = shutil.which("rsvg-convert")
    require(renderer is not None, "PNG export requires installed rsvg-convert")
    renderer_version = subprocess.run([renderer, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".build-", dir=destination.parent))
    try:
        outputs, preview = temporary / "outputs", temporary / "preview"
        outputs.mkdir()
        preview.mkdir()
        content = load(extraction / "content.json")
        diagrams = {item["id"]: item for item in content["diagrams"]}
        dimensions = make_images(recipe, extraction, diagrams, outputs, renderer, media)
        media_records = []
        for item in media.values():
            filename = "media-" + item["id"] + item["local_path"].suffix.lower()
            shutil.copyfile(item["local_path"], outputs / "assets" / filename)
            media_records.append({**{k: v for k, v in item.items() if k not in {"local_path", "path"}}, "input_path": item["path"], "path": "assets/" + filename})
        dump(outputs / "media.json", media_records)
        dump(outputs / "visual-plan.json", {"audience": recipe["audience"], "cover": recipe["cover"], "figures": recipe["figures"], "media": media_records})
        statements = {item["id"]: item for item in topic["statements"]}
        evidence_ids = {key for claim_id in used_claims for key in statements[claim_id]["evidence_ids"]}
        references = {item["id"]: item for item in material["references"] if item["id"] in evidence_ids}
        title, html, markdown, body, css = article_outputs(recipe, references, statements, dimensions)
        (outputs / "article.html").write_text(html, encoding="utf-8")
        (outputs / "article.md").write_text(markdown, encoding="utf-8")
        (preview / "index.html").write_text(preview_html(recipe, title, body, css, topic), encoding="utf-8")
        (preview / "visuals.html").write_text(visual_review_html(recipe, media), encoding="utf-8")
        dump(outputs / "references.json", list(references.values()))
        publish = {"platform": "toutiao", "title": title, "summary": recipe["summary"], "tags": recipe["tags"], "cover": "assets/cover.png", "cover_in_article": recipe["cover"].get("show_in_article", True), "article": "article.html", "media": "media.json", "visual_plan": "visual-plan.json", "images": [{"path": f"assets/{item['id']}.png", "alt": item["alt"], "caption": item["caption"]} for item in recipe["figures"]]}
        dump(outputs / "publish.json", publish)
        dump(temporary / "recipe.json", recipe)
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        statuses = ["completed", "completed", "completed", "completed", "waiting", "not_started"]
        run = {"schema_version": "1.0", "run_id": recipe["build_id"] + "-" + recipe["version"], "workflow_ref": workflow_ref, "platform": "toutiao", "build_id": recipe["build_id"], "build_version": recipe["version"], "status": "waiting_for_approval", "created_at": created_at, "steps": [{"id": key, "status": value} for key, value in zip(WORKFLOW_STEPS, statuses)]}
        dump(temporary / "workflow-run.json", run)
        with ZipFile(outputs / "content-package.zip", "w") as archive:
            for path in sorted(outputs.rglob("*")):
                if path.is_file() and path.name != "content-package.zip":
                    info = ZipInfo(path.relative_to(outputs).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = ZIP_DEFLATED
                    archive.writestr(info, path.read_bytes())
        artifacts = [{"path": path.relative_to(temporary).as_posix(), "sha256": sha(path), "size_bytes": path.stat().st_size} for path in sorted(temporary.rglob("*")) if path.is_file()]
        characters = sum(len(re.findall(r"[\u3400-\u9fff]", paragraph["text"])) for section in recipe["sections"] for paragraph in section["paragraphs"])
        subject = {"build_id": recipe["build_id"], "build_version": recipe["version"], "platform": "toutiao", "source_ref": material["source_ref"], "review_ref": review_ref, "skill": skill, "workflow_ref": workflow_ref, "recipe_sha256": recipe_hash, "artifacts": artifacts}
        manifest = {"schema_version": "1.0", **subject, "status": "awaiting_approval", "requires_publication_approval": True, "created_at": created_at, "title": title, "parameters": {"audience": recipe["audience"], "format": "article", "body_chinese_characters": characters, "figure_count": len(figures), "renderer": renderer_version, "raster_width": 1440, "fonts": "system_fallback"}, "approval_subject_sha256": fingerprint(subject)}
        dump(temporary / "manifest.json", manifest)
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest, destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=TOOL_ROOT)
    parser.add_argument("--material", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest, path = build(args.root.resolve(), args.root / args.material, args.root / args.recipe)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ET.ParseError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(json.dumps({"build": str(path), "status": manifest["status"], "title": manifest["title"], "characters": manifest["parameters"]["body_chinese_characters"], "approval_subject_sha256": manifest["approval_subject_sha256"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
