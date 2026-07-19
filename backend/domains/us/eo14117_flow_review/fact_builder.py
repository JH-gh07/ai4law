from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import FactItem
from backend.domains.us.eo14117_flow_review.schema import CNFlowRequest


def _fact_id(field_path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", field_path).strip("-")
    return f"FACT-{safe}"


def _fact(field_path: str, value: Any, *, source_type: str = "schema", source_ref: str | None = None) -> FactItem:
    return FactItem(
        fact_id=_fact_id(field_path),
        source_type=source_type,
        source_ref=source_ref or "CNFlowRequest",
        field_path=field_path,
        value=value,
        normalized_value=value,
        confidence=1.0,
    )


def build_cn_flow_facts(
    payload: CNFlowRequest,
    *,
    risk_level: str,
    risk_items: list[Any],
) -> list[FactItem]:
    facts: list[FactItem] = [
        _fact("request.company_name", payload.company_name),
        _fact("request.transfer_purpose", payload.transfer_purpose),
        _fact("request.data_categories", list(payload.data_categories)),
        _fact("request.sensitive_data_flags", list(payload.sensitive_data_flags)),
        _fact("request.transfer_chain", payload.transfer_chain),
        _fact("request.attachments", [item.model_dump() for item in payload.attachments]),
        _fact("request.recipient_entities", [item.model_dump() for item in payload.recipient_entities]),
        _fact("derived.risk_level", risk_level, source_type="derived", source_ref="CNFlowService"),
        _fact(
            "derived.risk_item_ids",
            [item.risk_id for item in risk_items],
            source_type="derived",
            source_ref="CNFlowService",
        ),
    ]
    return facts
