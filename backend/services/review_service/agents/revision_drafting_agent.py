"""Agent P2-1: RevisionDraftingAgent — generate document-type-specific replacement clause text.

Different document types need different revision templates:
- DPA: data processing location, audit rights, onward transfer restrictions
- Confidentiality agreement: data location, security incident notification, deletion proof
- SCC: compliance with standard clauses, subject rights, retention period
- Privacy policy: disclosure items, user rights path, cross-border notice
"""

from __future__ import annotations

from backend.services.review_service.agents import ReviewAgentBase

_DOC_TYPE_TEMPLATES = {
    "dpa": {
        "数据处理地点": "受托方应仅在中华人民共和国境内处理、存储和访问委托方提供的数据。未经委托方事先书面同意，受托方不得将数据传输、存储至中华人民共和国境外，亦不得允许境外主体远程访问相关数据。",
        "审计权": "委托方有权自行或委托独立第三方每年对受托方的数据处理活动进行审计。受托方应在收到审计通知后[15]个工作日内提供必要的配合、信息和访问权限。",
        "安全事件通知": "受托方应在知悉数据安全事件后[24]小时内书面通知委托方，说明事件性质、受影响数据范围、已采取和拟采取的补救措施。",
        "删除返还证明": "委托关系终止后，受托方应在[30]日内将所有数据返还委托方或不可恢复地删除，并提供书面删除/返还证明。",
        "再转移限制": "未经委托方事先书面同意，受托方不得将个人数据再转移至任何第三方。经授权的再转移须以书面合同约束再转移接收方承担不低于本协议的义务。",
    },
    "other": {  # data security / confidentiality agreements
        "数据处理地点": "乙方应仅在中华人民共和国境内处理、存储甲方数据。未经甲方事先书面同意，乙方不得将数据传输至境外，亦不得允许境外主体远程访问。",
        "审计权": "甲方有权对乙方的数据处理活动进行定期或临时审计，乙方应提供合理配合。",
        "安全事件通知": "乙方应在知悉数据安全事件后[24]小时内书面通知甲方，包括事件性质、影响范围和应对措施。",
        "销毁证明": "协议终止后乙方应在[30]日内不可恢复地删除或返还所有数据，并提供书面销毁/返还证明。",
    },
    "scc_contract": {
        "争议解决": "因本协议产生的争议，双方应协商解决；协商不成的，任何一方可向甲方所在地有管辖权的人民法院提起诉讼。",
        "责任条款": "境外接收方违反本合同约定造成个人信息主体损害的，应依法承担赔偿责任。双方不得通过合同约定限制或免除该等责任。",
        "保存期限": "个人信息保存期限为实现处理目的所必要的最短时间，最长不超过[具体期限]。期限届满后应不可恢复地删除或返还。",
    },
    "privacy_policy": {
        "跨境传输告知": "我们可能将您的个人信息传输至[境外接收方名称]，用于[处理目的]，涉及[个人信息种类]。我们已依据《个人信息保护法》采取[安全评估/标准合同/认证]等合规措施保障您的个人信息安全。",
    },
}


class RevisionDraftingAgent(ReviewAgentBase):
    agent_name = "review_revision_drafting"
    max_tokens = 700

    def run(self, doc_type: str = "other", issue_title: str = "",
            problem_type: str = "", original_text: str = "",
            recommendation: str = "") -> dict:
        templates = _DOC_TYPE_TEMPLATES.get(doc_type, _DOC_TYPE_TEMPLATES["other"])

        # Match issue title to template
        matched_template = ""
        for keyword, template_text in templates.items():
            if keyword in issue_title or keyword in recommendation:
                matched_template = template_text
                break

        agent = self._call_llm(
            f"""Generate a replacement or new clause for a document review finding.

Document type: {doc_type}
Issue: {issue_title}
Problem type: {problem_type}
Original text: {original_text[:300]}
Current recommendation: {recommendation}
Template suggestion: {matched_template[:300]}

Return JSON:
{{
  "revision_type": "REPLACE|INSERT|DELETE|CLARIFY",
  "suggested_text": "<draft clause text, up to 300 words>",
  "rationale": "<why this revision addresses the issue>",
  "key_references": ["<cited law or standard>"]
}}"""
        )
        if agent:
            return agent

        if matched_template:
            return {
                "revision_type": "INSERT" if not original_text else "REPLACE",
                "suggested_text": matched_template,
                "rationale": recommendation or "基于文档类型模板生成",
                "key_references": [],
            }
        return {
            "revision_type": "CLARIFY", "suggested_text": "",
            "rationale": "Agent不可用，请人工草拟修改建议",
            "key_references": [],
        }
