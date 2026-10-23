# 科学审校输出约定（1.0）

## 文件

每次审校保存于提取目录的 reviews/<review-id>/：

- review.json：代理查证后填写的证据、结论和选题范围。
- review.md：由脚本生成的阅读报告。
- reviewed-knowledge.json：由脚本生成的平台构建输入。

后两项通过 finalize.py 生成，状态随证据和结论派生。审校记录修订时使用新 review ID。

## review.json

根字段为 schema_version、review_id、source_ref、extraction_id、reviewed_at、reviewer、skill、input_hashes、scope_notes、evidence、claims、diagram_reviews、topic_plans。

- source_ref：与本次提取一致的源 ID、版本、哈希和快照路径。
- reviewer：type（agent 或 human）及 name，按实际执行者填写。
- skill：name、version、instructions_sha256。
- input_hashes：content_sha256 与 knowledge_sha256，绑定审校输入。
- scope_notes：覆盖范围、未取得的资料、修订使用范围等说明。
- evidence：id、title、publisher、url、section、accessed_on、note。note 是已阅读段落的证据摘要，不使用搜索结果 ID；科学来源与图像授权分开处理。
- claims：id、title、original_text、source_refs、knowledge_point_ids、related_review_item_ids、decision、reason、recommended_text、evidence_ids、scope、constraints。原文必须能在引用正文块中定位。
- diagram_reviews：diagram_id、decision（reuse、revise 或 unresolved）、claim_ids、requirements。逐一覆盖提取出的图解；revise 必须说明修改要求。
- topic_plans：topic_id、scope、claim_ids、diagram_ids、constraints。逐一覆盖候选选题，每个选题涉及的知识点至少关联一项结论。

所有知识点、初始 review_items 和图解均须有审校记录。accepted/approved 等发布审批状态不在本格式中。

## 派生状态

- supported、revise、qualify：附证据和修订后的可用文本。
- unresolved：保留原因，recommended_text 为 null。
- 选题引用的结论或图解有 unresolved 时为 blocked，其他选题为 ready_for_build。
- 有 revise 图解时仍可进入构建，required_changes 必须带入构建任务并落实。
- 全部选题与结论均已处理时总状态为 reviewed，否则为 completed_with_open_items。

reviewed-knowledge.json 包含 source_ref、extraction_id、review_id、reviewed_at、status、provenance、requires_publication_approval、knowledge_points、topics、diagram_reviews、references。

knowledge_points 仅携带已有依据的 statements 和 unresolved_claim_ids。topics 仅在 ready_for_build 时包含 statements；blocked 选题携带阻塞 ID 及空 statements。下游构建以 topics 中的允许表述、scope、constraints 和 required_changes 为输入，不回退读取原 HTML 中未审校的结论。

provenance 记录 review、提取输入、SKILL 指令和生成脚本的哈希。requires_publication_approval 始终为 true。结构与引用检查不能代替科学查证，也不会创建发布审批记录。
