---
name: extract-content
description: 从 ELI5 HTML 学习材料登记源版本，提取带原文定位的知识素材、SVG 图解、交互和候选选题，供平台构建使用。用于项目的 HTML 内容提取阶段。
metadata:
  version: "0.1.0"
---

# 提取 HTML 内容

输入是用户指定的 HTML 文件。输出是源登记、文件快照、机械提取结果及整理后的知识素材。先阅读 [输出约定](references/output-contract.md)。

## 登记与机械提取

在仓库根目录运行（将参数替换为实际输入）：

```bash
python3 skills/extract-content/scripts/extract.py \
  --source "storage/sources/教材目录/文件.html" \
  --source-id "src-example" \
  --book "教材名称" \
  --extraction-id "extract-001"
```

脚本仅使用 Python 标准库。它保留输入文件，登记内容哈希和版本，建立快照并提取标题、正文块、SVG 和按钮。重复运行复用已有结果；输入改变产生新源版本。需要重新提取时使用新的 extraction ID。

远程资源仅登记依赖，局部文件依赖标记为未复制。检查依赖状态后再判断快照是否能完整展示；独立 SVG 包含原始内嵌样式并使用系统字体回退。

## 整理知识素材

阅读输出的 `content.json` 和原 HTML，在同一个提取目录创建 `knowledge.json` 与 `summary.md`：

- 知识点、例子和候选选题引用正文块或图解 ID，并保留教材语境。
- 源文件中的判断属于原文表述，核查前设为 `unverified`。将概括过度、类比边界、术语和无出处的数据列入核查项。
- 确有原文链接时记录为来源候选。字体链接和文件哈希不作为科学证据。
- 图解与交互分别登记；按钮答案可提取为文稿素材，交互行为需要在网站或视频制作阶段适配。
- 记录提取所用 SKILL 的版本；此阶段的知识素材状态为 `pending_science_review`。

用 `source_refs` 和 `diagram_ids` 关联素材，检查引用能在 `content.json` 中找到。核查工作交给后续科学审校步骤；本阶段的完成状态不授予发布批准。
