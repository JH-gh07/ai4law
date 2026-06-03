"""Agent P1-2: CrossDocSemanticAgent — semantic cross-document consistency checking.

Detects conflicts like: privacy policy says no cross-border, but DPA shows HK servers;
internal policy requires 24h notification, but contract says "timely".
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

_CROSS_DOC_CHECK_DIMENSIONS = [
    ("cross_border_disclosure", "跨境传输披露", [
        ("隐私政策未提出境，但合同/DPA涉及境外传输", "HIGH"),
        ("标准合同接收方与隐私政策披露的接收方不一致", "HIGH"),
    ]),
    ("retention_period", "保存期限", [
        ("不同文件中的保存期限不一致", "MEDIUM"),
    ]),
    ("security_incident_timeline", "安全事件通知时限", [
        ("内部制度要求较严时限，外部合同较宽", "MEDIUM"),
    ]),
    ("data_types", "数据类型", [
        ("隐私政策披露的数据类型与DPA实际处理的数据类型不一致", "MEDIUM"),
        ("合同附件中的数据类别与正文描述不一致", "LOW"),
    ]),
    ("subject_rights_path", "用户权利路径", [
        ("隐私政策承诺的DSR时限与内部SOP不一致", "MEDIUM"),
    ]),
    ("third_party_recipients", "第三方接收方", [
        ("隐私政策未列明境外接收方，但SCC/DPA明确了境外子公司", "HIGH"),
    ]),
]


class CrossDocSemanticAgent(ReviewAgentBase):
    agent_name = "review_cross_doc_semantic"
    max_tokens = 600

    def run(self, doc_profiles: list[dict] | None = None,
            existing_warnings: list[str] | None = None) -> dict:
        profiles = doc_profiles or []
        warnings = existing_warnings or []
        conflicts: list[dict] = []

        if len(profiles) < 2:
            return {"conflicts": [], "has_critical_conflict": False, "summary": "仅一份文档，无需跨文档检查"}

        for dim_key, dim_label, scenarios in _CROSS_DOC_CHECK_DIMENSIONS:
            values = {}
            for p in profiles:
                val = p.get(dim_key, "")
                if val:
                    values[p.get("filename", "?")] = str(val)[:120]
            if len(values) >= 2:
                unique = set(values.values())
                if len(unique) > 1:
                    for scenario_desc, severity in scenarios:
                        conflicts.append({
                            "dimension": dim_label, "severity": severity,
                            "description": f"{scenario_desc}: {' vs '.join(f'{k}={v[:60]}' for k,v in values.items())}",
                        })

        critical = any(c["severity"] == "HIGH" for c in conflicts)

        agent = self._call_llm(
            f"""Analyze cross-document consistency for these document profiles.

{profiles}
Existing warnings: {warnings[:5]}

Return JSON:
{{
  "conflicts": [{{"dimension": "...", "severity": "HIGH|MEDIUM|LOW", "description": "..."}}],
  "has_critical_conflict": true|false,
  "summary": "<one sentence>"
}}"""
        )
        if agent:
            return agent

        return {
            "conflicts": conflicts, "has_critical_conflict": critical,
            "summary": f"检测到{len(conflicts)}项跨文档不一致" if conflicts else "未检测到跨文档冲突",
        }
