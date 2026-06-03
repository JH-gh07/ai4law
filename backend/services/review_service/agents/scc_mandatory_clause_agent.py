"""Agent P0-3: SccMandatoryClauseAgent — mandatory clause comparison for CN SCC.

Key capability: detect when Annex II undermines standard contract body terms
(foreign court jurisdiction, liability caps, other-agreement-priority, etc.)
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

_SCC_MANDATORY_ANCHORS = {
    "dispute_resolution": {
        "allowed": ["中国内地", "内地", "北京", "上海", "深圳", "广州", "中国国际经济贸易仲裁委员会", "北京仲裁委员会"],
        "forbidden": ["香港", "新加坡", "美国", "英国", "境外", "外国", "开曼"],
        "rule": "《个人信息出境标准合同办法》第五条：争议解决应选择中国内地有管辖权的法院或仲裁机构",
    },
    "liability_cap": {
        "forbidden_patterns": ["责任总额不超过", "赔偿上限", "最高赔偿", "责任上限", "限额", "不超过.*服务费"],
        "rule": "标准合同不得通过责任上限条款削弱个人信息主体的损害赔偿权利",
    },
    "other_agreement_priority": {
        "forbidden_patterns": ["以.*为准", "优先.*适用", "不一致.*以.*为准", "主协议.*优先", "其他.*协议.*优先", "集团.*协议.*优先"],
        "rule": "制度合同约定其他约定不得与正文冲突",
    },
    "suspend_subject_rights": {
        "forbidden_patterns": ["暂缓.*请求", "暂停.*处理.*请求", "延迟.*主体.*权利", "可视.*情况", "自行决定"],
        "rule": "不得暂缓或限制个人信息主体的查阅、更正、删除等权利",
    },
    "retention_period": {
        "excessive_patterns": [r"长期.*保存", r"永久.*保存", r"10.*年", r"无限期", r"直到.*不再.*需要"],
        "rule": "《个人信息保护法》第19条：保存期限应为实现处理目的所必要的最短时间",
    },
    "storage_location_risk": {
        "high_risk_locations": ["美国", "印度", "开曼", "塞舌尔", "马绍尔"],
        "rule": "保存地点涉及高风险国家/地区需评估当地法律政策影响",
    },
}


class SccMandatoryClauseAgent(ReviewAgentBase):
    agent_name = "review_scc_mandatory"
    max_tokens = 600

    def run(self, full_text: str = "", annex_ii_text: str = "",
            is_scc: bool = False, clause_findings: list[dict] | None = None) -> dict:
        """Check SCC mandatory clause violations in Annex II."""
        text = full_text[:10000] if full_text else ""
        annex = annex_ii_text if annex_ii_text else text
        existing = clause_findings or []

        import re
        findings: list[dict] = []

        # 1. Dispute resolution
        for kw in _SCC_MANDATORY_ANCHORS["dispute_resolution"]["forbidden"]:
            pat = rf"{kw}.*(?:法院|管辖|仲裁|诉讼)"
            if re.search(pat, annex):
                findings.append({
                    "location": "附录二 / 争议解决条款",
                    "problem_type": "non_compliant",
                    "severity": "HIGH",
                    "finding": f"约定{kw}管辖/仲裁，违反标准合同正文争议解决条款",
                    "legal_basis": _SCC_MANDATORY_ANCHORS["dispute_resolution"]["rule"],
                    "recommendation": "修改为中国内地有管辖权的法院或仲裁机构",
                })
                break

        # 2-6 generic checks
        checks = [
            ("liability_cap", "附录二 / 责任条款", "设置了责任上限，可能削弱标准合同保护力度"),
            ("other_agreement_priority", "附录二 / 优先适用条款", "约定其他协议优先，可能架空标准合同正文"),
            ("suspend_subject_rights", "附录二 / 主体权利条款", "可能不当暂缓或限制个人信息主体权利"),
        ]
        for key, location, desc in checks:
            for pat in _SCC_MANDATORY_ANCHORS[key]["forbidden_patterns"]:
                if re.search(pat, annex):
                    findings.append({
                        "location": location, "problem_type": "non_compliant",
                        "severity": "HIGH", "finding": desc,
                        "legal_basis": _SCC_MANDATORY_ANCHORS[key]["rule"],
                        "recommendation": f"删除或修改该条款，确保符合标准合同要求",
                    })
                    break

        # Retention
        for pat in _SCC_MANDATORY_ANCHORS["retention_period"]["excessive_patterns"]:
            if re.search(pat, text):
                findings.append({
                    "location": "附录一 / 保存期限", "problem_type": "non_compliant", "severity": "MEDIUM",
                    "finding": "保存期限约定过长或模糊",
                    "legal_basis": _SCC_MANDATORY_ANCHORS["retention_period"]["rule"],
                    "recommendation": "明确最短保存期限并说明必要性",
                })
                break

        # Storage location
        for loc in _SCC_MANDATORY_ANCHORS["storage_location_risk"]["high_risk_locations"]:
            if loc in text and "评估" not in text and "TIA" not in text:
                findings.append({
                    "location": "附录一 / 保存地点", "problem_type": "missing_requirement", "severity": "MEDIUM",
                    "finding": f"保存地点涉及{loc}但未评估当地法律政策影响",
                    "legal_basis": _SCC_MANDATORY_ANCHORS["storage_location_risk"]["rule"],
                    "recommendation": f"补充对{loc}法律环境的评估及补充措施说明",
                })
                break

        # Agent refinement
        agent = self._call_llm(
            f"""Identify SCC mandatory clause violations in Chinese standard contract.

Annex II text: {annex[:3000]}
Full text excerpt: {text[:3000]}
Heuristic findings: {findings}
Existing rule findings: {existing[:5]}

Return JSON:
{{
  "mandatory_clause_violations": [
    {{"location": "...", "severity": "HIGH|MEDIUM|LOW", "violation": "...", "legal_basis": "...", "recommendation": "..."}}
  ],
  "scc_protection_weakened": true|false,
  "risk_of_filing_rejection": true|false,
  "summary": "<one sentence>"
}}"""
        )
        if agent:
            return agent

        return {
            "mandatory_clause_violations": findings,
            "scc_protection_weakened": len(findings) > 0,
            "risk_of_filing_rejection": any(f["severity"] == "HIGH" for f in findings),
            "summary": f"检测到{len(findings)}项标准合同强制条款违规" if findings else "未检测到标准合同强制条款违规",
        }
