# 图文构建约定（1.2）

## 路径与输入

每份作品保存为 storage/builds/<build-id>/<version>/：

- manifest.json：源、审校、SKILL及工作流版本，产物哈希与审批对象指纹。
- recipe.json：作品正文和配图的可复现制作输入。
- workflow-run.json：当前构建的独立执行记录，停在等待审批。
- preview/index.html：供审阅的本地页面。
- preview/visuals.html：封面、16:9／4:3／1:1居中裁切示例、正文图及图源。裁切比例为本地检查情形，不是平台规格承诺。
- outputs/article.md、article.html：正文及参考来源。
- outputs/publish.json：标题、摘要、标签、封面和配图顺序。
- outputs/references.json：正文实际使用的证据资料。
- outputs/media.json、visual-plan.json：图片来源、用途、使用依据、处理与素材哈希；与正文、发布配置一起绑定审批指纹。
- outputs/assets/：封面及配图的SVG和PNG。
- outputs/content-package.zip：文章和素材的归档。

## recipe.json

根字段：schema_version、build_id、version、topic_id、titles、selected_title、summary、tags、audience、cover、sections、figures、change_resolutions、editorial_review；media为可选扩展。

- titles 是标题候选数组；selected_title 为0起始索引。summary为摘要，audience记录受众。
- cover 包含 lines（两行标题）、subtitle、source_diagram_ids、claim_ids 和 alt。
- 自制封面可用asset_id关联media，并写purpose、caption；show_in_article=false表示仅作列表封面，不在正文重复插入。缺省保留旧版正文封面行为。
- sections 包含 heading、paragraphs 和 figure_id。每个paragraph包含text和claim_ids，事实改写须能由引用的已审校结论支持。
- figures 包含 id、kind（single或comparison）、title、source_diagram_ids、labels、caption、alt和claim_ids。single 使用一张源图和一条label；comparison使用三张源图与三组label（title、subtitle）。
- kind=asset时用asset_id引用本地图片，填写purpose，labels为空数组。摄影的source_diagram_ids可为空；重新绘制的示意图仍关联审校允许的源图，并落实修改要求。脚本核对引用及哈希，图解的语义仍需代理核对。
- media逐项记录id、path（storage内路径）、sha256、kind（photograph／illustration／composition）、credit、rights_notes、adaptation、verified_at；摄影另填source_url、rights_url、width、height。derived_from记录组合图依赖的media ID。文件支持JPEG、PNG及仅含内联属性的SVG；SVG图片须嵌入，不能引用外部资源或包含脚本。
- change_resolutions 逐项包含 diagram_id、instruction、resolution、figure_ids。instruction逐字引用审校的修改要求，resolution说明本作品如何落实，figure_ids关联落实位置。
- editorial_review 记录type、name、notes；本轮由代理核对正文与审校范围，不标记为人工审校。

素材只可引用选题允许的claim与源图。每项修改要求必须有关联图，且该图实际使用对应源图。正文、封面、图注与替代文本均属于需要核对的成品。

## 产物与审批

manifest记录 source_ref、review_ref、skill、workflow_ref、parameters、artifacts、approval_subject_sha256等字段。skill记录指令、脚本、assets及references内文件的哈希；视觉规范和可编辑示例随所用SKILL一起进入追溯范围。指纹绑定文件内容、所选标题和发布配置，新的版本拥有新的审批对象。旧构建保留创建时的SKILL版本，更新SKILL后使用新构建版本。

工作流定义在 workflows/toutiao.yaml。本阶段由build.py执行构建部分并记录状态；通用工作流执行器和平台发布尚待实现。

每个构建的status为awaiting_approval，requires_publication_approval为true。预览页提供正文和素材下载，Approve由后续审批步骤记录。

渲染需要本机rsvg-convert及可显示中文的系统字体。字体文件不打包，配图不引用远程资源。源SVG保留原始出处，输出SVG重新排版并导出PNG。

本地摄影原件和自制SVG会随media记录归档入图文包。摄影说明只认证原始素材的身份，不把照片当机制证明，也不暗示来源机构审核了文章。使用范围发生变化时重新核素材条件与平台标识，不自动勾选原创声明。
