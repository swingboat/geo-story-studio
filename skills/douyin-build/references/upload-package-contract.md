# 抖音上传素材约定（1.5）

用户已明确要求每条抖音作品同时交付横版4:3封面、竖版3:4封面、标题、简介、30个关键词与话题。2026-10-18补充要求：标题、简介、关键词和话题统一放在一个文件中；2026-10-19将关键词数量调整为30个。该约定记录本项目的制作需求，不替代平台最新上传规格。

## 交付文件

- 横版4:3封面PNG及可编辑SVG；当前采用1440×1080。
- 竖版3:4封面PNG及可编辑SVG；当前采用1080×1440。
- `发布文案.txt`：发布文字的统一入口，UTF-8文本，依次包含【标题】、【简介】、【关键词（30个）】、【话题】四栏；关键词全部放在同一行，用英文逗号`,`分隔，话题保留`#`便于复制。新交付不再另生成`title.txt`、`description.txt`、`keywords.txt`、`hashtags.txt`或重复的`upload-copy.txt`。
- `publication.json`：供工作流读取的平台、系列、标题、简介、`keywords`数组、话题、科学结论引用和草稿状态；内容与统一文案一致。
- `upload-package.zip`：封面源文件、PNG、文案和关键词归档。

横竖封面分别排版，沿用作品主体、色彩及署名；检查原尺寸和缩小后的标题、标签、边距与对象对应关系。已建立SVG视觉系统的作品优先复用可编辑插图；新增图源如实登记。封面文字和简介遵守原作品的科学范围，避免加入视频未讲解的结论。

## 关键词

从本条视频实际讲解的对象、概念、过程及所属领域中提炼30个关键词，优先使用具体、常用的中文词语。去除重复项，交付前核对恰好30个非空词条。

在`发布文案.txt`的【关键词（30个）】栏中，将30个词用英文逗号`,`连接成一行，不手动换行，不带编号或`#`；`publication.json`中的`keywords`数组与该栏内容及顺序一致。将统一文案纳入上传素材归档和产物清单，最终回复与预览页优先链接此文件。话题放在同一文件的【话题】栏中，数量按作品需要选择。

可从已完成的`publication.json`生成统一文案：

```bash
python3 skills/douyin-build/scripts/write_publication_copy.py \
  --publication storage/builds/<build-id>/<version>/outputs/publication.json
```

## 统一输出目录

用户要求一个SKILL的交付集中保存：本次作品的全部文件位于`storage/builds/<build-id>/<version>/`，所有成品放在其`outputs/`中，预览放在`preview/`中。

```text
storage/builds/<build-id>/<version>/
  manifest.json
  upload-manifest.json           后补上传素材时使用
  preview/
  outputs/
    script.md
    narration.txt
    subtitles-draft.srt
    scenes/
    animation-draft.mp4          动画阶段生成
    cover-landscape-4x3.png
    cover-landscape-4x3.svg
    cover-portrait-3x4.png
    cover-portrait-3x4.svg
    发布文案.txt
    publication.json
    upload-package.zip
```

新构建在生成阶段将本次产物一起纳入`manifest.json`。在现有构建中补齐尚不存在的封面、文案时，同样放入该构建的`outputs/`，使用根目录下的`upload-manifest.json`记录新增文件的指纹、尺寸、图源及其对应构建，不覆盖原有文件。修改已有成品时递增构建版本。

进入动画或成片新版本时，将仍适用的封面与统一发布文案一起带入新版本的`outputs/`并纳入清单。用户从该版本目录即可取得完整交付。从旧格式整理时，在新版本合并四类发布文字，预览链接和素材包同步使用`发布文案.txt`；保留旧版归档。

可在分镜阶段先制作封面和文案。此时素材为草稿，`publication_approval_eligible=false`；最终与实际成片一同审阅。
