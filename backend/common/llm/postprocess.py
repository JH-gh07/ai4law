from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.common.citation.locators import normalize_article_no
from backend.common.citation.markers import CIT_MARKER_RE as _CIT_MARKER_RE

if TYPE_CHECKING:
    from backend.common.citation.registry import CitationRegistry
_CHAPTER_LABEL_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇两0-9]+章\b")
_SECTION_LABEL_RE = re.compile(r"^[一二三四五六七八九十百千万零〇两0-9]+、")
_SUBSECTION_LABEL_RE = re.compile(r"^（[一二三四五六七八九十百千万零〇两0-9]+）")
_ORDERED_ITEM_RE = re.compile(r"^(?:\(?(\d+)\)|(\d+)[、.])\s*")
_MARKDOWN_PREFIX_RE = re.compile(
    r"^\s*(?:#{1,6}\s|[*_]{2,3}[^*_\s]|[-*]\s|\d+\.\s|>\s|\|)"
)
_BASIS_BLOCK_RE = re.compile(r"【依据：[^】]+】")
_TRUNCATED_CIT_MARKER_RE = re.compile(r"\{\{CIT-[A-Z0-9_-]*(?:\}\}?)?")
# P0-7: Tighten patterns to avoid flagging generic descriptive prose
# Only match when asserting specific legal obligations or definitive judgments
_LEGAL_RULE_RE = re.compile(
    r"(?:依据《[^》]+》[^。；]*?(?:应当|必须|不得|禁止)|"
    r"《[^》]+》第[一二三四五六七八九十百千万零〇两0-9]+条[^。；]*?(?:规定|要求)|"
    r"(?:违反|不符合)《[^》]+》|"
    r"(?:应当|必须|不得|禁止)[^。；]{0,40}(?:评估|合规|义务|保护|处理|出境|个人信息|数据))"
)
_RISK_JUDGMENT_RE = re.compile(
    r"(?:经评估，.*?(?:属于|为|系).*?(?:高|中|低)风险|"
    r"(?:合规|不合规)结论[:：][^，。；]*(?:是|为|系))"
)
_PLACEHOLDER_CITATIONS = {"未检索到", "未检索到相关法规", "未检索到法规依据"}
# Matches markdown inline formatting: **bold**, __bold__, *italic*, _italic_, `code`
# Group 2 captures the inner content so we can strip the markers
_MD_INLINE_RE = re.compile(r"(\*{1,3}|_{1,3})([^*_\n]+?)\1|`([^`\n]+)`")


@dataclass(frozen=True)
class CitationPolicyViolation:
    paragraph_index: int
    code: str
    claim_type: str
    detail: str = ""


@dataclass(frozen=True)
class CitationPolicyResult:
    text: str
    violations: list[CitationPolicyViolation]


class CitationPipelineError(ValueError):
    """Raised when citation syntax is processed without a citation registry."""


@dataclass(frozen=True)
class CitationPipelineResult:
    text: str
    violations: list[CitationPolicyViolation]


def normalize_legal_markdown_structure(text: str) -> str:
    """Normalize loosely structured legal prose into stable Markdown blocks.

    Goals:
    - split packed headings like "第一章...一、...（一）..."
    - keep existing Markdown headings/lists/tables intact
    - force legal basis blocks onto their own lines
    - render Chinese legal document hierarchy into Markdown headings
    """
    if not text:
        return text

    # P0-4: Repair pipe-less tables by adding leading pipes before normalization
    text = _repair_pipeless_tables(text)

    normalized = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u00a0", " ")
        .replace("\u3000", " ")
    )
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)

    items: list[tuple[str, str]] = []
    for raw_line in normalized.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue
        for segment in _explode_packed_line(stripped):
            kind, rendered = _classify_legal_block(segment)
            if rendered:
                items.append((kind, rendered))

    if not items:
        return ""

    rendered_parts: list[str] = []
    prev_kind: str | None = None
    for kind, value in items:
        if rendered_parts:
            separator = "\n\n"
            if kind in {"list_item", "table_row"} and prev_kind == kind:
                separator = "\n"
            elif kind == "table_row" and prev_kind == "table_rule":
                separator = "\n"
            elif kind == "table_rule" and prev_kind == "table_row":
                separator = "\n"
            elif kind == "table_rule" and prev_kind == "table_rule":
                separator = "\n"
            rendered_parts.append(separator)
        rendered_parts.append(value)
        prev_kind = kind

    output = "".join(rendered_parts)
    output = re.sub(r"\n{3,}", "\n\n", output)
    return output.strip()


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

            # If we found 2+ consecutive lines, it's likely a table.
            # Exception: if the line immediately before this block already starts
            # with "|" (i.e. a proper table header is in place), do NOT add pipes
            # — the normalizer will handle those rows as regular content blocks.
            if len(table_block) >= 2:
                first_in_block = table_block[0]
                preceding = lines[first_in_block - 1].strip() if first_in_block > 0 else ""
                if not preceding.startswith("|"):
                    for idx in table_block:
                        result_lines.append("| " + lines[idx].strip())
                    i = j
                    continue

        result_lines.append(line)
        i += 1

    return "\n".join(result_lines)


def _explode_packed_line(line: str) -> list[str]:
    line = re.sub(r"\s*(【依据：[^】]+】)", r"\n\1", line)

    if not _MARKDOWN_PREFIX_RE.match(line):
        line = re.sub(r"(?<!\n)(第[一二三四五六七八九十百千万零〇两0-9]+章)", r"\n\1", line)
        line = re.sub(r"(?<!\n)([一二三四五六七八九十百千万零〇两0-9]+、)", r"\n\1", line)
        line = re.sub(r"(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)", r"\n\1", line)
        # P0-3: Fix regex to avoid breaking TLS 1.3, v1.2.3 etc.
        # Only match numbered lists at line start or after whitespace, exclude \d.\d patterns
        line = re.sub(r"(?<!\n)(?<!\d)(\(?\d+\)|\d+[、])\s*(?=\S)", lambda m: f"\n{m.group(1)} ", line)

    return [part.strip() for part in line.split("\n") if part.strip()]


def _classify_legal_block(line: str) -> tuple[str, str]:
    if _BASIS_BLOCK_RE.fullmatch(line):
        return "basis", line

    if line.startswith("|"):
        if re.fullmatch(r"\|?[\s:|-]+\|?", line):
            return "table_rule", line
        return "table_row", line

    if _MARKDOWN_PREFIX_RE.match(line):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            return "heading", line
        if stripped.startswith("|"):
            if re.fullmatch(r"\|?[\s:|-]+\|?", stripped):
                return "table_rule", line
            return "table_row", line
        if re.match(r"^\d+\.\s", stripped) or re.match(r"^[-*]\s", stripped):
            return "list_item", line
        return "paragraph", line

    if _CHAPTER_LABEL_RE.match(line):
        return "heading", f"# {line}"
    if _SECTION_LABEL_RE.match(line):
        return "heading", f"## {line}"
    if _SUBSECTION_LABEL_RE.match(line):
        return "heading", f"### {line}"

    ordered = _ORDERED_ITEM_RE.match(line)
    if ordered:
        number = ordered.group(1) or ordered.group(2) or "1"
        rest = line[ordered.end():].strip()
        return "list_item", f"{number}. {rest}".rstrip()

    return "paragraph", line


def strip_markdown_inline(text: str) -> str:
    """Strip markdown inline formatting from text destined for DOCX rendering.

    Converts **bold**, __bold__, *italic*, _italic_ and `code` to plain text
    while preserving the inner content.  Does NOT touch block-level constructs
    like headings, lists, tables, or citation markers.
    """
    if not text:
        return text

    citation_markers: list[str] = []

    def _protect_citation_marker(match: re.Match) -> str:
        citation_markers.append(match.group(0))
        return f"\ufff0{len(citation_markers) - 1}\ufff1"

    protected = _CIT_MARKER_RE.sub(_protect_citation_marker, text)

    def _strip(m: re.Match) -> str:
        inner = m.group(2) or m.group(3) or ""
        return inner

    stripped = _MD_INLINE_RE.sub(_strip, protected)
    for index, marker in enumerate(citation_markers):
        stripped = stripped.replace(f"\ufff0{index}\ufff1", marker)
    return stripped


def ensure_paragraph_citations(
    text: str,
    citations: list[str] | None,
    max_items: int = 3,
) -> str:
    """Compatibility wrapper for the claim-aware citation policy.

    It deliberately does not attach retrieval results to every paragraph.
    """
    return apply_citation_policy(text, citations, max_items=max_items).text


def _citation_key(value: str) -> str:
    return re.sub(r"[\s《》【】\[\]（）()]", "", value or "").lower()


def _claim_type(paragraph: str) -> str | None:
    without_markers = _BASIS_BLOCK_RE.sub("", paragraph)
    if _LEGAL_RULE_RE.search(without_markers):
        return "LEGAL_RULE"
    if _RISK_JUDGMENT_RE.search(without_markers):
        return "RISK_JUDGMENT"
    return None


def apply_citation_policy(
    text: str,
    allowed_citations: list[str] | None,
    *,
    max_items: int = 3,
    verified_footnotes: set[int] | None = None,
) -> CitationPolicyResult:
    """Validate explicit citations and mark unsupported high-stakes claims.

    Retrieval candidates are an allowlist, not proof that every paragraph is
    supported by every candidate. Only citations explicitly emitted next to a
    claim survive this gate.
    """
    if not text:
        return CitationPolicyResult(text=text, violations=[])

    cleaned = strip_markdown_inline(text)
    cleaned = re.sub(r"\n\s*\n(?=【依据：)", "\n", cleaned)
    allowed = {
        _citation_key(str(item).strip()): str(item).strip()
        for item in (allowed_citations or [])
        if str(item).strip()
    }
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", cleaned) if item.strip()]
    rendered: list[str] = []
    violations: list[CitationPolicyViolation] = []

    for index, paragraph in enumerate(paragraphs, start=1):
        claim_type = _claim_type(paragraph) or "NONE"
        valid_citations: list[str] = []
        for block in _BASIS_BLOCK_RE.findall(paragraph):
            raw_items = block[len("【依据："):-1].split("；")
            for raw_item in raw_items:
                item = raw_item.strip()
                if not item:
                    continue
                if item in _PLACEHOLDER_CITATIONS:
                    violations.append(
                        CitationPolicyViolation(
                            paragraph_index=index,
                            code="citation_placeholder",
                            claim_type=claim_type,
                            detail=item,
                        )
                    )
                    continue
                canonical = allowed.get(_citation_key(item))
                if canonical is None:
                    violations.append(
                        CitationPolicyViolation(
                            paragraph_index=index,
                            code="citation_not_allowed",
                            claim_type=claim_type,
                            detail=item,
                        )
                    )
                    continue
                if canonical not in valid_citations:
                    valid_citations.append(canonical)

        paragraph_without_basis = _BASIS_BLOCK_RE.sub("", paragraph).strip()
        if valid_citations:
            selected = "；".join(valid_citations[:max_items])
            paragraph_without_basis = f"{paragraph_without_basis} 【依据：{selected}】"

        numeric_footnotes = {
            int(number) for number in re.findall(r"\[(\d+)\]", paragraph)
        }
        has_verified_marker = bool(valid_citations) or bool(
            numeric_footnotes & (verified_footnotes or set())
        )
        if claim_type != "NONE" and not has_verified_marker:
            if "【待核验：" not in paragraph_without_basis:
                paragraph_without_basis = (
                    f"{paragraph_without_basis} 【待核验：缺少法规依据】"
                )
            violations.append(
                CitationPolicyViolation(
                    paragraph_index=index,
                    code="required_citation_missing",
                    claim_type=claim_type,
                )
            )
        rendered.append(paragraph_without_basis)

    normalized = normalize_legal_markdown_structure("\n\n".join(rendered))
    return CitationPolicyResult(text=normalized, violations=violations)


_BASIS_ARTICLE_RE = re.compile(
    r"第\s*([零〇一二两三四五六七八九十百千万\d]+)\s*条"
)


def _basis_key(value: str) -> str:
    return re.sub(r"[\s《》【】\[\]（）()：:；;，,。、“”\"']", "", value or "").lower()


def _resolve_basis_to_number(raw_basis: str, registry: "CitationRegistry") -> int | None:
    article_match = _BASIS_ARTICLE_RE.search(raw_basis)
    requested_article = normalize_article_no(article_match.group(0)) if article_match else ""
    basis_title = _basis_key(_BASIS_ARTICLE_RE.sub("", raw_basis))
    candidates: list[str] = []
    for item in registry:
        title_key = _basis_key(item.title or item.display_label)
        if not title_key or not (title_key in basis_title or basis_title in title_key):
            continue
        item_article = normalize_article_no(str(item.article_no or ""))
        if requested_article and item_article != requested_article:
            continue
        candidates.append(item.citation_id)
    if len(candidates) != 1:
        return None
    return registry.assign_footnote_number(candidates[0])


def _convert_basis_blocks_to_footnotes(text: str, registry: "CitationRegistry") -> str:
    def replace(block_match: re.Match) -> str:
        inner = block_match.group(0)[len("【依据："):-1]
        numbers = [
            number
            for raw in re.split(r"[；;]+", inner)
            if (number := _resolve_basis_to_number(raw.strip(), registry)) is not None
        ]
        return "".join(f"[{number}]" for number in numbers) or "【待核验：引用无法映射】"

    return _BASIS_BLOCK_RE.sub(replace, text)


def apply_citation_pipeline(
    text: str,
    *,
    registry: "CitationRegistry | None",
    allowed_citations: list[str] | None = None,
    max_items: int = 3,
) -> CitationPipelineResult:
    """Run the only supported legacy-text citation pipeline.

    Both LLM markers and the deprecated ``【依据：...】`` form are resolved
    against the same registry before claim validation. The deprecated form is
    an input compatibility format only; it never reaches a final report.
    """
    if not text:
        return CitationPipelineResult(text=text, violations=[])
    has_citation_syntax = bool(_CIT_MARKER_RE.search(text) or _BASIS_BLOCK_RE.search(text))
    if has_citation_syntax and registry is None:
        raise CitationPipelineError("CitationRegistry is required for citation syntax")

    converted = text
    if registry is not None:
        converted = _replace_registered_markers(converted, registry)
        converted = _convert_basis_blocks_to_footnotes(converted, registry)
        verified_footnotes = set(registry.get_footnote_map())
    else:
        verified_footnotes = set()

    policy = apply_citation_policy(
        converted,
        allowed_citations,
        max_items=max_items,
        verified_footnotes=verified_footnotes,
    )
    return CitationPipelineResult(text=policy.text, violations=policy.violations)


def convert_citation_markers(text: str, registry: "CitationRegistry") -> str:
    """Convert {{CIT-xxx}} markers to [1], [2] footnotes in text.

    Uses global footnote numbering from the registry so a citation always
    receives the same number across all chapters.
    """
    if not text:
        return text
    return normalize_legal_markdown_structure(_replace_registered_markers(text, registry))


def _replace_registered_markers(text: str, registry: "CitationRegistry") -> str:
    """Replace citation markers without changing surrounding paragraphs."""
    text = strip_markdown_inline(text)
    def _replace_marker(match: re.Match) -> str:
        cid = match.group(1)
        num = registry.assign_footnote_number(cid)
        if num is not None:
            return f"[{num}]"
        # Keep unresolved identity visible for diagnostics instead of silently
        # deleting evidence from the delivered text.
        return "【待核验：引用无法映射】"

    converted = _CIT_MARKER_RE.sub(_replace_marker, text)
    return _TRUNCATED_CIT_MARKER_RE.sub(
        "【待核验：引用格式不完整】",
        converted,
    )
