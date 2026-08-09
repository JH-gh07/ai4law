"""Deterministic CPRA report chapters used as the reliable generation floor."""

from __future__ import annotations

import re

from backend.common.citation.registry import CitationRegistry
from backend.common.llm.postprocess import apply_citation_pipeline
from backend.domains.us.cpra.schema import CPRAChapter, CPRACitationRef

_GAP_RE = re.compile(
    r"^- \[(HIGH|MEDIUM|LOW)\] ([^｜]+)｜([^｜]+)｜([^｜]+)｜(.+)$",
    re.MULTILINE,
)
_BAD_OUTPUT_MARKERS = (
    "LLM未配置",
    "占位内容",
    "{{CIT-",
    "引用格式不完整",
    "引用无法映射",
    "[TRUNCATED]",
)
_DOMAIN_LABELS = {
    "notice_and_consent": "告知与同意",
    "consumer_rights_process": "消费者权利流程",
    "opt_out_and_sale_sharing": "退出出售或共享",
    "consent_ui": "同意界面",
    "vendor_management": "供应商管理",
    "vendor_review": "供应商合同",
    "spi": "敏感个人信息",
    "spi_review": "敏感个人信息",
    "overall": "总体合规",
}


def is_usable_cpra_chapter(text: str, violations: list[object] | None = None) -> bool:
    normalized = (text or "").strip()
    return (
        len(normalized) >= 120
        and not any(marker in normalized for marker in _BAD_OUTPUT_MARKERS)
        and not violations
    )


def build_deterministic_cpra_chapters(
    *,
    context: str,
    level: str,
    citations: list[CPRACitationRef],
    registry: CitationRegistry,
) -> list[CPRAChapter]:
    fields = _parse_fields(context)
    gaps = _GAP_RE.findall(context)
    company = fields.get("企业名称", "未提供企业名称")
    business = fields.get("业务模型", "未提供")
    lifecycle = fields.get("数据生命周期", "未提供")
    notice = fields.get("告知与同意现状", "未提供")
    rights = fields.get("消费者权利流程", "未提供")
    sharing = fields.get("出售或共享现状", "未提供")
    vendor = fields.get("供应商管理现状", "未提供")

    high = [item for item in gaps if item[0] == "HIGH"]
    medium = [item for item in gaps if item[0] == "MEDIUM"]
    top_gap_lines = _gap_lines(gaps[:5]) or "- 当前输入范围内未形成可列示的差距项。"
    action_lines = _action_lines(gaps) or "- 持续保存合规证据，并在业务或法规变化时重新评估。"

    chapter_specs = [
        (
            "执行摘要",
            f"本次评估对象为{company}，综合风险等级为 {level}。规则检查共形成 {len(gaps)} 项差距，"
            f"其中高风险 {len(high)} 项、中风险 {len(medium)} 项。该结论只覆盖本次提交的信息和附件，"
            "未提供的制度、系统配置或合同证据不视为已经满足要求。\n\n"
            f"重点事项如下：\n{top_gap_lines}",
            (),
        ),
        (
            "企业适用性与范围",
            f"企业名称：{company}。业务模型：{business}。数据生命周期：{lifecycle}。"
            "适用性判断应结合企业门槛、加州消费者数量、数据出售或共享活动及法定例外逐项确认；"
            "当前未提供的门槛数据均保留为待核验事项，不能据此作出不适用结论。",
            ("1798.140", "1798.145"),
        ),
        (
            "数据处理活动合规分析",
            f"当前告知与同意情况：{notice}。当前数据生命周期描述：{lifecycle}。"
            "评估重点包括收集时告知、目的相容性、数据最小化、保存期限、合理安全措施以及向第三方、"
            "服务提供商或承包商披露时的合同控制。缺少证据的控制项应列入整改台账，而非默认通过。",
            ("1798.100",),
        ),
        (
            "消费者权利保障评估",
            f"当前消费者权利流程：{rights}。当前出售或共享说明：{sharing}。"
            "需要核验知情、访问、删除、更正、退出出售或共享、限制敏感个人信息使用等入口是否可用，"
            "以及身份验证、受理、答复、延期和留痕机制是否能够按统一流程执行。",
            ("1798.105", "1798.106", "1798.110", "1798.120", "1798.130"),
        ),
        (
            "敏感信息与第三方管理",
            f"当前供应商管理情况：{vendor}。对敏感个人信息，应核验用途限制和消费者限制使用入口；"
            "对第三方、服务提供商和承包商，应核验合同目的限制、同等保护、通知、审计或核查、停止和补救机制。"
            "仅出现 DPA 名称而没有实际条款或执行证据，不能证明控制已经落地。",
            ("1798.100", "1798.121", "1798.140"),
        ),
        (
            "行动清单与优先级",
            "整改应以差距清单为唯一任务来源，先处理高风险和短期事项，再处理流程完善与持续监控。"
            "每项任务应指定负责人、完成日期、验收证据和复核人；没有验收证据的任务不得标记完成。\n\n"
            f"建议行动：\n{action_lines}",
            ("1798.100", "1798.120", "1798.121", "1798.130"),
        ),
    ]

    chapters: list[CPRAChapter] = []
    for number, (title, body, preferred_articles) in enumerate(chapter_specs, start=1):
        selected = _select_refs(citations, preferred_articles)
        if selected:
            markers = "".join(f"{{{{{ref.citation_id}}}}}" for ref in selected)
            body = f"{body} {markers}"
        processed = apply_citation_pipeline(
            body,
            registry=registry,
            allowed_citations=[ref.display_label for ref in selected],
        )
        chapters.append(
            CPRAChapter(
                chapter_no=number,
                title=title,
                content=processed.text,
                citations=[ref.citation_id for ref in selected],
                citation_refs=selected,
                risk_level=level,
            )
        )
    return chapters


def _parse_fields(context: str) -> dict[str, str]:
    return {
        key.strip(): value.strip()
        for key, value in re.findall(r"^- ([^：\n]+)：(.*)$", context, re.MULTILINE)
    }


def _select_refs(
    citations: list[CPRACitationRef], preferred_articles: tuple[str, ...]
) -> list[CPRACitationRef]:
    selected = [ref for ref in citations if ref.article_no in preferred_articles]
    if not selected and citations and not preferred_articles:
        selected = citations[:1]
    return selected[:3]


def _gap_lines(gaps: list[tuple[str, str, str, str, str]]) -> str:
    return "\n".join(
        f"- [{risk}] {_DOMAIN_LABELS.get(domain, domain)}：{gap}"
        for risk, domain, gap, _basis, _action in gaps
    )


def _action_lines(gaps: list[tuple[str, str, str, str, str]]) -> str:
    ordered = sorted(gaps, key=lambda item: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[item[0]])
    return "\n".join(
        f"- [{risk}] {_DOMAIN_LABELS.get(domain, domain)}：{action}（问题：{gap}）"
        for risk, domain, gap, _basis, action in ordered[:8]
    )
