"""DPIA writing strategy builder — forbidden expressions and external/internal expressions for DPIA issues."""

from __future__ import annotations

from typing import Any

from backend.common.workflow import IssueItem

_BASE_FORBIDDEN_EXPRESSIONS = [
    "风险已完全消除",
    "不存在歧视风险",
    "已充分取得所有同意",
    "匿名化后无任何个人数据风险",
    "自动化决策不影响个人权利",
    "无需进一步监管沟通",
    "可直接上线",
    "完全符合GDPR要求",
    "不涉及个人数据",
    "数据处理绝对安全",
    "彻底解决了隐私问题",
]

_ISSUE_FORBIDDEN: dict[str, list[str]] = {
    "DPIA-ISSUE-automated-decision": [
        "自动化决策不影响数据主体权利",
        "算法决策完全公平公正",
        "系统自动决策无需人工干预",
    ],
    "DPIA-ISSUE-profiling-risk": [
        "画像处理对个人无影响",
        "评分系统不存在偏差",
    ],
    "DPIA-ISSUE-special-category": [
        "特殊类别数据已获得充分同意保护",
        "处理敏感数据无明显风险",
    ],
    "DPIA-ISSUE-large-scale": [
        "大规模处理不影响数据安全",
        "数据量不影响风险评估结论",
    ],
    "DPIA-ISSUE-systematic-monitoring": [
        "监控系统不影响公众隐私",
        "监控已充分公示，不涉及隐私问题",
    ],
    "DPIA-ISSUE-data-matching": [
        "数据匹配不产生额外风险",
        "组合数据不存在重识别可能",
    ],
    "DPIA-ISSUE-new-technology": [
        "新技术已充分验证安全性",
        "技术方案不涉及隐私风险",
    ],
    "DPIA-ISSUE-vulnerable-subjects": [
        "弱势群体保护已充分考虑",
        "数据主体不存在权利不对等问题",
    ],
    "DPIA-ISSUE-necessity-weak": [
        "数据处理确有必要",
        "必要性已充分论证无需补充",
    ],
    "DPIA-ISSUE-proportionality-weak": [
        "处理范围与目的相称",
        "相称性已充分论证",
    ],
    "DPIA-ISSUE-lawful-basis-unclear": [
        "合法性基础已明确",
        "处理活动具备充分法律依据",
    ],
    "DPIA-ISSUE-consent-not-free": [
        "数据主体同意为自由给予",
        "雇佣关系中同意有效",
    ],
    "DPIA-ISSUE-transparency-gap": [
        "透明度要求已完全满足",
        "告知信息已充分覆盖所有要求",
    ],
    "DPIA-ISSUE-discrimination-risk": [
        "不存在歧视或偏见风险",
        "算法公平性已得到保证",
    ],
    "DPIA-ISSUE-cross-border-risk": [
        "接收国数据保护水平等同于欧盟",
        "跨境传输无需额外保障措施",
    ],
    "DPIA-ISSUE-mitigation-insufficient": [
        "现有措施已足以应对所有风险",
        "风险已得到完全控制",
    ],
    "DPIA-ISSUE-prior-consultation-needed": [
        "无需监管机构事先咨询",
        "剩余风险可接受无需进一步评估",
    ],
    "DPIA-ISSUE-dpo-opinion-missing": [
        "DPO意见已口头确认",
        "无需DPO书面意见",
    ],
}


def _external_expression(issue: IssueItem) -> str:
    if issue.issue_id == "DPIA-ISSUE-automated-decision":
        return (
            "该项目涉及自动化决策或画像处理，依据GDPR Art 22，"
            "应确保数据主体有权获得人工干预、表达观点和质疑决策的机会。"
            "建议补充算法逻辑说明、人工干预机制和数据主体救济渠道。"
        )
    if issue.issue_id == "DPIA-ISSUE-profiling-risk":
        return (
            "项目目标涉及评估、评分或画像处理，可能对数据主体产生重大影响。"
            "建议补充画像逻辑说明、数据源、准确性保障及异议处理机制。"
        )
    if issue.issue_id == "DPIA-ISSUE-special-category":
        return (
            "该项目涉及特殊类别个人数据，需依据GDPR Art 9确认适用的豁免条件"
            "并补充对应的保护措施。建议在DPIA中详细论证处理该等数据的必要性、"
            "相称性及额外安全保障措施。"
        )
    if issue.issue_id == "DPIA-ISSUE-large-scale":
        return (
            "该项目涉及大规模处理个人数据，依据WP248高风险标准，"
            "应补充处理规模的统计口径、数据最小化措施和定期审查计划。"
        )
    if issue.issue_id == "DPIA-ISSUE-systematic-monitoring":
        return (
            "该项目涉及公共区域的大规模系统性监控，属于WP248明确列举的高风险活动。"
            "建议补充监控的合法性基础、数据保留期限、透明度措施和数据主体异议机制。"
        )
    if issue.issue_id == "DPIA-ISSUE-data-matching":
        return (
            "该项目涉及多源数据匹配或重识别组合，可能超出原始收集目的。"
            "建议进行目的兼容性分析并评估重识别风险。"
        )
    if issue.issue_id == "DPIA-ISSUE-new-technology":
        return (
            "该项目使用新技术处理方式，依据GDPR Art 35(1)，"
            "需评估其对个人数据保护的影响。建议补充技术说明和新技术的隐私风险评估。"
        )
    if issue.issue_id == "DPIA-ISSUE-vulnerable-subjects":
        return (
            "该项目涉及弱势数据主体，存在权利不对等，依据WP248需要特别保护。"
            "建议补充弱势群体保护措施和额外保障机制。"
        )
    if issue.issue_id == "DPIA-ISSUE-necessity-weak":
        return (
            "当前必要性论证尚不充分，依据GDPR Art 35(7)(b)，"
            "应补充详细论证说明为何必须处理该个人数据及为何无法以侵入性更低的方式实现目的。"
        )
    if issue.issue_id == "DPIA-ISSUE-proportionality-weak":
        return (
            "当前相称性分析尚不充分，依据GDPR Art 5(c)数据最小化原则，"
            "应论证处理范围、频率和存储期限与处理目的相称。"
        )
    if issue.issue_id == "DPIA-ISSUE-lawful-basis-unclear":
        return (
            "当前未明确列示处理活动的合法性基础，依据GDPR Art 6，"
            "应明确说明所依赖的具体合法性基础并附上相关论证。"
        )
    if issue.issue_id == "DPIA-ISSUE-consent-not-free":
        return (
            "在涉及健康数据的雇佣或保险等不对等关系中，数据主体的同意可能非自由给予。"
            "建议评估同意的自由性，并考虑是否应依赖其他合法性基础替代同意。"
        )
    if issue.issue_id == "DPIA-ISSUE-transparency-gap":
        return (
            "当前透明度信息不足，可能无法满足GDPR Art 13/14的告知要求。"
            "建议补充数据主体告知内容，包括处理目的、法律依据、接收方、保留期限和数据主体权利。"
        )
    if issue.issue_id == "DPIA-ISSUE-discrimination-risk":
        return (
            "自动化决策与特殊类别数据叠加使用可能导致歧视性结果。"
            "建议补充反歧视保障措施、算法公平性审计和定期偏差检测机制。"
        )
    if issue.issue_id == "DPIA-ISSUE-cross-border-risk":
        return (
            "数据将传输至未获得欧盟充分性认定的国家/地区，依据GDPR Art 44-46，"
            "需补充传输保障措施（标准合同条款/约束性公司规则/行为准则等）并评估接收方数据保护水平。"
        )
    if issue.issue_id == "DPIA-ISSUE-mitigation-insufficient":
        return (
            "已识别的风险与缓解措施之间可能存在覆盖缺口。"
            "建议逐项核查每个已识别风险是否有对应的缓解措施，补充缺失项。"
        )
    if issue.issue_id == "DPIA-ISSUE-prior-consultation-needed":
        return (
            "存在多项高风险因素，若剩余风险无法充分降低，"
            "应依据GDPR Art 36进行监管机构事先咨询。建议评估剩余风险可接受性，"
            "如不可接受则准备事先咨询材料。"
        )
    if issue.issue_id == "DPIA-ISSUE-dpo-opinion-missing":
        return (
            "DPO审查意见缺失，依据GDPR Art 35(2)和Art 39，"
            "应请DPO审查DPIA草案并出具书面意见。"
        )
    if issue.category == "documentation":
        return "当前材料尚需进一步补充，以提高DPIA草案论证充分性和合规说服力。"
    if issue.category == "mitigation_gap":
        return "建议进一步补充风险缓解措施的细节、负责方和实施时间表，以增强剩余风险评估的可信度。"
    return f"建议围绕\"{issue.title}\"进一步补充事实说明、法律依据和缓解措施。"


def _internal_expression(issue: IssueItem) -> str:
    return f"{issue.title}：{issue.description} 建议：{issue.recommended_action}"


def build_writing_strategy(issues: list[IssueItem]) -> dict[str, Any]:
    strategies: list[dict[str, Any]] = []
    for issue in issues:
        forbidden = [*_BASE_FORBIDDEN_EXPRESSIONS, *_ISSUE_FORBIDDEN.get(issue.issue_id, [])]
        tone = "conservative" if issue.severity in {"HIGH", "BLOCKER"} else "balanced"
        strategies.append({
            "issue_id": issue.issue_id,
            "issue_type": issue.category,
            "risk_level": issue.severity,
            "internal_expression": _internal_expression(issue),
            "external_expression": _external_expression(issue),
            "forbidden_expressions": forbidden,
            "tone": tone,
            "can_enter_external_report": True,
        })

    return {
        "module": "dpia",
        "strategy_version": "v1",
        "global_external_tone": (
            "审慎、正式、避免绝对化断言。"
            "使用\"建议\"\"可能\"\"尚需\"等审慎措辞，避免\"已完全\"\"确定性地\"等绝对表述。"
            "在最终结论部分明确声明残余风险水平及是否需要事先咨询。"
        ),
        "global_forbidden_expressions": _BASE_FORBIDDEN_EXPRESSIONS,
        "strategies": strategies,
    }
