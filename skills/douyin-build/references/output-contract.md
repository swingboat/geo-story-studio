# 视频脚本与分镜输出约定（1.1）

## 输入

recipe根字段：schema_version、build_id、version、topic_id、title、audience、format、visual_baseline、cover_plan、scenes、change_resolutions、editorial_review。

- format：width、height、fps；本阶段固定输出1080×1920关键帧，fps记录未来成片的计划值。
- visual_baseline：path、sha256，引用仓库内已选定的视觉源文件；仅作为风格依据。
- cover_plan：headline、visual、source_scene_id，属于待后续制作的封面方案。
- 每个scene：id（shot-01等）、start、end（秒）、heading、narration、subtitles（文本片段数组）、on_screen_text、visual、motion、claim_ids、source_diagram_ids、artwork。
- artwork：path（storage内SVG）、sha256、alt、credit、rights_notes、adaptation。SVG须自包含，仅允许内联属性、渐变和本地片段引用。
- 字幕片段连接后必须与旁白一致。脚本在镜头内按字符权重分配暂定时间，SRT文件名注明draft；并非语音识别或实际音频对齐。
- change_resolutions：diagram_id、instruction（原审校要求）、resolution、scene_ids。关联镜头必须实际声明对应源图。
- editorial_review：type、name、notes，记录实际核对范围，代理自查与真人试读分别记录。

镜头从0秒开始，按时间连续排列。画面与旁白只能引用当前选题的允许结论，图示条件由代理核对；机械检查不认证证据语义。

## 构建目录

`storage/builds/<build-id>/<version>/`：

- recipe.json、manifest.json：制作输入、源与审校引用、SKILL及工作流指纹、产物哈希。
- workflow-run.json：独立运行记录，停在review_storyboard。
- preview/index.html：可播放、暂停、拖动时间和逐镜选择的无声关键帧预演。关键帧按计划时间切换，不是连续动画或成片。
- outputs/script.md、narration.txt：分镜脚本及供后续配音使用的纯旁白。
- outputs/storyboard.json、subtitles-draft.srt：带暂定时间的镜头与字幕计划。
- outputs/cover-plan.json、references.json、media.json：封面方案、科学来源和图源。
- outputs/scenes/shot-NN.svg、.png、-mobile.png：可编辑源图、1080px关键帧及375px检查图。
- outputs/storyboard-contact-sheet.svg、.png：六镜头等的视觉总览，按实际镜头数排版。
- outputs/storyboard-package.zip：脚本、分镜、图源及关键帧归档。

封面、标题、简介等上传素材也放在本版本的`outputs/`中，格式及后补文件的清单约定见[上传素材约定](upload-package-contract.md)。

## 状态与审批

manifest的stage=storyboard，status=awaiting_storyboard_review，requires_publication_approval=true，publication_approval_eligible=false。review_subject_sha256绑定本阶段作品与上下文，不作为发布批准。

分镜工作流在review_storyboard等待，后续步骤尚未开始；分镜阶段完成不能将这些步骤标为完成。确认继续制作后按[动画构建约定](animation-contract.md)保存新版本。当前已支持无声动画，配音和发布待接入；最终视频、封面和发布配置齐备后再建立审批对象。

重复运行验证已有构建及文件指纹，输入变化时使用新版本。所有SVG与PNG均为科普示意；真实摄影另核具体图源，生成画面不得作为观测记录。
