# 动画构建约定（1.0）

## 输入与命令

从已确认继续制作的分镜生成新版本，保留原版目录：

```bash
python3 skills/douyin-build/scripts/animate.py --recipe <animation-recipe.json>
```

需要Python 3标准库、rsvg-convert、FFmpeg/ffprobe，以及中文系统字体。直接渲染原生SVG对象；不依赖浏览器或外部图像服务。

recipe字段：schema_version=1.0、mode=silent_animation、version、storyboard_ref、storyboard_review、scenes、audio_status、cover、publication_draft。

2026-10-23新增可选`delivery_target=silent_video`用于本项目正式无声交付。新作品应设置该字段；生成状态为`awaiting_video_review`，`produce_audio=not_required`，字幕状态为`planned_for_silent_reading`，播放器不提示等待配音。未设置的旧recipe保留历史行为；旧构建不改写。

- storyboard_ref：path为分镜构建目录，manifest_sha256绑定原清单。构建重验原版全部产物及科学审校素材。
- storyboard_review：decision=proceed_with_production、reviewer、user_instruction、note，记录实际用户授权。其范围仅为继续制作。
- 每项scenes：scene_id、artwork（path、sha256、adaptation）、tracks。保留原分镜的科学范围，新增画面条件由代理核对。
- artwork：自包含1080×1920 SVG。为运动对象设置唯一id，保留id=live-caption的空组，替换原静态字幕；不能残留重复字幕。
- track：target（SVG id）、property、keyframes、可选easing。property支持opacity、translate、scale、rotate、reveal；关键帧时间为镜头内秒数，严格递增。value分别为[透明度]、[x,y]、[倍率,中心x,中心y]、[角度,中心x,中心y]、[0至1]。reveal另有bounds=[x,y,宽,高]，按自上而下裁切显示。easing为smooth或linear。
- cover：path、sha256、status，独立SVG封面；publication_draft保存待审文案与标签。
- audio_status：如实记录是否有音频、尝试的引擎和阻塞原因。当前只支持无声动画，不能用空文件或静音音轨冒充配音。

## 产物与复用

保存到 `storage/builds/<build-id>/<新version>/`。输出animation-draft.mp4、cover.svg/png、动态字幕使用的storyboard.json、subtitles-draft.srt、素材说明、音频状态、视频探测信息、审阅帧及HTML播放器。

将仍适用的横版4:3、竖版3:4封面及标题、简介一起带入新版本的`outputs/`，供用户在同一目录取得视频与上传素材。具体文件见[上传素材约定](upload-package-contract.md)。

MP4使用1080×1920、计划fps、H.264、yuv420p与faststart，字幕烧录进画面。检查实际分辨率、帧数和时长，从编码视频中导出每镜早晚帧确认运动、字幕、科学条件及遮挡；记录真实检查范围。播放默认暂停，提供完整旁白与镜头跳转。

输入、SKILL资源及工作流与产物均记录指纹。相同输入重复运行只检查并复用；修改输入后使用新版本。manifest的stage=silent_animation、status=awaiting_audio、publication_approval_eligible=false。review_subject_sha256只绑定动画审阅对象，不产生发布批准。

## 配音与后续

动画可在配音阻塞时独立制作，工作流仍记录produce_audio为blocked_environment；review_video等待音频。字幕时间仍为estimated_pending_voice，不能宣称已经按音频对齐。获得音频后需要新版本、实际时长重排、字幕对齐、成片审阅及最终发布Approve。
