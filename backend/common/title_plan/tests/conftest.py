"""task082 测试 fixture：手写最小模板，保证测试独立于 task080 资产。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.common.title_plan import (
    ArtifactRole,
    TemplateSnapshot,
    ValidationContext,
    load_template,
)


def write_spec(
    directory: Path,
    *,
    module_key: str = "test",
    artifact_role: str = "schema_first_markdown",
    template_version: str = "test-v0",
    sections: list[dict],
    title_spec_version: str = "1.0",
    filename: str | None = None,
) -> Path:
    path = directory / (filename or f"{module_key}-{artifact_role}.json")
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "title_spec_version": title_spec_version,
                "template_version": template_version,
                "module_key": module_key,
                "artifact_role": artifact_role,
                "sections": sections,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def section(
    section_id: str,
    canonical_title: str,
    *,
    parent_id: str | None = None,
    level: int = 2,
    order: int = 1,
    semantic_purpose: str = "测试职责",
    title_policy: str = "fixed",
    required: bool = True,
    conditional_rule: str = "always",
    allowed_aliases: list[str] | None = None,
    allowed_candidates: list[str] | None = None,
    dynamic_child_limit: int = 0,
    allowed_child_purpose_codes: list[str] | None = None,
) -> dict:
    return {
        "section_id": section_id,
        "parent_id": parent_id,
        "level": level,
        "order": order,
        "canonical_title": canonical_title,
        "semantic_purpose": semantic_purpose,
        "required": required,
        "conditional_rule": conditional_rule,
        "title_policy": title_policy,
        "allowed_aliases": allowed_aliases or [],
        "allowed_candidates": allowed_candidates or [],
        "dynamic_child_limit": dynamic_child_limit,
        "allowed_child_purpose_codes": allowed_child_purpose_codes or [],
    }


@pytest.fixture
def make_snapshot():
    def _make(tmp_path: Path, sections: list[dict], **kwargs) -> TemplateSnapshot:
        write_spec(tmp_path, sections=sections, **kwargs)
        return load_template(
            module_key=kwargs.get("module_key", "test"),
            artifact_role=ArtifactRole(kwargs.get("artifact_role", "schema_first_markdown")),
            template_dir=tmp_path,
        )
    return _make


@pytest.fixture
def ctx() -> ValidationContext:
    return ValidationContext(validator_version="test-0.1.0", input_hash="input-hash-1")


@pytest.fixture
def fixed_sections() -> list[dict]:
    return [
        section("doc", "{company_name} 报告", level=1, order=0, semantic_purpose="文档标题"),
        section("s1", "执行摘要", level=2, order=1, semantic_purpose="摘要"),
        section("s2", "审查概况与方法", level=2, order=2, semantic_purpose="概况"),
    ]


@pytest.fixture
def rewrite_sections() -> list[dict]:
    return [
        section("doc", "{company_name} 报告", level=1, order=0, semantic_purpose="文档标题"),
        section(
            "ch1",
            "出境活动概述",
            level=2,
            order=1,
            semantic_purpose="出境活动",
            title_policy="controlled_rewrite",
        ),
        section(
            "ch2",
            "数据类型与规模",
            level=2,
            order=2,
            semantic_purpose="数据类型",
            title_policy="controlled_rewrite",
        ),
    ]
