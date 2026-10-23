# 工作流设计

## 职责

- `skills/` 定义内容提取、核查、构建或发布的具体方法。
- `workflows/` 定义各平台的步骤、依赖和审批节点。
- `packages/workflow/` 执行步骤，保存运行状态，处理暂停、恢复与重试。
- `packages/platforms/` 提供实际平台操作，并返回发布结果。
- `packages/core/` 管理业务对象、版本关系和审批规则。

## 基本流程

导入 HTML → 选择平台与构建参数 → 提取与核查内容 → 生成构建 → 预览与修改 → 等待 Approve → 发布 → 保存发布记录。

同一源内容可启动多个平台工作流；同一平台可生成多个构建，各构建独立审批。某个平台或构建失败时，其他运行仍可推进。

## 审批与恢复

审批节点暂停自动推进。批准后，发布步骤检查审批对应的构建版本、目标平台与发布配置。修改后进入重新审批流程。

发布失败保留已生成的作品和有效审批记录。重试从失败步骤恢复，并先检查是否已在外部平台成功发布。

## 独立站

独立站工作流构建内容详情页、完整交互 HTML 和衍生作品关联，并经过预览、审批与发布。保存的源内容版本与网站公开版本分别记录。

## 当前状态

今日头条工作流已在 `workflows/toutiao.yaml` 定义，抖音工作流在 `workflows/douyin.yaml` 定义，均使用兼容YAML的JSON子集，供本地脚本以标准库读取。其他平台仍为占位；通用工作流执行器与发布接入尚待实现。

源登记、第一次内容提取与第一轮代理科学审校已完成。`review-science` 的辅助脚本已实现来源哈希、素材覆盖与引用检查，并生成各选题的可构建状态。

“流星体、流星、陨石”和“恒星、行星、卫星”已通过 `toutiao-build` 生成独立图文构建，各自保存版本及运行记录。“哪些算天体”的判断题继续等待具体教材依据。

本地脚本执行 verify_review → compose → export_assets → preview，记录 approve 为 waiting、publish 为 not_started。正文与图注由代理核对，脚本检查科学审校的哈希、范围和修改要求覆盖。发布函数和审批记录存储将在后续实现，当前没有外部平台写入。

## 抖音分阶段制作

`douyin-build` 当前执行 verify_review → write_script → design_storyboard → preview_storyboard，在 review_storyboard 等待编辑审阅。首版流星篇保存六镜头、60秒的时间规划、旁白、暂定SRT、原生SVG关键帧及无声HTML预演。

分镜确认继续后，produce_audio与animate可独立推进；render_video依赖animate，可先生成无声动画供审阅。最终顺序为音频与动画齐备 → 调整字幕和节奏 → review_video → approve → publish。分镜制作授权只允许进入制作阶段；最终成片、封面和发布配置齐备后，另执行发布Approve。

当前抖音流星篇v002已实现原生SVG对象动画及MP4编码。语音合成被运行环境权限阻止，produce_audio为blocked_environment；animate和render_video为completed，review_video为waiting_for_audio，approve与publish为not_started。音频和平台发布尚未接入。工作流保存阻塞原因，当前不会自动恢复或发布；后续修改生成新版本，审批绑定最终产物。


## 本项目的无声视频交付（2026-10-23）

新作品设置`delivery_target=silent_video`：produce_audio记录为not_required，animate与render_video完成后进入awaiting_video_review，review_video等待画面与字幕审阅；approve和publish仍独立。字幕按无声阅读节奏安排，播放器不提示等待配音。旧recipe未设置该字段时保留原行为，既有构建与指纹保持原样。
