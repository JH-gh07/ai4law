"""Canonical source identity resolver（task073 T06-A）。

把 CitationItem/绑定里的 ``source_id`` 通过 **exact membership** 解析回
SourceRegistry 的权威身份，得到三类结果：

- ``REGISTERED``：source_id 命中 Registry，读取权威 ``review_status`` /
  ``can_be_cited`` / ``can_enter_external_report`` / ``allowed_usage``。
- ``UNREGISTERED``：source_id 不在 Registry（含 DeliLegal 合成、fallback），
  绝不 fuzzy 提升。
- ``INELIGIBLE``：命中 Registry 但 ``review_status=metadata_review_required``
  或 ``can_be_cited=False``，fail-closed 为不可正式引用。

权威值只来自 ``SourceRegistryEntry``，绝不从 chunk 复制形成第二真相源。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from backend.common.knowledge.registry import ensure_source_registry
from backend.common.knowledge.v2 import SourceRegistryEntry

IdentityStatus = Literal["REGISTERED", "UNREGISTERED", "INELIGIBLE"]

_FAIL_CLOSED_USAGE = ["internal_review"]


@dataclass
class SourceIdentity:
    source_id: str
    registry_source_id: str | None
    status: IdentityStatus
    review_status: str = ""
    can_be_cited: bool = False
    can_enter_external_report: bool = False
    allowed_usage: list[str] = field(default_factory=list)
    reason: str = ""


class SourceIdentityResolver:
    """Exact-membership lookup over the canonical SourceRegistry."""

    def __init__(self, entries: list[SourceRegistryEntry] | None = None) -> None:
        entries = entries if entries is not None else ensure_source_registry()
        self._by_source_id: dict[str, SourceRegistryEntry] = {
            entry.source_id: entry for entry in entries
        }

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._by_source_id

    def resolve(self, source_id: str) -> SourceIdentity:
        entry = self._by_source_id.get(source_id)
        if entry is None:
            return SourceIdentity(
                source_id=source_id,
                registry_source_id=None,
                status="UNREGISTERED",
                reason="source_id 不在 SourceRegistry（未注册/合成来源）",
            )

        review_status = (entry.review_status or "").strip().lower()
        ineligible = review_status == "metadata_review_required" or not entry.can_be_cited
        if ineligible:
            return SourceIdentity(
                source_id=source_id,
                registry_source_id=entry.source_id,
                status="INELIGIBLE",
                review_status=entry.review_status,
                can_be_cited=False,
                can_enter_external_report=False,
                allowed_usage=list(_FAIL_CLOSED_USAGE),
                reason="review_status/can_be_cited fail-closed",
            )

        return SourceIdentity(
            source_id=source_id,
            registry_source_id=entry.source_id,
            status="REGISTERED",
            review_status=entry.review_status,
            can_be_cited=entry.can_be_cited,
            can_enter_external_report=entry.can_enter_external_report,
            allowed_usage=list(entry.allowed_usage),
        )
