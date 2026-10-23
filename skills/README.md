# SKILL 目录

每个子目录对应一个独立 SKILL。`extract-content`、`review-science`、`toutiao-build` 和 `douyin-build` 已实现指令、输出约定及辅助脚本；其他目录使用 `.gitkeep` 保留，后续实现时添加 `SKILL.md` 及必要资源。

| 目录 | 计划职责 |
| --- | --- |
| `extract-content/` | 已实现：登记源版本，提取知识点、图解和讲解素材 |
| `review-science/` | 已实现：核查事实与来源，保存修订表述及选题构建范围 |
| `toutiao-build/` | 已实现：生成独立图文、封面与配图，记录版本并等待Approve |
| `toutiao-publish/` | 执行已审批构建的今日头条发布步骤 |
| `douyin-build/` | 已实现脚本、分镜与无声动画MP4；配音和最终成片审阅待接入 |
| `douyin-publish/` | 执行已审批构建的抖音发布步骤 |
| `site-build/` | 生成完整内容与衍生作品的站点构建 |

其他平台的 SKILL 按实际实现增加。审批状态由系统保存，所有发布操作必须经过服务端审批检查。

从 [extract-content/SKILL.md](extract-content/SKILL.md) 开始使用第一个 SKILL。当前 SKILL 保存在仓库中，可由代理读取执行；自动调用由后续工作流执行器接入。

提取后使用 [review-science/SKILL.md](review-science/SKILL.md)。查证由代理读取资料完成，辅助脚本负责格式、引用及哈希检查和产物生成。

审校后的选题可通过 [toutiao-build/SKILL.md](toutiao-build/SKILL.md) 制作图文，辅助脚本负责审校约束与版本检查、图解渲染和作品归档。

`toutiao-build` 当前为 **0.3.0**。制作前读取其[图文视觉规范](toutiao-build/references/visual-guide.md)，参考随SKILL保存的封面与连续场景SVG。该规范吸收了流星篇v005的视觉反馈；新构建记录所用规范和示例指纹。这里的SKILL为仓库内版本，工作流按名称引用；全局安装和自动执行尚未接入。

抖音使用 [douyin-build/SKILL.md](douyin-build/SKILL.md)，当前为 **0.2.0**。先读取[视频视觉规范](douyin-build/references/visual-guide.md)，参考其竖屏SVG。分镜确认继续后，按[动画构建约定](douyin-build/references/animation-contract.md)生成连续对象运动和动态字幕的MP4。当前本机配音受环境权限阻止，无声版等待音频；最终成片另需发布Approve。
