---
name: toutiao-build
description: 将已完成科学审校的选题制作成今日头条图文构建，生成正文、封面、PNG/SVG配图、参考来源和本地预览，并停在等待发布Approve的状态。用于平台图文制作阶段。
metadata:
  version: "0.3.0"
---

# 今日头条图文构建

输入为 review-science 生成的 reviewed-knowledge.json 和选题 ID。先阅读 [构建约定](references/build-contract.md) 与 [图文视觉规范](references/visual-guide.md)，查看其中的封面和场景插图示例，再编写作品。

## 编写作品

选择 ready_for_build 的选题，按其中的 statements、scope、constraints 和 required_changes 编写 recipe.json。标题、段落、图注和替代文本均保持在已有证据范围内；新增科学结论先补充审校。正文中的事实段落关联对应 claim_ids。

每个构建独立设置 build_id 和 version。为同一源文件生成不同文章时使用不同 build_id，修订同一作品时递增版本。

先确定主要读者、具体问题和材料能回答的范围。用简短回应引入，再解释必要概念与过程；删重复时保留条件和推理。每篇独立回答一个问题，篇幅与图数按理解需要决定。列出实际用到的科学来源；标题和封面中的承诺逐项对照正文。

## 图解与核对

当前项目以流星篇 v005 的视觉反馈为制作基准：封面使用清楚主体与短标题，过程图采用有空间层次的连续场景，结合材质、光迹与条件路径组织内容。新题材沿用信息层级、色彩关系和精细程度，按知识本身选择场景或对照结构。示例SVG与缩略图随本SKILL保存，可复制到新构建的素材目录编辑；具体图源和使用范围见视觉规范。

新制作的封面与场景图使用自制SVG，通过cover.asset_id和figures的kind=asset接入构建。single／comparison布局可用于已有配图复用或适合简洁对照的任务，按本次视觉目标选择。

为封面、实景首图、过程图和对照图分别写明用途。封面突出主体、少量文字，检查缩略图及居中裁切；正文图解释过程与关系，重复的图可省略。地理科普面向普通读者时，用熟悉的现象进入，教材编号与课件式标题按需保留。

使用选题允许的源SVG，或依据这些图解重新绘制本地SVG，在 recipe.json 的 change_resolutions 中逐项说明 required_changes 的落实位置。脚本支持单图、三行对比图和本地素材。示意图注明属性，机制、波段与幸存条件在正文、图注和替代文本中一致。

摄影回查原始图源、拍摄说明与使用条件，不能把搜索结果或其他作者的配图当授权。逐项记录署名、使用依据、处理方式、依赖素材和哈希；生成画面不能冒充观测摄影。素材使用权、实质贡献和平台原创声明资格分别判断。详细字段见构建约定。

在仓库根目录运行：

```bash
python3 skills/toutiao-build/scripts/build.py \
  --material "storage/sources/<source-id>/<version>/extractions/<extraction-id>/reviews/<review-id>/reviewed-knowledge.json" \
  --recipe "<recipe.json路径>"
```

脚本使用 Python 标准库与已安装的 rsvg-convert 导出PNG，构建阶段只读取本地素材。它重算审校产物，检查版本、素材哈希、选题状态和事实引用，输出独立图文构建及文件指纹；所用规范与示例资源的哈希一并记录。已有构建内容不覆盖，SKILL或内容变化后使用新版本。

阅读成品全文，检查PNG、封面裁切及移动端预览；预览的“封面与配图”页单独展示题图与图源。科学准确和初学者易懂分别核对，没有真实试读就记录代理自查。脚本的结构检查不替代事实、权利与视觉核对。

构建状态固定为 awaiting_approval，工作流停在 Approve。用户对视觉效果的肯定只作为设计反馈；发布另需具体构建的Approve。用户暂缓发布时继续保留作品，等待其明确恢复发布安排。此阶段保存作品及发布配置，不调用平台发布操作。
