"""Compatibility boundary from the historical CN Flow request to EO 14117.

The adapter is deliberately strict about facts that affect the legal result. It
must never turn an omitted value into a benign default such as zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.domains.us.eo14117.schema import (
    US14117DataItem,
    US14117Entity,
    US14117Request,
)
from backend.domains.us.eo14117_flow_review.schema import CNFlowRequest


class CompatibilityClarificationRequired(ValueError):
    """Raised when legacy input cannot support a defensible canonical decision."""

    def __init__(self, questions: list[str], *, lossy_fields: list[str] | None = None) -> None:
        self.questions = questions
        self.lossy_fields = lossy_fields or []
        super().__init__("; ".join(questions))


@dataclass(frozen=True)
class CNFlowCompatibilityResult:
    canonical_request: US14117Request
    lossy_fields: list[str]
    clarification_questions: list[str]
    canonical_module: str = "us_14117"


@dataclass(frozen=True)
class CNFlowProjectionResult:
    legacy_request: CNFlowRequest
    lossy_fields: list[str]


def project_us14117_request_to_cn_flow(payload: US14117Request) -> CNFlowProjectionResult:
    """Project canonical facts into the historical request without inventing detail."""
    if len(payload.attachments) < 2:
        raise ValueError("CN Flow projection requires data and entity inventory attachments")

    def legacy_role(role: str) -> str:
        return role if role in {"processor", "controller", "subprocessor", "affiliate", "vendor"} else "vendor"

    item_names = [item.data_item_name for item in payload.data_items]
    counts = {item.us_person_count for item in payload.data_items}
    if len(counts) != 1:
        raise ValueError("CN Flow cannot represent different US-person counts per data item")
    attachments = []
    for index, path in enumerate(payload.attachments):
        suffix = Path(path).suffix.lower().lstrip(".")
        if suffix not in {"xlsx", "csv", "docx", "pdf"}:
            raise ValueError(f"CN Flow does not support attachment format: {path}")
        attachments.append({
            "file_role": "data_inventory" if index == 0 else "entity_inventory" if index == 1 else "supporting_material",
            "file_name": Path(path).name,
            "file_format": suffix,
            "storage_uri": path,
        })

    legacy = CNFlowRequest.model_validate({
        "company_name": payload.company_name,
        "transfer_purpose": payload.transaction_description,
        "data_categories": item_names,
        "sensitive_data_flags": [item.data_item_name for item in payload.data_items if item.is_sensitive_personal_info],
        "us_person_count": counts.pop(),
        "transaction_type": payload.transaction_type,
        "doj_data_category_by_item": {item.data_item_name: item.doj_data_category for item in payload.data_items},
        "recipient_entities": [
            {
                "entity_name": entity.entity_name,
                "country_region": entity.country_of_registration,
                "entity_role": legacy_role(entity.entity_role),
                "is_restricted_party": entity.is_covered_person is True,
            }
            for entity in payload.recipient_entities
        ],
        "transfer_chain": f"{payload.company_name} -> " + " -> ".join(entity.entity_name for entity in payload.recipient_entities),
        "attachments": attachments,
    })
    lossy = [
        "data_items.details",
        "recipient_entities.ownership_and_governance",
        "access_persons",
        "security_measures",
        "onward_transfer",
    ]
    return CNFlowProjectionResult(legacy_request=legacy, lossy_fields=lossy)


def adapt_cn_flow_request(payload: CNFlowRequest) -> CNFlowCompatibilityResult:
    """Convert a legacy request when all result-critical facts are present."""
    questions: list[str] = []
    lossy: list[str] = []

    if payload.us_person_count is None:
        questions.append("请补充每类数据涉及的美国个人数量（us_person_count）。")
        lossy.append("data_items.us_person_count")
    if not payload.transaction_type:
        questions.append("请明确交易类型（transaction_type），例如 vendor_agreement 或 data_brokerage。")
        lossy.append("transaction_type")

    item_names = list(dict.fromkeys(payload.data_categories + payload.sensitive_data_flags))
    missing_categories = [name for name in item_names if name not in payload.doj_data_category_by_item]
    if missing_categories:
        questions.append("请为以下数据项补充 DOJ 数据分类：" + "、".join(missing_categories) + "。")
        lossy.extend(f"doj_data_category_by_item.{name}" for name in missing_categories)

    if questions:
        raise CompatibilityClarificationRequired(questions, lossy_fields=lossy)

    assert payload.us_person_count is not None
    assert payload.transaction_type is not None
    data_items = [
        US14117DataItem(
            data_item_name=item_name,
            data_description=item_name,
            is_personal_info=True,
            is_sensitive_personal_info=item_name in payload.sensitive_data_flags,
            us_person_count=payload.us_person_count,
            doj_data_category=payload.doj_data_category_by_item[item_name],
        )
        for item_name in item_names
    ]
    entities = [
        US14117Entity(
            entity_name=item.entity_name,
            country_of_registration=item.country_region,
            entity_role=item.entity_role,
            is_covered_person=None,
        )
        for item in payload.recipient_entities
    ]
    attachments = [item.storage_uri for item in payload.attachments]
    canonical = US14117Request(
        project_name=f"{payload.company_name}数据流合规评估",
        transaction_description=f"{payload.transfer_purpose}；传输链路：{payload.transfer_chain}",
        transaction_type=payload.transaction_type,
        data_items=data_items,
        recipient_entities=entities,
        access_persons=[],
        security_measures=[],
        onward_transfer=False,
        onward_transfer_description="",
        attachments=attachments,
        company_name=payload.company_name,
    )
    if any(item.is_restricted_party for item in payload.recipient_entities):
        lossy.append("recipient_entities.is_restricted_party")
    lossy.append("onward_transfer")
    lossy.append("attachments.content_unparsed")
    return CNFlowCompatibilityResult(canonical, lossy, [], "us_14117")
