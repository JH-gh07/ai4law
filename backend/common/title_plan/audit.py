"""task082 脱敏审计、序列化与恢复接口。

审计必须可持久化、可脱敏、可恢复；禁止写入 token、绝对路径、私有思维链、
未经授权的原始敏感输入。持久化失败不影响 canonical fallback，但必须产生
``AUDIT_PERSIST_ERROR`` 诊断（由调用方在持久化边界触发）。
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from backend.common.title_plan.canonical import canonical_json
from backend.common.title_plan.errors import ErrorCode, TitlePlanError
from backend.common.title_plan.models import FrozenTitlePlan


class RedactionPolicy(str, Enum):
    STANDARD = "standard"
    STRICT = "strict"


DEFAULT = RedactionPolicy.STANDARD

_SENSITIVE_KEYS = {
    "api_key", "apikey", "api-key", "token", "authorization", "auth", "cookie",
    "secret", "password", "passwd", "bearer", "access_key", "access-key",
    "session", "session_id", "credential",
}

_SENSITIVE_VALUE_RES = (
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/=]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9\-_]+", re.IGNORECASE),
    re.compile(r"^/Users/[^\s]*|^/home/[^\s]*|^/root/[^\s]*|^C:\\[^\s]*", re.IGNORECASE),
    re.compile(r"https?://(?:localhost|127\.0\.0\.1|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)\S*", re.IGNORECASE),
)

_REDACTED = "[REDACTED]"


def redact(value: Any, *, policy: RedactionPolicy = DEFAULT) -> Any:
    """递归脱敏：敏感 key 直接替换值，敏感字符串值替换为占位符。"""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            if key.lower() in _SENSITIVE_KEYS:
                out[key] = _REDACTED
            else:
                out[key] = redact(val, policy=policy)
        return out
    if isinstance(value, list):
        return [redact(item, policy=policy) for item in value]
    if isinstance(value, tuple):
        return [redact(item, policy=policy) for item in value]
    if isinstance(value, str):
        for pattern in _SENSITIVE_VALUE_RES:
            value = pattern.sub(_REDACTED, value)
        return value
    return value


def _audit_payload(frozen_plan: FrozenTitlePlan) -> dict[str, Any]:
    plan = frozen_plan.plan
    audit = plan.audit
    return {
        "audit_version": audit.audit_version if audit else "1.0",
        "template_version": plan.template_version,
        "template_hash": plan.template_hash,
        "title_plan_version": plan.title_plan_version,
        "validator_version": plan.validator_version,
        "input_hash": plan.input_hash,
        "raw_plan_hash": audit.raw_plan_hash if audit else None,
        "frozen_plan_hash": frozen_plan.frozen_plan_hash,
        "validation_status": plan.plan_validation_status.value,
        "fallback": plan.fallback,
        "fallback_scope": plan.fallback_scope.value,
        "fallback_reason": plan.fallback_reason.value if plan.fallback_reason else None,
        "fallback_node_ids": list(plan.fallback_node_ids),
        "rejected_dynamic_ids": list(plan.rejected_dynamic_ids),
        "model": audit.model if audit else None,
        "provider": audit.provider if audit else None,
        "created_at": audit.created_at if audit else None,
        "redaction_version": "1.0",
        "nodes": [
            {
                "section_id": node.section_id,
                "canonical_title": node.canonical_title,
                "display_title": node.display_title,
                "title_source": node.title_source.value,
                "purpose_code": node.purpose_code.value if node.purpose_code else None,
                "status": node.validation.status.value,
                "rule_ids": list(node.validation.rule_ids),
                "fallback": node.validation.fallback,
                "fallback_reason": node.validation.fallback_reason.value
                if node.validation.fallback_reason else None,
            }
            for node in plan.sections
        ],
    }


def serialize_audit(
    frozen_plan: FrozenTitlePlan,
    *,
    redaction: RedactionPolicy = DEFAULT,
) -> dict[str, object]:
    """序列化脱敏审计（§3.2 API）。返回可 JSON 化的 dict。"""
    payload = _audit_payload(frozen_plan)
    return redact(payload, policy=redaction)


def serialize_audit_json(frozen_plan: FrozenTitlePlan, *, redaction: RedactionPolicy = DEFAULT) -> str:
    return canonical_json(serialize_audit(frozen_plan, redaction=redaction))


def restore_audit(text: str) -> dict[str, Any]:
    """从序列化审计恢复为 dict（可核对 hash/status/version）。

    JSON 损坏时抛 ``AUDIT_PERSIST_ERROR``，表示审计无法恢复。
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TitlePlanError(ErrorCode.AUDIT_PERSIST_ERROR, f"审计 JSON 损坏: {exc}") from exc
    if not isinstance(data, dict):
        raise TitlePlanError(ErrorCode.AUDIT_PERSIST_ERROR, "审计根必须是对象")
    return data


def verify_audit_hash(data: dict[str, Any], *, frozen_plan_hash: str) -> bool:
    """核对恢复后的审计 hash 是否与冻结 hash 一致。"""
    return str(data.get("frozen_plan_hash", "")) == frozen_plan_hash


__all__ = [
    "DEFAULT",
    "RedactionPolicy",
    "redact",
    "restore_audit",
    "serialize_audit",
    "serialize_audit_json",
    "verify_audit_hash",
]
