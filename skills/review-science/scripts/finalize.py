#!/usr/bin/env python3
"""Validate a researched review and derive material scoped for platform builds."""

import argparse
from collections import Counter
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse


SKILL_VERSION = "0.1.0"
DECISIONS = {"supported", "revise", "qualify", "unresolved"}
LABELS = {"supported": "有依据支持", "revise": "需要修改", "qualify": "需要限定范围", "unresolved": "证据不足"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def unique_index(items, key):
    require(isinstance(items, list), f"{key}: expected a list")
    result = {}
    for item in items:
        require(isinstance(item, dict) and text(item.get(key)), f"Missing {key}")
        require(item[key] not in result, f"Duplicate {key}: {item[key]}")
        result[item[key]] = item
    return result


def check_refs(values, available, label, allow_empty=False):
    require(isinstance(values, list) and all(text(value) for value in values), f"{label}: expected string IDs")
    require(len(values) == len(set(values)), f"{label}: duplicate references")
    require(allow_empty or bool(values), f"{label}: empty references")
    require(set(values) <= set(available), f"{label}: unknown references")


def inside(root, path):
    path = path.resolve()
    path.relative_to(root.resolve())
    return path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def compile_review(root, extraction, review, review_sha256):
    root = root.resolve()
    extraction = inside(root, extraction)
    content_path, knowledge_path = extraction / "content.json", extraction / "knowledge.json"
    content, knowledge = load(content_path), load(knowledge_path)
    require(review.get("schema_version") == "1.0", "Unsupported review schema")
    require(isinstance(review.get("review_id"), str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", review["review_id"]), "Invalid review ID")
    require(review["source_ref"] == content["source_ref"] == knowledge["source_ref"], "Source reference mismatch")
    require(review["extraction_id"] == content["extraction_id"] == knowledge["extraction_id"], "Extraction ID mismatch")
    require(review["input_hashes"] == {"content_sha256": sha256(content_path), "knowledge_sha256": sha256(knowledge_path)}, "Review input hash mismatch")
    snapshot = inside(root, root / review["source_ref"]["snapshot_path"])
    require(sha256(snapshot) == review["source_ref"]["sha256"], "Source snapshot integrity failure")
    reviewed_at = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
    require(reviewed_at.utcoffset() is not None, "Review timestamp must include timezone")
    require(review["reviewer"]["type"] in {"agent", "human"} and text(review["reviewer"]["name"]), "Invalid reviewer")
    skill_path = Path(__file__).resolve().parents[1] / "SKILL.md"
    require(review["skill"] == {"name": "review-science", "version": SKILL_VERSION, "instructions_sha256": sha256(skill_path)}, "Review SKILL provenance mismatch")
    require(isinstance(review["scope_notes"], list) and all(text(item) for item in review["scope_notes"]), "Invalid scope notes")

    blocks = unique_index(content["text_blocks"], "id")
    diagrams = unique_index(content["diagrams"], "id")
    points = unique_index(knowledge["knowledge_points"], "id")
    items = unique_index(knowledge["review_items"], "id")
    topics = unique_index(knowledge["candidate_topics"], "id")
    evidence = unique_index(review["evidence"], "id")
    claims = unique_index(review["claims"], "id")
    diagram_reviews = unique_index(review["diagram_reviews"], "diagram_id")
    plans = unique_index(review["topic_plans"], "topic_id")
    require(bool(claims), "Review has no claims")
    require(set(diagram_reviews) == set(diagrams), "Diagram coverage mismatch")
    require(set(plans) == set(topics), "Topic coverage mismatch")
    for item in evidence.values():
        require(all(text(item.get(field)) for field in ["title", "publisher", "url", "section", "note"]), "Evidence metadata incomplete")
        parsed = urlparse(item["url"])
        require(parsed.scheme in {"https", "http"} and bool(parsed.netloc), "Evidence must use a source URL")
        require(date.fromisoformat(item["accessed_on"]) <= reviewed_at.date(), "Evidence access date follows review date")

    covered_points, covered_items = set(), set()
    for claim in claims.values():
        require(claim["decision"] in DECISIONS, "Unknown claim decision")
        require(all(text(claim.get(field)) for field in ["title", "original_text", "reason", "scope"]), "Claim text incomplete")
        check_refs(claim["source_refs"], blocks, "Claim source")
        check_refs(claim["knowledge_point_ids"], points, "Claim knowledge point")
        check_refs(claim["related_review_item_ids"], items, "Initial review item", allow_empty=True)
        check_refs(claim["evidence_ids"], evidence, "Claim evidence", allow_empty=claim["decision"] == "unresolved")
        require(any(claim["original_text"] in blocks[key]["text"] for key in claim["source_refs"]), f"Claim quote not found: {claim['id']}")
        require(isinstance(claim["constraints"], list) and all(text(value) for value in claim["constraints"]), "Invalid claim constraints")
        if claim["decision"] == "unresolved":
            require(claim["recommended_text"] is None, "Unresolved claim cannot have usable text")
        else:
            require(text(claim["recommended_text"]), "Resolved claim needs recommended text")
        covered_points.update(claim["knowledge_point_ids"])
        covered_items.update(claim["related_review_item_ids"])
    require(covered_points == set(points), "Knowledge point coverage mismatch")
    require(covered_items == set(items), "Initial review-item coverage mismatch")

    for identifier, diagram in diagram_reviews.items():
        require(diagram["decision"] in {"reuse", "revise", "unresolved"}, "Unknown diagram decision")
        check_refs(diagram["claim_ids"], claims, "Diagram claim")
        require(isinstance(diagram["requirements"], list) and all(text(value) for value in diagram["requirements"]), "Invalid diagram requirements")
        require(diagram["decision"] == "reuse" or bool(diagram["requirements"]), "Diagram changes or open issues need instructions")
        asset = inside(extraction, extraction / diagrams[identifier]["path"])
        require(sha256(asset) == diagrams[identifier]["sha256"], "Diagram integrity failure")

    def statement(claim):
        return {key: claim[key] for key in ["id", "recommended_text", "evidence_ids", "scope", "constraints"]}

    reviewed_points = []
    for identifier, point in points.items():
        selected = [claim for claim in claims.values() if identifier in claim["knowledge_point_ids"]]
        usable = [claim for claim in selected if claim["decision"] != "unresolved"]
        unresolved = [claim["id"] for claim in selected if claim["decision"] == "unresolved"]
        status = "blocked" if not usable else ("partially_reviewed" if unresolved else "reviewed")
        reviewed_points.append({"id": identifier, "title": point["title"], "status": status, "statements": [statement(claim) for claim in usable], "unresolved_claim_ids": unresolved})

    reviewed_topics = []
    for identifier, plan in plans.items():
        require(text(plan["scope"]), "Topic scope missing")
        check_refs(plan["claim_ids"], claims, "Topic claim")
        check_refs(plan["diagram_ids"], diagrams, "Topic diagram", allow_empty=True)
        require(isinstance(plan["constraints"], list) and all(text(value) for value in plan["constraints"]), "Invalid topic constraints")
        effective_ids = list(dict.fromkeys(plan["claim_ids"] + [claim_id for diagram_id in plan["diagram_ids"] for claim_id in diagram_reviews[diagram_id]["claim_ids"]]))
        covered = {point_id for claim_id in effective_ids for point_id in claims[claim_id]["knowledge_point_ids"]}
        require(set(topics[identifier]["knowledge_point_ids"]) <= covered, "Topic plan omits a knowledge point")
        blocked_claims = [key for key in effective_ids if claims[key]["decision"] == "unresolved"]
        blocked_diagrams = [key for key in plan["diagram_ids"] if diagram_reviews[key]["decision"] == "unresolved"]
        ready = not blocked_claims and not blocked_diagrams
        constraints = list(dict.fromkeys(plan["constraints"] + [value for key in effective_ids for value in claims[key]["constraints"]]))
        changes = [{"diagram_id": key, "instructions": diagram_reviews[key]["requirements"]} for key in plan["diagram_ids"] if diagram_reviews[key]["requirements"]]
        reviewed_topics.append({"id": identifier, "title": topics[identifier]["title"], "scope": plan["scope"], "readiness": "ready_for_build" if ready else "blocked", "claim_ids": effective_ids, "statements": [statement(claims[key]) for key in effective_ids] if ready else [], "diagram_ids": plan["diagram_ids"], "constraints": constraints, "required_changes": changes, "blocking_claim_ids": blocked_claims, "blocking_diagram_ids": blocked_diagrams})

    open_items = any(claim["decision"] == "unresolved" for claim in claims.values()) or any(item["decision"] == "unresolved" for item in diagram_reviews.values())
    return {"schema_version": "1.0", "source_ref": review["source_ref"], "extraction_id": review["extraction_id"], "review_id": review["review_id"], "reviewed_at": review["reviewed_at"], "status": "completed_with_open_items" if open_items else "reviewed", "provenance": {"review_sha256": review_sha256, **review["input_hashes"], "skill": review["skill"], "script_sha256": sha256(Path(__file__).resolve())}, "requires_publication_approval": True, "knowledge_points": reviewed_points, "topics": reviewed_topics, "diagram_reviews": review["diagram_reviews"], "references": review["evidence"]}


def report(review, reviewed):
    evidence = {item["id"]: item for item in review["evidence"]}
    counts = Counter(item["decision"] for item in review["claims"])
    lines = ["# 科学审校报告", "", f"审校：{review['review_id']}；源版本：{review['source_ref']['source_version']}；提取：{review['extraction_id']}。", "", f"执行者：{review['reviewer']['name']}（{review['reviewer']['type']}）；日期：{review['reviewed_at']}。", "", f"状态：{reviewed['status']}。共 {len(review['claims'])} 项结论、{len(review['diagram_reviews'])} 张图解、{len(evidence)} 份来源。", "", "判定统计：" + "；".join(f"{LABELS[key]} {counts[key]}" for key in ["supported", "revise", "qualify", "unresolved"]) + "。", "", "## 范围", ""]
    lines.extend("- " + note for note in review["scope_notes"])
    lines += ["", "## 选题构建状态", "", "| 选题 | 状态 | 适用范围 |", "| --- | --- | --- |"]
    for topic in reviewed["topics"]:
        lines.append(f"| {topic['id']}：{topic['title']} | {topic['readiness']} | {topic['scope']} |")
    lines += ["", "ready_for_build 表示可按允许表述开始制作；图解修改要求需在构建中落实。成品随后核对并进行发布 Approve。", "", "## 逐条结论", ""]
    for claim in review["claims"]:
        sources = "、".join(f"[{evidence[key]['title']}]({evidence[key]['url']})" for key in claim["evidence_ids"]) or "尚缺对应资料"
        lines += [f"### {claim['id']}：{claim['title']}", "", f"- 判定：{LABELS[claim['decision']]}。", f"- 原文：{claim['original_text']}", "- 定位：" + "、".join(claim["source_refs"]), f"- 理由：{claim['reason']}", f"- 建议表述：{claim['recommended_text'] or '待取得资料后确定。'}", f"- 范围：{claim['scope']}", f"- 依据：{sources}。"]
        lines.extend("- 使用条件：" + value for value in claim["constraints"])
        lines.append("")
    lines += ["## 图解处理", "", "| 图解 | 判定 | 构建要求 |", "| --- | --- | --- |"]
    for diagram in review["diagram_reviews"]:
        lines.append(f"| {diagram['diagram_id']} | {diagram['decision']} | {'；'.join(diagram['requirements']) or '保留原图形，按审校文本配文。'} |")
    lines += ["", "## 来源记录", ""]
    for item in review["evidence"]:
        lines += [f"- {item['id']}：[{item['title']}]({item['url']})，{item['publisher']}。段落：{item['section']}；查阅：{item['accessed_on']}。", "  证据摘要：" + item["note"]]
    lines += ["", "## 后续使用", "", "平台构建读取 reviewed-knowledge.json 中选定 topics 的 statements、scope、constraints 和 required_changes。blocked 选题等待补充依据或新一轮审校。", "", "本报告记录代理查证及其范围。结构检查只验证哈希、引用和状态派生；未创建发布批准。", ""]
    return "\n".join(lines)


def finalize(root, extraction, review_path):
    extraction = inside(root, extraction)
    review_path = inside(extraction, review_path)
    review = load(review_path)
    require(review_path == extraction / "reviews" / review["review_id"] / "review.json", "Review path must match review ID")
    reviewed = compile_review(root, extraction, review, sha256(review_path))
    outputs = {review_path.parent / "reviewed-knowledge.json": json.dumps(reviewed, ensure_ascii=False, indent=2) + "\n", review_path.parent / "review.md": report(review, reviewed)}
    for path, body in outputs.items():
        require(not path.exists() or path.read_text(encoding="utf-8") == body, f"Existing output differs; create a new review ID: {path}")
    for path, body in outputs.items():
        if not path.exists():
            with path.open("x", encoding="utf-8") as handle:
                handle.write(body)
    return reviewed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    try:
        reviewed = finalize(args.root.resolve(), args.root / args.extraction, args.root / args.review)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Review validation failed: {error}\n")
    print(json.dumps({"review_id": reviewed["review_id"], "status": reviewed["status"], "topics": {item["id"]: item["readiness"] for item in reviewed["topics"]}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
