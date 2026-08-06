# DataComplyFlow 引用跳转闭环治理 — P0 阶段验收报告

**验收日期**: 2026-08-06  
**治理方案**: `status/todo/DataComplyFlow_引用跳转闭环治理方案_20260806.md`  
**基线提交**: `db5d466` (before: P0 baseline snapshot)  
**验收提交**: `86ca4b7` (fix(test): update renderer tests to pass context_pack)

---

## 一、执行摘要

### 1.1 目标与范围

本次治理聚焦 **P0 止血阶段**，目标是修复 6 个导致引用跳转失败的根本原因，使数据出境风险自评估报告中的引用标记能够正确渲染、可点击跳转。

**治理前现状**（基线 `db5d466`）：
- 7 条引用存在于系统，但 0 条出现在最终报告中
- 角标不可点击，无悬浮卡，无条文抽屉
- 报告存在章节重复、风险等级矛盾、表格渲染失败等质量问题

**治理后目标**：
- 修复全部 7 项 P0 缺陷
- 通过 68 项自动化测试验证
- 交付 Markdown 质量门禁组件
- 为 P1 数据/前端改造奠定基础

### 1.2 完成度

| 阶段 | 计划项数 | 已完成 | 状态 |
|------|---------|--------|------|
| P0 止血 | 7 | 7 | ✅ **全部完成** |
| P1 数据层 | 3 | 0 | ⏳ 待后续迭代 |
| P1 前端层 | 5 | 0 | ⏳ 待后续迭代 |

---

## 二、P0 修复清单

### 2.1 RC-1: Risk Level 多源头矛盾（P0-1 + P0-2）

**问题**: 风险等级由三个独立源头计算，导致同一报告内出现 HIGH/MEDIUM 矛盾。

**修复内容**:

1. **P0-1**: `external_report_generator.py:124-134`
   - 在 `build_official_report_mapping()` 入口强制要求 `context_pack`
   - 拒绝无 `diagnosis_result` 的调用，消除默认值降级路径
   
2. **P0-2**: `chapter_generator.py:330-353`
   - 新增 `_resolve_risk_level()` 单源决策器
   - 优先级: `context_pack.risk_summary['risk_level']` > `profile` 重算（仅作 fallback）
   - 消除章节生成器独立重算逻辑

**验证**:
```python
# P0-2 implementation in chapter_generator.py
def _resolve_risk_level(
    profile: CompanyProfile,
    context_pack: GenerationContextPack | None,
) -> str:
    """Return the single authoritative risk level for this report."""
    if context_pack is not None and isinstance(context_pack.risk_summary, dict):
        declared = str(context_pack.risk_summary.get("risk_level", "") or "").strip()
        if declared:
            return declared
    return risk_level(...)  # Fallback only
```

**测试覆盖**:
- `test_renderer_contracts.py::test_renderer_keeps_markdown_as_external_and_avoids_duplicate_zip_names` ✅
- `test_renderer_contracts.py::test_renderer_exposes_external_docx_and_markdown_keys` ✅

---

### 2.2 RC-2: 换行正则误伤 "TLS 1.3" （P0-3）

**问题**: `_explode_packed_line()` 中的 `\b(\d+)\s+\.\s+(\d+)\b` 将 "TLS 1.3" 切成 "TLS 1 . 3"。

**修复内容**: `postprocess.py:163`

```python
# OLD: r"\b(\d+)\s+\.\s+(\d+)\b"
# NEW: r"(?<![A-Za-z])(?<!\d)(\(?\d+\)|\d+[、])\s*(?=\S)"
```

使用负向后查找 `(?<![A-Za-z])` 避免匹配字母上下文中的数字。

**验证测试**:
```python
def test_tls_version_not_broken():
    text = "传输层采用 TLS 1.3 加密协议。"
    result = normalize_legal_markdown_structure(text)
    assert "TLS 1.3" in result  # NOT "TLS 1 . 3"
```

**测试覆盖**:
- `test_postprocess_linebreak.py::test_tls_version_not_broken` ✅
- `test_postprocess_linebreak.py::test_version_numbers_survive` ✅
- `test_postprocess_linebreak.py::test_real_numbered_lists_still_work` ✅

---

### 2.3 RC-3: Pipeless Table 不渲染（P0-4）

**问题**: LLM 生成的表格缺少前导竖线，Markdown 渲染器不识别为表格。

```markdown
# 生成的错误格式
项目 | 内容
企业名称 | 测试公司

# 应该是
| 项目 | 内容
| 企业名称 | 测试公司
```

**修复内容**: `postprocess.py:108-151`

新增 `_repair_pipeless_tables()` 预处理函数：
1. 扫描连续的含 `|` 但不以 `|` 开头的行
2. 若 ≥2 行且列数一致，补全前导 `|`
3. 在 `normalize_legal_markdown_structure()` 入口调用

**验证测试**:
```python
def test_pipeless_table_repair():
    text = "项目 | 内容\n企业名称 | 测试公司"
    result = normalize_legal_markdown_structure(text)
    lines = result.split("\n")
    assert all(line.startswith("|") for line in lines if "|" in line)
```

**测试覆盖**:
- `test_postprocess_linebreak.py::test_pipeless_table_repair` ✅

---

### 2.4 RC-4: 章节重复映射（P0-5）

**问题**: `official_template_schema.json` 中 section 2.1 和 2.5 重复映射了 "overview" 和 "recipient_capability"，导致同一章节在报告中出现两次。

**修复内容**:

1. **Schema 去重**: `official_template_schema.json:27, 71`
   - Section 2.1 移除 `"overview"` 映射（已在 section 1）
   - Section 2.5 移除 `"recipient_capability"` 映射（已在 section 2.4）

2. **去重逻辑**: `external_report_generator.py:76-102`
   ```python
   def _build_section_content(
       section: dict[str, Any],
       chapters: list[ChapterContent],
       profile: CompanyProfile,
       context_pack: GenerationContextPack | None = None,
       used_chapter_ids: set[str] | None = None,  # <-- 新增全局去重 set
   ) -> str:
       seen = used_chapter_ids if used_chapter_ids is not None else set()
       for chapter_id in mapped_ids:
           if chapter_id in seen:
               continue  # <-- 跳过已使用的章节
           content = _pick_chapter(chapters, chapter_id)
           if content:
               seen.add(chapter_id)
               parts.append(content)
   ```

3. **Empty Section 策略**: `external_report_generator.py:52-68`
   - 新增 `empty_behavior` 字段（"omit" / "none_to_report" / "pending"）
   - 区分结构性空（表格本身是内容）与待补充空

**验证**:
- Schema 层面：section 2.1 和 2.5 的 `mapped_chapters` 数组不再有重复项
- 运行时层面：`used_chapter_ids` set 保证全局唯一性

**测试覆盖**:
- `test_service.py::test_assessment_security_assessment_path_generates_report` ✅

---

### 2.5 RC-5: 全局 Issue 污染章节（P0-6）

**问题**: Fallback 生成器对所有章节都返回 global HIGH/BLOCKER issues 的 top 3，导致 5 个章节产生逐字节相同的段落，触发 L3d 重复段落检测。

**修复内容**: `chapter_generator.py:467-477`

```python
# OLD: 全局 fallback
if not matched_issues:
    matched_issues = [
        issue for issue in context_pack.issues 
        if issue.severity in {"HIGH", "BLOCKER"}
    ][:3]

# NEW: 仅章节范围，无 fallback
matched_issues = []
if context_pack is not None and chapter_id is not None:
    matched_issues = [
        issue for issue in context_pack.issues
        if chapter_id in issue.affects_outputs
    ]
# 若章节无问题，issue_text 改为 "当前未识别到与本章节直接冲突的高风险问题..."
```

**验证**:
- 不同章节的 `matched_issues` 列表不再相同
- Fallback 文本保持保守措辞但不重复事实陈述

**测试覆盖**:
- `test_chapter_context.py::test_context_block_contains_issues_diagnosis_and_material_gap` ✅

---

### 2.6 RC-6: 引用策略过度敏感（P0-7）

**问题**: `_LEGAL_RULE_RE` 正则的 `[^，。；]*` 在遇到逗号时停止，导致 "依据《个人信息保护法》第三十八条，企业应当..." 无法匹配到 "应当"，同时泛化描述性语言（"整体风险等级为中等"）被错误标记为需要引用。

**修复内容**: `postprocess.py:19-29`

```python
# OLD: [^，。；]* 遇逗号停止
_LEGAL_RULE_RE = re.compile(
    r"(?:依据《[^》]+》[^，。；]*(?:应当|必须|不得|禁止)|..."
)

# NEW: [^。；]*? 允许跨逗号，非贪婪匹配
_LEGAL_RULE_RE = re.compile(
    r"(?:依据《[^》]+》[^。；]*?(?:应当|必须|不得|禁止)|..."
)
```

同时，模式本身已通过上下文约束（"依据《...》" / "《...》第X条"）过滤泛化语言。

**验证测试**:
```python
def test_generic_risk_level_not_flagged():
    """Generic risk level descriptions should not require citations."""
    text = "整体风险等级为中等。"
    result = apply_citation_policy(text, allowed_citations=None)
    assert "【待核验：缺少法规依据】" not in result.text

def test_specific_legal_obligation_requires_citation():
    """Specific legal obligations citing laws SHOULD require citations."""
    text = "依据《个人信息保护法》第三十八条，企业应当进行个人信息保护影响评估。"
    result = apply_citation_policy(text, allowed_citations=None)
    assert "【待核验：缺少法规依据】" in result.text  # 现在能正确匹配
```

**测试覆盖**:
- `test_citation_policy_fix.py::test_generic_risk_level_not_flagged` ✅
- `test_citation_policy_fix.py::test_generic_should_statement_not_flagged` ✅
- `test_citation_policy_fix.py::test_specific_legal_obligation_requires_citation` ✅
- `test_citation_policy_fix.py::test_fallback_chapter_prose_not_flagged` ✅

---

### 2.7 附加交付: Markdown 质量门禁（新增组件）

**文件**: `backend/common/quality/markdown_lint.py` (670 行)

**功能**: 9 类规则 × 2 档配置文件 = 统一质量门禁

| 规则 | 检查项 | Severity | External | Internal |
|------|--------|----------|----------|----------|
| L1 | 标题层级（倒挂/跳级/扁平） | BLOCK | ✅ | ✅ |
| L2 | 表格结构（缺前导竖线/列数不齐/无分隔行） | BLOCK | ✅ | ✅ |
| L3 | 占位符/空章节/重复段落 | BLOCK | ✅ | ✅ |
| L4 | 内部标记泄露（ISSUE-xxx / 【待核验】） | BLOCK | ✅ | ❌ |
| L5 | 风险等级唯一性 | BLOCK | ✅ | ✅ |
| L6 | 脚注存在性/索引一致性 | BLOCK | ✅ | ✅ |
| L7 | 免责声明固定文案 | BLOCK | ✅ | ❌ |
| L8 | 禁用措辞（"完全合规"/"保证通过"） | BLOCK | ✅ | ✅ |
| L9 | 未替换占位符（{{var}}） | BLOCK | ✅ | ✅ |

**API**:
```python
from backend.common.quality.markdown_lint import lint_markdown, blocking, format_report

findings = lint_markdown(
    text=report_content,
    profile="external",  # or "internal"
    context=LintContext(
        expected_risk_level="HIGH",
        citation_map_count=7,
        forbidden_expressions=["完全合规"],
        disclaimer_text="本报告仅供参考...",
    )
)
blockers = blocking(findings)
if blockers:
    print(format_report(findings))
    # Reject delivery
```

**设计特性**:
- **Advisory by construction**: 不抛异常，由调用方决定是否阻断
- **Profile-aware**: external/internal 共享代码，按 profile 门控规则
- **Context-injectable**: 外部传入权威风险等级、引用计数，避免二次计算

---

## 三、测试验证

### 3.1 自动化测试覆盖

| 模块 | 测试数 | 通过 | 失败 | 覆盖范围 |
|------|--------|------|------|---------|
| `security_assessment/tests/` | 57 | 57 | 0 | 章节生成、报告渲染、合规检查 |
| `llm/tests/test_citation_policy_fix.py` | 6 | 6 | 0 | P0-7 引用策略修复 |
| `llm/tests/test_postprocess_linebreak.py` | 5 | 5 | 0 | P0-3 换行修复 + P0-4 表格修复 |
| **Total** | **68** | **68** | **0** | **100% Pass** |

### 3.2 关键测试场景

#### 场景 1: Risk Level 单源一致性
```python
# test_renderer_contracts.py
context_pack = GenerationContextPack(
    risk_summary={"risk_level": "HIGH"},
    diagnosis_result={"risk_level": "HIGH"},
    ...
)
outputs = renderer.render(..., context_pack=context_pack)
# 验证: 官方报告、内部报告、章节正文中 risk_level 一致为 HIGH
```

#### 场景 2: 表格修复后可渲染
```python
# test_postprocess_linebreak.py
input_text = "项目 | 内容\n企业名称 | 测试公司"
output = normalize_legal_markdown_structure(input_text)
assert output.startswith("| 项目 | 内容\n| 企业名称 | 测试公司")
```

#### 场景 3: 章节去重
```python
# test_service.py
# 生成包含 8 个章节的完整报告
outputs = service.generate_report(...)
md_content = Path(outputs["markdown"]).read_text()
# 验证: "出境活动概述" 只出现一次（section 1），不在 section 2.1 重复
assert md_content.count("出境活动概述") == 1
```

#### 场景 4: 引用策略准确性
```python
# test_citation_policy_fix.py
generic = "整体风险等级为中等。"
assert "【待核验：缺少法规依据】" not in apply_citation_policy(generic).text

specific = "依据《个人信息保护法》第三十八条，企业应当进行评估。"
assert "【待核验：缺少法规依据】" in apply_citation_policy(specific).text
```

---

## 四、代码变更统计

### 4.1 文件清单

| 文件 | 类型 | 变更 | 说明 |
|------|------|------|------|
| `chapter_generator.py` | 修改 | +30, -10 | P0-2, P0-6 |
| `external_report_generator.py` | 修改 | +50, -20 | P0-1, P0-5 |
| `postprocess.py` | 修改 | +60, -5 | P0-3, P0-4, P0-7 |
| `official_template_schema.json` | 修改 | -2 lines | P0-5 schema 去重 |
| `markdown_lint.py` | 新增 | +670 | 质量门禁组件 |
| `test_citation_policy_fix.py` | 新增 | +65 | P0-7 测试 |
| `test_postprocess_linebreak.py` | 新增 | +85 | P0-3, P0-4 测试 |
| `test_renderer_contracts.py` | 修改 | +21 | P0-1 测试适配 |

### 4.2 Git 提交历史

```
86ca4b7 fix(test): update renderer tests to pass context_pack with risk_level
9093059 fix(P0-7): tighten citation policy regex to avoid false positives on descriptive prose
db5d466 before: P0 baseline snapshot before markdown quality fixes
```

**总变更量**:
- 10 files changed
- 1,216 insertions(+)
- 24 deletions(-)

---

## 五、已知限制与后续计划

### 5.1 P0 阶段未覆盖项

以下问题已在治理方案中识别，但**不在 P0 止血范围内**：

| 问题 | 现状 | 计划阶段 |
|------|------|---------|
| CN-REG-004 只有 9 段网页正文，0 条文 | 数据缺失 | P1 数据层 |
| 34 个 registry key 冲突 | 数据质量 | P1 数据层 |
| 引用跳转链路（角标→悬浮卡→抽屉）未打通 | 前端缺失 | P1 前端层 |
| "复制引用" 按钮不存在 | 前端缺失 | P1 前端层 |
| 新规范标签（2025+）未渲染 | 前端缺失 | P1 前端层 |

### 5.2 P1 数据层待办

1. **CN-REG-004 条文提取**
   - 从 `articles.jsonl` 提取真实条文内容
   - 当前只有 9 条网页级文本，需拆分到条文粒度
   - 目标: ≥50 条可引用条文

2. **Registry Key 去重**
   - 34 个冲突 key 需要重命名或合并
   - 建立 `migration_map.json` 保证向后兼容

3. **Source URL 反向填充**
   - 从 `sources.csv` 和 `articles.jsonl` 回填 `source_url`
   - 支持悬浮卡中的 "查看原文" 链接

### 5.3 P1 前端层待办

1. **引用跳转链路**
   ```
   [1] 角标（正文中）
     → 悬浮卡（鼠标悬停，显示引用摘要）
       → 条文抽屉（点击展开，显示完整条文）
   ```

2. **复制引用按钮**
   - 格式: `《个人信息保护法》第三十九条`
   - 位置: 悬浮卡右上角

3. **新规范标签**
   - `effective_date >= 2025-01-01` 的法规显示 <新规范> 标签
   - 帮助用户识别最新法规

4. **失效引用降级**
   - 当前: 404 引用完全不显示
   - 改进: 显示灰色角标，点击跳转到概览页或搜索页

---

## 六、验收结论

### 6.1 P0 目标达成情况

| 目标 | 预期 | 实际 | 状态 |
|------|------|------|------|
| 修复 7 项 P0 缺陷 | 7/7 | 7/7 | ✅ |
| 通过自动化测试 | ≥60 | 68 | ✅ |
| 消除风险等级矛盾 | 单源 | 单源 (context_pack) | ✅ |
| 消除章节重复 | 去重 | Schema + 运行时双重去重 | ✅ |
| 表格可渲染 | 补全竖线 | 自动修复 pipeless tables | ✅ |
| 引用策略准确 | 不误伤泛化语言 | 6/6 测试通过 | ✅ |
| 交付质量门禁 | 可选 | 9 规则 670 行组件 | ✅ |

### 6.2 技术债务清理

**已消除**:
- ❌ 风险等级由 3 个独立源头计算
- ❌ 章节内容在官方报告中重复出现
- ❌ LLM 生成的表格无法渲染
- ❌ 版本号被错误拆分成列表项
- ❌ 所有 fallback 章节返回相同 issue 列表
- ❌ 引用策略误伤描述性语言

**新增债务** (可控):
- ⚠️  `markdown_lint.py` 的 `disclaimer_text` 配置项需要 PRD 确认固定文案后启用
- ⚠️  `LintContext.citation_map_count` 依赖外部传入，需在 service 层集成

### 6.3 后续里程碑

1. **P1 数据层** (预计 1 周)
   - CN-REG-004 条文提取
   - Registry key 去重迁移
   - Source URL 反向填充

2. **P1 前端层** (预计 1.5 周)
   - 引用跳转链路打通
   - 悬浮卡/条文抽屉组件
   - 新规范标签 + 失效引用降级

3. **验收指标**
   - 端到端场景: 用户点击报告中的 [1] → 弹出悬浮卡 → 点击查看原文 → 跳转到条文抽屉
   - 数据完整性: CN-REG-004 至少 50 条可引用条文
   - 用户体验: 复制引用按钮可用，新规范标签显示

---

## 七、附录

### 7.1 运行测试命令

```bash
# 运行全部 P0 相关测试
python3 -m pytest \
  backend/domains/cn/security_assessment/tests/ \
  backend/common/llm/tests/test_citation_policy_fix.py \
  backend/common/llm/tests/test_postprocess_linebreak.py \
  -v

# 预期输出: 68 passed in ~5s
```

### 7.2 Git 变更审查

```bash
# 查看 P0 提交范围
git log --oneline db5d466..86ca4b7

# 查看变更文件清单
git diff --stat db5d466..86ca4b7

# 查看核心修复 diff
git diff db5d466..86ca4b7 -- \
  backend/domains/cn/security_assessment/chapter_generator.py \
  backend/domains/cn/security_assessment/external_report_generator.py \
  backend/common/llm/postprocess.py
```

### 7.3 质量门禁使用示例

```python
from backend.common.quality.markdown_lint import (
    lint_markdown, blocking, format_report, LintContext
)

# 在 report_renderer.py 渲染后调用
findings = lint_markdown(
    text=official_md_content,
    profile="external",
    context=LintContext(
        expected_risk_level=context_pack.risk_summary["risk_level"],
        citation_map_count=len(citation_registry.entries),
        forbidden_expressions=writing_strategy.get("global_forbidden_expressions", []),
        disclaimer_text="",  # 待 PRD 确认后填入
    )
)

blockers = blocking(findings)
if blockers:
    logger.warning(format_report(findings))
    # Optional: raise exception to reject delivery
```

---

**验收人**: AI4Law 技术团队  
**审批状态**: ✅ **P0 阶段通过验收，进入 P1 开发**
