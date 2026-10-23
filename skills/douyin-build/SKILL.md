---
name: douyin-build
description: 将已科学审校的选题制作成抖音脚本、竖屏分镜及原生SVG动画MP4审阅版，保存独立构建版本。用于脚本、分镜和无声动画制作；配音与平台发布另行接入。
metadata:
  version: "0.2.0"
---

# 抖音视频构建

## 当前项目交付目标

用户于2026-10-23明确：本项目只制作无声视频。连续MP4、可读且按讲解节奏切换的字幕、画面核对、封面和发布文案齐备后，即达到视频制作交付目标；不把没有配音记为缺项，不反复要求用户选择配音服务。旁白文本保留为字幕与叙事底稿，字幕按无声阅读节奏审阅。工具与旧版归档中的`awaiting_audio`、`waiting_for_audio`、`estimated_pending_voice`是历史实现字段，不能据此把已完成的无声视频报告为未制作完成。视频制作完成与用户审阅、发布批准分别记录。

当前实现脚本、分镜及无声动画MP4。输入为 `review-science` 的 `reviewed-knowledge.json`、选题ID及recipe。先读[输出约定](references/output-contract.md)；制作视觉时读[视频视觉规范](references/visual-guide.md)。从分镜继续制作时读[动画构建约定](references/animation-contract.md)。

同一次交付集中保存在`storage/builds/<build-id>/<version>/`，成品放`outputs/`，预览放`preview/`。每条抖音作品还需提供横版4:3、竖版3:4两张封面；标题、简介、30个不重复的相关关键词和话题统一保存为`outputs/发布文案.txt`，分四栏方便复制，关键词用英文逗号分隔成一行。所有交付与脚本、分镜和视频放在同一个`outputs/`，详见[上传素材约定](references/upload-package-contract.md)。用户要求时可在分镜阶段先制作这些素材。

## 脚本与分镜

选择ready_for_build的选题，从其允许结论组织口语脚本。每个镜头记录旁白、画面重点、计划运动、字幕草案、时长和claim_ids。画内文字、箭头、字幕、旁白都保留审校条件；新增结论先补审校。

围绕一个具体问题安排镜头，结尾完整回应。按实际材料分配时长；首版可用9:16、约45—60秒，参数属于项目选择。时间按无声观看和字幕阅读节奏安排，检查每条字幕是否留足阅读时间。

每个镜头保存本地SVG和哈希；源图关联与change_resolutions落实审校要求。为同源的不同视频使用不同build_id；修订同一作品递增version。科学输入引用源与审校记录，图文作品只提供视觉参考。

## 制作与审阅

使用有层次的场景插图，按镜头重排主体、文字与空间，字幕区留白。查看导出的关键帧原尺寸、375px宽预览和总览图，核对边界、路径、字号及手机可读性。图片来源、使用依据和实际制作人进入素材记录。

```bash
python3 skills/douyin-build/scripts/build.py \
  --material "storage/sources/<source-id>/<version>/extractions/<extraction-id>/reviews/<review-id>/reviewed-knowledge.json" \
  --recipe "<recipe.json路径>"
```

脚本使用Python标准库和本机rsvg-convert，重算科学审校结果，验证引用、时间、素材及工作流，生成脚本、分镜、SRT、关键帧、无声HTML预演和归档。查看脚本与分镜后提出修改，或进入连续动画制作。

分镜阶段状态为awaiting_storyboard_review；用户要求继续后记录对应分镜指纹及制作授权，进入动画。将主体、条件分支与概念标签分层，用关键帧轨道表达运动；字幕随时间切换。通过animate.py生成1080×1920 H.264 MP4、独立封面草稿和播放预览，核对实际编码视频中的早晚帧。

本项目无声交付不运行配音尝试，也不添加静音音轨冒充配音。新作品动画recipe设置`delivery_target=silent_video`，生成器记录`awaiting_video_review`、`produce_audio=not_required`及`planned_for_silent_reading`，播放器按无声交付显示。编码后检查实际音轨数为0、画面和字幕可读。未设置新字段的旧recipe仍保留历史行为，统计时以实际无声产物及核对记录判断完成度。旧版构建与指纹保持原样，修订视频或预览页时创建新版本。分镜制作授权与最终发布Approve分别记录，用户暂缓发布的安排继续保留。
