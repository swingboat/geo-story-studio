#!/usr/bin/env python3
"""Register an HTML source and create a traceable local extraction."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from html import entities
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


SKILL_VERSION = "0.1.0"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class Node:
    def __init__(self, tag, attrs=None, parent=None, start=0, line=1):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []
        self.start = start
        self.end = start
        self.line = line
        self.end_line = line

    def text(self):
        return "".join(child.text() if isinstance(child, Node) else child for child in self.children)

    def normalized_text(self):
        return re.sub(r"\s+", " ", self.text()).strip()

    def inside(self, tags):
        parent = self.parent
        while parent:
            if parent.tag in tags:
                return True
            parent = parent.parent
        return False

    def locator(self):
        return {"start_line": self.line, "end_line": self.end_line}


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.offsets = [0]
        for match in re.finditer("\n", source):
            self.offsets.append(match.end())
        self.root = Node("document")
        self.stack = [self.root]
        self.nodes = []
        self.feed(source)
        self.close()
        for node in self.stack[1:]:
            node.end = len(source)
            node.end_line = len(self.offsets)

    def absolute_offset(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1], self.absolute_offset(), self.getpos()[0])
        node.end = node.start + len(self.get_starttag_text())
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                end = self.source.find(">", self.absolute_offset()) + 1
                for node in self.stack[index:]:
                    node.end = end
                    node.end_line = self.getpos()[0]
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def dependencies(document):
    found = []
    for node in document.nodes:
        attributes = []
        if node.tag == "link":
            attributes = ["href"]
        elif node.tag in {"script", "img", "audio", "video", "source", "iframe"}:
            attributes = ["src", "poster"]
        elif node.tag == "image":
            attributes = ["href", "xlink:href"]
        for attribute in attributes:
            url = node.attrs.get(attribute)
            if not url or url.startswith(("#", "data:")):
                continue
            remote = url.startswith(("https://", "http://", "//"))
            found.append({"url": url, "kind": node.attrs.get("rel", node.tag), "availability": "remote" if remote else "not_copied", "locator": node.locator()})
    # CSS imports and url() references also matter to the original page.
    for node in document.nodes:
        css = node.text() if node.tag == "style" else node.attrs.get("style", "")
        for match in re.finditer(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)|@import\s+['\"]([^'\"]+)['\"]", css):
            url = (match.group(1) or match.group(2)).strip()
            if url.startswith(("#", "data:")):
                continue
            remote = url.startswith(("https://", "http://", "//"))
            found.append({"url": url, "kind": "css", "availability": "remote" if remote else "not_copied", "locator": node.locator()})
    return found


def standalone_svg(raw, css):
    # XML readers need the namespace and numeric forms of HTML-only entities.
    raw = re.sub(r"&([A-Za-z][A-Za-z0-9]+);", lambda m: f"&#{entities.name2codepoint[m.group(1)]};" if m.group(1) in entities.name2codepoint else m.group(0), raw)
    opening_end = raw.find(">")
    if not re.search(r"\bxmlns=", raw[:opening_end]):
        raw = re.sub(r"<svg\b", '<svg xmlns="http://www.w3.org/2000/svg"', raw, count=1)
    opening_end = raw.find(">") + 1
    css = css.replace("]]>", "]]]]><![CDATA[>")
    return raw[:opening_end] + '\n<style type="text/css"><![CDATA[' + css + "]]></style>\n" + raw[opening_end:]


def extract(document, output, source_ref, extraction_id, skill):
    assets = output / "assets"
    assets.mkdir(parents=True)
    css = "\n".join(node.text() for node in document.nodes if node.tag == "style")
    (assets / "source-style.css").write_text(css, encoding="utf-8")
    regions = [node for node in document.nodes if node.tag in {"header", "section"} and not node.inside({"header", "section", "svg"})]
    region_ids = {id(node): f"section-{index:03d}" for index, node in enumerate(regions, 1)}

    def region_id(node):
        while node:
            if id(node) in region_ids:
                return region_ids[id(node)]
            node = node.parent
        return None

    sections = []
    for node in regions:
        heading = next((item for item in document.nodes if item.tag in {"h1", "h2"} and node.start <= item.start < node.end), None)
        sections.append({"id": region_ids[id(node)], "title": heading.normalized_text() if heading else "", "locator": node.locator()})
    blocks, diagrams, interactions = [], [], []
    for node in document.nodes:
        if node.tag in {"h1", "h2", "h3", "p", "button"} and not node.inside({"svg", "script", "style"}):
            blocks.append({"id": f"block-{len(blocks) + 1:03d}", "tag": node.tag, "text": node.normalized_text(), "section_id": region_id(node), "locator": node.locator()})
        if node.tag == "svg" and not node.inside({"svg"}):
            diagram_id = f"svg-{len(diagrams) + 1:03d}"
            raw = document.source[node.start:node.end]
            raw_path = f"assets/{diagram_id}.raw.svg"
            path = f"assets/{diagram_id}.svg"
            rendered = standalone_svg(raw, css)
            (output / raw_path).write_text(raw, encoding="utf-8")
            (output / path).write_text(rendered, encoding="utf-8")
            diagrams.append({"id": diagram_id, "section_id": region_id(node), "label": node.attrs.get("aria-label", ""), "locator": node.locator(), "raw_path": raw_path, "path": path, "sha256": digest(rendered.encode()), "font_policy": "system_fallback"})
        if node.tag == "button":
            interactions.append({"id": f"interaction-{len(interactions) + 1:03d}", "section_id": region_id(node), "text": node.normalized_text(), "attributes": node.attrs, "locator": node.locator()})
    return {"schema_version": "1.0", "source_ref": source_ref, "extraction_id": extraction_id, "extracted_at": now(), "skill": skill, "sections": sections, "text_blocks": blocks, "diagrams": diagrams, "interactions": interactions, "dependencies": dependencies(document)}


@contextmanager
def registry_lock(root):
    state = root / "storage/state"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "source-registry.lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
        fcntl.flock(handle, fcntl.LOCK_UN)


def register_and_extract(root, source, source_id, book, extraction_id):
    root = root.resolve()
    source = source.resolve()
    input_path = source.relative_to(root).as_posix()
    data = source.read_bytes()
    document = Document(data.decode("utf-8-sig"))
    sha256 = digest(data)
    source_id = source_id or "src-" + digest(input_path.encode())[:16]
    for identifier in [source_id, extraction_id]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", identifier):
            raise ValueError("IDs must use lowercase letters, digits and hyphens (1–64 characters)")
    script_path = Path(__file__).resolve()
    skill = {"name": "extract-content", "version": SKILL_VERSION, "script_sha256": digest(script_path.read_bytes()), "instructions_sha256": digest((script_path.parents[1] / "SKILL.md").read_bytes())}
    with registry_lock(root):
        registry_path = root / "storage/state/source-registry.json"
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"schema_version": "1.0", "sources": []}
        record = next((item for item in registry["sources"] if item["source_id"] == source_id), None)
        if record is None:
            record = {"source_id": source_id, "input_path": input_path, "versions": []}
            registry["sources"].append(record)
        elif record["input_path"] != input_path:
            raise ValueError("Source ID already belongs to another input path")
        existing = next((item for item in record["versions"] if item["sha256"] == sha256), None)
        if existing:
            manifest_path = root / existing["manifest_path"]
            manifest = json.loads(manifest_path.read_text())
            if digest((root / manifest["snapshot_path"]).read_bytes()) != sha256:
                raise ValueError("Existing source snapshot failed integrity check")
        else:
            version = f"v{len(record['versions']) + 1:03d}"
            folder = root / "storage/sources" / source_id / version
            if folder.exists():
                raise ValueError(f"Unregistered version directory exists: {folder}")
            folder.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".register-", dir=folder.parent))
            manifest_path = folder / "manifest.json"
            title = next((node.normalized_text() for node in document.nodes if node.tag == "h1"), source.stem)
            document_title = next((node.normalized_text() for node in document.nodes if node.tag == "title"), title)
            deps = dependencies(document)
            manifest = {"schema_version": "1.0", "source_id": source_id, "source_version": version, "input_path": input_path, "snapshot_path": (folder / "index.html").relative_to(root).as_posix(), "sha256": sha256, "size_bytes": len(data), "registered_at": now(), "title": title, "document_title": document_title, "curriculum": {"book": book}, "dependencies": deps, "snapshot_complete": not any(item["availability"] == "not_copied" for item in deps)}
            try:
                (temporary / "index.html").write_bytes(data)
                write_json(temporary / "manifest.json", manifest)
                temporary.rename(folder)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
            record["versions"].append({"source_version": version, "sha256": sha256, "manifest_path": manifest_path.relative_to(root).as_posix()})
            write_json(registry_path, registry)
        source_ref = {key: manifest[key] for key in ["source_id", "source_version", "sha256", "snapshot_path"]}
        output = manifest_path.parent / "extractions" / extraction_id
        if output.exists():
            content = json.loads((output / "content.json").read_text())
            if content["source_ref"] != source_ref or content["skill"] != skill:
                raise ValueError("Extraction ID already exists with different provenance; use a new extraction ID")
            for diagram in content["diagrams"]:
                if digest((output / diagram["path"]).read_bytes()) != diagram["sha256"]:
                    raise ValueError("Existing diagram failed integrity check")
            return manifest_path, output, content
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".extract-", dir=output.parent))
        try:
            content = extract(document, temporary, source_ref, extraction_id, skill)
            write_json(temporary / "content.json", content)
            temporary.rename(output)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return manifest_path, output, content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-id")
    parser.add_argument("--book", default="")
    parser.add_argument("--extraction-id", default="extract-001")
    args = parser.parse_args()
    source = args.source if args.source.is_absolute() else args.root / args.source
    try:
        manifest, output, content = register_and_extract(args.root, source, args.source_id, args.book, args.extraction_id)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Extraction failed: {error}\n")
    print(json.dumps({"manifest": str(manifest), "extraction": str(output), "sections": len(content["sections"]), "text_blocks": len(content["text_blocks"]), "diagrams": len(content["diagrams"]), "interactions": len(content["interactions"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
