"""P0 Agent 3: ContractReviewAgent — review contract terms beyond "has contract or not".

Solves: the current system only checks has_scc_draft (True/False). It cannot detect:
  1. Missing "legal/policy change response" clauses
  2. Missing periodic security audit report obligations
  3. Jurisdiction clauses unfavorable to Chinese PI subjects
  4. English-only agreements without certified Chinese translations
  5. Agreements that don't protect Chinese PI subject rights

Reference: docs/archive/design-provenance/认证标准合同路径.md Section 4
"""

from __future__ import annotations

from backend.domains.cn.scc_review.agents import SCCAgentBase
from backend.domains.cn.scc_review.schema import ContractFinding, RiskLevel


class ContractReviewAgent(SCCAgentBase):
    agent_name = "cn_scc_contract_review"
    max_tokens = 1200

    def run(
        self,
        contract_text: str,
        contract_type: str = "standard_contract",
        receiver_country: str = "",
        path_type: str = "standard_contract",
        uploaded_file_names: list[str] | None = None,
    ) -> list[dict]:
        """Review contract/document text against CN SCC template requirements.

        Handles multiple document types:
        - 标准合同 (Standard Contract)
        - 数据处理协议 (DPA)
        - 认证服务合同 (Certification Service Contract)
        - 员工手册 (Employee Handbook)
        - 集体合同 (Collective Agreement)
        - 隐私政策 (Privacy Policy)
        """
        if not contract_text or len(contract_text.strip()) < 50:
            return _missing_text_finding(contract_type)

        if not self.enabled:
            return _rule_based_contract_review(contract_text, contract_type, receiver_country)

        doc_type_hint = _contract_type_hint(contract_type)
        text_excerpt = contract_text[:5000]

        prompt = f"""Review the following {doc_type_hint} for CN SCC compliance.

CONTRACT TYPE: {contract_type}
RECEIVER COUNTRY: {receiver_country}
PATH TYPE: {path_type}
UPLOADED FILES: {", ".join(uploaded_file_names) if uploaded_file_names else "未提供"}

DOCUMENT TEXT (first 5000 chars):
---
{text_excerpt}
---

REVIEW DIMENSIONS:
1. Party Information: Are data exporter and importer clearly identified?
2. Transfer Purpose: Is the purpose specific, limited, and necessary?
3. Data Scope: Are data categories and subjects clearly defined?
4. Recipient Obligations: Does the contract bind the recipient to PIPL-equivalent protection?
5. Security Measures: Are technical and organizational measures specified (encryption, access control, audit)?
6. Onward Transfer / Sub-processing: Are restrictions and authorization requirements present?
7. PI Subject Rights: Are access, correction, deletion, portability rights provided for Chinese subjects?
8. Legal/Policy Change Response: Is there a clause requiring the recipient to adapt to changes in Chinese law?
9. Audit and Supervision: Does the recipient agree to regular security audits and provide reports?
10. Dispute Resolution: Is jurisdiction favorable to Chinese PI subjects? Is there a Chinese translation?
11. Termination and Data Return/Deletion: Are post-termination data handling obligations specified?

Return JSON array of findings:
[
  {{
    "finding_id": "CN-SCC-CONTRACT-XXX",
    "location": "<clause/article reference or '全文'>",
    "issue": "<1 sentence description>",
    "severity": "LOW" | "MEDIUM" | "HIGH" | "BLOCKER",
    "risk_analysis": "<1-2 sentences on legal/compliance risk>",
    "suggested_text": "<proposed revision or addition>",
    "clause_category": "party_info" | "purpose" | "data_scope" | "recipient_obligation" | "security_measure" | "onward_transfer" | "subject_rights" | "legal_change" | "audit" | "dispute_resolution" | "termination"
  }}
]

IMPORTANT:
- Focus on MISSING or WEAK clauses, not adequately covered ones
- For Chinese standard contract review, check alignment with 个人信息出境标准合同办法 template
- Flag any jurisdiction clause that places burden on Chinese PI subjects (e.g. German law, Berlin court for Chinese citizens)
- Flag lack of Chinese language version or certified translation
- Flag absence of Chinese PI subject rights protection clauses
"""

        findings = self._call_llm(prompt)
        if findings is None:
            return _rule_based_contract_review(contract_text, contract_type, receiver_country)

        if isinstance(findings, dict):
            findings = [findings]
        if not isinstance(findings, list):
            return _rule_based_contract_review(contract_text, contract_type, receiver_country)

        # Ensure required fields in each finding
        for i, f in enumerate(findings):
            f.setdefault("finding_id", f"CN-SCC-CONTRACT-{i + 1:03d}")
            f.setdefault("location", "全文")
            f.setdefault("issue", "条款缺失或表述不足")
            f.setdefault("severity", "MEDIUM")
            f.setdefault("risk_analysis", "")
            f.setdefault("suggested_text", "")
            f.setdefault("clause_category", "recipient_obligation")

        return findings


def _rule_based_contract_review(
    contract_text: str,
    contract_type: str,
    receiver_country: str,
) -> list[dict]:
    """Fallback rule-based contract review when LLM is unavailable."""
    findings: list[dict] = []
    text_lower = contract_text.lower()

    checks = [
        ("数据出境目的", ["出境目的", "transfer purpose", "processing purpose", "处理目的"]),
        ("数据范围", ["数据范围", "data categories", "categories of data", "数据类型"]),
        ("接收方安全义务", ["安全措施", "security measures", "technical and organizational", "技术和组织措施"]),
        ("转委托限制", ["转委托", "sub-process", "onward transfer", "再传输", "第三方处理"]),
        ("个人信息主体权利", ["个人信息主体", "data subject right", "访问权", "更正权", "删除权", "right to access"]),
        ("法律政策变化应对", ["法律变化", "政策变化", "legal change", "regulatory change", "法律环境变化"]),
        ("审计监督", ["审计", "audit", "检查", "inspection", "合规审计"]),
        ("争议解决", ["争议解决", "管辖", "jurisdiction", "dispute resolution", "适用法律", "governing law"]),
        ("终止后数据处理", ["终止", "termination", "返还", "return", "删除", "deletion", "销毁"]),
    ]

    for clause_name, keywords in checks:
        found = any(kw.lower() in text_lower for kw in keywords)
        if not found:
            findings.append({
                "finding_id": f"CN-SCC-CONTRACT-R{len(findings) + 1:03d}",
                "location": "全文检索",
                "issue": f"合同缺少'{clause_name}'相关条款",
                "severity": "HIGH" if clause_name in ("接收方安全义务", "个人信息主体权利", "争议解决") else "MEDIUM",
                "risk_analysis": f"缺少{clause_name}条款可能导致合同不符合标准合同办法的必备内容要求",
                "suggested_text": f"建议补充{clause_name}条款，明确各方权利义务",
                "clause_category": _map_clause_category(clause_name),
            })

    # Country-specific checks
    if receiver_country and receiver_country.lower() not in ("中国", "china", "cn", ""):
        has_jurisdiction_check = any(
            kw in text_lower for kw in ["中国法", "chinese law", "中国法律", "中华人民共和国", "people's republic of china"]
        )
        if not has_jurisdiction_check:
            findings.append({
                "finding_id": f"CN-SCC-CONTRACT-R{len(findings) + 1:03d}",
                "location": "争议解决条款",
                "issue": f"合同管辖条款可能未充分考虑中国个人信息保护法律的强制性要求，境外接收方所在国({receiver_country})法律可能对中国个人信息主体维权构成障碍",
                "severity": "HIGH",
                "risk_analysis": "境外管辖条款可能增加中国个人信息主体维权成本，并削弱中国法强制性保护要求的可执行性",
                "suggested_text": "双方确认本协议的履行不得排除中国个人信息保护相关法律法规的强制性要求，个人信息主体有权向其住所地人民法院提起诉讼",
                "clause_category": "dispute_resolution",
            })

    # Language check
    has_chinese = any(
        ord(ch) > 0x4e00 and ord(ch) < 0x9fff for ch in contract_text[:1000]
    )
    if not has_chinese:
        findings.append({
            "finding_id": f"CN-SCC-CONTRACT-R{len(findings) + 1:03d}",
            "location": "全文",
            "issue": "协议为纯外文文本，未提供经认证的中文译本",
            "severity": "MEDIUM",
            "risk_analysis": "标准合同办法要求提供中文版本，纯外文协议可能影响备案审查和个人信息主体权益保护",
            "suggested_text": "建议提供经认证的中文译本，并约定中文本与外文本不一致时以中文本为准",
            "clause_category": "dispute_resolution",
        })

    if not findings:
        findings.append({
            "finding_id": "CN-SCC-CONTRACT-R000",
            "location": "全文",
            "issue": "基于关键词检索未发现明显条款缺失，但需人工逐条审查确认",
            "severity": "LOW",
            "risk_analysis": "自动审查存在局限性，建议仍由合规律师进行逐条款比对",
            "suggested_text": "保持现有条款结构，进行人工逐条核查",
            "clause_category": "recipient_obligation",
        })

    return findings


def _missing_text_finding(contract_type: str) -> list[dict]:
    """Generate finding when no contract text is provided."""
    doc_label = _contract_type_hint(contract_type)
    return [{
        "finding_id": "CN-SCC-CONTRACT-001",
        "location": "合同主文/附件",
        "issue": f"未提供可审查的{doc_label}文本",
        "severity": "BLOCKER",
        "risk_analysis": f"缺少{doc_label}文本会导致无法进行条款级审查，备案材料不具备提交条件",
        "suggested_text": f"请先上传完整的{doc_label}文本（含附件），再执行逐条款审查",
        "clause_category": "recipient_obligation",
    }]


def _contract_type_hint(contract_type: str) -> str:
    mapping = {
        "standard_contract": "标准合同",
        "dpa": "数据处理协议",
        "certification_service_contract": "认证服务合同",
        "employee_handbook": "员工手册",
        "collective_agreement": "集体合同",
        "privacy_policy": "隐私政策",
    }
    return mapping.get(contract_type, "合同文件")


def _map_clause_category(clause_name: str) -> str:
    mapping = {
        "数据出境目的": "purpose",
        "数据范围": "data_scope",
        "接收方安全义务": "security_measure",
        "转委托限制": "onward_transfer",
        "个人信息主体权利": "subject_rights",
        "法律政策变化应对": "legal_change",
        "审计监督": "audit",
        "争议解决": "dispute_resolution",
        "终止后数据处理": "termination",
    }
    return mapping.get(clause_name, "recipient_obligation")
