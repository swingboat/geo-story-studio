---
name: review-science
description: 审校从学习 HTML 提取的知识素材，逐条查证科学表述、数字、类比和图注，保存证据及修订文本，并判断选题是否可进入平台构建。用于内容提取后的科学审校阶段。
metadata:
  version: "0.1.0"
---

# 科学审校

输入为一次 extract-content 提取的 content.json、knowledge.json 和对应 HTML 快照。先阅读 [输出约定](references/output-contract.md)。

## 查证与判断

覆盖全部知识点、初始待核查项及图解的文字/图示含义。把数字、机制、分类规则等拆成可单独核实的结论。检查原始 HTML，留意提取结果未覆盖的图注、颜色图例和判断卡片。

为每项结论读取权威来源的正文，记录支持该结论的具体段落及访问日期。优先选择科研机构、大学、原始研究与相应教材；搜索摘要用于定位资料。一个直接且清楚的权威来源可支持常识性结论；资料冲突或技术细节复杂时增加交叉核对。用自己的话简述证据，避免复制整篇资料。

通用科学事实与具体教材的考试判定分别记录适用范围。教材出版社、版次或原文缺失时，将依赖它的结论保留为 unresolved，并继续审校其他内容。权威机构的简化科普表述同样需要检查范围和上下文。

每项结论使用 supported、revise、qualify 或 unresolved。前三类必须附证据及可用于创作的 recommended_text；unresolved 的 recommended_text 为 null。修改机制和术语时同步检查图注、替代文本、箭头、颜色图例及数字。

## 整理供构建使用的素材

在本次提取的 reviews/<review-id>/ 创建 review.json。审校绑定源版本、提取 ID、输入文件哈希和本 SKILL 版本。记录实际执行者；代理审校不标记为人工审校。

为每个候选选题列出本次允许使用的结论及适用范围。可以缩小选题范围，保留未解决条目；覆盖该选题涉及的知识点并说明省略内容。下游仅使用审校后的表述。图解修改要求随选题传递到平台构建。

在仓库根目录运行：

```bash
python3 skills/review-science/scripts/finalize.py \
  --extraction "storage/sources/<source-id>/<version>/extractions/<extraction-id>" \
  --review "storage/sources/<source-id>/<version>/extractions/<extraction-id>/reviews/<review-id>/review.json"
```

脚本检查版本、哈希、覆盖范围和引用，派生各选题的构建状态并生成 review.md、reviewed-knowledge.json。它不访问网页，也不判断证据语义；查证由执行 SKILL 的代理完成。输出已存在且内容不同则停止，修订应使用新的 review ID。

科学审校完成后仍需平台构建、成品核对和发布 Approve。源 HTML 和原提取结果保持可追溯。
