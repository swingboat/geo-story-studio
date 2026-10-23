#!/usr/bin/env python3
"""Write one human-readable publication copy file from publication.json."""

import argparse
import json
from pathlib import Path

KEYWORD_COUNT = 30


def render(data):
    for key in ("title", "description"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing {key}")
    keywords = data.get("keywords")
    if (not isinstance(keywords, list) or len(keywords) != KEYWORD_COUNT
            or not all(isinstance(word, str) and word.strip() == word and word and '\n' not in word for word in keywords)
            or len(set(keywords)) != KEYWORD_COUNT):
        raise ValueError(f"Expected exactly {KEYWORD_COUNT} distinct, nonempty keywords")
    tags = data.get("hashtags")
    if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) and tag.strip().lstrip('#') for tag in tags):
        raise ValueError("Missing hashtags")
    hashtags = ' '.join('#' + tag.strip().lstrip('#') for tag in tags)
    return ("【标题】\n" + data['title'].strip()
            + "\n\n【简介】\n" + data['description'].strip()
            + f"\n\n【关键词（{KEYWORD_COUNT}个）】\n" + ','.join(keywords)
            + "\n\n【话题】\n" + hashtags + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        content = render(json.loads(args.publication.read_text(encoding="utf-8")))
        output = args.output or args.publication.with_name("发布文案.txt")
        if output.exists() and output.read_text(encoding="utf-8") != content:
            raise ValueError("Publication copy already exists with different content; use a new version")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Publication copy failed: {error}\n")
    print(output)


if __name__ == "__main__":
    main()
