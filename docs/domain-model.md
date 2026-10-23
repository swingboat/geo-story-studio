# 业务模型

## 源内容 Source

输入为 ELI5 skill 生成的 HTML，连同依赖资源保存。源内容拥有唯一 ID 和版本；新版本保留旧版本以便追溯。

当前源登记通过 `skills/extract-content/scripts/extract.py` 实现。教材目录中的输入保留，规范快照存放于 `storage/sources/<source-id>/<version>/index.html`；清单为同目录的 `manifest.json`。原文件的本地资源引用暂仅登记，远程字体等资源不下载，完整性状态记录在清单中。

同一源版本可拥有多次提取：`extractions/<extraction-id>/` 内保存 `content.json`、`knowledge.json`、`summary.md` 和图解。机械提取与知识整理分别记录，后者初始为待科学审校。输出格式见 `packages/core/sources/schemas/`。

## 科学审校 Science Review

每次审校绑定源版本、提取 ID、输入哈希及 SKILL 版本，保存于提取目录的 `reviews/<review-id>/`。`review.json` 记录原文定位、逐条判断、证据、图解处理要求和选题范围；辅助脚本生成阅读报告与 `reviewed-knowledge.json`。

证据充足的结论提供修订后的可用文本；证据不足的结论保留为 `unresolved`。脚本根据选题直接引用的结论及图解依赖派生 `ready_for_build` 或 `blocked`，各选题独立推进。图解修改要求随素材传递给构建步骤。

原始提取记录保留。当前第一轮为代理审校，教材出版社及版本尚缺；构建时使用选定范围内的审校文本。发布仍需要成品 Approve，完整 HTML 的公开版本需要处理其全部公开结论的审校问题。

## 构建 Build

构建是一份面向指定平台的作品。同一源内容在同一平台可创建多个构建，例如不同选题的短视频。每个构建可产生多个版本，每个版本记录源内容版本、平台、SKILL 版本、生成参数、预览和成品。

建议保存路径：`storage/sources/<source-id>/<version>/` 与 `storage/builds/<build-id>/<version>/`。构建目录可包含 `manifest.json`、`preview/` 和 `outputs/`；具体文件格式在实现时确定。

今日头条构建已实现 `recipe.json`、`manifest.json`、`workflow-run.json`、预览及图文产物，格式见 `packages/core/builds/schemas/`。构建会重算审校产物，拒绝未通过审校的选题及超出选题范围的引用，并保留每项图解修改的落实说明。

今日头条构建状态为 `awaiting_approval`。`approval_subject_sha256` 绑定作品版本、平台、源与审校引用、SKILL/工作流版本及全部产物哈希。修改后的作品生成新版本；发布审批记录与产物分别保存。

抖音首阶段的 `stage=storyboard`，状态为 `awaiting_storyboard_review`。构建包含脚本、暂定字幕、关键帧和预演；`review_subject_sha256` 绑定本阶段上下文及产物。`publication_approval_eligible=false` 表示尚无可发布成片；分镜审阅不能授予发布资格。成片制作后保存新版本，再建立最终发布审批对象。字段见 `skills/douyin-build/references/output-contract.md`，该阶段尚未接入通用构建JSON Schema。

后续无声动画为 `stage=silent_animation`、`status=awaiting_audio`，保存原分镜清单引用、制作授权、对象运动轨道、动态字幕、独立封面草稿及MP4。其审阅指纹继续与发布审批分离，发布资格保持false。音频失败不影响独立的动画制作，但音频对齐和最终成片审阅仍未完成。具体字段见 `skills/douyin-build/references/animation-contract.md`。

2026-10-23起，本项目的新作品使用`delivery_target=silent_video`，以无声视频作为交付目标。动画构建记录`status=awaiting_video_review`、`audio_status=not_required`及`timing_status=planned_for_silent_reading`；画面与字幕审阅记录独立保存，最终发布批准继续绑定具体产物。未指定该字段的历史recipe保留原状态语义，旧构建不改写。


## 上传素材 Upload Assets

抖音作品的横版4:3封面、竖版3:4封面、标题和简介，与脚本、分镜和视频一同保存在`storage/builds/<build-id>/<version>/outputs/`。一次SKILL交付使用同一个构建目录；预览位于同目录下的`preview/`。新构建的清单统一记录产物；后补尚不存在的上传素材时使用根目录下的`upload-manifest.json`记录附件指纹及对应构建。修改已有成品仍使用新构建版本，动画或成片阶段把适用的封面与文案一起带入新版本。详见[上传素材约定](../skills/douyin-build/references/upload-package-contract.md)。

## 工作流运行 Workflow Run

每次运行引用一个平台工作流定义及其版本，记录输入、各步骤状态与产物关联。各平台运行独立推进。一次运行可关联多个构建，各构建分别审批和发布。

## 审批 Approval

审批绑定具体构建版本、目标平台和发布配置，并记录审批人、时间和决定。成品、标题、封面或发布配置修改后需重新审批。发布资格由服务端检查。

## 发布记录 Publication

记录构建版本、平台、发布状态、时间、外部标识或链接以及失败信息。发布重试前检查外部结果，避免重复发布。

## 存储边界

原始文件、预览与成品保存在文件存储中。当前已实现的源登记暂使用 `storage/state/source-registry.json`，通过文件锁和原子替换保存。后续对象关联、工作流状态、审批和发布记录将迁入数据库，具体技术尚未确定。

独立站也是发布目标，关联完整源内容版本和已公开的衍生作品。
