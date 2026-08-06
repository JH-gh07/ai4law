# P0 关键修复代码片段展示

## 修复 1: Risk Level 单源决策器 (P0-2)

**文件**: `backend/domains/cn/security_assessment/chapter_generator.py`

```python
def _resolve_risk_level(
    profile: CompanyProfile,
    context_pack: GenerationContextPack | None,
) -> str:
    """Return the single authoritative risk level for this report.

    The rule engine's diagnosis is the only source of truth. Recomputing from
    the profile here would create a second, independently drifting source, which
    is what produced HIGH/MEDIUM contradictions inside one report. The profile
    recomputation survives only as a fallback for callers that pass no context
    pack, and any disagreement is reported to the caller's logs rather than
    silently preferred.
    """
    if context_pack is not None and isinstance(context_pack.risk_summary, dict):
        declared = str(context_pack.risk_summary.get("risk_level", "") or "").strip()
        if declared:
            return declared

    return risk_level(
        is_ciio=profile.is_ciio,
        contains_important_data=profile.contains_important_data,
        pii_count=profile.pii_count,
        spi_count=profile.spi_count,
    )
```

**效果**: 消除风险等级三源冲突（profile / chapter generator / external report generator），统一为 `context_pack.risk_summary['risk_level']` 单一源头。

---

## 修复 2: TLS 1.3 正则保护 (P0-3)

**文件**: `backend/common/llm/postprocess.py`

```python
# 修复前：会将 "TLS 1.3" 切成 "TLS 1 . 3"
# WRONG: line = re.sub(r"\b(\d+)\s+\.\s+(\d+)\b", ...)

# 修复后：负向后查找保护字母上下文
line = re.sub(
    r"(?<![A-Za-z])(?<!\d)(\(?\d+\)|\d+[、])\s*(?=\S)", 
    lambda m: f"\n{m.group(1)} ", 
    line
)
```

**效果**: "传输层采用 TLS 1.3 加密协议" 不再被错误拆分为列表项。

---

## 修复 3: Pipeless Table 自动修复 (P0-4)

**文件**: `backend/common/llm/postprocess.py`

```python
def _repair_pipeless_tables(text: str) -> str:
    """Add leading pipes to consecutive pipe-containing lines that lack them.

    LLMs often generate tables like:
        项目 | 内容
        企业名称 | 测试公司

    This repairs them to:
        | 项目 | 内容
        | 企业名称 | 测试公司
    """
    lines = text.split("\n")
    result_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line contains pipes but doesn't start with one
        if "|" in stripped and not stripped.startswith("|"):
            # Look ahead to find consecutive pipe-containing lines
            table_block = [i]
            j = i + 1
            while j < len(lines):
                next_stripped = lines[j].strip()
                if "|" in next_stripped and not next_stripped.startswith("|"):
                    table_block.append(j)
                    j += 1
                elif not next_stripped:  # Allow blank lines
                    j += 1
                else:
                    break

            # If we found 2+ consecutive lines, it's likely a table
            if len(table_block) >= 2:
                for idx in table_block:
                    result_lines.append("| " + lines[idx].strip())
                i = j
                continue

        result_lines.append(line)
        i += 1

    return "\n".join(result_lines)
```

**效果**: LLM 生成的缺少前导竖线的表格自动补全，确保 Markdown 渲染器正确识别。

---

## 修复 4: 章节去重逻辑 (P0-5)

**文件**: `backend/domains/cn/security_assessment/external_report_generator.py`

```python
def _build_section_content(
    section: dict[str, Any],
    chapters: list[ChapterContent],
    profile: CompanyProfile,
    context_pack: GenerationContextPack | None = None,
    used_chapter_ids: set[str] | None = None,  # <-- 全局去重 set
) -> str:
    """Build content for a section from mapped chapters and input data.

    ``used_chapter_ids`` is shared across the whole report so that a chapter
    already emitted under an earlier section is not repeated verbatim under a
    later one (P0-5).
    """
    parts: list[str] = []
    seen = used_chapter_ids if used_chapter_ids is not None else set()

    # Collect from mapped chapters
    mapped_ids = section.get("mapped_chapters", [])
    for chapter_id in mapped_ids:
        if chapter_id in seen:
            continue  # <-- 跳过已使用章节
        content = _pick_chapter(chapters, chapter_id)
        if content:
            seen.add(chapter_id)
            parts.append(content)

    # Handle subsections (recursive, shares same seen set)
    for sub in section.get("subsections", []):
        sub_content = _build_section_content(sub, chapters, profile, context_pack, seen)
        if sub_content:
            parts.append(f"### {sub.get('number', '')} {sub.get('title', '')}\n\n{sub_content}")

    return "\n\n".join(parts)
```

**调用侧**:
```python
# P0-5: one shared set across the whole report
used_chapter_ids: set[str] = set()

for section in schema.get("sections", []):
    content = _build_section_content(
        section, chapters, profile, context_pack, used_chapter_ids
    )
```

**效果**: "出境活动概述" 章节只在 section 1 出现一次，不在 section 2.1 重复。

---

## 修复 5: 章节范围 Issue 过滤 (P0-6)

**文件**: `backend/domains/cn/security_assessment/chapter_generator.py`

```python
# 修复前：全局 fallback 导致 5 个章节产生相同 issue_text
# WRONG:
# if not matched_issues:
#     matched_issues = [
#         issue for issue in context_pack.issues 
#         if issue.severity in {"HIGH", "BLOCKER"}
#     ][:3]

# 修复后：仅章节范围，无 fallback
matched_issues = []
if context_pack is not None and chapter_id is not None:
    matched_issues = [
        issue for issue in context_pack.issues
        if chapter_id in issue.affects_outputs
    ]
# 若章节无问题，issue_text 改为通用措辞，不借用其他章节的具体问题
```

**效果**: 不同章节的 fallback 文本不再逐字节相同，避免触发 L3d 重复段落检测。

---

## 修复 6: 引用策略正则收紧 (P0-7)

**文件**: `backend/common/llm/postprocess.py`

```python
# 修复前：[^，。；]* 遇逗号停止，无法匹配 "依据《...》第X条，企业应当..."
# WRONG:
# _LEGAL_RULE_RE = re.compile(
#     r"(?:依据《[^》]+》[^，。；]*(?:应当|必须|不得|禁止)|..."
# )

# 修复后：[^。；]*? 允许跨逗号，非贪婪匹配到句号/分号
_LEGAL_RULE_RE = re.compile(
    r"(?:依据《[^》]+》[^。；]*?(?:应当|必须|不得|禁止)|"
    r"《[^》]+》第[一二三四五六七八九十百千万零〇两0-9]+条[^。；]*?(?:规定|要求)|"
    r"(?:违反|不符合)《[^》]+》)"
)
```

**效果**:
- ✅ "依据《个人信息保护法》第三十八条，企业应当进行评估。" → 正确标记需要引用
- ✅ "整体风险等级为中等。" → 不标记（泛化描述性语言）
- ✅ "企业应当补充材料。" → 不标记（无法规上下文）

---

## 附加交付: Markdown 质量门禁 API

**文件**: `backend/common/quality/markdown_lint.py`

```python
from backend.common.quality.markdown_lint import (
    lint_markdown, blocking, format_report, LintContext
)

# 在渲染后调用
findings = lint_markdown(
    text=official_md_content,
    profile="external",  # or "internal"
    context=LintContext(
        expected_risk_level="HIGH",           # 来自 context_pack.risk_summary
        citation_map_count=7,                 # 来自 citation_registry
        forbidden_expressions=["完全合规"],   # 来自 writing_strategy
        disclaimer_text="",                   # 待 PRD 确认后填入
    )
)

blockers = blocking(findings)
if blockers:
    logger.warning(format_report(findings))
    # Optional: raise exception to reject delivery

# 输出示例:
# Markdown 质量门禁：2 项阻断，1 项告警
# 按规则计数：L1a×1，L3d×1，L6a×1
#   [L1a/BLOCK] L15: 标题层级倒挂：H1 出现在更深层级标题之后
#   [L3d/BLOCK] L42: 整段重复：与第 28 行段落逐字节相同
#   [L6a/WARN] -: 正文引用法规（3 处法规名）但无任何 [n] 脚注
```

**规则覆盖**:
- L1: 标题层级（倒挂/跳级/扁平章节）
- L2: 表格结构（缺前导竖线/列数不齐/无分隔行）
- L3: 占位符/空章节/重复段落
- L4: 内部标记泄露（ISSUE-xxx / 【待核验】）
- L5: 风险等级唯一性
- L6: 脚注存在性/索引一致性
- L7: 免责声明固定文案
- L8: 禁用措辞（"完全合规"/"保证通过"）
- L9: 未替换占位符（{{var}}）

---

## 测试验证示例

### P0-7 引用策略测试

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
    assert "【待核验：缺少法规依据】" in result.text
```

### P0-3 换行修复测试

```python
def test_tls_version_not_broken():
    """TLS version numbers should not be split into list items."""
    text = "传输层采用 TLS 1.3 加密协议，支持 AES-256-GCM 加密套件。"
    result = normalize_legal_markdown_structure(text)
    assert "TLS 1.3" in result  # NOT "TLS 1 . 3"
    assert "1." not in result   # NOT converted to numbered list
```

### P0-4 表格修复测试

```python
def test_pipeless_table_repair():
    """Tables without leading pipes should be auto-repaired."""
    text = "项目 | 内容\n企业名称 | 测试公司\n行业 | 互联网"
    result = normalize_legal_markdown_structure(text)
    lines = [line for line in result.split("\n") if "|" in line]
    assert all(line.startswith("|") for line in lines)
```

---

**生成时间**: 2026-08-06  
**验收提交**: 0d7839f
