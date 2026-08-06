"""Unified Markdown quality gate for delivered compliance reports.

Nine rule classes, each addressing a defect class observed in real delivered
output (see ``status/todo/DataComplyFlow_Markdown质量门禁与报告一致性治理方案_20260806.md``):

===  ==========================  ==========================================
ID   Class                       What it catches
===  ==========================  ==========================================
L1   Heading hierarchy           H1 nested under H2/H3, level skips, flat chapters
L2   Table structure             pipe-less tables, ragged columns, missing rule row
L3   Empty / placeholder         "待补充" boilerplate, stub sections, duplicate paragraphs
L4   Internal marker leakage     ISSUE- ids, 【待核验】, 【已移除禁用措辞】, field names
L5   Risk-level uniqueness       two different risk conclusions in one report
L6   Footnote presence           legal prose with zero footnotes; index/map contradiction
L7   Disclaimer                  fixed wording present in the three required places
L8   Forbidden wording           "完全合规" / "可直接申报通过" and friends
L9   Placeholder residue         literal ``{{var}}`` surviving template substitution
===  ==========================  ==========================================

Two profiles. ``external`` is the customer deliverable and enables every rule.
``internal`` is the analyst-facing artifact: L4 and L7 are relaxed there because
issue ids and pending-review markers are *legitimate* internal content.

The linter is advisory by construction: it returns findings and never raises.
Callers decide whether a ``BLOCK`` finding stops a render.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["BLOCK", "WARN"]
Profile = Literal["external", "internal"]


@dataclass(frozen=True)
class LintFinding:
    """One rule violation, anchored to a line where possible."""

    rule: str
    severity: Severity
    message: str
    line: int = 0
    snippet: str = ""

    def __str__(self) -> str:
        where = f"L{self.line}" if self.line else "-"
        return f"[{self.rule}/{self.severity}] {where}: {self.message}"


@dataclass
class LintContext:
    """Facts the linter cannot derive from the text alone."""

    # Authoritative risk level from the rule engine. When set, L5 asserts the
    # report agrees with it rather than merely being self-consistent.
    expected_risk_level: str = ""
    # Number of entries in citation_map.json. Enables the L6 cross-artifact
    # check that catches "未引用法规依据索引" coexisting with a populated map.
    citation_map_count: int = 0
    # Forbidden expressions, normally writing_strategy.global_forbidden_expressions.
    forbidden_expressions: list[str] = field(default_factory=list)
    # Canonical disclaimer text. Empty disables L7 (we refuse to freeze wording
    # we have not been given -- see plan section 2.11).
    disclaimer_text: str = ""
    disclaimer_required_count: int = 3


# --------------------------------------------------------------------------
# patterns
# --------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_TABLE_RULE_RE = re.compile(r"^\|?[\s:|-]+\|?$")
_FENCE_RE = re.compile(r"^\s*```")

# CJK is a word character to Python's ``re``, so ``\bHIGH\b`` never matches in
# "整体风险等级为HIGH". Use ASCII-letter lookarounds instead, which still refuse
# to match inside HIGHLIGHT / LOWER.
_RISK_TOKEN_RE = re.compile(r"(?<![A-Za-z])(HIGH|MEDIUM|LOW)(?![A-Za-z])")

_RISK_CN_TO_EN = {"高风险": "HIGH", "中风险": "MEDIUM", "低风险": "LOW"}

# Only lines that state a *conclusion* participate in L5. A line merely
# discussing risk issues ("本次报告必须重点关注的高风险问题包括…") is not a
# competing conclusion and must not manufacture a conflict.
_RISK_CONCLUSION_CUES = (
    "综合风险等级",
    "整体风险等级",
    "风险等级为",
    "风险等级：",
    "总体风险等级",
    "风险结论",
)

_PLACEHOLDER_PATTERNS = (
    ("（该部分内容待补充", "结构性占位段落"),
    ("该部分内容待补充", "结构性占位段落"),
    ("[待补充]", "待补充占位"),
    ("待补充，需基于", "待补充占位"),
)

_INTERNAL_MARKERS = (
    (re.compile(r"ISSUE-[a-z][a-z0-9-]*"), "内部问题编号"),
    (re.compile(r"【待核验[^】]*】"), "内部待核验标记"),
    (re.compile(r"【已移除禁用措辞[^】]*】"), "禁用措辞移除标记"),
    (re.compile(r"\{\{CIT-[^}]*\}\}"), "未转换的引用标记"),
    (re.compile(r"(?<![A-Za-z_])CIT-[A-Z]{2,}-[A-Z0-9-]+"), "原始引用ID"),
    (re.compile(r"(?<![A-Za-z_])(chunk_id|source_kind|confidence_score|affects_outputs|evidence_status)(?![A-Za-z_])"), "内部字段名"),
)

_DEFAULT_FORBIDDEN = (
    "完全合规",
    "可直接申报通过",
    "零风险",
    "保证通过",
    "必然获批",
    "肯定通过",
)

_PLACEHOLDER_RESIDUE_RE = re.compile(r"\{\{([a-z_][a-z0-9_]*)\}\}")

_FOOTNOTE_RE = re.compile(r"\[(\d{1,3})\]")
_LAW_MENTION_RE = re.compile(r"《[^》]{4,40}》")
_EMPTY_INDEX_RE = re.compile(r"（?本报告未引用(?:外部可用)?法规依据索引）?")

_MIN_SECTION_BODY_CHARS = 30
_FLAT_CHAPTER_CHARS = 800


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    """Blank out fenced code blocks, preserving line numbering."""
    out: list[str] = []
    inside = False
    for line in text.split("\n"):
        if _FENCE_RE.match(line):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


@dataclass
class _Section:
    line: int
    level: int
    title: str
    body: list[str] = field(default_factory=list)


def _split_sections(lines: list[str]) -> list[_Section]:
    sections: list[_Section] = []
    current: _Section | None = None
    for idx, line in enumerate(lines, start=1):
        m = _HEADING_RE.match(line)
        if m:
            current = _Section(line=idx, level=len(m.group(1)), title=m.group(2).strip())
            sections.append(current)
            continue
        if current is not None:
            current.body.append(line)
    return sections


def _paragraphs(lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_no, paragraph_text) for blank-line separated blocks."""
    out: list[tuple[int, str]] = []
    buf: list[str] = []
    start = 0
    for idx, line in enumerate(lines, start=1):
        if line.strip():
            if not buf:
                start = idx
            buf.append(line.strip())
        elif buf:
            out.append((start, " ".join(buf)))
            buf = []
    if buf:
        out.append((start, " ".join(buf)))
    return out


# --------------------------------------------------------------------------
# L1 heading hierarchy
# --------------------------------------------------------------------------

def _check_headings(lines: list[str]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    headings = [
        (idx, len(m.group(1)), m.group(2).strip())
        for idx, line in enumerate(lines, start=1)
        if (m := _HEADING_RE.match(line))
    ]
    if not headings:
        return findings

    seen_deeper = False
    prev_level = 0
    for line_no, level, title in headings:
        # L1a inversion: an H1 appearing after any H2+ heading
        if level == 1 and seen_deeper:
            findings.append(
                LintFinding(
                    rule="L1a",
                    severity="BLOCK",
                    message="标题层级倒挂：H1 出现在更深层级标题之后",
                    line=line_no,
                    snippet=title[:60],
                )
            )
        if level >= 2:
            seen_deeper = True

        # L1b skip: H2 -> H4
        if prev_level and level > prev_level + 1:
            findings.append(
                LintFinding(
                    rule="L1b",
                    severity="BLOCK",
                    message=f"标题层级跳级：H{prev_level} 直接跳到 H{level}",
                    line=line_no,
                    snippet=title[:60],
                )
            )
        prev_level = level

    # L1c flat: long section with no subheading
    for section in _split_sections(lines):
        body = "\n".join(section.body).strip()
        if len(body) > _FLAT_CHAPTER_CHARS and not any(
            _HEADING_RE.match(b) for b in section.body
        ):
            findings.append(
                LintFinding(
                    rule="L1c",
                    severity="WARN",
                    message=f"章节正文 {len(body)} 字但无子标题，可扫描性差",
                    line=section.line,
                    snippet=section.title[:60],
                )
            )
    return findings


# --------------------------------------------------------------------------
# L2 table structure
# --------------------------------------------------------------------------

def _cell_count(line: str) -> int:
    stripped = line.strip().strip("|")
    # ignore escaped pipes
    return len(re.split(r"(?<!\\)\|", stripped))


def _check_tables(lines: list[str]) -> list[LintFinding]:
    findings: list[LintFinding] = []

    # L2a pipe-less table: >=2 consecutive lines with an inner pipe, no leading pipe
    run: list[tuple[int, str]] = []

    def flush_pipeless() -> None:
        if len(run) >= 2:
            counts = {_cell_count(t) for _, t in run}
            if len(counts) == 1 and counts != {1}:
                findings.append(
                    LintFinding(
                        rule="L2a",
                        severity="BLOCK",
                        message=f"检出 {len(run)} 行无前导竖线的表格，Markdown 不会渲染为表格",
                        line=run[0][0],
                        snippet=run[0][1][:60],
                    )
                )
        run.clear()

    for idx, line in enumerate(lines, start=1):
        s = line.strip()
        if s and not s.startswith("|") and re.search(r"[^|]\|[^|]", s):
            run.append((idx, s))
        else:
            flush_pipeless()
    flush_pipeless()

    # L2b/L2c: real tables with ragged columns or missing rule row
    block: list[tuple[int, str]] = []

    def flush_block() -> None:
        if len(block) >= 2:
            has_rule = any(_TABLE_RULE_RE.match(t) for _, t in block)
            if not has_rule:
                findings.append(
                    LintFinding(
                        rule="L2c",
                        severity="BLOCK",
                        message="表格缺少分隔行（|---|），不会渲染为表格",
                        line=block[0][0],
                        snippet=block[0][1][:60],
                    )
                )
            widths = {
                _cell_count(t) for _, t in block if not _TABLE_RULE_RE.match(t)
            }
            if len(widths) > 1:
                findings.append(
                    LintFinding(
                        rule="L2b",
                        severity="BLOCK",
                        message=f"表格列数不一致：检出 {sorted(widths)} 种列数",
                        line=block[0][0],
                        snippet=block[0][1][:60],
                    )
                )
        block.clear()

    for idx, line in enumerate(lines, start=1):
        s = line.strip()
        if s.startswith("|"):
            block.append((idx, s))
        else:
            flush_block()
    flush_block()

    return findings


# --------------------------------------------------------------------------
# L3 empty / placeholder / duplication
# --------------------------------------------------------------------------

def _check_empty_and_placeholder(lines: list[str]) -> list[LintFinding]:
    findings: list[LintFinding] = []

    for idx, line in enumerate(lines, start=1):
        for needle, label in _PLACEHOLDER_PATTERNS:
            if needle in line:
                findings.append(
                    LintFinding(
                        rule="L3a",
                        severity="BLOCK",
                        message=f"{label}进入交付正文",
                        line=idx,
                        snippet=line.strip()[:60],
                    )
                )
                break
        if line.strip() in {"未提供", "无", "N/A"}:
            findings.append(
                LintFinding(
                    rule="L3b",
                    severity="BLOCK",
                    message="占位值单独成段",
                    line=idx,
                    snippet=line.strip(),
                )
            )

    # L3c stub section
    for section in _split_sections(lines):
        body = "\n".join(section.body).strip()
        if body and len(body) < _MIN_SECTION_BODY_CHARS:
            findings.append(
                LintFinding(
                    rule="L3c",
                    severity="BLOCK",
                    message=f"章节正文仅 {len(body)} 字，低于 {_MIN_SECTION_BODY_CHARS} 字下限",
                    line=section.line,
                    snippet=section.title[:60],
                )
            )

    # L3d byte-identical paragraph repetition -- the "事实重复" defect
    seen: dict[str, int] = {}
    for line_no, para in _paragraphs(lines):
        if len(para) < 40:
            continue
        if para.startswith("|"):
            continue
        if para in seen:
            findings.append(
                LintFinding(
                    rule="L3d",
                    severity="BLOCK",
                    message=f"整段重复：与第 {seen[para]} 行段落逐字节相同",
                    line=line_no,
                    snippet=para[:60],
                )
            )
        else:
            seen[para] = line_no
    return findings


# --------------------------------------------------------------------------
# L4 internal marker leakage
# --------------------------------------------------------------------------

def _check_internal_markers(lines: list[str]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for idx, line in enumerate(lines, start=1):
        for pattern, label in _INTERNAL_MARKERS:
            m = pattern.search(line)
            if m:
                findings.append(
                    LintFinding(
                        rule="L4",
                        severity="BLOCK",
                        message=f"{label}泄露到对外正文：{m.group(0)[:40]}",
                        line=idx,
                        snippet=line.strip()[:60],
                    )
                )
    return findings


# --------------------------------------------------------------------------
# L5 risk-level uniqueness
# --------------------------------------------------------------------------

def _check_risk_uniqueness(lines: list[str], ctx: LintContext) -> list[LintFinding]:
    findings: list[LintFinding] = []
    found: dict[str, list[int]] = {}

    for idx, line in enumerate(lines, start=1):
        if not any(cue in line for cue in _RISK_CONCLUSION_CUES):
            continue
        tokens = set(_RISK_TOKEN_RE.findall(line.upper()))
        for cn, en in _RISK_CN_TO_EN.items():
            if cn in line:
                tokens.add(en)
        for tok in tokens:
            found.setdefault(tok, []).append(idx)

    if len(found) > 1:
        detail = "，".join(
            f"{lvl}（第 {'/'.join(str(n) for n in ln)} 行）"
            for lvl, ln in sorted(found.items())
        )
        findings.append(
            LintFinding(
                rule="L5a",
                severity="BLOCK",
                message=f"同一报告出现 {len(found)} 个不同风险等级结论：{detail}",
                line=min(min(v) for v in found.values()),
            )
        )

    expected = (ctx.expected_risk_level or "").strip().upper()
    if expected and found and expected not in found:
        findings.append(
            LintFinding(
                rule="L5b",
                severity="BLOCK",
                message=(
                    f"报告风险等级结论 {sorted(found)} 与规则引擎判定 {expected} 不一致"
                ),
                line=min(min(v) for v in found.values()),
            )
        )
    return findings


# --------------------------------------------------------------------------
# L6 footnote presence + cross-artifact consistency
# --------------------------------------------------------------------------

def _check_footnotes(text: str, lines: list[str], ctx: LintContext) -> list[LintFinding]:
    findings: list[LintFinding] = []
    footnotes = _FOOTNOTE_RE.findall(text)
    law_mentions = _LAW_MENTION_RE.findall(text)
    has_basis_block = "【依据：" in text

    if (law_mentions or has_basis_block) and not footnotes:
        findings.append(
            LintFinding(
                rule="L6a",
                severity="BLOCK",
                message=(
                    f"正文引用法规（{len(law_mentions)} 处法规名"
                    f"{'、含依据块' if has_basis_block else ''}）但无任何 [n] 脚注"
                ),
            )
        )

    for idx, line in enumerate(lines, start=1):
        if _EMPTY_INDEX_RE.search(line) and ctx.citation_map_count > 0:
            findings.append(
                LintFinding(
                    rule="L6b",
                    severity="BLOCK",
                    message=(
                        f"正文声明未引用法规依据索引，但 citation_map 有 "
                        f"{ctx.citation_map_count} 条记录（跨产物矛盾）"
                    ),
                    line=idx,
                    snippet=line.strip()[:60],
                )
            )
    return findings


# --------------------------------------------------------------------------
# L7 disclaimer
# --------------------------------------------------------------------------

def _check_disclaimer(text: str, ctx: LintContext) -> list[LintFinding]:
    if not ctx.disclaimer_text.strip():
        return [
            LintFinding(
                rule="L7",
                severity="WARN",
                message="免责声明门禁未启用：未配置固定文案（待 PRD 原文确认）",
            )
        ]
    count = text.count(ctx.disclaimer_text.strip())
    if count < ctx.disclaimer_required_count:
        return [
            LintFinding(
                rule="L7",
                severity="BLOCK",
                message=(
                    f"免责声明固定文案出现 {count} 次，"
                    f"要求 {ctx.disclaimer_required_count} 处固定展示"
                ),
            )
        ]
    return []


# --------------------------------------------------------------------------
# L8 forbidden wording
# --------------------------------------------------------------------------

def _check_forbidden(lines: list[str], ctx: LintContext) -> list[LintFinding]:
    findings: list[LintFinding] = []
    vocabulary = list(_DEFAULT_FORBIDDEN) + [
        e.strip() for e in ctx.forbidden_expressions if e and e.strip()
    ]
    for idx, line in enumerate(lines, start=1):
        for phrase in vocabulary:
            if phrase in line:
                findings.append(
                    LintFinding(
                        rule="L8",
                        severity="BLOCK",
                        message=f"禁用措辞出现在正文：{phrase}",
                        line=idx,
                        snippet=line.strip()[:60],
                    )
                )
                break
    return findings


# --------------------------------------------------------------------------
# L9 placeholder residue
# --------------------------------------------------------------------------

def _check_placeholder_residue(lines: list[str]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for idx, line in enumerate(lines, start=1):
        for m in _PLACEHOLDER_RESIDUE_RE.finditer(line):
            findings.append(
                LintFinding(
                    rule="L9",
                    severity="BLOCK",
                    message=f"模板占位符未替换即交付：{{{{{m.group(1)}}}}}",
                    line=idx,
                    snippet=line.strip()[:60],
                )
            )
    return findings


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def lint_markdown(
    text: str,
    *,
    profile: Profile = "external",
    context: LintContext | None = None,
) -> list[LintFinding]:
    """Run every applicable rule and return findings, most structural first.

    Never raises. An empty list means the document passed the gate for the
    given profile.
    """
    if not text or not text.strip():
        return [
            LintFinding(rule="L3b", severity="BLOCK", message="报告正文为空")
        ]

    ctx = context or LintContext()
    scanned = _strip_code_fences(text)
    lines = scanned.split("\n")

    findings: list[LintFinding] = []
    findings += _check_headings(lines)
    findings += _check_tables(lines)
    findings += _check_empty_and_placeholder(lines)
    findings += _check_risk_uniqueness(lines, ctx)
    findings += _check_footnotes(scanned, lines, ctx)
    findings += _check_forbidden(lines, ctx)
    findings += _check_placeholder_residue(lines)

    # Profile-gated: issue ids and pending-review markers are legitimate
    # internal content; the fixed disclaimer is an external-delivery duty.
    if profile == "external":
        findings += _check_internal_markers(lines)
        findings += _check_disclaimer(scanned, ctx)

    return findings


def blocking(findings: list[LintFinding]) -> list[LintFinding]:
    """Filter to findings that should stop a delivery render."""
    return [f for f in findings if f.severity == "BLOCK"]


def format_report(findings: list[LintFinding]) -> str:
    """Human-readable summary for logs and render warnings."""
    if not findings:
        return "Markdown 质量门禁：通过（0 项）"
    blocks = blocking(findings)
    warns = [f for f in findings if f.severity == "WARN"]
    lines = [
        f"Markdown 质量门禁：{len(blocks)} 项阻断，{len(warns)} 项告警"
    ]
    by_rule: dict[str, int] = {}
    for f in findings:
        by_rule[f.rule] = by_rule.get(f.rule, 0) + 1
    lines.append("按规则计数：" + "，".join(f"{k}×{v}" for k, v in sorted(by_rule.items())))
    for f in findings[:40]:
        lines.append(f"  {f}")
    if len(findings) > 40:
        lines.append(f"  …另有 {len(findings) - 40} 项未列出")
    return "\n".join(lines)
