"""Utilities for combining rule-generated and agent-generated CPRA gaps."""

from __future__ import annotations

from backend.modules.cpra.schema import CPRAGapItem


class CPRAGapMerger:
    def merge(self, base_items: list[CPRAGapItem], extra_items: list[CPRAGapItem]) -> list[CPRAGapItem]:
        merged: list[CPRAGapItem] = []
        seen: set[tuple[str, str, str]] = set()
        for item in [*base_items, *extra_items]:
            key = (item.domain, item.gap, item.legal_basis)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged
