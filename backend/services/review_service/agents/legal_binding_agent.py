"""Agent P1-3: LegalBindingAgent — bind issues to precise legal citations with why_applicable.

Ensures each HIGH/MEDIUM issue has a tightly-matched legal basis, not just RAG-retrieved.
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

# Issue-type → default legal basis mapping
_ISSUE_LAW_MAP = {
    "cross_border": [
        ("《个人信息保护法》第38条", "规定个人信息出境须具备安全评估、标准合同或认证条件"),
        ("《数据出境安全评估办法》第4条", "规定触发安全评估的具体情形"),
    ],
    "consent": [
        ("《个人信息保护法》第39条", "规定向境外提供个人信息须告知并取得单独同意"),
    ],
    "security": [
        ("《个人信息保护法》第38条", "要求采取必要措施保障信息安全"),
        ("《数据安全法》第27条", "要求建立健全全流程数据安全管理制度"),
    ],
    "retention": [
        ("《个人信息保护法》第19条", "保存期限应为实现处理目的所必要的最短时间"),
    ],
    "liability": [
        ("《个人信息出境标准合同办法》第5条", "争议解决应选择中国内地法院或仲裁机构"),
        ("《民法典》第497条", "格式条款不得不合理免除或减轻责任"),
    ],
    "anonymization": [
        ("《个人信息保护法》第4条", "匿名化处理后的信息不属于个人信息"),
        ("《个人信息保护法》第73条", "匿名化定义：无法识别特定自然人且不能复原"),
    ],
    "sensitive_pi": [
        ("《个人信息保护法》第28条", "敏感个人信息定义及处理条件"),
        ("《个人信息保护法》第29条", "处理敏感个人信息需单独同意"),
    ],
    "onward_transfer": [
        ("《个人信息出境标准合同办法》第6条", "境外接收方再转移限制"),
    ],
}


class LegalBindingAgent(ReviewAgentBase):
    agent_name = "review_legal_binding"
    max_tokens = 500

    def run(self, issues: list[dict] | None = None) -> dict:
        items = issues or []
        bound: list[dict] = []

        for issue in items:
            issue_type = str(issue.get("clause_type", issue.get("category", ""))).lower()
            title = str(issue.get("title", ""))
            existing_cites = issue.get("citation_sources", []) or []

            matched_cites = []
            for map_key, citations in _ISSUE_LAW_MAP.items():
                if map_key in issue_type or map_key in title.lower():
                    matched_cites.extend(citations)
                    break

            if not matched_cites:
                matched_cites = [("待匹配", "请人工确认适用法规")]

            bound.append({
                "issue_id": issue.get("issue_id", "?"),
                "title": title[:80],
                "existing_citations": existing_cites[:3],
                "suggested_citations": [
                    {"source": c[0], "why_applicable": c[1]} for c in matched_cites[:3]
                ],
            })

        agent = self._call_llm(
            f"""Bind specific legal provisions to review issues.

Issues: {[{k: str(v)[:200] for k,v in i.items()} for i in items[:8]]}
Heuristic bindings: {bound[:8]}

Return JSON:
{{
  "bindings": [
    {{"issue_id": "...", "citations": [{{"source": "...", "why_applicable": "..."}}]}}
  ],
  "ungrounded_issues": ["issue_id with no clear legal basis"],
  "summary": "<one sentence>"
}}"""
        )
        if agent:
            return agent

        return {"bindings": bound, "ungrounded_issues": [], "summary": f"已为{len(bound)}个问题绑定法规依据"}
