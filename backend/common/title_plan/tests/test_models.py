"""L0 模型与闭集枚举测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.common.title_plan import (
    ArtifactRole,
    FallbackReason,
    FallbackScope,
    PlanValidationStatus,
    PurposeCode,
    SectionSpec,
    TitlePlanDraft,
    TitlePolicy,
    TitleSource,
)


def test_artifact_role_closed_set():
    values = {r.value for r in ArtifactRole}
    assert values == {
        "official_markdown", "internal_markdown", "schema_first_markdown",
        "legacy_markdown", "web", "docx", "pdf", "document_ir",
    }


def test_title_policy_closed_set():
    assert {p.value for p in TitlePolicy} == {
        "fixed", "display_alias_only", "controlled_rewrite",
        "candidate_select", "model_generated", "additional_section",
    }


def test_fallback_reason_includes_task082_additions():
    values = {r.value for r in FallbackReason}
    assert {"hash_mismatch", "policy_violation"} <= values


def test_fallback_scope_closed_set():
    assert {s.value for s in FallbackScope} == {"none", "node", "dynamic_node", "plan"}


@pytest.mark.parametrize("bad", ["report", "final", "preview", "OUT_OF_SCOPE", ""])
def test_artifact_role_rejects_free_string(bad):
    with pytest.raises(ValueError):
        ArtifactRole(bad)


@pytest.mark.parametrize("bad", ["experimental", "free", "anything"])
def test_title_policy_rejects_free_string(bad):
    with pytest.raises(ValueError):
        TitlePolicy(bad)


def test_section_spec_extra_forbid():
    with pytest.raises(ValidationError):
        SectionSpec(
            section_id="s", canonical_title="t", semantic_purpose="p",
            purpose_code=PurposeCode.OVERVIEW, level=1, order=0, bogus="x",
        )


def test_title_plan_draft_requires_sections():
    with pytest.raises(ValidationError):
        TitlePlanDraft(
            template_version="v", module_key="m",
            artifact_role=ArtifactRole.LEGACY_MARKDOWN,  # type: ignore[arg-type]
        )


def test_title_plan_draft_extra_forbid():
    with pytest.raises(ValidationError):
        TitlePlanDraft(
            schema_version="1.0", template_version="v", module_key="m",
            artifact_role=ArtifactRole.LEGACY_MARKDOWN,
            sections=[], additional_sections=[], fallback=False,
            bogus_field="x",
        )


def test_title_source_closed_set():
    assert {s.value for s in TitleSource} == {"canonical", "model", "fallback"}


def test_plan_validation_status_closed_set():
    assert {s.value for s in PlanValidationStatus} == {"pass", "fallback", "reject"}
