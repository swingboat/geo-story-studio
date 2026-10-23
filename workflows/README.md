# 平台工作流

每个平台保留一份独立定义：`toutiao.yaml`、`douyin.yaml`、`youtube.yaml`、`x.yaml` 和 `site.yaml`。

`toutiao.yaml` 已定义本地辅助工作流，使用兼容YAML的JSON格式。`toutiao-build/scripts/build.py` 检查其审批要求，执行构建部分，并为每个构建保存独立的 `workflow-run.json`。执行停在 Approve，平台发布尚未接入。

其余文件仍为注释占位。通用执行引擎、审批记录持久化与外部发布将在后续实现。
