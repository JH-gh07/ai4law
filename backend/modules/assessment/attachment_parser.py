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


# ── Certification Extractor ──


_CERTIFICATION_PATTERNS: dict[str, list[str]] = {
    "iso_27001": [r"ISO[/\s]*27001", r"ISO 27001", r"iso27001"],
    "iso_27701": [r"ISO[/\s]*27701", r"ISO 27701", r"iso27701"],
    "iso_27018": [r"ISO[/\s]*27018", r"ISO 27018", r"iso27018"],
    "soc2": [r"SOC\s*2", r"SOC2", r"SOC 2 Type"],
    "djcp": [r"等级保护", r"等保", r"网络安全等级保护", r"DJCP"],
    "cbpr": [r"CBPR", r"Cross.Border Privacy Rules", r"跨境隐私规则"],
    "gdpr_compliance": [r"GDPR", r"General Data Protection Regulation", r"通用数据保护条例"],
}

_CERT_VALIDITY_PATTERNS: dict[str, list[str]] = {
    "valid": [r"有效", r"valid", r"通过", r"pass", r"认证有效期至", r"证书有效期", r"issued"],
    "expired": [r"过期", r"expired", r"失效", r"lapsed", r"逾期"],
    "pending": [r"审核中", r"pending", r"under review", r"申请中", r"renewal"],
}


@dataclass
class CertificationExtractor:
    """Extracts structured info from security certification documents."""

    def extract(self, content: str) -> dict[str, Any]:
        found_types: list[str] = []
        for cert_type, patterns in _CERTIFICATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    found_types.append(cert_type)
                    break

        validity = "unknown"
        for status, patterns in _CERT_VALIDITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    validity = status
                    break
            if validity != "unknown":
                break

        has_scope = bool(re.search(r"认证范围|certification scope|覆盖.*系统|scope.*include", content, re.IGNORECASE))
        has_issuer = bool(re.search(r"认证机构|certification body|issued by|颁发", content, re.IGNORECASE))

        return {
            "cert_types_found": found_types,
            "validity_status": validity,
            "has_scope_statement": has_scope,
            "has_issuing_body": has_issuer,
            "coverage_summary": (
                f"检测到认证类型：{', '.join(found_types) if found_types else '未识别'}；"
                f"有效性：{validity}；"
                f"范围说明：{'有' if has_scope else '无'}；"
                f"颁发机构：{'有' if has_issuer else '无'}"
            ),
        }

    @staticmethod
    def missing_summary(result: dict[str, Any]) -> str:
        issues: list[str] = []
        cert_types = result.get("cert_types_found", [])
        if not cert_types:
            issues.append("未识别到已知认证类型（ISO 27001、等保、SOC 2 等）")
        if result.get("validity_status") != "valid":
            issues.append(f"认证有效性状态为 {result.get('validity_status', 'unknown')}")
        if not result.get("has_scope_statement"):
            issues.append("缺少认证范围说明")
        if not result.get("has_issuing_body"):
            issues.append("缺少认证颁发机构信息")
        if not issues:
            return f"认证材料已识别：{', '.join(cert_types)}，状态有效。"
        return "认证材料存在问题：" + "；".join(issues) + "。"


# ── Consent Record Extractor ──

_CONSENT_ELEMENT_PATTERNS: dict[str, list[str]] = {
    "separate_consent": [r"单独同意", r"separate consent", r"单独.*告知", r"明示同意", r"explicit consent"],
    "notice_content": [r"告知.*(?:目的|方式|种类|保存期限|信息类型)", r"notice.*(?:purpose|method|category|retention)", r"个人信息处理告知"],
    "rights_statement": [r"查询权|更正权|删除权|撤回.*同意|投诉.*渠道", r"right to (?:access|rectif|eras|withdraw|complaint)"],
    "overseas_transfer_notice": [r"境外.*接收方|overseas.*recipient|数据出境|cross.border.*transfer|第三十九条"],
    "consent_evidence": [r"签署|sign|同意.*记录|consent.*record|opt.*in.*(?:log|record|timestamp)"],
}


@dataclass
class ConsentRecordExtractor:
    """Extracts structured info from consent/notice documents."""

    def extract(self, content: str) -> dict[str, Any]:
        elements: dict[str, bool] = {}
        details: dict[str, list[str]] = {}
        for element_key, patterns in _CONSENT_ELEMENT_PATTERNS.items():
            matched = False
            matched_kws: list[str] = []
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    matched = True
                    matched_kws.append(pattern)
            elements[element_key] = matched
            if matched_kws:
                details[element_key] = matched_kws

        missing = [key for key, found in elements.items() if not found]
        return {
            "consent_elements": elements,
            "missing_elements": missing,
            "matched_patterns": details,
            "all_covered": len(missing) == 0,
        }

    @staticmethod
    def missing_summary(result: dict[str, Any]) -> str:
        missing = result.get("missing_elements", [])
        if not missing:
            return "告知同意记录已覆盖全部五项要素（单独同意、告知内容、信息权益、境外转移告知、同意日志）。"
        element_names = {
            "separate_consent": "单独同意",
            "notice_content": "告知内容（目的/方式/种类/保存期限）",
            "rights_statement": "个人权益保障（查询/更正/删除/撤回/投诉）",
            "overseas_transfer_notice": "境外接收方告知",
            "consent_evidence": "同意记录/日志",
        }
        missing_cn = [element_names.get(k, k) for k in missing]
        return f"告知同意记录缺少以下要素：{'、'.join(missing_cn)}。须补充后方可用于申报。"


# ── Audit Report Extractor ──

_AUDIT_TYPE_PATTERNS: dict[str, list[str]] = {
    "third_party": [r"第三方审计|third.party audit|外部审计|external audit|独立审计|independent audit"],
    "internal": [r"内部审计|internal audit|自查|self.audit|内部检查"],
    "regulatory": [r"监管.*检查|regulatory.*inspection|合规审计|compliance audit|行政检查"],
}

_AUDIT_SCOPE_PATTERNS: dict[str, list[str]] = {
    "data_security": [r"数据安全|data security|加密|access control|访问控制|安全措施"],
    "privacy_compliance": [r"隐私.*合规|privacy.*compliance|个人信息保护|PIPL|GDPR"],
    "cross_border": [r"数据出境|cross.border|境外传输|跨境|overseas transfer"],
    "organizational": [r"组织.*措施|organizational.*measure|管理制度|人员.*培训|意识.*教育"],
}


@dataclass
class AuditReportExtractor:
    """Extracts structured info from audit/assessment reports."""

    def extract(self, content: str) -> dict[str, Any]:
        audit_types: list[str] = []
        for atype, patterns in _AUDIT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    audit_types.append(atype)
                    break

        scope_areas: list[str] = []
        for area, patterns in _AUDIT_SCOPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    scope_areas.append(area)
                    break

        has_findings = bool(re.search(r"(?:发现|finding|不符合|non.conformity|缺陷|deficiency|问题.*项)(?!.*[没有无])", content, re.IGNORECASE))
        has_remediation = bool(re.search(r"(?:整改|remediation|纠正措施|corrective action|改进建议|recommendation)", content, re.IGNORECASE))
        has_date = bool(re.search(r"(?:审计日期|audit date|报告日期|评估日期|assessment date|20\d{2}.*[年月])", content, re.IGNORECASE))

        return {
            "audit_types": audit_types,
            "scope_areas": scope_areas,
            "has_findings_section": has_findings,
            "has_remediation_section": has_remediation,
            "has_report_date": has_date,
            "coverage_summary": (
                f"审计类型：{', '.join(audit_types) if audit_types else '未识别'}；"
                f"覆盖领域：{', '.join(scope_areas) if scope_areas else '未识别'}；"
                f"发现问题：{'有' if has_findings else '无'}；"
                f"整改建议：{'有' if has_remediation else '无'}"
            ),
        }

    @staticmethod
    def missing_summary(result: dict[str, Any]) -> str:
        issues: list[str] = []
        if not result.get("audit_types"):
            issues.append("未识别审计类型（第三方/内部/监管）")
        if not result.get("scope_areas"):
            issues.append("未识别审计覆盖领域")
        if not result.get("has_findings_section"):
            issues.append("缺少审计发现/不合规项说明")
        if not result.get("has_remediation_section"):
            issues.append("缺少整改措施或纠正建议")
        if not result.get("has_report_date"):
            issues.append("缺少审计/报告日期")
        if not issues:
            return f"审计报告已识别，类型：{', '.join(result.get('audit_types', []))}，覆盖：{', '.join(result.get('scope_areas', []))}。"
        return "审计报告存在问题：" + "；".join(issues) + "。"


# ── Data Inventory Extractor ──

_DATA_CATEGORY_PATTERNS: dict[str, list[str]] = {
    "personal_info": [r"个人信息|personal.info|PII|姓名|手机号|身份证|email|邮箱|地址|电话"],
    "sensitive_personal": [r"敏感.*个人|sensitive.*personal|生物识别|金融账户|行踪轨迹|健康.*(?:数据|信息)|医疗|宗教信仰|SPI"],
    "important_data": [r"重要数据|important data|关键数据|核心数据|国家秘密"],
    "financial": [r"(?:银行|金融|交易|支付|财务|账号)(?!.*敏感).*(?:数据|信息|记录)", r"financial.*(?:data|info|record)"],
    "network_identifiers": [r"IP.*地址|设备.*ID|MAC.*地址|cookie|device.*id|IMEI|IDFA"],
}


@dataclass
class DataInventoryExtractor:
    """Extracts structured info from data inventory/catalog documents."""

    def extract(self, content: str) -> dict[str, Any]:
        categories: dict[str, bool] = {}
        for cat_key, patterns in _DATA_CATEGORY_PATTERNS.items():
            matched = any(re.search(p, content, re.IGNORECASE) for p in patterns)
            categories[cat_key] = matched

        has_field_list = bool(re.search(r"(?:字段|数据项|字段名|列名|field.*name|column).{0,20}(?:清单|列表|目录|map|list|inventory)", content, re.IGNORECASE))
        has_volume = bool(re.search(r"(?:数据量|记录数|人数|data volume|record count|\d+.*(?:条|人|行|record))", content, re.IGNORECASE))
        has_purpose = bool(re.search(r"(?:处理目的|使用目的|purpose|业务场景|使用场景)", content, re.IGNORECASE))

        return {
            "data_categories": categories,
            "has_field_level_detail": has_field_list,
            "has_volume_indicator": has_volume,
            "has_purpose_statement": has_purpose,
            "category_summary": "；".join(
                f"{cat}: {'有' if present else '无'}"
                for cat, present in categories.items()
            ),
        }

    @staticmethod
    def missing_summary(result: dict[str, Any]) -> str:
        categories = result.get("data_categories", {})
        issues: list[str] = []
        if not categories.get("personal_info"):
            issues.append("未识别到个人信息字段")
        if not result.get("has_field_level_detail"):
            issues.append("缺少字段级别清单")
        if not result.get("has_volume_indicator"):
            issues.append("缺少数据量/规模指标")
        if not issues:
            present = [cat for cat, found in categories.items() if found]
            return f"数据清单已识别数据类别：{', '.join(present)}，包含字段级详情。"
        return "数据清单存在问题：" + "；".join(issues) + "。"


# ── Policy Document Extractor ──

_POLICY_TYPE_PATTERNS: dict[str, list[str]] = {
    "privacy_policy": [r"隐私.*政策|privacy.*policy|个人信息保护.*政策|数据处理.*政策"],
    "data_protection_policy": [r"数据.*保护.*(?:政策|制度|办法)|data.*protection.*policy|数据安全.*(?:政策|制度)"],
    "data_retention_policy": [r"数据.*(?:保存|保留|存储|retention).*(?:政策|制度|办法|规定)"],
    "breach_response": [r"应急.*(?:响应|预案)|安全.*事件.*(?:响应|处置)|breach.*response|incident.*response"],
    "access_control_policy": [r"访问.*控制|权限.*管理|access.*control|最小权限|least.*privilege"],
}

_POLICY_REQUIREMENT_PATTERNS: dict[str, list[str]] = {
    "scope": [r"适用.*范围|scope|覆盖|apply.*to"],
    "responsibility": [r"责任.*部门|负责.*人|职责|responsibility|DPO|数据保护官"],
    "review_cycle": [r"定期.*(?:审查|更新|review)|年度.*审查|annual.*review|修订.*记录|版本"],
    "enforcement": [r"违规.*(?:处理|处罚|惩罚)|enforcement|consequence|纪律|纪律处分"],
}


@dataclass
class PolicyDocumentExtractor:
    """Extracts structured info from policy/management documents."""

    def extract(self, content: str) -> dict[str, Any]:
        policy_types: list[str] = []
        for ptype, patterns in _POLICY_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    policy_types.append(ptype)
                    break

        requirements: dict[str, bool] = {}
        for req_key, patterns in _POLICY_REQUIREMENT_PATTERNS.items():
            matched = any(re.search(p, content, re.IGNORECASE) for p in patterns)
            requirements[req_key] = matched

        missing_reqs = [key for key, found in requirements.items() if not found]
        has_update_date = bool(re.search(r"(?:修订.*日期|更新.*日期|版本.*日期|生效.*日期|last.*updated|effective.*date|20\d{2}.*[年月日])", content, re.IGNORECASE))

        return {
            "policy_types_found": policy_types,
            "policy_requirements": requirements,
            "missing_requirements": missing_reqs,
            "has_update_date": has_update_date,
            "all_requirements_met": len(missing_reqs) == 0,
        }

    @staticmethod
    def missing_summary(result: dict[str, Any]) -> str:
        issues: list[str] = []
        policy_types = result.get("policy_types_found", [])
        if not policy_types:
            issues.append("未识别到明确的政策/制度类型")
        missing = result.get("missing_requirements", [])
        if missing:
            req_names = {
                "scope": "适用范围",
                "responsibility": "责任部门/责任人",
                "review_cycle": "定期审查机制",
                "enforcement": "违规处理/执行措施",
            }
            missing_cn = [req_names.get(k, k) for k in missing]
            issues.append(f"缺少要素：{'、'.join(missing_cn)}")
        if not result.get("has_update_date"):
            issues.append("缺少修订/生效日期")
        if not issues:
            return f"政策文件已识别类型：{', '.join(policy_types)}，制度要素完整。"
        return "政策文件存在问题：" + "；".join(issues) + "。"


def parse_attachment_metadata(filename: str, content: str | None = None) -> dict[str, Any]:
    classifier = AttachmentClassifier()
    atype = classifier.classify(filename, content)

    result: dict[str, Any] = {
        "filename": filename,
        "type": atype,
        "char_count": len(content) if content else 0,
    }

    if not content:
        result["missing_summary"] = "附件内容为空，无法解析。"
        return result

    if atype == "contract":
        extractor = ContractClauseExtractor()
        clauses = extractor.extract(content)
        result["contract_clauses"] = clauses
        result["missing_summary"] = ContractClauseExtractor.missing_summary(clauses)
    elif atype == "certification":
        extractor = CertificationExtractor()
        cert_info = extractor.extract(content)
        result["certification"] = cert_info
        result["missing_summary"] = CertificationExtractor.missing_summary(cert_info)
    elif atype == "consent_record":
        extractor = ConsentRecordExtractor()
        consent_info = extractor.extract(content)
        result["consent_record"] = consent_info
        result["missing_summary"] = ConsentRecordExtractor.missing_summary(consent_info)
    elif atype == "audit_report":
        extractor = AuditReportExtractor()
        audit_info = extractor.extract(content)
        result["audit_report"] = audit_info
        result["missing_summary"] = AuditReportExtractor.missing_summary(audit_info)
    elif atype == "data_inventory":
        extractor = DataInventoryExtractor()
        inventory_info = extractor.extract(content)
        result["data_inventory"] = inventory_info
        result["missing_summary"] = DataInventoryExtractor.missing_summary(inventory_info)
    elif atype == "policy_doc":
        extractor = PolicyDocumentExtractor()
        policy_info = extractor.extract(content)
        result["policy_doc"] = policy_info
        result["missing_summary"] = PolicyDocumentExtractor.missing_summary(policy_info)

    return result
