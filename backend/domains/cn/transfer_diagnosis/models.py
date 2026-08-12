"""
本文件用于定义诊断事实相关的数据模型，包括三态枚举、诊断路径枚举、事实来源枚举以及诊断事实模型。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TriState(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class DiagnosisPath(str, Enum):
    SECURITY_ASSESSMENT = "security_assessment"
    SCC_OR_CERTIFICATION = "scc_or_certification"
    EXEMPTION = "exemption"
    MANUAL_REVIEW = "manual_review"
    INSUFFICIENT_FACTS = "insufficient_facts"


class FactSource(str, Enum):
    USER = "user"
    DOCUMENT = "document"
    RULE = "rule"
    LLM_INFERENCE = "llm_inference"
    ESTIMATE = "estimate"
    DEFAULT = "default"


class DiagnosisFacts(BaseModel):
    is_ciio: TriState
    contains_important_data: TriState
    personal_info_count: int = Field(ge=0)
    sensitive_personal_info_count: int = Field(ge=0)
    no_personal_info: TriState = TriState.NO
    transfer_scenario: str = "other"
    receiver_type: str = "third_party"
    transfer_purpose: str = ""
    field_provenance: dict[str, FactSource] = Field(default_factory=dict)
    missing_facts: list[str] = Field(default_factory=list)

    def source_for(self, field_name: str) -> FactSource:
        return self.field_provenance.get(field_name, FactSource.DEFAULT)
