"""
本文件用于定义评估用例的 Pydantic 模型，包括检索评估和生成评估的用例结构，以及相关的字段验证和约束。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Jurisdiction = Literal["cn", "eu", "us"]


class RetrievalEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    module: str = Field(min_length=1)
    jurisdiction: Jurisdiction
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)
    path: str = ""
    document_type: str = ""
    task_stage: str = ""
    must_retrieve_source_ids: list[str] = Field(min_length=1)
    must_not_retrieve_layers: list[str] = Field(default_factory=list)
    must_not_retrieve_source_kinds: list[str] = Field(default_factory=list)
    must_not_retrieve_jurisdictions: list[Jurisdiction] = Field(default_factory=list)


class GenerationEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    module: str = Field(min_length=1)
    jurisdiction: Jurisdiction
    input: dict[str, Any]
    must_find_issues: list[str] = Field(min_length=1)
    must_cite_source_ids: list[str] = Field(min_length=1)
    must_not_use_layers: list[str] = Field(default_factory=list)
    must_not_claim: list[str] = Field(default_factory=list)
    must_use_official_template_sections: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_module_input(self) -> "GenerationEvalCase":
        if self.module == "cn_assessment":
            if not isinstance(self.input.get("assessment_request"), dict):
                raise ValueError("cn_assessment requires input.assessment_request")
            return self

        required = {"clause_type", "clause_text", "document_type"}
        missing = sorted(required.difference(self.input))
        if missing:
            raise ValueError(f"review case input is missing: {', '.join(missing)}")
        if not str(self.input["clause_text"]).strip():
            raise ValueError("review case input.clause_text must not be empty")
        return self
