"""External report generator — maps internal 8-chapter analysis to official template structure.

The official 《数据出境风险自评估报告》has 3 top-level sections:
  一、自评估工作情况
  二、出境活动整体情况 (6 sub-sections)
  三、出境活动风险自评估情况及结论
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.common.workflow import GenerationContextPack
from backend.modules.assessment.chapter_generator import (
    ASSESSMENT_CHAPTER_KEYS,
    _format_fact_value,
)
from backend.modules.assessment.schema import ChapterContent, CompanyProfile

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_SCHEMA_PATH = _TEMPLATE_DIR / "official_template_schema.json"
_MD_TEMPLATE_PATH = _TEMPLATE_DIR / "official_risk_self_assessment_template.md"


class TemplateMissingError(Exception):
    """Raised when the official template file does not exist."""


def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_PATH.exists():
        raise TemplateMissingError(
            f"官方数据出境风险自评估报告模板 schema 不存在: {_SCHEMA_PATH}"
        )
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _pick_chapter(chapters: list[ChapterContent], chapter_id: str) -> str:
    """Find chapter content by its internal chapter_id (e.g. 'overview', 'data_scope')."""
    for chapter in chapters:
        # Map title to chapter_id
        for title, cid in ASSESSMENT_CHAPTER_KEYS.items():
            if cid == chapter_id and chapter.title == title:
                return chapter.content
    return ""


def _build_section_content(
    section: dict[str, Any],
    chapters: list[ChapterContent],
    profile: CompanyProfile,
    context_pack: GenerationContextPack | None = None,
) -> str:
    """Build content for a section from mapped chapters and input data."""
    parts: list[str] = []

    # Collect from mapped chapters
    mapped_ids = section.get("mapped_chapters", [])
    for chapter_id in mapped_ids:
        content = _pick_chapter(chapters, chapter_id)
        if content:
            parts.append(content)

    # Handle subsections
    for sub in section.get("subsections", []):
        sub_content = _build_section_content(sub, chapters, profile, context_pack)
        if sub_content:
            parts.append(f"### {sub.get('number', '')} {sub.get('title', '')}\n\n{sub_content}")

    return "\n\n".join(parts)


def _resolve_input_value(field_path: str, profile: CompanyProfile, request_payload: dict[str, Any] | None = None) -> str:
    """Resolve a dotted field path from available data sources."""
    schema = _load_schema()
    mapping = schema.get("data_source_mapping", {}).get(field_path, {})
    fallback = mapping.get("fallback", "未提供")

    if field_path.startswith("request."):
        field_name = field_path.split(".", 1)[1]
        if request_payload:
            value = request_payload.get(field_name)
            if value is not None:
                if isinstance(value, bool):
                    return "是" if value else "否"
                if isinstance(value, (int, float)):
                    return f"{value:,}"
                return str(value)
        return fallback

    return fallback


def build_official_report_mapping(
    profile: CompanyProfile,
    chapters: list[ChapterContent],
    date_stamp: str,
    report_id: str,
    path_warning: str | None = None,
    alignment_warning: str | None = None,
    context_pack: GenerationContextPack | None = None,
    citation_registry: object | None = None,
    request_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Build template variable mapping for the official report structure.

    Returns a dict of template variable name → value for the official markdown template.
    """
    schema = _load_schema()
    diagnosis = context_pack.diagnosis_result if context_pack else {}

    is_ciio = "是" if profile.is_ciio else "否"
    contains_important = "是" if profile.contains_important_data else "否"
    pii_str = f"{profile.pii_count:,}人" if profile.pii_count else "未提供"
    spi_str = f"{profile.spi_count:,}人" if profile.spi_count else "未提供"

    overall_risk = diagnosis.get("risk_level", "MEDIUM") if diagnosis else "MEDIUM"
    if path_warning:
        overall_risk += "（路径不匹配，本报告为强制生成的参考草案）"

    mapping: dict[str, str] = {
        "report_date": date_stamp,
        "report_id": report_id,
        "company_name": profile.company_name or "未提供",
        "industry": profile.industry or "未提供",
        "is_ciio": is_ciio,
        "data_processor_role": "数据出境方（境内数据处理者）",
        "transfer_purpose": profile.transfer_purpose or "未提供",
        "pii_count": pii_str,
        "spi_count": spi_str,
        "contains_important_data": contains_important,
        "receiver_country": profile.receiver_country or "未提供",
        "overall_risk_level": overall_risk,
        "path_warning": path_warning or "",
        "alignment_warning": alignment_warning or "",
    }

    # Build section content from mapped chapters
    for section in schema.get("sections", []):
        section_id = section["section_id"]
        if section_id == "2" and section.get("subsections"):
            # Section 二 has subsections — build each
            for sub in section["subsections"]:
                sub_id = sub["section_id"]
                content = _build_section_content(sub, chapters, profile, context_pack)
                if not content:
                    content = "（该部分内容待补充，需基于申报材料进一步生成）"
                mapping[f"section_{sub_id.replace('.', '_')}_content"] = content
        else:
            content = _build_section_content(section, chapters, profile, context_pack)
            if not content:
                content = "（该部分内容待补充，需基于申报材料进一步生成）"
            mapping[f"section_{section_id}_content"] = content

    # Citation map — use external-only version to exclude case references
    if citation_registry is not None and hasattr(citation_registry, "build_external_citation_map_section"):
        mapping["citation_map"] = citation_registry.build_external_citation_map_section()
    elif citation_registry is not None and hasattr(citation_registry, "build_citation_map_section"):
        mapping["citation_map"] = citation_registry.build_citation_map_section()
    else:
        mapping["citation_map"] = "（未启用引用系统，暂无引用依据索引）"

    return mapping


def render_official_report_md(
    output_path: Path,
    mapping: dict[str, str],
) -> Path:
    """Render the official report markdown from the template and mapping."""
    if not _MD_TEMPLATE_PATH.exists():
        raise TemplateMissingError(
            f"官方数据出境风险自评估报告模板 MARKDOWN 不存在: {_MD_TEMPLATE_PATH}"
        )

    template = _MD_TEMPLATE_PATH.read_text(encoding="utf-8")

    # Simple placeholder substitution
    result = template
    for key, value in mapping.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding="utf-8")
    return output_path
