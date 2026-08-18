from __future__ import annotations

from typing import Any

from backend.common.workflow import FactItem, IssueItem
from backend.domains.cn.security_assessment.chapter_generator import ASSESSMENT_CHAPTER_KEYS
from backend.domains.cn.security_assessment.schema import RegulationHit

ALL_CHAPTER_IDS = list(ASSESSMENT_CHAPTER_KEYS.values())


def _diagnosis_value(diagnosis_result: object | None, field: str) -> Any:
    if diagnosis_result is None:
        return None
    if isinstance(diagnosis_result, dict):
        return diagnosis_result.get(field)
    return getattr(diagnosis_result, field, None)


def _diagnosis_rule_ref(diagnosis_result: object | None) -> str:
    matched_rule_id = _diagnosis_value(diagnosis_result, "matched_rule_id")
    if matched_rule_id:
        return f"diagnosis:{matched_rule_id}"
    recommended_path = _diagnosis_value(diagnosis_result, "recommended_path") or "unknown"
    return f"diagnosis:{recommended_path}"


def _regulation_refs(regulations: list[RegulationHit]) -> list[str]:
    return [item.source_id for item in regulations if item.source_id]


def _by_field(facts: list[FactItem]) -> dict[str, FactItem]:
    return {fact.field_path or "": fact for fact in facts}


_SA_DEFAULT_ACTION = (
    "针对安全评估中发现的合规问题进行详细评估，"
    "根据《数据出境安全评估办法》和《个人信息保护法》完成合规整改，"
    "并补充数据清单、隐私政策、合同及安全措施说明等申报材料。"
)

# 法律文件六项核心条款 key → 中文标签（《数据出境安全评估办法》第九条口径）
_CLAUSE_LABELS: dict[str, str] = {
    "purpose_method_scope": "处理目的、方式、范围条款",
    "overseas_retention_location_period": "境外保存地点与期限条款",
    "onward_transfer_constraint": "再转移约束条款",
    "legal_environment_change_response": "法律环境变化应对条款",
    "breach_liability_dispute_resolution": "违约责任与争议解决条款",
    "incident_response_and_individual_rights": "安全事件处置与个人权利条款",
}


def _issue(
    issue_id: str,
    title: str,
    description: str,
    category: str,
    severity: str,
    fact_refs: list[str],
    rule_refs: list[str],
    recommended_action: str,
    affects_outputs: list[str],
    missing_materials: list[str] | None = None,
) -> IssueItem:
    if not recommended_action or not str(recommended_action).strip():
        recommended_action = _SA_DEFAULT_ACTION
    return IssueItem(
        issue_id=issue_id,
        title=title,
        description=description,
        category=category,
        severity=severity,
        fact_refs=fact_refs,
        rule_refs=rule_refs,
        recommended_action=recommended_action,
        affects_outputs=affects_outputs,
        missing_materials=list(missing_materials or []),
    )


def _attachment_evidence(attachment_notes: list) -> dict[str, bool]:
    """Scan attachment_notes for structured evidence to inform issue suppression.

    Reads structured fields from all 6 extractor types (contract, certification,
    consent_record, audit_report, data_inventory, policy_doc).
    """
    result: dict[str, bool] = {
        "has_contract_clauses": False,
        "contract_all_covered": False,
        "has_consent_records": False,
        "consent_all_covered": False,
        "has_certification": False,
        "certification_valid": False,
        "has_audit_report": False,
        "has_data_inventory": False,
        "has_policy_doc": False,
        "has_onward_transfer_clause": False,
        "has_anonymization_claim": False,
    }
    for item in attachment_notes:
        if isinstance(item, dict):
            atype = item.get("type", "")

            if atype == "contract":
                result["has_contract_clauses"] = True
                all_covered = item.get("all_covered", "False")
                result["contract_all_covered"] = all_covered in (True, "True")
                missing_str = item.get("missing_core_clauses", "")
                if "onward_transfer" not in missing_str:
                    result["has_onward_transfer_clause"] = True

            elif atype == "consent_record":
                result["has_consent_records"] = True
                consent_all = item.get("consent_all_covered", "False")
                result["consent_all_covered"] = consent_all in (True, "True")

            elif atype == "certification":
                result["has_certification"] = True
                validity = item.get("cert_validity", "unknown")
                result["certification_valid"] = validity == "valid"

            elif atype == "audit_report":
                result["has_audit_report"] = True

            elif atype == "data_inventory":
                result["has_data_inventory"] = True

            elif atype == "policy_doc":
                result["has_policy_doc"] = True

            # Anonymization check from summary text
            summary = item.get("summary", "")
            if any(kw in summary for kw in ("匿名化", "去标识化", "anonymization", "de-identification")):
                result["has_anonymization_claim"] = True

        elif isinstance(item, str):
            item_lower = item.lower()
            if any(kw in item_lower for kw in ("合同", "协议", "contract", "agreement")):
                result["has_contract_clauses"] = True
            if any(kw in item_lower for kw in ("同意", "consent", "告知")):
                result["has_consent_records"] = True
            if any(kw in item_lower for kw in ("认证", "certif", "审计", "audit")):
                result["has_certification"] = True
            if any(kw in item_lower for kw in ("匿名化", "去标识化", "anonymization")):
                result["has_anonymization_claim"] = True

    return result


def _fact_value(fact: FactItem | None) -> Any:
    if fact is None:
        return None
    return fact.normalized_value if fact.normalized_value is not None else fact.value


def _structured_evidence(field_facts: dict[str, FactItem]) -> dict[str, Any]:
    """Read structured input fields carried as facts, so provided fields are not
    reported as entirely missing.

    task081 T081-02: `security_capability.certifications`,
    `legal_document_review.clause_coverage`, `data_inventory_items`,
    `recipient_info`, `personal_info_protection` and `system_link` must all
    participate in evidence-driven issue suppression / refinement, instead of
    relying on attachment_notes alone.
    """
    result: dict[str, Any] = {
        "has_certification": False,          # 已声明或已有佐证
        "certification_valid": False,
        "has_certification_evidence": False,  # 有证书/审计佐证
        "declared_certifications": [],
        "has_audit_report": False,
        "has_data_inventory": False,
        "has_contract_clauses": False,
        "contract_all_covered": False,
        "clause_coverage": {},
        "missing_clauses": [],
        "partial_clauses": [],
        "has_consent_records": False,
        "consent_all_covered": False,
        "has_recipient_info": False,
        "has_system_link": False,
    }

    cap = _fact_value(field_facts.get("request.security_capability"))
    if isinstance(cap, dict):
        certs = cap.get("certifications") or []
        if certs:
            result["declared_certifications"] = list(certs)
            result["has_certification"] = True
        if cap.get("compliance_records"):
            result["has_audit_report"] = True

    recipient = _fact_value(field_facts.get("request.recipient_info"))
    if isinstance(recipient, dict):
        if recipient.get("name"):
            result["has_recipient_info"] = True
        if recipient.get("security_certifications"):
            certs = list(recipient["security_certifications"])
            result["declared_certifications"] = list(
                dict.fromkeys(result["declared_certifications"] + certs)
            )
            result["has_certification"] = True
        if recipient.get("audit_reports"):
            result["has_audit_report"] = True
            result["has_certification_evidence"] = True

    ldr = _fact_value(field_facts.get("request.legal_document_review"))
    if isinstance(ldr, dict):
        coverage = ldr.get("clause_coverage") or {}
        if coverage:
            result["has_contract_clauses"] = True
            result["clause_coverage"] = dict(coverage)
            missing = [k for k, v in coverage.items() if v == "missing"]
            partial = [k for k, v in coverage.items() if v == "partial"]
            result["missing_clauses"] = missing
            result["partial_clauses"] = partial
            result["contract_all_covered"] = not missing and not partial
        extra_missing = ldr.get("missing_items") or []
        if extra_missing:
            result["missing_clauses"] = list(
                dict.fromkeys(result["missing_clauses"] + list(extra_missing))
            )

    inventory = _fact_value(field_facts.get("request.data_inventory_items"))
    if isinstance(inventory, list) and inventory:
        result["has_data_inventory"] = True

    protection = _fact_value(field_facts.get("request.personal_info_protection"))
    if isinstance(protection, dict):
        if protection.get("separate_consent_status") == "obtained":
            result["has_consent_records"] = True
            result["consent_all_covered"] = True

    if _fact_value(field_facts.get("request.system_link")) is not None:
        result["has_system_link"] = True

    return result


def _merge_evidence(attachment: dict[str, Any], structured: dict[str, Any]) -> dict[str, Any]:
    """Overlay structured evidence on top of attachment evidence.

    Structured declarations count as "has X" but never as valid/evidenced, so a
    declared certification still produces a "已声明但缺证书佐证" refinement
    rather than silently flipping to "完全具备".
    """
    merged = dict(attachment)
    for key, value in structured.items():
        if value in (False, [], {}, None):
            continue
        if isinstance(value, bool) or isinstance(value, list):
            if key in ("has_certification_evidence", "certification_valid"):
                merged[key] = bool(merged.get(key)) or bool(value)
            elif key in merged and isinstance(merged.get(key), bool):
                merged[key] = bool(merged.get(key)) or bool(value)
            else:
                merged[key] = value
        else:
            merged[key] = value
    return merged


def build_assessment_issues(
    facts: list[FactItem],
    diagnosis_result: object | None,
    regulations: list[RegulationHit],
    attachment_notes: list[dict] | list[str],
) -> list[IssueItem]:
    field_facts = _by_field(facts)
    issues: list[IssueItem] = []
    regulation_refs = _regulation_refs(regulations)
    diagnosis_rule_ref = _diagnosis_rule_ref(diagnosis_result)
    legal_rule_refs = [diagnosis_rule_ref, *regulation_refs[:3]]
    attachment_evidence = _attachment_evidence(attachment_notes)
    structured_evidence = _structured_evidence(field_facts)
    evidence = _merge_evidence(attachment_evidence, structured_evidence)

    security_capability_fact = field_facts.get("request.security_capability")
    recipient_info_fact = field_facts.get("request.recipient_info")
    legal_document_fact = field_facts.get("request.legal_document_review")
    _cert_fact_refs = [
        fact.fact_id
        for fact in (security_capability_fact, recipient_info_fact)
        if fact and fact.fact_id
    ]

    recommended_path = _diagnosis_value(diagnosis_result, "recommended_path")
    recommended_path_fact = field_facts.get("diagnosis_result.recommended_path")
    if recommended_path and recommended_path != "security_assessment" and recommended_path_fact:
        issues.append(
            _issue(
                issue_id="ISSUE-recommended-path-mismatch",
                title="诊断路径与安全评估报告不匹配",
                description=f"诊断模块推荐路径为 {recommended_path}，当前仍在生成安全评估报告。",
                category="path",
                severity="HIGH",
                fact_refs=[recommended_path_fact.fact_id],
                rule_refs=[diagnosis_rule_ref],
                recommended_action="复核合规路径；如继续生成，应在报告中标注为强制生成的参考草案。",
                affects_outputs=["overview", "risk_remediation", "conclusion"],
            )
        )

    is_ciio_fact = field_facts.get("request.is_ciio")
    if is_ciio_fact and is_ciio_fact.normalized_value is True:
        issues.append(
            _issue(
                issue_id="ISSUE-ciio-security-assessment",
                title="CIIO 触发安全评估路径",
                description="输入事实显示企业属于 CIIO，应按高风险路径处理数据出境评估。",
                category="path",
                severity="HIGH",
                fact_refs=[is_ciio_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="按安全评估申报要求准备自评估报告和配套材料。",
                affects_outputs=["overview", "risk_remediation", "conclusion"],
            )
        )

    important_data_fact = field_facts.get("request.contains_important_data")
    if important_data_fact and important_data_fact.normalized_value is True:
        issues.append(
            _issue(
                issue_id="ISSUE-important-data-security-assessment",
                title="重要数据触发高风险路径",
                description="输入事实显示本次出境涉及重要数据，应按安全评估口径处理。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[important_data_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="补充重要数据识别依据、目录映射和出境必要性说明。",
                affects_outputs=["data_scope", "risk_remediation", "conclusion"],
            )
        )

    pii_fact = field_facts.get("request.pii_count")
    if pii_fact and int(pii_fact.normalized_value or 0) >= 1_000_000:
        issues.append(
            _issue(
                issue_id="ISSUE-pii-threshold",
                title="个人信息规模达到安全评估阈值",
                description="普通个人信息出境人数达到 100 万人以上，触发安全评估关注点。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[pii_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="核验近 12 个月累计人数口径，并在报告中说明统计方法。",
                affects_outputs=["data_scope", "risk_remediation", "conclusion"],
            )
        )

    spi_fact = field_facts.get("request.spi_count")
    if spi_fact and int(spi_fact.normalized_value or 0) >= 10_000:
        issues.append(
            _issue(
                issue_id="ISSUE-spi-threshold",
                title="敏感个人信息规模达到安全评估阈值",
                description="敏感个人信息出境人数达到 1 万人以上，应按高风险口径处理。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[spi_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="补充敏感个人信息类型、数量统计和单独同意材料。",
                affects_outputs=["data_scope", "rights_impact", "risk_remediation", "conclusion"],
            )
        )

    uploaded_files_fact = field_facts.get("request.uploaded_files")
    if uploaded_files_fact and not uploaded_files_fact.normalized_value:
        issues.append(
            _issue(
                issue_id="ISSUE-missing-attachments",
                title="申报支撑材料缺失",
                description="当前请求未提供上传附件，报告中的材料审查和证据追溯能力不足。",
                category="documentation",
                severity="MEDIUM",
                fact_refs=[uploaded_files_fact.fact_id],
                rule_refs=[],
                recommended_action="补充数据清单、隐私政策、合同/协议、安全措施说明等材料。",
                affects_outputs=["overview", "security_measures", "risk_remediation", "conclusion"],
            )
        )
    elif not attachment_notes and uploaded_files_fact:
        issues.append(
            _issue(
                issue_id="ISSUE-attachments-not-parsed",
                title="附件解析摘要缺失",
                description="请求包含附件路径，但当前未形成可用附件解析摘要。",
                category="documentation",
                severity="LOW",
                fact_refs=[uploaded_files_fact.fact_id],
                rule_refs=[],
                recommended_action="检查附件路径和格式，确保解析摘要进入生成上下文。",
                affects_outputs=["security_measures", "risk_remediation"],
            )
        )

    receiver_fact = field_facts.get("request.receiver_country")
    if receiver_fact and not str(receiver_fact.normalized_value or "").strip():
        issues.append(
            _issue(
                issue_id="ISSUE-missing-receiver-country",
                title="境外接收方国家/地区缺失",
                description="未提供境外接收方国家/地区，无法充分评估接收方所在地风险。",
                category="recipient",
                severity="HIGH",
                fact_refs=[receiver_fact.fact_id],
                rule_refs=regulation_refs[:3],
                recommended_action="补充境外接收方名称、国家/地区、联系方式和处理角色。",
                affects_outputs=["recipient_capability", "risk_remediation", "conclusion"],
            )
        )

    purpose_fact = field_facts.get("request.transfer_purpose")
    if purpose_fact and not str(purpose_fact.normalized_value or "").strip():
        issues.append(
            _issue(
                issue_id="ISSUE-missing-transfer-purpose",
                title="出境目的不明确",
                description="未提供清晰的出境目的，无法支撑必要性和合法性分析。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[purpose_fact.fact_id],
                rule_refs=regulation_refs[:3],
                recommended_action="补充出境目的、处理方式、使用场景和必要性论证。",
                affects_outputs=["necessity_legal_basis", "risk_remediation", "conclusion"],
            )
        )

    # ── Document audit dimension issues (gap 5) ──

    # 数据定性模糊
    if spi_fact and int(spi_fact.normalized_value or 0) > 0:
        issues.append(
            _issue(
                issue_id="ISSUE-spi-classification-uncertain",
                title="敏感个人信息定性需进一步确认",
                description="存在敏感个人信息出境，但未提供具体敏感类型清单和分类依据。",
                category="data_classification",
                severity="HIGH",
                fact_refs=[spi_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="补充敏感个人信息类型清单、分类依据和合法基础说明。",
                affects_outputs=["data_scope", "rights_impact", "conclusion"],
            )
        )

    # 必要性论证过泛
    _necessity_severity = "MEDIUM"
    _purpose_text = (
        str(purpose_fact.normalized_value) if purpose_fact and purpose_fact.normalized_value is not None
        else ""
    )
    if len(_purpose_text.strip()) > 50:
        _necessity_severity = "LOW"
    issues.append(
        _issue(
            issue_id="ISSUE-necessity-argument-generic",
            title="出境必要性论证可能过于泛化",
            description="当前出境目的描述可能不足以支撑严格的必要性审查，需补充业务场景和不可替代性分析。",
            category="necessity",
            severity=_necessity_severity,
            fact_refs=[purpose_fact.fact_id] if purpose_fact and purpose_fact.fact_id else [],
            rule_refs=legal_rule_refs,
            recommended_action="补充业务必要性论证，说明为何必须将数据转移至境外而非境内处理。",
            affects_outputs=["necessity_legal_basis", "risk_remediation"],
        )
    )

    # 接收方安全能力证明不足 / 已声明认证但缺证书佐证
    declared_certs = list(evidence.get("declared_certifications") or [])
    has_cert_evidence = bool(
        evidence.get("has_certification_evidence")
        or evidence.get("certification_valid")
        or evidence.get("has_audit_report")
    )
    if not evidence.get("has_certification"):
        issues.append(
            _issue(
                issue_id="ISSUE-recipient-security-evidence-missing",
                title="境外接收方安全保障能力证明不足",
                description="当前材料对境外接收方的数据安全管理制度、认证证明或第三方审计材料描述不足，无法充分证明其保障能力。",
                category="recipient",
                severity="HIGH",
                fact_refs=[receiver_fact.fact_id] if receiver_fact and receiver_fact.fact_id else [],
                rule_refs=legal_rule_refs,
                recommended_action="补充境外接收方安全管理制度、认证证明或第三方审计材料。",
                affects_outputs=["recipient_capability", "risk_remediation", "conclusion"],
                missing_materials=[
                    "security_capability.certifications",
                    "第三方审计报告",
                    "境外接收方安全管理制度说明",
                ],
            )
        )
    elif declared_certs and not has_cert_evidence:
        issues.append(
            _issue(
                issue_id="ISSUE-recipient-certification-evidence-missing",
                title="境外接收方已声明认证但缺少证书佐证",
                description=(
                    f"输入声明接收方持有认证（{'、'.join(declared_certs)}），"
                    "但未提供认证证书或第三方审计佐证材料，无法核验认证有效性。"
                ),
                category="recipient",
                severity="MEDIUM",
                fact_refs=_cert_fact_refs,
                rule_refs=legal_rule_refs,
                recommended_action="补充认证证书副本或第三方审计报告，以核验认证有效性。",
                affects_outputs=["recipient_capability", "risk_remediation", "conclusion"],
                missing_materials=[
                    f"security_capability.certifications 证书佐证（{'、'.join(declared_certs)}）",
                    "第三方审计报告",
                ],
            )
        )

    # 法律文件条款缺失 / 结构化条款逐项缺失
    missing_clauses = list(evidence.get("missing_clauses") or [])
    partial_clauses = list(evidence.get("partial_clauses") or [])
    legal_fact_refs = [legal_document_fact.fact_id] if legal_document_fact and legal_document_fact.fact_id else []
    for clause_key in missing_clauses:
        label = _CLAUSE_LABELS.get(clause_key, clause_key)
        issues.append(
            _issue(
                issue_id=f"ISSUE-legal-document-clause-missing-{clause_key}",
                title=f"法律文件缺失：{label}",
                description=f"结构化法律文件审查显示「{label}」缺失。",
                category="legal_document",
                severity="MEDIUM",
                fact_refs=legal_fact_refs,
                rule_refs=regulation_refs[:3],
                recommended_action=f"补充法律文件中的「{label}」内容。",
                affects_outputs=["recipient_capability", "security_measures", "risk_remediation"],
                missing_materials=[f"legal_document_review.clause_coverage.{clause_key}"],
            )
        )

    if not evidence.get("contract_all_covered"):
        _legal_severity = "LOW" if evidence.get("has_contract_clauses") else "HIGH"
        _gap_materials = [
            f"legal_document_review.clause_coverage.{key}"
            for key in missing_clauses + partial_clauses
        ] or ["法律文件核心条款覆盖核验"]
        if evidence.get("has_contract_clauses") and (missing_clauses or partial_clauses):
            _gap_labels = "、".join(
                _CLAUSE_LABELS.get(key, key) for key in (missing_clauses + partial_clauses)
            )
            _gap_description = f"结构化法律文件审查显示以下条款未完全覆盖：{_gap_labels}。"
        else:
            _gap_description = (
                "与境外接收方签署的法律文件未验证是否包含处理目的、保存期限、"
                "再转移约束、安全事件处置和违约责任等核心条款。"
            )
        issues.append(
            _issue(
                issue_id="ISSUE-legal-document-gaps",
                title="法律文件核心条款可能存在缺失",
                description=_gap_description,
                category="legal_document",
                severity=_legal_severity,
                fact_refs=legal_fact_refs,
                rule_refs=regulation_refs[:3],
                recommended_action="核验法律文件是否覆盖六项核心条款，补充缺失内容。",
                affects_outputs=["recipient_capability", "security_measures", "risk_remediation", "conclusion"],
                missing_materials=_gap_materials,
            )
        )

    # 再转移约束不明确
    if not evidence.get("has_onward_transfer_clause"):
        issues.append(
            _issue(
                issue_id="ISSUE-onward-transfer-unclear",
                title="再转移约束条款不明确",
                description="未验证法律文件是否明确约束境外接收方不得将数据再转移至第三方。",
                category="onward_transfer",
                severity="MEDIUM",
                fact_refs=legal_fact_refs,
                rule_refs=regulation_refs[:3],
                recommended_action="补充再转移约束条款，明确接收方未经同意不得向第三方提供数据。",
                affects_outputs=["recipient_capability", "security_measures", "risk_remediation"],
                missing_materials=["legal_document_review.clause_coverage.onward_transfer_constraint"],
            )
        )

    # 同意记录证据不足
    if not evidence.get("has_consent_records"):
        issues.append(
            _issue(
                issue_id="ISSUE-consent-evidence-missing",
                title="个人信息出境单独同意记录证据不足",
                description="涉及个人信息出境时，未验证是否已取得个人信息主体的单独同意及同意记录。",
                category="consent",
                severity="HIGH",
                fact_refs=[],
                rule_refs=legal_rule_refs,
                recommended_action="补充告知和单独同意记录，或说明适用的豁免情形。",
                affects_outputs=["necessity_legal_basis", "rights_impact", "risk_remediation", "conclusion"],
                missing_materials=[
                    "personal_info_protection.separate_consent_status 单独同意记录",
                    "告知内容与留痕证据",
                ],
            )
        )

    # 匿名化有效性不明
    if not evidence.get("has_anonymization_claim"):
        issues.append(
            _issue(
                issue_id="ISSUE-anonymization-uncertain",
                title="匿名化或去标识化有效性未验证",
                description="如拟主张数据已匿名化或去标识化，需补充技术验证、重识别风险评估或第三方审计材料。",
                category="anonymization",
                severity="MEDIUM",
                fact_refs=[],
                rule_refs=regulation_refs[:3],
                recommended_action="补充匿名化/去标识化技术方案和有效性验证材料；材料补足前采用审慎表述。",
                affects_outputs=["data_scope", "security_measures", "risk_remediation"],
                missing_materials=["匿名化/去标识化技术方案", "重识别风险评估报告"],
            )
        )

    # 缺失材料补充建议
    _checklist_materials: list[str] = ["隐私政策", "合同/数据处理协议", "安全措施说明"]
    if not evidence.get("has_data_inventory"):
        _checklist_materials.insert(0, "数据清单")
    issues.append(
        _issue(
            issue_id="ISSUE-material-checklist-incomplete",
            title="申报支撑材料清单不完整",
            description="当前仅根据输入字段推断材料需求，未基于完整申报材料清单逐项核验。",
            category="documentation",
            severity="MEDIUM",
            fact_refs=[],
            rule_refs=[],
            recommended_action="对照安全评估申报材料清单逐项核验，补充数据清单、隐私政策、合同、安全措施说明等材料。",
            affects_outputs=["overview", "risk_remediation", "conclusion"],
            missing_materials=_checklist_materials,
        )
    )

    # 内部审批和监控机制缺失
    issues.append(
        _issue(
            issue_id="ISSUE-internal-approval-missing",
            title="内部审批和数据出境监控机制未体现",
            description="未体现企业内部数据出境审批流程、定期监控机制和责任人信息。",
            category="internal_approval",
            severity="MEDIUM",
            fact_refs=[],
            rule_refs=[],
            recommended_action="补充内部数据出境管理制度、审批流程和定期安全评估机制说明。",
            affects_outputs=["security_measures", "risk_remediation"],
            missing_materials=["内部数据出境管理制度", "审批流程与责任人说明", "定期安全评估机制"],
        )
    )

    # ── Tri-state classification ──
    # Mark each issue as confirmed_issue, suspected_issue, or default_review_item
    # This controls how the issue is expressed in external reports
    _CERTAINTY_MAP: dict[str, str] = {
        "ISSUE-ciio-security-assessment": "confirmed_issue",
        "ISSUE-important-data-security-assessment": "confirmed_issue",
        "ISSUE-pii-threshold": "confirmed_issue",
        "ISSUE-spi-threshold": "confirmed_issue",
        "ISSUE-recommended-path-mismatch": "confirmed_issue",
        "ISSUE-missing-transfer-purpose": "confirmed_issue",
        "ISSUE-missing-receiver-country": "confirmed_issue",
        #
        "ISSUE-recipient-security-evidence-missing": "suspected_issue",
        "ISSUE-recipient-certification-evidence-missing": "suspected_issue",
        "ISSUE-legal-document-gaps": "suspected_issue",
        "ISSUE-onward-transfer-unclear": "suspected_issue",
        "ISSUE-consent-evidence-missing": "suspected_issue",
        "ISSUE-anonymization-uncertain": "suspected_issue",
        "ISSUE-spi-classification-uncertain": "suspected_issue",
        "ISSUE-necessity-argument-generic": "suspected_issue",
        #
        "ISSUE-missing-attachments": "default_review_item",
        "ISSUE-attachments-not-parsed": "default_review_item",
        "ISSUE-material-checklist-incomplete": "default_review_item",
        "ISSUE-internal-approval-missing": "default_review_item",
    }

    for issue in issues:
        if issue.issue_id.startswith("ISSUE-legal-document-clause-missing-"):
            certainty = "suspected_issue"
        else:
            certainty = _CERTAINTY_MAP.get(issue.issue_id, "default_review_item")
        if certainty == "confirmed_issue":
            prefix = "[confirmed_issue]"
        elif certainty == "suspected_issue":
            prefix = "[suspected_issue]"
        else:
            prefix = "[default_review_item]"
        # Embed certainty in the recommended_action for downstream consumption
        if prefix not in issue.recommended_action:
            issue.recommended_action = f"{prefix} {issue.recommended_action}"

    return issues
