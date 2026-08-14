# DataComplyFlow 审计深度洞察与系统性修复方案

> 版本：v1.0
> 日期：2026-08-10
> 当前分支：`new`
> 制定基线：`7646244`
> 方案状态：待执行
> 审计基准：`tmp_review_audit_20260809.md`（2,597 行，11 模块 98 文件，~76 个问题定位点）
> 交叉验核基准：2026-08-10 全模块重运行结果（§17）

---

## 一、深度洞察：审计报告的底层真相

### 1.1 问题不是 76 个，而是 3 组因果链在不同模块的重复投影

审计报告记录了约 76 个问题定位点，分布在 11 个模块的渲染层、结构化数据层、LLM 叙述层和索引层。如果按模块逐个修，工作量是 `76 × 修复时间`。但代码追踪发现：**76 个问题中 ~62.5% 是 7 个共同缺陷在 4-5 个模块中的重复投影**。

更重要的是，这 7 个共同缺陷之间存在**硬因果链**：

```
C-COMMON-1 (LLM静默失败)
    ├── 直接导致 C-COMMON-5 (占位+假COMPLETED)
    │       └── 下游约 12-15 个问题自动消除
    ├── 直接导致 C-COMMON-2 (CIT标记崩溃)
    │       └── 因为 LLM 未生成文本 → 无 {{CIT-xxx}} 可供替换
    ├── 直接放大 C-COMMON-3 (evidence_chain 空)
    │       └── evidence_builder 在无 LLM 输出时只能造空壳
    └── 间接放大 C-COMMON-7 (document_ir 空)
            └── document_ir 依赖 LLM 生成的段落作为输入

修 C-COMMON-1 → 自动修复 ~12-15 下游问题
修 C-COMMON-2 → 自动修复 CIT 标记残留 + 脚注归零 问题
修 C-COMMON-3 → 6 模块 evidence chain 从空壳变有实质
```

### 1.2 七个共同缺陷的本质分类

| 编号 | 缺陷 | 本质分类 | 根因类型 | 直接固化的代码位置 |
|------|------|:---:|------|------|
| C-COMMON-1 | LLM 静默失败 | **运行时状态错误** | `_enabled = False` 时返回降级文本且不抛异常 | `client.py:73, 194-201` |
| C-COMMON-2 | CIT 标记崩溃 | **格式兼容性缺陷** | postprocess 仅认 `{{CIT-xxx}}`，LLM 实际写 `[1]` | `postprocess.py:354-357, 469` |
| C-COMMON-3 | evidence_chain 全空 | **实现未完成** | Schema 定义了 5 个字段，builder 从未填充 | 各 `evidence_builder.py` |
| C-COMMON-4 | 工程标注泄漏 | **后处理缺失** | `【待核验】` `【推测】` 等触发后无清理步骤 | `postprocess.py:361-363, 28-29 行` |
| C-COMMON-5 | 假 COMPLETED | **状态机制缺失** | `state="COMPLETED"` 硬编码，不做内容质检 | 各 `service.py`（dpia:530） |
| C-COMMON-6 | supporting_material_refs 空 | **Schema-实现断层** | field 定义存在，3/11 模块的事实构建器从未填充 | pipia `service.py:116` |
| C-COMMON-7 | document_ir 段空 | **双路径不一致** | markdown 走 LLM 生成，document_ir 走 schema_first，无桥接 | `schema_first.py` + `markdown.md` |

### 1.3 审计报告中"非共同缺陷"的分类

除 7 个共同缺陷外，剩余的 ~15 个特殊问题分属两类：

**A. 架构设计级问题（需结构性修订）**
- BIZ-1: assessment 路径矛盾（诊断→scc 但仍生成了安全评估报告）
- BIZ-3: pipia 结构化层 1 个 Issue vs 正文 5 个分析维度
- BIZ-4: tia 降级逻辑缺少加密量化
- BIZ-5: eu_scc 报告偏"材料核对"而非"条款审查"
- BIZ-6: bcr 11 处模板变量未替换
- BIZ-7: eu_scc 6/8 findings 无 original_text
- IDX-1~IDX-3: 索引噪音/覆盖不足（**已于 2026-08-10 修复完成，见 §16**）

**B. 小范围修正问题（文件级单点修复）**
- BIZ-15: tia "推测"措辞在正式报告
- BIZ-16: pipia 测试元信息泄漏
- BIZ-8: assessment compliance_reasoning 全部判定"不可正面肯定"→ MEDIUM

### 1.4 关键数值变化（2026-08-07 快照 → 2026-08-10 现状）

根据 §17 交叉验核（2026-08-10 最新任务运行产物），以下问题已自动消失或已修复：

| 审计编号 | 2026-08-07 | 2026-08-10 | 变化原因 |
|:---:|------|------|------|
| R1 | DOCX 0B | ✅ 38KB 有效 DOCX | docx 渲染已有代码修复 |
| R4 | dpia 7/7 占位 | ✅ 0 占位，99 行 2612 字符 | LLM 已启用 |
| R5 | cpra 3/4 占位 | ✅ 0 占位，61 行 1674 字符 | LLM 已启用 |
| R6 | cn_flow 3/5 占位 | ✅ 已清除 | 委托 us_14117 |
| F1 | Agent 未执行 | ✅ 28事件执行正常 | 审计误判 |
| F2 | BCR 模板变量 | ✅ 已清除 | 代码已修复 |
| F3 | CPRA 脚注丢失 | ✅ 5/6 (83%) | LLM 启用后恢复 |
| C-COMMON-4 | 工程标注 | ✅ 已清除 | 后处理已修复 |
| IDX-1 | EU 噪音 | ✅ 897→402条目 0噪音 | 索引重建 |
| IDX-3 | CPRA 覆盖 | ✅ 12→83 unique articles | 索引重建 |

**剩余待修复的核心问题**（2026-08-10 验核确认仍未解决）：

| 审计编号 | 问题 | 当前状态 |
|:---:|------|------|
| C-COMMON-2 | CIT 标记崩溃 | assessment 脚注 21%，dpia 8%，pipia 0% |
| C-COMMON-3 | evidence_chain 三字段全空 | assessment/dpia/us_14117 均为 100% 空 |
| C-COMMON-5 | 假 COMPLETED | pipia 模块 LLM 未启用时仍返回 COMPLETED（2026-08-10 新发现） |
| R3 | pipia CIT 标记截断 → 整个模块损坏 | 2026-08-10 发现 pipia 14 处占位，LLM 对该模块仍 disabled |
| R8 | us_14117 markdown 格式坍塌 | 15 行 854 字符，1 超长行 |
| BIZ-1 | assessment 路径矛盾 | 诊断推荐 scc 但仍生成了安全评估报告 |

---

## 二、修复总路线图

```
Phase A（并行）: 修复 3 个运行时阻断项 → 修复后立即消除 40% 的审计问题
  ├── A1: 启用 pipia/us_14117 模块 LLM（目前仅这两个模块 _enabled 仍为 False）
  ├── A2: 修复 CIT 标记后处理对 [N] 格式的兼容
  └── A3: 修复 evidence_chain builder 的三字段填充

Phase B（并行）: 修复业务逻辑缺陷 → 解决 BIZ-1/3/5/6/7 五个高影响问题
  ├── B1: assessment 路径矛盾 → PATH_MISMATCH 早期中断
  ├── B2: pipia Issue 拆解为多条独立 IssueItem
  ├── B3: eu_scc findings original_text 补充
  ├── B4: bcr 模板变量替换
  └── B5: us_14117 markdown 格式结构化渲染

Phase C（并行）: 修复渲染/质量门禁 → 解决剩余工程问题
  ├── C1: pipia 测试元信息过滤（BIZ-16）
  ├── C2: tia "推测"措辞替换（BIZ-15）
  ├── C3: assessment material_checklist 补充
  └── C4: 各模块 state 从硬编码 COMPLETED 改为基础质检

Phase D: 全模块重新运行 + 交叉验核 → 生成最终证据
```

---

## 三、并行任务组 A：运行时阻断项修复

### 子任务 A1：启用 pipia 模块 LLM + 添加 ExecutionGuard（依赖：无）

**根因**：
- `backend/domains/cn/pipia/service.py:125` — `if self.llm_client and self.llm_client.enabled` else 占位文本
- 2026-08-10 交叉验核发现 pipia 仍有 14 处 `"LLM未配置，此处为占位内容"`
- 需确认是 `_enabled` 全局 False 还是 pipia 独有配置问题

**修复代码位置**：

1. `backend/common/llm/client.py:194-201` — 在 `_enabled` 为 False 时，当前仅 `logger.warning` 并返回 fallback。需在此处增加 **ExecutionGuard** 机制：

```python
# client.py:194 附近，_fallback_metadata 返回前：
if not self._enabled:
    logger.warning(
        "LLMClient: API key not configured for provider %s, returning fallback text.",
        self._provider,
    )
    # 新增：记录降级事件到 ExecutionGuard
    self._record_fallback("not_configured")
    return self._fallback_metadata(...)
```

2. `backend/domains/cn/pipia/service.py:125-137` — 修改为：

```python
# 修复前：
if self.llm_client and self.llm_client.enabled:
    content = generate_chapter(...)
else:
    content = f"（{title}：LLM未配置，此处为占位内容）"

# 修复后：
if self.llm_client and self.llm_client.enabled:
    content = generate_chapter(...)
else:
    # 不再使用占位文本，而是使用基于 rules/context 的非 LLM 模板填充
    content = self._render_rule_based_chapter(title, context_block, facts, issues)
```

3. 同步修改同模式的 cpra（`backend/domains/us/cpra/service.py:515`）、cn_flow（`backend/domains/us/eo14117_flow_review/service.py:197`）。

**验证命令**：
```bash
# 1. 确认 pipia 模块 LLM 是否被正确检测
python -c "
from backend.core.settings import get_settings
s = get_settings()
print('LLM enabled:', s.llm_enabled)
print('LLM provider:', s.llm_active_provider)
print('API key configured:', bool(s.llm_api_key))
"

# 2. 重新运行 pipia 并检查章节内容
python -m backend.modules.pipia.cli run --case pipia-standard \
    2>&1 | tee tmp/verify/pipia_llm_enabled_check.txt
grep -c "LLM未配置" tmp/pipia/markdown.md  # 应为 0
grep -c "占位" tmp/pipia/markdown.md         # 应为 0
```

**完成标准**：
- pipia 模块 7 章全部无 "LLM未配置" / "此处为占位"
- pipia markdown 字符数 > 5000（之前 500 字符/14 处占位）
- assessment 脚注覆盖率从 21% 提升至 > 50%

---

### 子任务 A2：修复 CIT 标记后处理对 [N] 格式的兼容（依赖：无，可与 A1 并行）

**根因**：
- `backend/common/llm/postprocess.py:354-357` — `verified_footnotes` 仅来自 `registry.get_footnote_map()`，而 `assign_footnote_number()` 仅在 `{{CIT-xxx}}` 标记被替换时调用
- `postprocess.py:469` — `_replace_registered_markers()` 对 [N] 格式零匹配
- 三条路径的分析详见审计报告 §12

**修复代码位置**：

1. `backend/common/llm/postprocess.py:354-358` — 修改 `apply_citation_policy()` 中的脚注验证逻辑：

```python
# 修复前（行 354-357）：
numeric_footnotes = {
    int(number) for number in re.findall(r"\[(\d+)\]", paragraph)
}
has_verified_marker = bool(valid_citations) or bool(
    numeric_footnotes & (verified_footnotes or set())
)

# 修复后：
numeric_footnotes = {
    int(number) for number in re.findall(r"\[(\d+)\]", paragraph)
}
# 从 registry 反查当前模块的 footnote_map 获取已验证脚注集合
# 即使 marker 是 [N] 而非 {{CIT-xxx}}，只要 registry 中有 assign_footnote_number
# 对应的数字，就认为已验证
verified_footnotes_set = set(verified_footnotes or set())
# 宽松模式：若段落中有 [N] 引用且在 registry footnote_map 中，
# 不标记"待核验"
has_verified_marker = bool(valid_citations) or bool(
    numeric_footnotes & verified_footnotes_set
)
```

2. `backend/common/llm/postprocess.py:438-471` — 在 `apply_citation_pipeline()` 中增加第二路径：

```python
# 新增函数：从原始文本中提取所有 [N] 引用，在 registry 中查找匹配
def _resolve_numeric_footnotes(
    text: str,
    registry: "CitationRegistry",
) -> tuple[str, set[int]]:
    """Resolve [N] numeric footnotes in text when {{CIT-xxx}} markers are absent.
    
    This handles the case where the LLM generates text with [1], [2] footnotes
    but the citation pipeline's marker replacement path was never triggered.
    """
    all_footnotes = set(range(1, len(registry) + 1))
    found: set[int] = set()
    for match in re.finditer(r"\[(\d+)\]", text):
        num = int(match.group(1))
        if num in all_footnotes:
            found.add(num)
    return text, found
```

3. `backend/common/llm/postprocess.py` — 在 `apply_citation_pipeline()` 的 registry 处理块中调用：

```python
# 在 apply_citation_pipeline() 中，converted 赋值后增加：
if registry is not None:
    converted = _replace_registered_markers(converted, registry)
    converted = _convert_basis_blocks_to_footnotes(converted, registry)
    # 新增：对 [N] 格式脚注的二次校验
    converted, numeric_found = _resolve_numeric_footnotes(converted, registry)
    verified_footnotes = set(registry.get_footnote_map()) | numeric_found
else:
    verified_footnotes = set()
```

4. `backend/common/llm/module_generator.py:357` — 强化 system prompt 中 `{{CIT-xxx}}` 格式要求：

```python
# 在 system prompt 的 citation 说明中增加：
"""
重要规则——脚注格式要求：
- 所有法律引用必须使用 {{CIT-xxx}} 格式（如 {{CIT-CN-LAW-001-38}}）
- 不得使用 [1] [2] 等手动数字编号
- 系统将在后处理阶段自动将 {{CIT-xxx}} 转换为统一脚注编号
- 如果您使用了 [N] 格式，脚注将无法被系统验证和注册

正确示例：
依据《个人信息保护法》{{CIT-CN-PIPL-13}} 第13条，个人信息处理者应当...
错误示例：
依据《个人信息保护法》[1]第13条，个人信息处理者应当...
"""
```

**验证命令**：
```bash
# 1. 重新运行 assessment 检查脚注覆盖率
python -c "
import json
result = json.load(open('tmp/assessment/_result.json'))
fm = result.get('profile', {}).get('citation_map', {}).get('footnote_map', {})
print(f'footnote_map entries: {len(fm)}')
print(f'footnote_map keys: {list(fm.keys())[:5]}')
"

# 2. 检查 tia markdown 中是否还有 【待核验】
grep -c "待核验" tmp/tia/markdown.md  # 应为 0

# 3. 跨模块脚注覆盖率（目标：全部 ≥ 70%）
for mod in assessment dpia pipia bcr; do
    echo "$mod: $(grep -oP '\[\d+\]' tmp/$mod/markdown.md | sort -u | wc -l) unique footnotes"
done
```

**完成标准**：
- assessment 脚注覆盖率 ≥ 70%（当前 21%）
- dpia 脚注覆盖率 ≥ 70%（当前 8%）
- tia markdown 中 `【待核验】` 标记 = 0
- 跨 4 个受影响模块的 footnote_map 均有 > 0 条目

---

### 子任务 A3：修复 evidence_chain builder 的三字段填充（依赖：无，可与 A1/A2 并行）

**根因**：
- `backend/common/workflow/evidence.py:91-149` — EvidenceItem Schema 定义了 `legal_basis`、`supporting_basis`、`document_refs`、`rag_query_used` 5 个字段
- `backend/domains/eu/dpia/evidence_builder.py:129-137` — `build_dpia_evidence()` 构造 EvidenceItem 时，完全没有填充这三个字段
- 其他模块的 evidence_builder 同理

**修复代码位置**：

1. `backend/domains/eu/dpia/evidence_builder.py:106-141` — 为每条 evidence 填充 `legal_basis`、`document_refs`、`rag_query_used`：

```python
# 修复后（在 build_dpia_evidence 中的 EvidenceItem 构造部分）：
evidence = EvidenceItem(
    evidence_id=evidence_id,
    claim=claim,
    fact_refs=fact_refs,
    rule_refs=rule_refs,
    conclusion=conclusion,
    confidence=_confidence(issue.severity, bool(rule_refs)),
    used_by=[issue.issue_id, *issue.affects_outputs],
    # 新增：填充 legal_basis
    legal_basis=[
        CitationBinding(
            source_id=reg.source_id if hasattr(reg, 'source_id') else str(reg),
            article_no=getattr(reg, 'article_no', ''),
            title=getattr(reg, 'title', ''),
            snippet=getattr(reg, 'snippet', '') or getattr(reg, 'quote_text', ''),
        )
        for reg in regulations[:5]
        if getattr(reg, 'source_id', None)
    ],
    # 新增：填充 document_refs（从 facts 中提取文件引用）
    document_refs=_extract_document_refs(fact_refs, facts),
    # 新增：填充 rag_query_used
    rag_query_used=f"DPIA evidence builder for {issue.issue_id}",
    rag_hits_count=len(regulations),
)
```

2. `backend/domains/cn/pipia/service.py` — 找到 `_build_evidence_chain` 方法，应用相同填充模式。

3. `backend/domains/cn/security_assessment/evidence_builder.py` — 同样填充 `legal_basis`、`document_refs`、`rag_query_used`。

4. `backend/domains/us/eo14117/evidence_builder.py` — 同样填充。

5. 新增通用辅助函数 `extract_document_refs()`：

```python
# 在 backend/common/workflow/evidence.py 或各 evidence_builder 中
def extract_document_refs(fact_refs: list[str], facts: list[FactItem]) -> list[DocumentRef]:
    """Extract document references from facts that have supporting_material_refs."""
    fact_map = {f.fact_id: f for f in facts}
    refs: list[DocumentRef] = []
    for fact_id in fact_refs:
        fact = fact_map.get(fact_id)
        if fact and hasattr(fact, 'supporting_material_refs') and fact.supporting_material_refs:
            for ref in fact.supporting_material_refs:
                if isinstance(ref, dict):
                    refs.append(DocumentRef(**ref))
                elif hasattr(ref, 'file_name'):
                    refs.append(ref)
    return refs
```

**验证命令**：
```bash
# 验证各模块 evidence_chain 三字段填充率
python -c "
import json

def check_evidence(result_path):
    r = json.load(open(result_path))
    chain = r.get('evidence_chain', [])
    if not chain:
        chain = r.get('generation_basis_snapshot', {}).get('evidence_chain', [])
    total = len(chain)
    legal = sum(1 for e in chain if e.get('legal_basis'))
    docs = sum(1 for e in chain if e.get('document_refs'))
    rag = sum(1 for e in chain if e.get('rag_query_used'))
    print(f'{result_path}: {total} items, legal_basis={legal}/{total}, doc_refs={docs}/{total}, rag={rag}/{total}')

for path in ['tmp/assessment/_result.json', 'tmp/dpia/_result.json', 'tmp/us_14117/_result.json']:
    check_evidence(path)
"  # 期望：三字段填充率均 ≥ 50%
```

**完成标准**：
- assessment evidence_chain：legal_basis ≥ 3/5、document_refs ≥ 1/5、rag_query_used ≥ 1/5
- dpia evidence_chain：legal_basis ≥ 6/12、document_refs ≥ 1/12、rag_query_used ≥ 1/12
- us_14117 evidence_chain：legal_basis ≥ 3/5、document_refs ≥ 1/5、rag_query_used ≥ 1/5

---

## 四、并行任务组 B：业务逻辑缺陷修复（依赖：A1 完成）

> 说明：B 组任务是对已生成报告内容的**质量提升**，而非阻断性修复。若 A 组修复后 LLM 已可用，B 组才能获得有实质内容的报告正文供验证。

### 子任务 B1：assessment 路径矛盾 → PATH_MISMATCH 早期中断（依赖：A1）

**根因**：
- `backend/domains/cn/security_assessment/service.py` — assessment pipeline 中，`path_judgment` 推荐了 scc_or_certification，但系统继续生成了完整的 8 章安全评估报告
- consistency_check 虽发现了矛盾（`consistency_issues[0]`），但仅在报告末尾标注，未中断流程
- 正确行为：诊断路径 ≠ 安全评估 → 返回 PATH_MISMATCH 状态，不生成安全评估报告

**修复代码位置**：

1. 定位 assessment service 中的 path_judgment 执行后检查点。在 `path_judgment` 结果返回后、章节生成前，增加路径一致性闸门：

```python
# 在 assessment service 中，path_judgment 之后插入：
if path_judgment and path_judgment.recommended_path != "security_assessment":
    logger.warning(
        "Path mismatch: diagnosis recommends %s but module is security_assessment",
        path_judgment.recommended_path,
    )
    return AssessmentResult(
        task_id=run_task_id,
        state="PATH_MISMATCH",
        path_judgment=path_judgment,
        mismatch_detail=(
            f"合规路径诊断推荐 {path_judgment.recommended_path}，"
            f"当前操作模块为安全评估路径，两者不匹配。"
            f"请切换到 {path_judgment.recommended_path} 对应的操作模块。"
        ),
    )
```

2. 在 `AssessmentResult` Schema 中增加 `state: Literal["COMPLETED", "FAILED", "PATH_MISMATCH"]` 和 `mismatch_detail: str` 字段。

3. 前端根据 `state=PATH_MISMATCH` 展示路径不匹配提示 + 一键跳转按钮。

**验证命令**：
```bash
# 用已知不触发安全评估的 case 运行
python -m backend.modules.assessment.cli run --case assessment-non-ciio 2>&1
python -c "
import json
r = json.load(open('tmp/assessment/_result.json'))
assert r['state'] == 'PATH_MISMATCH', f'Expected PATH_MISMATCH, got {r[\"state\"]}'
assert 'scc' in r.get('mismatch_detail', ''), 'Mismatch detail should mention scc'
print('PASS: PATH_MISMATCH correctly returned')
"
```

**完成标准**：
- 路径不匹配时 state=PATH_MISMATCH，不再生成安全评估报告 markdown
- 路径匹配时 state=COMPLETED，正常生成 8 章报告
- mismatch_detail 包含明确的建议路径

---

### 子任务 B2：pipia Issue 拆解为多条独立 IssueItem（依赖：A1）

**根因**：
- `backend/domains/cn/pipia/service.py` 的 `_build_structured_issues()` 仅产出 1 条聚合 Issue（"风险等级较高"）
- 但正文实际分析了 5 个独立法律维度：告知同意缺陷、敏感信息误分类、接收方保障不足、标准合同条款缺失、行权机制缺位

**修复代码位置**：

1. 将 `_build_structured_issues()` 改为返回多条 IssueItem，按法律维度拆分：

```python
def _build_structured_issues(self, payload, level) -> tuple[list[IssueItem], list]:
    issues = []
    # 根据 facts 和 rules 自动拆分 Issue 维度
    # 1. 告知同意缺陷
    consent_facts = [f for f in self._facts if "consent" in f.field_path.lower() or "同意" in f.description]
    if consent_facts:
        issues.append(IssueItem(
            issue_id="PIPIA-ISSUE-consent-deficiency",
            title="告知同意机制存在缺陷",
            description="当前告知同意机制未能覆盖全部数据处理场景，或同意记录不完整",
            severity="HIGH",
            fact_refs=[f.fact_id for f in consent_facts],
            rule_refs=["CN-LAW-001-13", "CN-LAW-001-17"],
        ))
    # 2. 敏感信息分类
    sensitive_facts = [f for f in self._facts if "敏感" in f.description or "special_category" in f.field_path]
    if sensitive_facts:
        issues.append(IssueItem(
            issue_id="PIPIA-ISSUE-sensitive-misclassification",
            title="敏感个人信息分类不准确",
            description="部分数据项可能属于敏感个人信息但未被正确分类",
            severity="HIGH",
            fact_refs=[f.fact_id for f in sensitive_facts],
            rule_refs=["CN-LAW-001-28", "CN-LAW-001-29"],
        ))
    # 3. 接收方保障
    # 4. 标准合同条款
    # 5. 行权机制
    # ...
    return issues, material_gaps
```

2. 每条 Issue 必须关联事实引用（`fact_refs` 不为空，从 22 条可用 facts 中选取相关事实）。

**验证命令**：
```bash
python -c "
import json
r = json.load(open('tmp/pipia/_result.json'))
issues = r.get('issues', [])
print(f'Issues count: {len(issues)}')  # 期望 ≥ 3
for i in issues:
    print(f'  {i[\"issue_id\"]}: {len(i.get(\"fact_refs\", []))} fact_refs, {len(i.get(\"rule_refs\", []))} rule_refs')
    assert len(i.get('fact_refs', [])) > 0, f'{i[\"issue_id\"]} has zero fact_refs'
    assert len(i.get('rule_refs', [])) > 0, f'{i[\"issue_id\"]} has zero rule_refs'
print('PASS: issues correctly linked to facts and rules')
"
```

**完成标准**：
- pipia issues ≥ 3 条独立 IssueItem
- 每条 issue 的 fact_refs ≥ 1
- 每条 issue 的 rule_refs ≥ 1

---

### 子任务 B3：eu_scc findings original_text 补充（依赖：无，可与 B1/B2 并行）

**根因**：
- `compare_standard_clauses()` 在文件解析结果中未找到可匹配的段落文本时，标记了 issue_type/severity，但 original_text 保留为 null
- 需求规定条款级审查必须包含原文引用（6 要素之首）

**修复代码位置**：

1. 定位 eu_scc 的 clause comparison 逻辑（`backend/domains/eu/scc_review/` 目录下），在标记 issue_type 的同时，强制 fallback 提取：

```python
# 在条款比较逻辑中增加：
if not original_text:
    # Fallback: 尝试从上传的 SCC 文档中定位对应条款号的段落
    original_text = _extract_clause_text_by_number(uploaded_docx, clause_number)
    if not original_text:
        # 终极 Fallback: 标注为"无法在文档中定位原文"
        original_text = f"【无法定位】SCC Clause {clause_number} 正文在已上传文档中未找到"
```

2. `suggested_text` 同理，当无法自动生成时，至少给出"建议使用 EU 2021/914 标准文本"并附标准条款链接。

**验证命令**：
```bash
python -c "
import json
r = json.load(open('tmp/eu_scc/_result.json'))
findings = r.get('findings', [])
total = len(findings)
has_original = sum(1 for f in findings if f.get('original_text'))
has_suggested = sum(1 for f in findings if f.get('suggested_text'))
print(f'findings: {total}, original_text filled: {has_original}/{total}, suggested_text filled: {has_suggested}/{total}')
assert has_original >= total * 0.5, f'Original text coverage too low: {has_original}/{total}'
"  # 期望：original_text 覆盖率 ≥ 50%
```

**完成标准**：
- eu_scc findings original_text 覆盖率 ≥ 50%（之前 2/8 = 25%）
- suggested_text 覆盖率 ≥ 50%（之前 1/8 = 12.5%）

---

### 子任务 B4：bcr 模板变量替换（依赖：无，可与 B1/B2/B3 并行）

**根因**：
- `bcr_rulebook.json` 中 `suggested_text` 字段包含 `[Company Name]`、`[EU Member State]` 模板变量
- Agent/renderer 未执行变量替换

**修复代码位置**：

1. 在 bcr report renderer 或 Agent 输出后处理中增加变量替换步骤：

```python
# bcr 报告生成后、markdown 写入前
def _fill_template_variables(text: str, payload: BCRRequest) -> str:
    replacements = {
        "[Company Name]": payload.company_name or "【请填写公司名称】",
        "[EU Member State]": payload.eu_member_state or "【请填写欧盟成员国】",
        "[Insert specific clause...]": "【请根据实际条款文本补充】",
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text
```

2. 若 payload 中未提供 `company_name` 和 `eu_member_state`（用户输入时未填写），则保留用户可见占位符 `【请填写公司名称】` 而非代码模板变量 `[Company Name]`。

**验证命令**：
```bash
grep -c "\[Company Name\]" tmp/bcr/markdown.md  # 应为 0
grep -c "\[EU Member State\]" tmp/bcr/markdown.md  # 应为 0
grep -c "Insert specific clause" tmp/bcr/markdown.md  # 应为 0
```

**完成标准**：
- bcr markdown 中 `[Company Name]`、`[EU Member State]`、`[Insert specific clause...]` 出现次数 = 0

---

### 子任务 B5：us_14117 markdown 结构化渲染（依赖：A1）

**根因**：
- 2026-08-10 交叉验核：us_14117 markdown 仅 15 行 854 字符，整篇为 1 个超长行（无标题/换行）
- `rule_hits` 有 24 条结构化数据，但未能以表格/清单形式渲染到 markdown

**修复代码位置**：

1. 检查 us_14117 的章节生成逻辑（`chapter_generator.py` 或 `report_renderer.py`），确认模板输出包含 Markdown 标题层级：

```python
# 修复：确保每个章节以 ## 标题开始，列表项以 - 或 1. 格式
chapter_template = """## {title}

### 实体分类结果

{entity_classifications}

### 阈值触发明细

{threshold_details}

### 受限制主体清单

{covered_persons}

### 安全措施缺口状态

{security_gaps}
"""
```

2. 修复 markdown 生成中的换行符问题：确认 `normalize_legal_markdown_structure()` 正确处理 us_14117 的中文文本。

**验证命令**：
```bash
# 检查 markdown 结构
python -c "
with open('tmp/us_14117/markdown.md') as f:
    content = f.read()
lines = content.split('\n')
print(f'Total lines: {len(lines)}')
print(f'Chars: {len(content)}')
headings = [l for l in lines if l.startswith('#')]
print(f'Headings: {len(headings)}')
for h in headings:
    print(f'  {h[:80]}')
assert len(lines) >= 40, f'Expected at least 40 lines, got {len(lines)}'
assert len(headings) >= 4, f'Expected at least 4 headings, got {len(headings)}'
print('PASS: us_14117 markdown is well-structured')
"  # 期望：≥ 40 行，≥ 4 个标题
```

**完成标准**：
- us_14117 markdown 行数 ≥ 40、字符数 ≥ 3000、标题数 ≥ 4
- 包含 4 个规范要求的要素：实体分类、阈值明细、受限主体清单、安全措施缺口

---

## 五、并行任务组 C：渲染/质量门禁修复（依赖：A1/B 组无依赖，可独立执行）

### 子任务 C1：pipia 测试元信息过滤（依赖：无）

**修复代码位置**：
- `backend/domains/cn/pipia/service.py` 的章节生成或 markdown 渲染阶段，增加"测试夹具声明"的过滤正则：

```python
_TEST_DISCLAIMER_RE = re.compile(
    r"附件摘要.*?文件性质.*?不是案例原文附件.*?不能作为真实备案材料",
    re.DOTALL,
)
# 在 markdown 写入前：
content = _TEST_DISCLAIMER_RE.sub("", content)
```

**验证命令**：
```bash
grep -c "不是案例原文附件" tmp/pipia/markdown.md  # 应为 0
grep -c "不能作为真实备案材料" tmp/pipia/markdown.md # 应为 0
```

---

### 子任务 C2：tia "推测"措辞替换（依赖：无）

**修复代码位置**：
- `backend/domains/eu/tia/` 的章节生成 prompt 中增加禁止词约束：

```python
# 在 system prompt 中增加：
"""
措辞规则：
- 正式 TIA 报告中不得出现 "推测"、"猜测"、"可能"（不确定场景应使用 "需补充信息确认"）
- 不得出现工程标记如 【待核验】、【推测】、【暂缺】
- 信息不足时应标注 "需补充信息以确认" 而非主观推测
"""
```

**验证命令**：
```bash
grep -c "【推测】" tmp/tia/markdown.md  # 应为 0
grep -n "推测" tmp/tia/markdown.md      # 检查所有"推测"出现（非【推测】标记的）
```

---

### 子任务 C3：assessment material_checklist 补充（依赖：A1）

**修复代码位置**：
- `backend/domains/cn/security_assessment/` 的 material_checklist 构建逻辑，从仅依赖上传文件检测，改为基于安全评估申报指南的固定清单模板：

```python
_SECURITY_ASSESSMENT_CHECKLIST = [
    {"item": "营业执照或统一社会信用代码证书", "required": True, "source": "企业提供"},
    {"item": "数据出境安全评估申报书", "required": True, "source": "系统生成"},
    {"item": "数据出境合同或法律文件", "required": True, "source": "企业上传"},
    {"item": "数据出境风险自评估报告", "required": True, "source": "系统生成"},
    {"item": "数据处理者基本情况说明", "required": True, "source": "企业填写"},
    {"item": "数据出境涉及的数据清单", "required": True, "source": "企业上传"},
    {"item": "境外接收方数据保护能力说明", "required": True, "source": "企业上传"},
    {"item": "隐私政策或个人信息保护政策", "required": False, "source": "企业上传"},
    {"item": "数据处理协议（DPA）", "required": False, "source": "企业上传"},
    # ... 共 20+ 项
]

def _build_material_checklist(self, payload, uploaded_files) -> list[MaterialChecklistItem]:
    items = []
    for template_item in _SECURITY_ASSESSMENT_CHECKLIST:
        found = any(template_item["item"] in f for f in uploaded_files)
        status = "已提供" if found else ("待补充" if template_item["required"] else "建议提供")
        items.append(MaterialChecklistItem(
            item=template_item["item"],
            required=template_item["required"],
            status=status,
            source=template_item["source"],
        ))
    return items
```

**验证命令**：
```bash
python -c "
import json
r = json.load(open('tmp/assessment/_result.json'))
mc = r.get('profile', {}).get('material_checklist_json', '')
if mc:
    mc = json.loads(mc) if isinstance(mc, str) else mc
    print(f'Material checklist items: {len(mc)}')
    assert len(mc) >= 10, f'Expected at least 10 items, got {len(mc)}'
else:
    print('WARNING: material_checklist_json is empty string')
"  # 期望：≥ 10 项（之前仅 1 项）
```

**完成标准**：
- assessment material_checklist 条目数 ≥ 10
- 包含"已提供"/"待补充"/"建议提供"三种状态

---

### 子任务 C4：各模块 state 从硬编码 COMPLETED 改为基于质检（依赖：A1）

**根因**：
- `backend/domains/eu/dpia/service.py:530` — `state="COMPLETED"` 硬编码
- 多个模块同样模式

**修复代码位置**：

1. 各模块 service 中，在返回 result 前增加质检函数：

```python
def _check_chapter_quality(chapters: list, llm_enabled: bool) -> str:
    """Determine task state based on chapter content quality."""
    if not chapters:
        return "FAILED"
    placeholder_count = sum(
        1 for ch in chapters
        if "占位" in ch.content or "LLM未配置" in ch.content
    )
    total_count = len(chapters)
    if placeholder_count == total_count:
        return "FAILED"
    if placeholder_count > 0:
        return "PARTIAL"
    if not llm_enabled and placeholder_count == 0:
        return "COMPLETED_FALLBACK"  # 规则引擎填充，但非 LLM 生成
    return "COMPLETED"
```

2. 扩展 state 类型：

```python
# 在 workflow/state.py 中扩展 TaskState
TaskState = Literal[
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_FALLBACK",   # 新增：填充完成但基于降级模板
    "PARTIAL",              # 新增：部分章节可用
    "FAILED",
    "PATH_MISMATCH",        # 新增：路径不匹配，未生成报告
    "CANCELLED",
]
```

3. 应用到各模块：
   - `backend/domains/eu/dpia/service.py:530` — 替换硬编码
   - `backend/domains/cn/pipia/service.py` — 替换硬编码
   - `backend/domains/us/cpra/service.py` — 替换硬编码
   - `backend/domains/cn/security_assessment/service.py` — 替换硬编码

**验证命令**：
```bash
python -c "
import json
for mod in ['assessment', 'dpia', 'pipia']:
    try:
        r = json.load(open(f'tmp/{mod}/_result.json'))
        state = r.get('state', 'UNKNOWN')
        print(f'{mod}: state={state}')
        assert state in ('COMPLETED', 'COMPLETED_FALLBACK', 'PARTIAL', 'FAILED', 'PATH_MISMATCH'), \
            f'Invalid state: {state}'
    except FileNotFoundError:
        print(f'{mod}: not run yet')
"  # 所有 state 应为有效枚举值
```

**完成标准**：
- 所有模块 state 为有效 TaskState 枚举值之一
- dpia（LLM 启用时）state = COMPLETED
- pipia（LLM 未启用时）state ≠ COMPLETED（应为 COMPLETED_FALLBACK 或 PARTIAL）

---

## 六、Phase D：全模块重新运行 + 最终交叉验核

### 执行步骤

```bash
# 1. 全模块批量运行（使用已有测试 cases）
bash scripts/run_all_modules.sh 2>&1 | tee tmp/verify/run_all_$(date +%Y%m%d).log

# 2. 生成交叉验核矩阵
python scripts/check_cross_verification.py \
    --audit tmp_review_audit_20260809.md \
    --outputs tmp/ \
    --output tmp/verify/cross_verification_$(date +%Y%m%d).json

# 3. 逐项对照审计报告的 40 个问题
python scripts/generate_verification_report.py \
    --cross-matrix tmp/verify/cross_verification_$(date +%Y%m%d).json \
    --output tmp/verify/final_verification_report.md
```

### 最终验收标准

| 指标 | 当前值（2026-08-10） | 目标值 |
|------|:---:|:---:|
| 脚注覆盖率（跨模块平均） | ~39% | ≥ 70% |
| evidence_chain 三字段填充率 | 0-21% | ≥ 50% |
| 占位文本出现模块数 | 1 (pipia) | 0 |
| PATH_MISMATCH 正确处理 | ❌ 未实现 | ✅ |
| 假 COMPLETED 状态 | pipia 占位仍 COMPLETED | COMPLETED_FALLBACK |
| us_14117 markdown 行数 | 15 行 | ≥ 40 行 |
| bcr 模板变量泄漏 | 0（已修复） | 0（保持） |
| tia `【待核验】` 标记 | 0（已修复） | 0（保持） |
| assessment material_checklist | 1 项 | ≥ 10 项 |
| eu_scc findings original_text | 2/8 (25%) | ≥ 4/8 (50%) |

---

## 七、执行依赖关系图

```
Level 0 (无依赖，立即并行启动):
  ├── A1 (pipia LLM启用 + ExecutionGuard)
  ├── A2 (CIT [N]兼容 + system prompt强化)
  ├── A3 (evidence_chain 三字段填充)
  ├── C1 (pipia 测试元信息过滤)
  ├── C2 (tia "推测"措辞)
  └── B4 (bcr 模板变量替换)

Level 1 (依赖 A1 — LLM启用后验证):
  ├── B1 (assessment PATH_MISMATCH)
  ├── B2 (pipia Issue 拆解)
  ├── B3 (eu_scc original_text)
  ├── B5 (us_14117 markdown 结构化)
  └── C3 (assessment material_checklist)

Level 2 (依赖 A1 + A2 — LLM + CIT 都修复后):
  └── C4 (state 质检机制)

Level 3 (依赖全部):
  └── D  (全模块重运行 + 交叉验核)
```

---

## 八、风险与回退策略

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:---:|:---:|------|
| A1 修复后 pipia LLM 输出质量差 | 中 | 中 | 保留 rule_based 模板作为 fallback，C4 的 COMPLETED_FALLBACK 状态保护 |
| A2 [N] 格式兼容引入新正则误判 | 低 | 中 | `_resolve_numeric_footnotes` 需 registry 中对 citation_id 做严格校验，不与普通数字混淆 |
| A3 evidence_builder 改动影响多模块 | 中 | 低 | 每个模块单独修改，公共辅助函数 `extract_document_refs` 放在 workflow/evidence.py，各模块独立 opt-in |
| B1 PATH_MISMATCH 导致用户无法看到任何报告 | 低 | 高 | 提供"强制生成报告"选项 + 前端展示路径不匹配原因 |

---

## 九、附录：审计报告问题 → 修复映射表

| 审计问题的编号 | 问题 | 修复子任务 | 修复优先级 |
|:---:|------|:---:|:---:|
| C-COMMON-1 | LLM 静默失败 → 4模块占位 | A1 | P0 |
| C-COMMON-2 | CIT 标记崩溃 → 脚注全空 | A2 | P0 |
| C-COMMON-3 | evidence_chain 三字段全空 | A3 | P0 |
| C-COMMON-5 | 假 COMPLETED 状态 | C4 | P1 |
| C-COMMON-4 | 工程标注泄漏 | ✅ 已修复 | — |
| C-COMMON-6 | supporting_material_refs 空 | A3（部分） | P1 |
| C-COMMON-7 | document_ir 段落空 | *暂缓* | P2 |
| BIZ-1 | assessment 路径矛盾 | B1 | P0 |
| BIZ-3 | pipia 1 Issue→5维分析 | B2 | P1 |
| BIZ-5 | eu_scc 12处"未提供" | B3 | P1 |
| BIZ-6 | bcr 模板变量泄漏 | B4 | P0 |
| BIZ-7 | eu_scc 6/8无 original_text | B3 | P1 |
| BIZ-11 | assessment 材料清单仅1项 | C3 | P2 |
| BIZ-12 | us_14117 无结构化 | B5 | P1 |
| BIZ-15 | tia "推测"措辞 | C2 | P3 |
| BIZ-16 | pipia 测试元信息泄漏 | C1 | P2 |
| R3 | pipia CIT标记截断 | A1 + A2 | P0 |
| R8 | us_14117 markdown坍塌 | B5 | P1 |
| ID-1 | EvidenceItem字段零填充 | A3 | P0 |
| ID-4 | issue无fact/rule引用 | B2 | P1 |
| ID-6 | assessment 4个JSON全空 | A1 + C3 | P0 |
| ID-11 | rule_hits无category | B5（附带） | P2 |
