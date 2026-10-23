# 地理故事工坊（Geo Story Studio）

以 ELI5 skill 生成的 HTML 为输入，为不同平台生成可审批的图文、视频等作品，并通过独立站完整呈现内容。

## 视频交付范围

用户于2026-10-23确认：**本项目只制作无声视频**。连续MP4、可读字幕、画面核对、封面及发布文案齐备，即达到视频制作目标。当前13条视频均已完成无声视频制作，配音不属于待办。用户审阅和发布批准另行记录。下文及既有归档中的“等待配音”、`awaiting_audio`等为历史记录，不再作为无声交付的阻塞；旧版产物与指纹保留。

## 内容系列

**高中地理必修一**：计划创建的抖音学习合集，简介、1080×1080方形封面和20个关键词已准备。查看[合集文案](storage/builds/douyin-collection-geography-b1/v002/outputs/collection-copy.txt)、[方形封面](storage/builds/douyin-collection-geography-b1/v002/outputs/cover-square-1080.png)及[完整素材包](storage/builds/douyin-collection-geography-b1/v002/outputs/collection-package.zip)。

**认识宇宙**：用户已确认的首个内容系列。最新完成《哪些算天体？先分清对象和状态》：60秒、6镜头、1080×1920、30fps连续无声动画，三种比例封面、统一发布文案及30个关键词齐备。查看[系列记录](docs/content-series.md)、[最新视频](storage/builds/douyin-celestial-judgement/v003/preview/watch.html)和[完整交付包](storage/builds/douyin-celestial-judgement/v003/outputs/complete-delivery.zip)。此前完成[航天器任务篇](storage/builds/douyin-spacecraft-missions/v002/preview/watch.html)、[分类篇](storage/builds/douyin-star-planet-moon/v003/preview/watch.html)和[月光篇](storage/builds/douyin-moonlight-origin/v002/preview/watch.html)。

用户提供的教材目录为`/Users/huyin/Desktop/Niki/教材/地理`，后续优先直接读取本地教材与图册。文件清单、已核对页码及版本说明见[本地教材资料库](docs/material-library.md)。天体辨析篇采用`extract-003/review-011/topic-006`：教材一般讨论天然天体，人造卫星另标补充知识；完整八卡考试判断仍保留待核实。

## 项目结构

```text
apps/
  studio/          管理端：导入、构建、预览、审批、发布
  site/            独立站：交互内容与衍生作品
packages/
  core/            源内容、构建、审批和发布的业务规则
  workflow/        工作流执行、暂停、恢复和重试
  platforms/       今日头条、抖音、YouTube、X 和独立站接入
skills/            内容提取、科学核查、平台构建与发布 SKILL
workflows/         每个平台独立的工作流定义
storage/
  sources/         原始 HTML、资源和源内容版本
  builds/          构建版本、预览和成品
  state/           本地数据库等运行状态
tests/             源内容、工作流、审批和发布的自动化测试
docs/             业务模型、工作流设计与平台指南
```

## 当前状态

已完成第一个 HTML 的源登记、内容提取、科学审校、两个独立的今日头条图文构建，以及十三条抖音作品的脚本、分镜和无声动画审阅版，实现 `extract-content`、`review-science`、`toutiao-build` 和 `douyin-build` SKILL。头条流星篇当前为`v005`，恒星篇为`v002`，均等待 Approve。抖音天体辨析篇当前为`douyin-celestial-judgement/v003`，已据本地人教教材及独立补充定义核对成片；抖音航天器任务篇当前为`douyin-spacecraft-missions/v002`，采用`delivery_target=silent_video`，无需音频步骤，已完成成片与素材核对。抖音分类篇当前为`douyin-star-planet-moon/v003`，月光篇为`douyin-moonlight-origin/v002`，两条均已从分镜推进到连续无声动画。其余动画：流星篇、星云篇、星际介质篇、日地辐射传播篇、照射角度篇和大气保温篇为`v002`，太阳能源篇为`v004`，宇宙地址篇为交付30个关键词的`v005`，大气受热篇为`v003`。十三条均已完成本项目要求的无声视频制作，用户审阅与发布批准另行记录，旧版分镜与动画保留。

当前发布安排（2026-10-16）：等待用户创建好新的今日头条账号并明确恢复发布。对视觉效果的肯定仅作为设计反馈，具体作品仍需发布Approve。

首轮审校记录覆盖29项表述与16张图解，保存了18份官方资料的来源信息。三个选题可在限定范围内进入构建，一个涉及教材判定的选题等待依据。月光篇另关联增量审校`review-002`，补充NASA Moonlight来源并缩小月光子选题范围；星云篇关联`review-003`，补充恒星形成过程与环状星云反例，星际介质篇关联`review-004`，补充恒星之间的气体尘埃、分布不均与稀薄概念的依据，太阳能源篇关联`review-005`，补充核聚变、内部辐射与对流传能、太阳辐射到达地球的依据。日地辐射传播篇关联`review-006`，补充电磁波真空传播和地表吸收、反射及大气吸收的依据。照射角度篇关联`review-007`，新增控制相同光束与时长的几何投影比较，并补充实际气温的其他影响条件。大气受热篇关联`review-008`，新增地表向大气传能的三类路径，并限定直接吸收、条件性对流与相变吸放热的范围。大气保温篇关联`review-009`，新增各向热红外发射、大气逆辐射及限定地表状态的净长波比较，并保留整体能量收支边界。航天器任务篇在派生提取`extract-002`中关联`review-010/topic-005`，补充中国载人航天工程网和国家航天局的空间站、北斗及嫦娥五号任务依据；原HTML与`extract-001`保留。继承的未解决教材判定保持原状态。

管理端、独立站和平台发布尚待实现，应用技术栈未选定。今日头条与抖音已定义独立本地工作流，其余平台工作流和 SKILL 保留骨架。目录中的 `.gitkeep` 用于保留空目录。

## 源登记与内容提取

机械提取脚本使用 Python 3 标准库，可从仓库根目录运行：

```bash
python3 skills/extract-content/scripts/extract.py \
  --source "storage/sources/必修第一册/第1章·宇宙中的地球-第1节·地球的宇宙环境-天体.html" \
  --source-id src-geo-b1-c1-s1-celestial-bodies \
  --book "必修第一册" \
  --extraction-id extract-001
```

源登记暂存于 `storage/state/source-registry.json`。输入文件保留在教材目录，版本快照及提取结果存放于 `storage/sources/<source-id>/<version>/`。重复运行复用已有结果，内容变化产生新源版本。知识整理步骤见 [extract-content SKILL](skills/extract-content/SKILL.md)。

第一份结果：[天体提取摘要](storage/sources/src-geo-b1-c1-s1-celestial-bodies/v001/extractions/extract-001/summary.md)。

运行现有自动化测试（源登记、科学审校、今日头条构建；尚未覆盖抖音）：

```bash
python3 -m unittest discover -s tests -v
```

## 科学审校

由代理按 [review-science SKILL](skills/review-science/SKILL.md) 读取资料、逐条查证并填写 `review.json`。结构检查脚本不访问网页；它验证输入哈希、覆盖范围和引用，并生成报告与供构建使用的知识素材：

```bash
extraction_dir="storage/sources/src-geo-b1-c1-s1-celestial-bodies/v001/extractions/extract-001"
python3 skills/review-science/scripts/finalize.py \
  --extraction "$extraction_dir" \
  --review "$extraction_dir/reviews/review-001/review.json"
```

第一份结果：[科学审校报告](storage/sources/src-geo-b1-c1-s1-celestial-bodies/v001/extractions/extract-001/reviews/review-001/review.md)、[审校后的构建素材](storage/sources/src-geo-b1-c1-s1-celestial-bodies/v001/extractions/extract-001/reviews/review-001/reviewed-knowledge.json)。

构建步骤将读取选定选题的允许表述、适用范围和图解修改要求。审校后的素材仍需生成成品、核对并执行发布 Approve。完整站点内容还需处理其中未解决的结论。

## 今日头条图文构建

由代理按 [toutiao-build SKILL](skills/toutiao-build/SKILL.md) 编写作品 recipe；构建脚本重算并验证审校结果，生成正文、封面、PNG/SVG配图、参考资料、图文包和本地预览。运行需要 Python 3、rsvg-convert 和可显示中文的系统字体。

继续制作时，先将现有 `v005/recipe.json` 另存为 `storage/state/build-recipes/toutiao-meteor-journey-v006.json`，把其中的version改为v006，再修改作品并运行：

```bash
material_path="storage/sources/src-geo-b1-c1-s1-celestial-bodies/v001/extractions/extract-001/reviews/review-001/reviewed-knowledge.json"
python3 skills/toutiao-build/scripts/build.py \
  --material "$material_path" \
  --recipe storage/state/build-recipes/toutiao-meteor-journey-v006.json
```

当前 `toutiao-build` 为0.3.0，制作时读取[图文视觉规范](skills/toutiao-build/references/visual-guide.md)，使用随SKILL保存的可编辑示例。现有v005为0.2.0生成的视觉参考。相同源、审校、recipe、SKILL及工作流输入可复用已有构建；版本变化则生成新构建。构建记录包含规范、示例及产物的文件指纹，工作流停在 Approve，发布接入尚未实现。

| 构建 | 正文汉字数 | 审阅 |
| --- | --- | --- |
| 流星体、流星、陨石 | 514 | [正文](storage/builds/toutiao-meteor-journey/v005/preview/index.html) · [封面与配图](storage/builds/toutiao-meteor-journey/v005/preview/visuals.html) |
| 恒星、行星、卫星 | 952 | [预览](storage/builds/toutiao-star-planet-moon/v002/preview/index.html) |

流星篇单独设计列表封面，正文采用一张实景照片与一张条件分支过程图；恒星篇保留原有4张配图与1张封面。构建支持原图重排、自制SVG和本地摄影，`media.json` 与 `visual-plan.json` 记录图源、使用依据、用途和处理。预览可查看封面裁切示例及素材说明，图文包位于同版本的 `outputs/`。图片尺寸和篇幅为本项目编辑选择。

## 抖音脚本与分镜

按 [douyin-build SKILL](skills/douyin-build/SKILL.md) 从审校后的选题编写口语旁白和分镜，独立记录视频构建与工作流。当前版本0.2.0已实现脚本与无声动画，需要Python 3、rsvg-convert及中文系统字体，动画编码另需FFmpeg/ffprobe。

此前完成的《大气怎样给地面保温？》为`douyin-atmosphere-insulation/v002`无声动画审阅版：60秒、6镜头、167字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-atmosphere-insulation/v002/preview/watch.html)、[MP4](storage/builds/douyin-atmosphere-insulation/v002/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-atmosphere-insulation/v002/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-atmosphere-insulation/v002/outputs/complete-delivery.zip)。交付方形1080×1080、横版4:3、竖版3:4封面。标题、简介、30个英文逗号分隔的关键词和话题集中在一个文件。吸收发射分开，不画成镜面折返；净长波比较固定地表温度和性质；地球整体不表示现实收支恒等。已检查六镜实际编码前后帧，当前等待配音，字幕时间暂定。

上一条《地面怎样把大气暖起来？》为`douyin-atmosphere-heating/v003`无声动画审阅版：60秒、6镜头、172字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-atmosphere-heating/v003/preview/watch.html)、[MP4](storage/builds/douyin-atmosphere-heating/v003/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-atmosphere-heating/v003/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-atmosphere-heating/v003/outputs/complete-delivery.zip)。交付方形1080×1080、横版4:3、竖版3:4封面；标题、简介、30个英文逗号分隔的关键词和话题集中在一个文件。`v003`移除第五镜穿过凝结说明文字的辅助箭头，保留水汽符号上移、凝结水滴及放热动画。三条路径只作定性拆解，不表示能量比例或完整收支。当前等待配音，字幕时间暂定。

2026-10-22复查本机macOS say / Tingting仍只输出4096字节、0秒音频，不能合成有声成片。上一条与本条均等待可用中文配音服务或用户音频；环境记录保存在`storage/state/reviews/audio-environment/2026-10-22/audio-status.json`。

上一条《为什么同样晒太阳，有的地方更热？》为`douyin-sun-angle/v002`无声动画审阅版：60秒、6镜头、179字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-sun-angle/v002/preview/watch.html)、[MP4](storage/builds/douyin-sun-angle/v002/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-sun-angle/v002/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-sun-angle/v002/outputs/complete-delivery.zip)。方形1080×1080、横版4:3、竖版3:4封面、脚本、旁白与视频集中在该版本`outputs/`。标题、简介、30个英文逗号分隔的关键词和话题合并在一个文件。当前等待配音，字幕按规划时间切换。几何图保留同截面光束与相同照射时长，单位面积接收能量不等于实际气温。

上一条《阳光为什么能穿过太空，温暖地球？》为`douyin-sunlight-through-space/v002`无声动画审阅版：60秒、6镜头、174字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-sunlight-through-space/v002/preview/watch.html)、[MP4](storage/builds/douyin-sunlight-through-space/v002/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-sunlight-through-space/v002/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-sunlight-through-space/v002/outputs/complete-delivery.zip)。方形1080×1080、横版4:3、竖版3:4封面、旁白、脚本与视频集中在该版本`outputs/`。标题、简介、30个英文逗号分隔的关键词与话题合并在一个文案文件。当前等待配音，字幕按规划时间切换。真空框只示传播能力，分支箭头不代表能量占比。

上一条《太阳为什么能发光发热？》为`douyin-sun-energy/v004`无声动画审阅版：60秒、6镜头、168字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-sun-energy/v004/preview/watch.html)、[MP4](storage/builds/douyin-sun-energy/v004/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-sun-energy/v004/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-sun-energy/v004/outputs/complete-delivery.zip)。方形1080×1080、横版4:3、竖版3:4封面、旁白、脚本与视频集中在该版本`outputs/`。标题、简介、30个英文逗号分隔的关键词与话题放在同一文案文件。当前等待配音，字幕按规划时间切换。反应图只示净结果，剖面、路径与速度均为示意。

上一条《太空里真的空无一物吗？》为`douyin-empty-space/v002`无声动画审阅版：60秒、6镜头、186字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-empty-space/v002/preview/watch.html)、[MP4](storage/builds/douyin-empty-space/v002/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-empty-space/v002/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-empty-space/v002/outputs/complete-delivery.zip)。方形1080×1080、横版4:3、竖版3:4封面与视频集中在该版本`outputs/`。关键词30个，用英文逗号分隔成一行；当前等待配音，字幕按规划时间切换。颗粒符号、放大镜与空白框均为概念示意，不表示真实密度或观测画面。

上一条《星云都是“恒星的摇篮”吗？》为`douyin-nebula-nursery/v002`无声动画审阅版：60秒、6镜头、200字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-nebula-nursery/v002/preview/watch.html)、[MP4](storage/builds/douyin-nebula-nursery/v002/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-nebula-nursery/v002/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-nebula-nursery/v002/outputs/complete-delivery.zip)。方形1080×1080、横版4:3、竖版3:4封面与视频集中在该版本`outputs/`。标题、简介、30个逗号分隔的关键词及话题放在同一个`发布文案.txt`中。当前等待配音，字幕按规划时间切换。

上一条《我们在宇宙中的什么位置？》为`douyin-cosmic-address/v005`无声动画审阅版：60秒、6镜头、217字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-cosmic-address/v005/preview/index.html)、[MP4](storage/builds/douyin-cosmic-address/v005/outputs/animation-draft.mp4)、[上传文案](storage/builds/douyin-cosmic-address/v005/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-cosmic-address/v005/outputs/complete-delivery.zip)。方形1080×1080、横版4:3、竖版3:4封面、品牌字标、标题、简介及30个关键词一同保存在该版本`outputs/`中。当前等待配音，字幕按规划时间切换。

《月亮那么亮，它的光从哪里来？》现为`douyin-moonlight-origin/v002`连续无声动画：40秒、5镜头、136字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-moonlight-origin/v002/preview/watch.html)、[MP4](storage/builds/douyin-moonlight-origin/v002/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-moonlight-origin/v002/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-moonlight-origin/v002/outputs/complete-delivery.zip)。沿用`review-002/topic-003`与原旁白，依次展开太阳光到月面、部分反射光到观察者的光路；另演示月球绕地球的示意轨道。横版4:3、竖版3:4及方形封面与30关键词文案齐备。等待配音，`v001`分镜保留。

《恒星、行星、卫星怎么分？》现为`douyin-star-planet-moon/v003`连续无声动画：60秒、6镜头、203字旁白、1080×1920、30fps。查看[动画预览](storage/builds/douyin-star-planet-moon/v003/preview/watch.html)、[MP4](storage/builds/douyin-star-planet-moon/v003/outputs/animation-draft.mp4)、[统一发布文案](storage/builds/douyin-star-planet-moon/v003/outputs/发布文案.txt)及[完整交付包](storage/builds/douyin-star-planet-moon/v003/outputs/complete-delivery.zip)。沿用`review-001/topic-003`与原旁白，太阳核心分层呈现，地球和月球绕转后再展开光路；结尾按规划时间揭示测验答案。横版4:3、竖版3:4及方形封面与30关键词文案齐备。等待配音，`v001/v002`分镜保留。

同一次SKILL交付统一保存在作品的构建版本目录中。标题、简介、30个关键词和话题统一放在`outputs/发布文案.txt`，按四栏方便复制，关键词用英文逗号分隔成一行。当前作品查看[发布文案](storage/builds/douyin-sun-angle/v002/outputs/发布文案.txt)和[上传素材包](storage/builds/douyin-sun-angle/v002/outputs/upload-package.zip)，见[上传素材约定](skills/douyin-build/references/upload-package-contract.md)。

`v002`将封面左上角升级为“地球＋书本＋轨道”的账号字标，搭配“工坊”折角印记。查看[字标预览](storage/builds/douyin-star-planet-moon/v002/outputs/brand-lockup-preview.png)，同目录提供透明PNG与可编辑SVG供后续封面复用。

继续修订脚本时，将 `v001/recipe.json` 另存为 `storage/state/build-recipes/douyin-meteor-journey-v003.json`，将version改为v003再修改内容。当前SKILL与工作流已升级，不能用它覆盖旧版v001。

```bash
material_path="storage/sources/src-geo-b1-c1-s1-celestial-bodies/v001/extractions/extract-001/reviews/review-001/reviewed-knowledge.json"
python3 skills/douyin-build/scripts/build.py \
  --material "$material_path" \
  --recipe storage/state/build-recipes/douyin-meteor-journey-v003.json
```

首版选题为“看见流星，地上就会有陨石吗？”，六镜头规划60秒，1080×1920。查看[无声关键帧预演](storage/builds/douyin-meteor-journey/v001/preview/index.html)、[分镜总览](storage/builds/douyin-meteor-journey/v001/outputs/storyboard-contact-sheet.png)及[旁白与分镜脚本](storage/builds/douyin-meteor-journey/v001/outputs/script.md)。预演按计划时间切换静态画面，画面字幕为首句排版示例，完整暂定字幕另列在检查栏和SRT中。

原版分镜状态为 `awaiting_storyboard_review`。用户要求继续后，新版单独记录分镜制作授权及原版指纹，制作连续对象动画与动态字幕：

```bash
python3 skills/douyin-build/scripts/animate.py \
  --recipe storage/state/build-recipes/douyin-meteor-journey-v002.json
```

新版：[动画播放器](storage/builds/douyin-meteor-journey/v002/preview/index.html) · [MP4](storage/builds/douyin-meteor-journey/v002/outputs/animation-draft.mp4) · [独立封面草稿](storage/builds/douyin-meteor-journey/v002/outputs/cover.png)。六镜头保持60秒、1080×1920、30fps；光迹、岩石、条件分支和概念标签独立运动。

当前 `v002` 状态为 `awaiting_audio`：macOS say受运行环境权限阻止，只输出文件头，未生成有效配音。音频步骤记录为 `blocked_environment`，动画与无声编码已完成；字幕仍按计划时间切换，配音后需要重排对齐。配音方式待用户选择，发布资格为false。修改recipe、规范或素材后使用新版本，最终成片另需发布Approve。

## 核心约定

- 一个源 HTML 可以在同一平台生成多个独立构建。
- 源内容和构建均保留版本；构建记录来源版本、SKILL 版本与生成参数。
- 每个平台拥有独立工作流，可共享内容提取、核查和审批步骤。
- 所有构建发布前需要 Approve；批准绑定具体构建版本和目标平台。
- 独立站通过自己的工作流发布完整内容与相关衍生作品。
- `storage/` 中的运行数据不纳入版本控制，目录占位文件除外。

## 设计文档

- [最初需求](INITIAL_REQUIREMENTS.md)
- [业务模型](docs/domain-model.md)
- [工作流设计](docs/workflow-design.md)
- [SKILL 目录说明](skills/README.md)
- [提取输出约定](skills/extract-content/references/output-contract.md)
- [科学审校输出约定](skills/review-science/references/output-contract.md)
- [图文构建约定](skills/toutiao-build/references/build-contract.md)
- [视频脚本与分镜约定](skills/douyin-build/references/output-contract.md)
- [动画构建约定](skills/douyin-build/references/animation-contract.md)
