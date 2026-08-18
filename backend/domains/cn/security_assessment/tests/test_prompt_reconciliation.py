"""task081 T081-04 — ContextPack 全局事实与逐章实际 Prompt 的对账回归。

历史缺陷：``build_context_block_from_pack`` 只把被 Issue 引用的
``confirmed_facts`` 写进 Prompt，导致 company_name/industry 等核心字段从未
进入任何章节 Prompt，且 data_scope/rights_impact 在全局有值时仍输出
「本章节无确认事实」。本文件固化为回归用例。
"""

from __future__ import annotations

from backend.common.workflow import FactItem, GenerationContextPack
from backend.domains.cn.security_assessment.chapter_generator import (
    build_context_block_from_pack,
)


def _fact(field_path: str, value: object) -> FactItem:
    return FactItem(
        fact_id=f"FACT-{field_path.replace('.', '-')}",
        source_type="schema",
        field_path=field_path,
        value=value,
        normalized_value=value,
    )


def _pack(facts: list[FactItem], chapter_id: str) -> GenerationContextPack:
    return GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=facts,
        diagnosis_result={"recommended_path": "security_assessment"},
        regulations=[],
        issues=[],
        evidence_chain=[],
        risk_summary={"risk_level": "HIGH"},
        generation_basis_pack={
            "section_packs": [
                # 该章节没有任何 Issue 引用的 confirmed_facts，以复现「无确认事实」路径。
                {"section_id": chapter_id, "section_title": chapter_id, "confirmed_facts": []}
            ]
        },
    )


def test_overview_prompt_carries_core_profile_not_just_path_and_files() -> None:
    pack = _pack(
        [
            _fact("request.company_name", "云帆数据科技有限公司"),
            _fact("request.industry", "跨境电商"),
            _fact("request.is_ciio", True),
            _fact("request.transfer_purpose", "模型训练"),
            _fact("request.receiver_country", "新加坡"),
        ],
        "overview",
    )

    prompt = build_context_block_from_pack(pack, "overview")

    assert "request.company_name" in prompt
    assert "request.industry" in prompt
    assert "request.is_ciio" in prompt
    assert "request.transfer_purpose" in prompt
    assert "request.receiver_country" in prompt
    assert "本章节无确认事实" not in prompt


def test_data_scope_prompt_includes_structured_data_inventory() -> None:
    pack = _pack(
        [_fact("request.data_inventory_items", [{"name": "订单号"}, {"name": "手机号"}])],
        "data_scope",
    )

    prompt = build_context_block_from_pack(pack, "data_scope")

    assert "request.data_inventory_items" in prompt
    assert "订单号" in prompt
    assert "本章节无确认事实" not in prompt


def test_rights_impact_prompt_includes_personal_info_protection() -> None:
    pack = _pack(
        [_fact("request.personal_info_protection", {"separate_consent_status": "obtained"})],
        "rights_impact",
    )

    prompt = build_context_block_from_pack(pack, "rights_impact")

    assert "request.personal_info_protection" in prompt
    assert "本章节无确认事实" not in prompt


def test_security_measures_prompt_includes_system_link() -> None:
    pack = _pack(
        [_fact("request.system_link", {"domestic_systems": ["订单系统"]})],
        "security_measures",
    )

    prompt = build_context_block_from_pack(pack, "security_measures")

    assert "request.system_link" in prompt
    assert "本章节无确认事实" not in prompt


def test_natural_fields_are_deduped_against_confirmed_facts() -> None:
    # confirmed_facts 已含 company_name，自然字段注入不得重复输出同一字段路径。
    pack = GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=[_fact("request.company_name", "云帆数据科技有限公司")],
        diagnosis_result={},
        regulations=[],
        issues=[],
        evidence_chain=[],
        generation_basis_pack={
            "section_packs": [
                {
                    "section_id": "overview",
                    "section_title": "overview",
                    "confirmed_facts": [
                        {"field_path": "request.company_name", "value": "云帆数据科技有限公司"}
                    ],
                }
            ]
        },
    )

    prompt = build_context_block_from_pack(pack, "overview")

    assert prompt.count("request.company_name") == 1
