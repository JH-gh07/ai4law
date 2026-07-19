"""P2 Agent 7: RAGPlanningAgent — plan precise legal retrieval queries for each issue.

Solves: CN SCC RAG is currently semi-dynamic (purpose + country only), leading to
generic regulation recall that cannot precisely support specific risk points.
This agent plans targeted queries by issue type.

Reference: docs/archive/design-provenance/认证标准合同路径.md Section 6
"""

from __future__ import annotations

from backend.domains.cn.scc_review.agents import SCCAgentBase
from backend.domains.cn.scc_review.schema import RAGQueryPlan


class RAGPlanningAgent(SCCAgentBase):
    agent_name = "cn_scc_rag_planning"
    max_tokens = 800

    def run(
        self,
        path_type: str = "standard_contract",
        issues: list[dict] | None = None,
        industry: str = "",
        receiver_country: str = "",
        data_types: list[str] | None = None,
        risk_points: list[str] | None = None,
    ) -> list[dict]:
        """Generate targeted RAG queries for each issue category.

        Ensures each issue can be supported by:
        - Higher-level law (上位法) — PIPL, DSL, CSL
        - Direct operational basis (直接操作依据) — Measures on Standard Contracts, Certification
        - Template basis (模板依据) — Official PIPIA templates
        - Technical standards (国家标准) — GB/T standards for technical issues
        """
        issues = issues or []
        data_types = data_types or []
        risk_points = risk_points or []

        if not self.enabled:
            return _rule_based_rag_planning(path_type, issues, industry, receiver_country, data_types, risk_points)

        issues_str = "\n".join(
            f"- [{i.get('category', 'other')}] {i.get('title', str(i))}" for i in issues[:10]
        ) if issues else "（无已识别问题）"

        risk_str = ", ".join(risk_points[:8]) if risk_points else "未指定"

        prompt = f"""Plan legal retrieval queries for CN SCC compliance report generation.

CONTEXT:
- Path Type: {path_type}
- Industry: {industry or "未指定"}
- Receiver Country: {receiver_country}
- Data Types: {", ".join(data_types) if data_types else "未指定"}
- Risk Points: {risk_str}

IDENTIFIED ISSUES:
{issues_str}

TASK: For each issue, generate 2-3 precise retrieval queries targeting:
1. 上位法: PIPL, Data Security Law, Cybersecurity Law, Personal Information Protection Law provisions
2. 直接操作依据: Measures on Standard Contracts for Cross-Border Transfer (个人信息出境标准合同办法), Measures on Certification (个人信息出境认证办法), Provisions on Promoting and Regulating Cross-Border Data Flow (促进和规范数据跨境流动规定)
3. 国家标准: GB/T 35273 (个人信息安全规范), GB/T 39335 (个人信息安全影响评估指南), GB/T 42460 (去标识化), GB/T 46068 (认证实施规则)
4. 官方指南: CAC guidelines, official Q&As, template documents

ISSUE CATEGORIES AND THEIR REQUIRED SOURCES:
- path (路径适用) → 上位法 + 部门规章
- consent (告知同意) → PIPL Art 13-17 + GB/T 35273 + 官方指南
- data_classification (数据分类) → PIPL Art 28 + GB/T 35273 + GB/T 42460
- contract (合同条款) → 标准合同办法 + 标准合同模板
- certification (认证) → 认证办法 + 认证实施规则 + GB/T 46068
- legal_document (法律文件) → 标准合同办法 + 必备条款清单
- security_measure (安全措施) → GB/T 35273 + GB/T 39335
- recipient (接收方) → PIPL Art 38-40 + 标准合同办法
- onward_transfer (转委托) → 标准合同模板 第8条
- anonymization (去标识化) → GB/T 42460 + PIPL Art 4, 73
- legal_basis (合法性基础) → PIPL Art 13 + GDPR对比参考

Return JSON array:
[
  {{
    "issue": "<issue title or category>",
    "queries": ["精准查询词1", "精准查询词2", "精准查询词3"],
    "required_source_types": ["national_standard", "personal_information_law", "official_guide", "departmental_regulation"]
  }}
]

IMPORTANT:
- Queries should be in Chinese and mirror legal search patterns on Chinese databases
- Include specific article numbers when known (e.g., "个人信息保护法 第13条 合法性基础")
- For technical issues, always include GB/T standard queries
- For contract issues, always include the standard contract template reference"""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_rag_planning(path_type, issues, industry, receiver_country, data_types, risk_points)

        if isinstance(result, dict):
            result = [result]
        if not isinstance(result, list):
            return _rule_based_rag_planning(path_type, issues, industry, receiver_country, data_types, risk_points)

        for plan in result:
            plan.setdefault("issue", "未指定问题")
            plan.setdefault("queries", [])
            plan.setdefault("required_source_types", ["personal_information_law", "official_guide"])

        return result


def _rule_based_rag_planning(
    path_type: str,
    issues: list[dict],
    industry: str,
    receiver_country: str,
    data_types: list[str],
    risk_points: list[str],
) -> list[dict]:
    """Fallback rule-based RAG query planning."""
    plans: list[dict] = []

    # Base queries by path type
    if path_type == "standard_contract":
        plans.append({
            "issue": "标准合同路径适用",
            "queries": [
                "个人信息出境标准合同办法 适用范围",
                "个人信息保护法 第38条 标准合同",
                "促进和规范数据跨境流动规定 标准合同备案",
            ],
            "required_source_types": ["personal_information_law", "departmental_regulation"],
        })

    elif path_type == "certification":
        plans.append({
            "issue": "认证路径适用",
            "queries": [
                "个人信息出境认证办法 适用范围",
                "个人信息保护认证实施规则",
                "GB/T 46068 个人信息出境认证",
            ],
            "required_source_types": ["departmental_regulation", "national_standard"],
        })

    elif path_type == "security_assessment":
        plans.append({
            "issue": "安全评估路径适用",
            "queries": [
                "数据出境安全评估办法 适用情形",
                "个人信息保护法 第40条 安全评估",
                "关键信息基础设施安全保护条例 数据出境",
            ],
            "required_source_types": ["personal_information_law", "departmental_regulation"],
        })

    # Issue-specific queries
    issue_queries = {
        "consent": {
            "queries": [
                "个人信息保护法 第13条 告知同意 单独同意",
                "GB/T 35273 个人信息安全规范 告知同意",
                "个人信息出境标准合同办法 告知同意要求",
            ],
            "sources": ["personal_information_law", "national_standard", "departmental_regulation"],
        },
        "contract": {
            "queries": [
                "个人信息出境标准合同办法 必备条款",
                "个人信息出境标准合同 模板 附件",
                "标准合同 境外接收方义务 安全措施",
            ],
            "sources": ["departmental_regulation", "official_guide"],
        },
        "security_measure": {
            "queries": [
                "GB/T 35273 个人信息安全规范 安全措施",
                "GB/T 39335 个人信息安全影响评估指南 安全措施",
                "个人信息保护法 第51条 安全保护措施",
            ],
            "sources": ["national_standard", "personal_information_law"],
        },
        "data_classification": {
            "queries": [
                "个人信息保护法 第28条 敏感个人信息",
                "GB/T 42460 个人信息去标识化 重标识化风险",
                "GB/T 35273 个人信息安全规范 个人敏感信息判定",
            ],
            "sources": ["personal_information_law", "national_standard"],
        },
        "anonymization": {
            "queries": [
                "GB/T 42460 个人信息去标识化 效果评估",
                "个人信息保护法 第4条 匿名化 第73条 去标识化",
                "GB/T 35273 匿名化 去标识化 技术措施",
            ],
            "sources": ["national_standard", "personal_information_law"],
        },
        "recipient": {
            "queries": [
                "个人信息保护法 第38条 境外接收方",
                "个人信息出境标准合同 境外接收方评估",
                "数据出境安全评估办法 境外接收方安全保障能力",
            ],
            "sources": ["personal_information_law", "departmental_regulation"],
        },
        "legal_document": {
            "queries": [
                "个人信息出境标准合同办法 合同文本要求",
                "标准合同 法律政策变化应对条款",
                "个人信息出境标准合同 争议解决 管辖条款",
            ],
            "sources": ["departmental_regulation", "official_guide"],
        },
        "legal_basis": {
            "queries": [
                "个人信息保护法 第13条 合法性基础",
                "个人信息出境标准合同办法 合法性正当性必要性",
                "GB/T 39335 个人信息安全影响评估 合法性基础评估",
            ],
            "sources": ["personal_information_law", "departmental_regulation", "national_standard"],
        },
    }

    for issue in issues:
        category = issue.get("category", "")
        title = issue.get("title", "")
        if category in issue_queries:
            plans.append({
                "issue": title or category,
                "queries": issue_queries[category]["queries"],
                "required_source_types": issue_queries[category]["sources"],
            })
        elif any(kw in (title + category).lower() for kw in ["安全", "security", "safety", "保护", "protection"]):
            plans.append({
                "issue": title or "安全措施",
                "queries": [
                    "个人信息保护法 第51条 安全保护措施",
                    "GB/T 35273 个人信息安全规范 安全措施要求",
                ],
                "required_source_types": ["personal_information_law", "national_standard"],
            })

    # Industry-specific
    if industry:
        plans.append({
            "issue": f"行业特别规定 - {industry}",
            "queries": [
                f"{industry} 数据安全 个人信息保护 行业规定",
                f"{industry} 数据出境 管理规定",
            ],
            "required_source_types": ["departmental_regulation", "official_guide"],
        })

    if not plans:
        plans.append({
            "issue": "通用合规依据",
            "queries": [
                "个人信息保护法 个人信息出境",
                "个人信息出境标准合同办法",
                "GB/T 35273 个人信息安全规范",
            ],
            "required_source_types": ["personal_information_law", "departmental_regulation", "national_standard"],
        })

    return plans
