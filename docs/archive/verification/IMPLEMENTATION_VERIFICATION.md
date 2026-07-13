# Implementation Verification

## 1. Pipeline evidence

- [x] 用户输入是否进入 FactItem？
  - 代码位置：`backend/common/workflow/pipeline.py`（`run()` 中 `facts_built`）、`backend/modules/assessment/fact_builder.py`、`backend/modules/cn_flow/fact_builder.py`
  - 测试位置：`backend/modules/assessment/tests/test_fact_builder.py`、`backend/modules/cn_flow/tests/test_service.py`
  - 示例输出文件：`outputs/assessment/9619c21b-243b-40e0-adbb-8c67ebc889e8/trace/005_facts_built.json`、`outputs/cn_flow/adebab72-a526-4e85-914b-98b75a8cb7c9/trace/005_facts_built.json`

- [x] FactItem 是否进入 IssueItem？
  - 代码位置：`backend/modules/assessment/issue_builder.py`、`backend/modules/cn_flow/issue_builder.py`
  - 测试位置：`backend/modules/assessment/tests/test_issue_builder.py`、`backend/modules/cn_flow/tests/test_service.py`
  - 示例输出文件：`outputs/assessment/9619c21b-243b-40e0-adbb-8c67ebc889e8/trace/007_issues_built.json`、`outputs/cn_flow/adebab72-a526-4e85-914b-98b75a8cb7c9/trace/007_issues_built.json`

- [x] IssueItem 是否进入 EvidenceItem？
  - 代码位置：`backend/modules/assessment/evidence_builder.py`、`backend/modules/cn_flow/evidence_builder.py`
  - 测试位置：`backend/modules/assessment/tests/test_evidence_builder.py`、`backend/modules/cn_flow/tests/test_service.py`
  - 示例输出文件：`outputs/assessment/9619c21b-243b-40e0-adbb-8c67ebc889e8/trace/008_evidence_built.json`、`outputs/cn_flow/adebab72-a526-4e85-914b-98b75a8cb7c9/trace/008_evidence_built.json`

- [x] IssueItem / EvidenceItem 是否进入 LLM prompt？
  - 代码位置：`backend/modules/assessment/chapter_generator.py`（`build_context_block_from_pack`）、`backend/modules/cn_flow/service.py`（`_build_context_block_from_pack`）
  - 测试位置：`backend/modules/assessment/tests/test_chapter_context.py`
  - prompt 截取：assessment prompt 包含 `ISSUE-missing-attachments` 与 `EVIDENCE-missing-attachments`（见 `test_final_llm_prompt_contains_context_pack_issue`）

- [x] IssueItem / EvidenceItem 是否进入最终交付物？
  - 代码位置：`backend/modules/assessment/report_renderer.py`、`backend/modules/cn_flow/service.py`（`_render_outputs`）
  - 文件路径：`issue_list.json`、`evidence_chain.json`（含 xlsx for assessment）
  - zip 内容示例：`outputs/assessment/9619c21b-243b-40e0-adbb-8c67ebc889e8/outputs/*.zip`、`outputs/cn_flow/adebab72-a526-4e85-914b-98b75a8cb7c9/outputs/*.zip`

## 2. Negative tests

- [x] 删除 issue_list 后，prompt 测试是否失败？
  - 证据：`backend/modules/assessment/tests/test_chapter_context.py::test_context_block_loses_issue_id_when_issue_list_is_removed`

- [ ] 删除 evidence_chain 后，trace 测试是否失败？
  - 当前状态：未实现专门负向测试（需新增一条强约束测试）。

- [x] 构造附件缺失但报告写“材料齐备”，一致性检查是否失败？
  - 证据：`backend/modules/assessment/tests/test_consistency_checker.py::test_report_against_context_detects_material_completion_conflict`

- [x] 构造 important_data unknown 但报告写“不涉及重要数据”，一致性检查是否失败？
  - 证据：`backend/modules/assessment/tests/test_consistency_checker.py::test_report_against_context_detects_unknown_important_data_denial`

## 3. Module coverage

| module | facts | issues | evidence | context_pack | prompt uses pack | artifacts | tests |
|---|---|---|---|---|---|---|---|
| assessment | yes | yes | yes | yes | yes | yes | yes |
| cn_flow | yes | yes | yes | yes | yes | yes | yes |
| cpra | no | no | no | no | no | no | no |
| bcr | no | no | no | no | no | no | no |
| scc | no | no | no | no | no | no | no |

## 4. Evidence of trace manifests

- assessment latest manifest: `outputs/assessment/9619c21b-243b-40e0-adbb-8c67ebc889e8/trace/manifest.json`
  - events: `assessment_request -> profile_extracted -> diagnosis -> path_validation -> facts_built -> retrieval_hits -> issues_built -> evidence_built -> context_pack_built -> chapters_generated -> consistency_issues -> alignment_issues`
- cn_flow latest manifest: `outputs/cn_flow/adebab72-a526-4e85-914b-98b75a8cb7c9/trace/manifest.json`
  - events: `cn_flow_request -> profile_extracted -> diagnosis -> path_validation -> facts_built -> retrieval_hits -> issues_built -> evidence_built -> context_pack_built -> chapters_generated -> consistency_issues -> alignment_issues`

## 5. Conclusion

- Current state is **mid-migration**: `assessment` and `cn_flow` are upgraded to intermediate-artifact-driven workflow.
- Remaining work is module rollout (`cpra/bcr/scc/...`) and one missing negative test (`delete evidence_chain -> trace test fail`).
