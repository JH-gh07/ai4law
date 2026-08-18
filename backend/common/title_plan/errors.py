"""task082 闭集错误码与诊断结构。

错误码是闭集，禁止调用方自由拼写字符串；所有公开 API 的失败都通过
:class:`TitlePlanError`（带 :class:`ErrorCode`）或 :class:`RuleViolation`
（带稳定 rule_id）表达。
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    """公共能力层的闭集错误码。"""

    TEMPLATE_NOT_FOUND = "template_not_found"
    TEMPLATE_AMBIGUOUS = "template_ambiguous"
    TEMPLATE_SCHEMA_INVALID = "template_schema_invalid"
    TEMPLATE_CONTENT_INVALID = "template_content_invalid"
    TEMPLATE_HASH_MISMATCH = "template_hash_mismatch"
    TEMPLATE_VERSION_MISMATCH = "template_version_mismatch"
    CONFIG_INVALID = "config_invalid"
    AUDIT_PERSIST_ERROR = "audit_persist_error"
    POST_VALIDATION_MUTATION = "post_validation_mutation"
    CANONICALIZE_ERROR = "canonicalize_error"


class TitlePlanError(Exception):
    """带闭集错误码的公共异常。"""

    def __init__(self, code: ErrorCode, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}


Severity = Literal["error", "warning"]


class RuleViolation(BaseModel):
    """一次确定性校验失败的记录，带稳定 rule_id，不依赖自由文本分类。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(min_length=1)
    section_id: str | None = None
    severity: Severity = "error"
    message: str = Field(min_length=1)


__all__ = [
    "ErrorCode",
    "RuleViolation",
    "Severity",
    "TitlePlanError",
]
