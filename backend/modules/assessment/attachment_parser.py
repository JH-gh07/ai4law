from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


AttachmentType = str  # "contract" | "certification" | "consent_record" | "audit_report" | "data_inventory" | "policy_doc" | "other"


_FILE_TYPE_HINTS: dict[str, list[str]] = {
    "contract": [
        r"合同", r"协议", r"contract", r"agreement", r"SCC", r"标准合同",
        r"数据处理协议", r"DPA", r"data processing",
    ],
    "certification": [
        r"认证", r"certif", r"ISO", r"等级保护", r"等保", r"SOC",
        r"安全评估", r"测评", r"audit report",
    ],
    "consent_record": [
        r"同意", r"consent", r"告知", r"notice", r"privacy notice",
        r"授权", r"authorization", r"opt-in",
    ],
    "audit_report": [
        r"审计", r"audit", r"评估报告", r"assessment report",
        r"第三方审计", r"third.party audit",
    ],
    "data_inventory": [
        r"数据清单", r"数据目录", r"data inventory", r"data catalog",
        r"数据流", r"data flow", r"字段", r"fields",
    ],
    "policy_doc": [
        r"隐私政策", r"privacy policy", r"数据保护政策", r"data protection policy",
        r"安全制度", r"security policy", r"管理制度", r"management policy",
    ],
}

_SIX_CORE_CLAUSE_KEYWORDS: dict[str, list[str]] = {
    "processing_purpose": [r"处理目的", r"处理方式", r"processing purpose", r"处理范围"],
    "retention_period": [r"保存期限", r"retention period", r"保存期", r"存储期限"],
    "onward_transfer": [r"再转移", r"onward transfer", r"第三方", r"不得向第三方", r"不得提供给第三方"],
    "security_incident": [r"安全事件", r"security incident", r"应急", r"通知", r"泄露", r"breach"],
    "breach_liability": [r"违约责任", r"breach", r"liability", r"赔偿", r"责任"],
    "rights_protection": [r"信息权益", r"rights", r"查询", r"更正", r"删除", r"投诉", r"complaint"],
}


@dataclass
class AttachmentClassifier:
    def classify(self, filename: str, content: str | None = None) -> AttachmentType:
        combined = f"{filename} {content or ''}".lower()
        best_type = "other"
        best_score = 0

        for atype, patterns in _FILE_TYPE_HINTS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    score += 1
            if score > best_score:
                best_score = score
                best_type = atype

        if best_score == 0:
            ext = Path(filename).suffix.lower()
            if ext in {".pdf", ".docx", ".doc"}:
                return "contract"
            if ext in {".xlsx", ".xls", ".csv"}:
                return "data_inventory"

        return best_type


@dataclass
class ContractClauseExtractor:
    """Checks whether uploaded contract/agreement documents cover the six core clauses."""

    coverage: dict[str, bool] = field(default_factory=dict)

    def extract(self, content: str) -> dict[str, Any]:
        coverage: dict[str, bool] = {}
        details: dict[str, list[str]] = {}

        for clause_key, keywords in _SIX_CORE_CLAUSE_KEYWORDS.items():
            matched = False
            matched_kws: list[str] = []
            for kw in keywords:
                if re.search(kw, content, re.IGNORECASE):
                    matched = True
                    matched_kws.append(kw)
            coverage[clause_key] = matched
            if matched_kws:
                details[clause_key] = matched_kws

        missing = [key for key, found in coverage.items() if not found]
        self.coverage = coverage

        return {
            "six_core_clauses_coverage": coverage,
            "missing_core_clauses": missing,
            "matched_keywords": details,
            "all_covered": len(missing) == 0,
        }

    @staticmethod
    def missing_summary(result: dict[str, Any]) -> str:
        missing = result.get("missing_core_clauses", [])
        if not missing:
            return "法律文件已覆盖六项核心条款关键词。"
        clause_names = {
            "processing_purpose": "处理目的",
            "retention_period": "保存期限",
            "onward_transfer": "再转移约束",
            "security_incident": "安全事件处置",
            "breach_liability": "违约责任",
            "rights_protection": "个人信息权益保障",
        }
        missing_cn = [clause_names.get(k, k) for k in missing]
        return f"法律文件缺少以下核心条款：{'、'.join(missing_cn)}。建议补充相应内容。"


def parse_attachment_metadata(filename: str, content: str | None = None) -> dict[str, Any]:
    classifier = AttachmentClassifier()
    atype = classifier.classify(filename, content)

    result: dict[str, Any] = {
        "filename": filename,
        "type": atype,
        "char_count": len(content) if content else 0,
    }

    if atype == "contract" and content:
        extractor = ContractClauseExtractor()
        clauses = extractor.extract(content)
        result["contract_clauses"] = clauses
        result["missing_summary"] = ContractClauseExtractor.missing_summary(clauses)

    return result
