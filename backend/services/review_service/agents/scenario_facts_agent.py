"""Agent P0-1: ScenarioFactsAgent — detect implicit cross-border risks beyond document text.

Key capability: when a contract doesn't mention cross-border transfer but
the business context suggests overseas servers/access/backup, flag it as
implicit cross-border risk.
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

_IMPLICIT_CB_SIGNALS = [
    # 境外服务器/数据中心
    (r"(?:服务器|数据中心|机房|云平台|cloud).{0,15}(?:新加坡|香港|美国|日本|韩国|英国|德国|法国|澳大利亚|印度|马来西亚|台湾|开曼)", "境外服务器/数据中心"),
    (r"(?:海外|境外|国外).{0,10}(?:服务器|机房|数据中心|节点|部署)", "海外部署"),
    # 跨国公司背景
    (r"(?:跨国|全球|国际).{0,10}(?:企业|集团|公司|业务)", "跨国企业背景"),
    (r"(?:新加坡|香港|美国|日本|韩国|英国).{0,10}(?:总部|集团|公司|子公司)", "海外实体"),
    # 远程访问风险
    (r"(?:远程|境外).{0,10}(?:运维|访问|管理|监控|支持|开发)", "境外远程运维/访问"),
    (r"(?:境外|海外|offshore).{0,10}(?:团队|开发|工程师|支持)", "境外团队"),
    # 云服务风险
    (r"(?:AWS|Azure|GCP|阿里云.*海外|腾讯云.*海外|华为云.*海外|Salesforce|Oracle.*Cloud)", "境外云服务"),
    # 备份风险
    (r"(?:境外|海外|异地).{0,10}(?:备份|灾备|容灾|disaster recovery)", "境外备份/灾备"),
    # 处理地点模糊
    (r"(?:处理.*地点|存储.*地点|服务器.*位置).{0,30}(?:未|不|待|详见|参见)", "处理地点未明确"),
]


class ScenarioFactsAgent(ReviewAgentBase):
    agent_name = "review_scenario_facts"
    max_tokens = 600

    def run(self, full_text: str = "", scenario_context: dict | None = None,
            extracted_indicators: list[str] | None = None) -> dict:
        """Detect implicit cross-border and other scenario risks.

        Returns structured findings about risks NOT explicitly stated in the document.
        """
        text = full_text[:10000] if full_text else ""
        ctx = scenario_context or {}
        indicators = extracted_indicators or []

        # ── Heuristic detection ──
        import re
        findings: list[dict] = []
        for pattern, label in _IMPLICIT_CB_SIGNALS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                excerpt = m.group(0)[:150]
                findings.append({
                    "type": "implicit_cross_border_indicator" if "境外" in label or "海外" in label or "跨国" in label or "云服务" in label or "备份" in label
                    else "processing_location_uncertain",
                    "label": label,
                    "excerpt": excerpt,
                    "severity": "HIGH" if ("境外" in label and "处理地点" not in label) else "MEDIUM",
                })
                break  # one finding per signal type

        # Cross-check: has overseas server but doc doesn't mention cross-border
        has_overseas = any("境外" in f["label"] or "海外" in f["label"] or "跨国" in f["label"] for f in findings)
        doc_mentions_cb = any(kw in text.lower() for kw in ["出境", "跨境", "境外.*传输", "cross.border", "数据传输.*境外"])
        if has_overseas and not doc_mentions_cb:
            findings.append({
                "type": "implicit_cross_border_transfer",
                "severity": "HIGH",
                "label": "隐含数据出境风险",
                "excerpt": "文档未明确提及数据出境，但背景信息显示存在境外服务器/访问/运维",
                "required_confirmations": [
                    "乙方服务器实际部署地点", "是否存在境外远程访问",
                    "是否存在境外备份", "是否向境外接收方提供个人信息",
                ],
            })

        # User context hints
        user_hints = ctx.get("cross_border_indicators", []) or []
        if user_hints and not doc_mentions_cb:
            findings.append({
                "type": "user_context_cross_border_flag",
                "severity": "HIGH",
                "label": "用户背景提示数据出境",
                "excerpt": f"用户提供背景: {'; '.join(user_hints[:3])}",
            })

        # ── Agent refinement ──
        agent_result = self._call_llm(
            f"""Detect implicit cross-border transfer risks from document and context.

Document text (excerpt): {text[:3000] if text else 'N/A'}
User context: {ctx}
Extracted indicators: {indicators[:10]}
Heuristic findings: {findings}

Return JSON:
{{
  "has_implicit_cross_border_risk": true|false,
  "risk_level": "HIGH|MEDIUM|LOW",
  "findings": [{{"type": "...", "severity": "...", "description": "..."}}],
  "required_confirmations": ["question1", "question2"],
  "summary": "<one sentence>"
}}"""
        )

        if agent_result:
            return agent_result

        return {
            "has_implicit_cross_border_risk": any(f["severity"] == "HIGH" for f in findings),
            "risk_level": "HIGH" if any(f["severity"] == "HIGH" for f in findings) else "MEDIUM",
            "findings": findings,
            "required_confirmations": list(dict.fromkeys(
                c for f in findings for c in f.get("required_confirmations", [])
            )),
            "summary": (
                "检测到文档未明确写明的出境的隐含风险" if findings
                else "未检测到文档外的隐含出境风险"
            ),
        }
