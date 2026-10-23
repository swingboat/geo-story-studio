# 输出约定（1.0）

## 文件与路径

```text
storage/state/source-registry.json
storage/sources/<source-id>/<source-version>/
  index.html
  manifest.json
  extractions/<extraction-id>/
    content.json
    knowledge.json
    summary.md
    assets/
      source-style.css
      svg-001.svg
      ...
```

登记表是现阶段的本地 JSON 存储，未来可迁移到数据库。教材目录中的输入文件保留。`source_id` 是稳定标识，`source_version` 按内容哈希递增；`extraction_id` 标识一次提取。同一提取的机械产物不覆盖，整理结果完成后应通过新的提取 ID 修订。

所有存储路径相对仓库根目录，素材路径相对提取目录。时间使用 UTC ISO 8601。格式的机器定义见仓库 `packages/core/sources/schemas/`。

## manifest.json

记录 `schema_version`、`source_id`、`source_version`、`input_path`、`snapshot_path`、`sha256`、`size_bytes`、`registered_at`、`title`、`document_title`、`curriculum`、`dependencies` 和 `snapshot_complete`。

`snapshot_complete` 仅表示已发现的本地文件引用是否包含在快照内，不保证网络依赖离线可用。远程依赖的 `availability` 为 `remote`，未复制的本地依赖为 `not_copied`。

## content.json

记录 `schema_version`、`source_ref`、`extraction_id`、`extracted_at`、`skill`、`sections`、`text_blocks`、`diagrams`、`interactions` 和 `dependencies`。

- `source_ref` 包含源 ID、版本、哈希和快照路径。
- `skill` 包含名称、版本、脚本哈希与指令哈希。
- `sections` 包含区域 ID、标题和定位。
- `text_blocks` 包含块 ID、标签、原文、区域 ID 和定位。
- `diagrams` 包含图解 ID、原始 SVG、独立 SVG 的路径及哈希、关联区域、无障碍标签和字体回退说明。
- `interactions` 包含按钮 ID、原文、HTML 属性及定位。脚本不执行输入中的 JavaScript。
- `locator` 是原 HTML 的 1 起始行号范围，`raw_path` 保存原始 SVG，独立 SVG 加入内嵌 CSS 后保存为 `path`。

## knowledge.json

记录 `schema_version`、`source_ref`、`extraction_id`、`status`、`knowledge_points`、`review_items`、`candidate_topics` 和 `references`。

- `status` 在内容提取阶段固定为 `pending_science_review`。
- `knowledge_points`：`id`、`title`、`summary`、`source_refs`、`diagram_ids`、`verification_status: unverified`。
- `review_items`：`id`、`source_quote`、`reason`、`source_refs`、`status: pending`。
- `candidate_topics`：`id`、`title`、`angle`、`knowledge_point_ids`、`source_refs`、`diagram_ids`。此处仅提供选题，不绑定平台。
- `references`：原文件确有提供的科学参考链接；无链接时使用空数组。

`source_refs` 引用 `text_blocks` 的块 ID，`diagram_ids` 引用图解 ID；必须能在同次提取结果中找到。`summary.md` 为人工阅读摘要，包含登记信息、知识范围、选题、依赖及待核查项。
