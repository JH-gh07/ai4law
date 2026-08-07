# ISSUE-reporting-001

> 记录日期：2026-08-08
> 格式依据：`status/todo/DataComplyFlow_架构统一迁移与可核验实施方案_20260808.md` §14.3

## ISSUE-reporting-001

- **严重级别**：BLOCK
- **运行任务**：阶段 3-1 DPIA 迁移 §12 Step 9（新旧产物比较）时发现，回溯确认阶段 2 assessment 同样受影响
- **输入案例**：生产形态章节内容 `该处理活动属于大规模处理特殊类别数据 [1]。`
- **代码位置**：
  - `backend/domains/cn/security_assessment/schema_first.py:53`（修复前）`_CITATION_MARKER_RE.findall(paragraph)`
  - `backend/domains/eu/dpia/schema_first.py:62`（修复前）同一模式
  - 触发源：`backend/domains/cn/security_assessment/chapter_generator.py:445` 与 `backend/domains/eu/dpia/chapter_generator.py:352` 调用 `convert_citation_markers`
- **期望结果**：适配器把带引用的段落转成 `ClaimBlock`，`citation_refs=['CIT-EU-GDPR-ART35-P01']`
- **实际结果**：抛出 `pydantic ValidationError: semantic block text must not contain Markdown or citation markers`，`build_*_document_ir` 直接崩溃
- **是否影响用户产物**：是 —— 开关开启后新流程无法生成任何产物
- **是否影响引用跳转**：是 —— `document_ir.json` 的 `citation_refs` 恒为空，Compiler 的 CitationValidationPass 无对象可校验

## 根本原因

引用标记的转换发生在**生成器内部**，不在 renderer：

```
chapter_generator._generate_chapter()
  └─ convert_citation_markers(raw, citation_registry)   # {{CIT-*}} → [1]
       └─ registry.assign_footnote_number(cid)          # 同时建立 footnote_map
  └─ ChapterContent(content=<已是 [1] 形态>)
       └─ renderer.render(chapters=...)
            └─ build_*_document_ir()  ← 两个适配器都只认 {{CIT-*}}
```

两个适配器都是针对 `{{CIT-*}}` 形态编写的，而生产管线交给它们的永远是 `[N]` 形态。
`[N]` 又被 `ParagraphBlock` / `ClaimBlock` 的语义校验判定为 citation marker 残留，于是失败关闭。

## 为什么此前的测试没有发现

阶段 2 与阶段 3 的首跑脚本都直接构造 `ChapterContent(content="... {{CIT-*}} ...")`，
**绕过了生成器**。fixture 里的形态在生产中不存在，因此：

- Golden Snapshot 测试通过，但锁定的是一个不可能出现的输入形态；
- §14.1「正文脚注和 CitationMap 数量不一致」这条阻断项从未被真正执行 ——
  harness 从不产生脚注，`footnote_map` 恒为 0 条，两边都是 0 所以"相等"。

## 临时处理

无。缺陷在开关开启时必然触发，没有可用的绕过手段。

## 永久修复

提交 `96df783`。新增 `backend/common/reporting/compat.py::extract_citation_refs()`，
同时接受两种形态并统一返回 `(cleaned_text, citation_refs)`：

- `{{CIT-*}}` 走 `markers.py::CIT_MARKER_RE`（单一数据源，不重复定义正则）；
- `[N]` 经 `legacy.get_footnote_map()` 反查回 `citation_id`；
- 两条路径都按首次出现顺序去重，输出完全一致；
- **无法反查的编号原样留在文本里**，让 Compiler 以诊断形式暴露，而不是在此静默丢弃
  （§2.2 迁移原则 4：禁止静默丢引用）。

两个适配器改为调用该 helper；各自重复的 `_CITATION_MARKER_RE` 按 §21.3 删除，
不保留注释块。

## 验证命令

```bash
uv run pytest -q backend/common/reporting/tests/test_citation_shape.py          # 10 passed
uv run pytest -q backend/domains/eu/dpia/tests/test_schema_first_adapter.py     # 10 passed
uv run pytest -q backend/domains/cn/security_assessment/tests/test_schema_first_adapter.py  # 4 passed
uv run pytest -q                                                                # 661 passed, 0 failed
```

回归钉子（防止缺陷静默复发）：

| 测试 | 位置 |
|---|---|
| `test_production_footnote_shape_yields_claim_block_with_refs` | 两个适配器测试文件各一份 |
| `test_both_shapes_produce_identical_refs` | `test_citation_shape.py` |
| `test_unmapped_footnote_number_is_left_in_text_as_diagnostic` | `test_citation_shape.py` |

## 关闭条件

- [x] 两种形态产出相同 `citation_refs`
- [x] 生产形态下 `document_ir.json` 的 `ClaimBlock` 携带正确 refs
- [x] 生产形态下正文 `[N]` 集合 == `citation_map.footnote_map` 键集合
- [x] 全量回归 0 失败
- [x] 两个适配器各有回归钉子
- [x] 阶段 2 验收报告的错误结论已更正（见 `phase2_assessment_firstrun_20260808/验收报告.md` 更正声明）
