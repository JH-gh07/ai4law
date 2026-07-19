"""CPRA gap rules — 10 modular rule functions for structured compliance diagnosis."""

from __future__ import annotations

from backend.domains.us.cpra.schema import (
    CPRAApplicabilityInfo,
    CPRAConsentUI,
    CPRADataItem,
    CPRADSRMechanism,
    CPRAGapItem,
    CPRAVendorInfo,
)

_SPI_CATEGORIES = {
    "health_data", "biometric_information", "precise_geolocation",
    "account_credentials", "racial_or_ethnic_origin", "social_security_number",
    "financial_account", "communication_content", "genetic_data",
    "sex_life_or_orientation", "citizenship_or_immigration",
}

_HIGH_RISK_PURPOSES = {
    "advertising", "marketing", "third_party_marketing",
    "insurance_recommendation", "data_broker", "sale",
}

# ── 1. Applicability ────────────────────────────────────────────────────

def check_applicability(info: CPRAApplicabilityInfo | None, text: str = "") -> list[CPRAGapItem]:
    items: list[CPRAGapItem] = []
    if info is None:
        # Fallback: check free text for revenue/consumer keywords
        if any(kw in text.lower() for kw in ["3000万", "25 million", "100,000", "100000"]):
            items.append(CPRAGapItem(
                domain="applicability", risk_level="MEDIUM",
                gap="企业适用性需确认：自由文本包含潜在适用信号",
                legal_basis="CPRA §1798.140(d) business definition",
                recommendation="建议填写结构化适用性字段以精确判定",
                phase="short_term", evidence_source="rule_inferred",
            ))
        return items

    reasons: list[str] = []
    applicable = False
    if info.annual_revenue_usd and info.annual_revenue_usd > 25_000_000:
        applicable = True
        reasons.append("年收入超过2500万美元")
    if info.ca_consumer_count and info.ca_consumer_count >= 100_000:
        applicable = True
        reasons.append("每年处理10万以上加州消费者个人信息")
    if info.sell_share_revenue_ratio and info.sell_share_revenue_ratio >= 0.5:
        applicable = True
        reasons.append("50%以上收入来自出售或共享个人信息")

    if applicable:
        items.append(CPRAGapItem(
            domain="applicability", risk_level="LOW",
            gap=f"企业适用CPRA（{'; '.join(reasons)}）",
            legal_basis="CPRA §1798.140(d)",
            recommendation="确认适用并推进全面合规评估",
            phase="short_term", evidence_source="rule_inferred",
        ))
    else:
        items.append(CPRAGapItem(
            domain="applicability", risk_level="MEDIUM",
            gap="无法确定企业是否适用CPRA（结构化字段均未满足阈值）",
            legal_basis="CPRA §1798.140(d)",
            recommendation="需要更多信息确认适用性",
            phase="short_term", evidence_source="rule_inferred",
        ))
    return items


# ── 2. Business Role ────────────────────────────────────────────────────

def check_business_role(text: str, vendors: list[CPRAVendorInfo]) -> list[CPRAGapItem]:
    items: list[CPRAGapItem] = []
    t = text.lower()

    is_sp = any(kw in t for kw in ["service provider", "服务提供商", "serviceprovider",
                                      "data processor", "数据处理者", "software as a service"])
    is_third = any(kw in t for kw in ["data broker", "advertising", "广告", "third party",
                                        "第三方", "ad network"])
    has_client_contract_mention = any(kw in t for kw in ["client contract", "客户合同", "customer agreement",
                                                           "client dpas", "master service"])

    if is_sp and not any(v.has_dpa for v in vendors):
        items.append(CPRAGapItem(
            domain="business_role", risk_level="MEDIUM",
            gap="企业描述为服务提供商，但供应商清单未体现DPA",
            legal_basis="CPRA §1798.140(ag) service provider",
            recommendation="确认服务提供商身份并签署必要的DPA",
            phase="mid_term", evidence_source="rule_inferred",
        ))
    if is_sp and has_client_contract_mention:
        items.append(CPRAGapItem(
            domain="business_role", risk_level="MEDIUM",
            gap="服务提供商需确保客户合同包含CPRA强制条款",
            legal_basis="CPRA §1798.140(ag), CPPA Regulations",
            recommendation="更新客户合同，纳入服务提供商义务条款",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if is_third and any(v.sale_or_share for v in vendors) and not any(v.dpa_honors_opt_out for v in vendors):
        items.append(CPRAGapItem(
            domain="business_role", risk_level="HIGH",
            gap="涉及数据出售/共享的第三方未要求尊重消费者opt-out",
            legal_basis="CPRA §1798.120",
            recommendation="要求第三方合同明确接受opt-out义务",
            phase="short_term", evidence_source="rule_inferred",
        ))
    return items


# ── 3. Notice ───────────────────────────────────────────────────────────

def check_notice(text: str) -> list[CPRAGapItem]:
    items: list[CPRAGapItem] = []
    t = text.lower()

    if any(kw in t for kw in ["缺失", "无", "none", "缺失告知", "no notice"]):
        items.append(CPRAGapItem(
            domain="notice_and_consent", risk_level="HIGH",
            gap="隐私告知或同意机制不完整",
            legal_basis="CPRA §1798.100 Notice at Collection",
            recommendation="补齐分场景告知文本与同意留痕机制",
            phase="short_term", evidence_source="user_input",
        ))
    if not any(kw in t for kw in ["data category", "个人信息类别", "收集.*类别", "purposes",
                                    "retention", "留存", "保存期限", "right to delete"]):
        items.append(CPRAGapItem(
            domain="notice_and_consent", risk_level="MEDIUM",
            gap="隐私告知可能未涵盖数据类别、处理目的或留存期限",
            legal_basis="CPRA §1798.100(a)",
            recommendation="在隐私政策中明确数据类别、目的和留存期限",
            phase="short_term", evidence_source="rule_inferred",
        ))
    return items


# ── 4. Data Mapping ─────────────────────────────────────────────────────

def check_data_mapping(items: list[CPRADataItem]) -> list[CPRAGapItem]:
    results: list[CPRAGapItem] = []
    if not items:
        return results

    for item in items:
        if item.is_sensitive and item.purpose in _HIGH_RISK_PURPOSES:
            results.append(CPRAGapItem(
                domain="data_mapping", risk_level="HIGH",
                gap=f"敏感个人信息'{item.category}'用于'{item.purpose}'，超出合理必要范围",
                legal_basis="CPRA §1798.121 Limit Use of SPI",
                recommendation="除非该使用属于§1798.121(a)列明的必需目的，应立即停止",
                phase="short_term", evidence_source="rule_inferred",
            ))
        if item.sale_or_share and item.recipient_type in ("advertising_network", "third_party"):
            results.append(CPRAGapItem(
                domain="data_mapping", risk_level="HIGH",
                gap=f"'{item.category}'数据出售/共享给{item.recipient_type}",
                legal_basis="CPRA §1798.120 opt-out right",
                recommendation="确保提供Do Not Sell or Share My Personal Information选择退出机制",
                phase="short_term", evidence_source="rule_inferred",
            ))
        if "year" in item.retention.lower() or "年" in item.retention:
            import re
            years = re.findall(r"(\d+)", item.retention)
            if years and int(years[0]) > 7:
                results.append(CPRAGapItem(
                    domain="data_mapping", risk_level="MEDIUM",
                    gap=f"'{item.category}'留存{int(years[0])}年需评估必要性",
                    legal_basis="CPRA §1798.100(c) data minimization",
                    recommendation="评估留存必要性，采用最短留存原则",
                    phase="mid_term", evidence_source="rule_inferred",
                ))
    return results


# ── 5. DSR ──────────────────────────────────────────────────────────────

def check_dsr(dsr: CPRADSRMechanism | None, text: str = "", has_spi: bool = False) -> list[CPRAGapItem]:
    items: list[CPRAGapItem] = []
    t = text.lower()

    # Fallback: check original text field
    if dsr is None:
        if "45" not in t and "sla" not in t:
            items.append(CPRAGapItem(
                domain="consumer_rights_process", risk_level="MEDIUM",
                gap="消费者权利响应时限与SLA未明确",
                legal_basis="CPRA §1798.130(a) 45-day response",
                recommendation="建立统一DSR流程并设置45天响应时限",
                phase="short_term", evidence_source="user_input",
            ))
        return items

    # Structured check
    channels = sum([dsr.has_web_form, dsr.has_email, dsr.has_toll_free_phone])
    if channels < 2:
        items.append(CPRAGapItem(
            domain="consumer_rights_process", risk_level="MEDIUM",
            gap=f"DSR提交渠道仅{channels}种（建议至少2种）",
            legal_basis="CPRA §1798.130(a), CPPA §7010",
            recommendation="增加DSR提交渠道（在线表单/邮箱/免费电话）",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if not dsr.has_toll_free_phone:
        items.append(CPRAGapItem(
            domain="consumer_rights_process", risk_level="MEDIUM",
            gap="缺少免费电话DSR渠道",
            legal_basis="CPRA §1798.130(a)",
            recommendation="提供免费电话作为DSR提交方式之一",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if not dsr.supports_opt_out:
        items.append(CPRAGapItem(
            domain="consumer_rights_process", risk_level="HIGH",
            gap="缺少出售/共享选择退出入口",
            legal_basis="CPRA §1798.120",
            recommendation="提供Do Not Sell or Share My Personal Information机制",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if has_spi and not dsr.supports_limit_spi:
        items.append(CPRAGapItem(
            domain="consumer_rights_process", risk_level="HIGH",
            gap="缺少限制敏感个人信息使用入口",
            legal_basis="CPRA §1798.121",
            recommendation="提供Limit Use of Sensitive Personal Information链接",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if dsr.response_days is not None and dsr.response_days > 45:
        items.append(CPRAGapItem(
            domain="consumer_rights_process", risk_level="HIGH",
            gap=f"DSR响应时限{dsr.response_days}天超过CPRA要求的45天",
            legal_basis="CPRA §1798.130(a)",
            recommendation="将响应时限缩短至45天以内",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if not dsr.is_easy_to_find:
        items.append(CPRAGapItem(
            domain="consumer_rights_process", risk_level="MEDIUM",
            gap="DSR入口不易于访问或发现",
            legal_basis="CPRA §1798.130(a), CPPA §7010",
            recommendation="确保DSR链接在主页显著位置",
            phase="short_term", evidence_source="rule_inferred",
        ))
    return items


# ── 6. Opt-Out ──────────────────────────────────────────────────────────

def check_opt_out(text: str, items: list[CPRADataItem], dsr: CPRADSRMechanism | None) -> list[CPRAGapItem]:
    results: list[CPRAGapItem] = []
    t = text.lower()

    # Original rule
    has_sale_signal = any(kw in t for kw in ["yes", "是", "出售", "共享", "share", "sell", "sale"])
    has_opt_out = any(kw in t for kw in ["opt-out", "opt out", "选择退出", "请勿出售", "do not sell",
                                           "limit the use", "global privacy control", "gpc"])
    if has_sale_signal and not has_opt_out:
        results.append(CPRAGapItem(
            domain="opt_out_and_sale_sharing", risk_level="HIGH",
            gap="存在出售/共享但未明确opt-out机制",
            legal_basis="CPRA §1798.120 opt-out right",
            recommendation="上线Do Not Sell/Share链接并记录执行日志",
            phase="short_term", evidence_source="user_input",
        ))

    # Structured checks
    has_ad_network = any(i.recipient_type == "advertising_network" for i in items)
    has_cross_context = any(i.cross_context_advertising for i in items)
    if (has_ad_network or has_cross_context) and not has_opt_out:
        results.append(CPRAGapItem(
            domain="opt_out_and_sale_sharing", risk_level="HIGH",
            gap="涉及跨上下文行为广告/广告网络但缺少标准Do Not Sell or Share入口",
            legal_basis="CPRA §1798.120, §1798.140(ad)",
            recommendation="提供标准化Do Not Sell or Share链接和Global Privacy Control支持",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if has_opt_out and not any(kw in t for kw in ["do not sell or share", "请勿出售或分享", "icon", "图标", "gpc"]):
        results.append(CPRAGapItem(
            domain="opt_out_and_sale_sharing", risk_level="MEDIUM",
            gap="opt-out链接可能不规范（缺标准文字/图标/GPC支持）",
            legal_basis="CPRA §1798.120, CPPA §7010",
            recommendation="使用标准化Do Not Sell or Share链接和图标",
            phase="mid_term", evidence_source="rule_inferred",
        ))
    return results


# ── 7. SPI ──────────────────────────────────────────────────────────────

def check_spi(items: list[CPRADataItem], dsr: CPRADSRMechanism | None, consent_ui: CPRAConsentUI | None) -> list[CPRAGapItem]:
    results: list[CPRAGapItem] = []
    spi_items = [i for i in items if i.is_sensitive]
    if not spi_items:
        return results

    spi_types = {i.category for i in spi_items}
    results.append(CPRAGapItem(
        domain="spi", risk_level="MEDIUM",
        gap=f"识别到敏感个人信息: {', '.join(spi_types)}",
        legal_basis="CPRA §1798.140(ae) SPI definition",
        recommendation="确认SPI处理是否在合理必要范围内",
        phase="short_term", evidence_source="rule_inferred",
    ))

    # Over-scope usage
    over_scope = [i for i in spi_items if i.purpose in _HIGH_RISK_PURPOSES]
    if over_scope:
        cats = ", ".join(i.category for i in over_scope)
        results.append(CPRAGapItem(
            domain="spi", risk_level="HIGH",
            gap=f"SPI ({cats}) 用于非必要目的（营销/广告/第三方），超出合理必要范围",
            legal_basis="CPRA §1798.121",
            recommendation="立即停止SPI的非必要使用，除非属于法定必需目的",
            phase="short_term", evidence_source="rule_inferred",
        ))

    # Missing Limit SPI entry
    if dsr and not dsr.supports_limit_spi:
        results.append(CPRAGapItem(
            domain="spi", risk_level="HIGH",
            gap="涉及SPI但未提供Limit Use of Sensitive Personal Information机制",
            legal_basis="CPRA §1798.121(a)",
            recommendation="提供显眼的'Limit the Use of My Sensitive Personal Information'链接",
            phase="short_term", evidence_source="rule_inferred",
        ))

    # Dark patterns + SPI
    if consent_ui and (consent_ui.bundled_consent or consent_ui.preselected_consent):
        results.append(CPRAGapItem(
            domain="spi", risk_level="HIGH",
            gap="SPI同意存在暗模式（预选/捆绑），同意可能无效",
            legal_basis="CPRA §1798.140(l), CPPA §7004",
            recommendation="重新设计同意界面，确保自由、知情、明确同意",
            phase="short_term", evidence_source="rule_inferred",
        ))

    return results


# ── 8. Vendor ───────────────────────────────────────────────────────────

def check_vendor(vendors: list[CPRAVendorInfo]) -> list[CPRAGapItem]:
    results: list[CPRAGapItem] = []
    if not vendors:
        return results

    for v in vendors:
        if v.receives_pi and not v.has_dpa:
            results.append(CPRAGapItem(
                domain="vendor_management", risk_level="MEDIUM" if v.vendor_type == "service_provider" else "HIGH",
                gap=f"供应商'{v.name}'（{v.vendor_type}）接收个人信息但缺少DPA",
                legal_basis="CPRA §1798.140(ag), §1798.140(aj)",
                recommendation=f"与{v.name}签署包含CPRA强制条款的DPA",
                phase="short_term", evidence_source="rule_inferred",
            ))
        if v.sale_or_share and not v.dpa_prohibits_sale_share:
            results.append(CPRAGapItem(
                domain="vendor_management", risk_level="HIGH",
                gap=f"供应商'{v.name}'涉及出售/共享但DPA未禁止",
                legal_basis="CPRA §1798.120",
                recommendation=f"在{v.name}的合同中加入禁止出售/共享条款",
                phase="short_term", evidence_source="rule_inferred",
            ))
        if v.vendor_type in ("ad_partner", "advertising_network") and not v.dpa_honors_opt_out:
            results.append(CPRAGapItem(
                domain="vendor_management", risk_level="HIGH",
                gap=f"广告合作伙伴'{v.name}'未要求尊重消费者opt-out",
                legal_basis="CPRA §1798.120",
                recommendation=f"要求{v.name}在合同中明确接受opt-out义务",
                phase="short_term", evidence_source="rule_inferred",
            ))
        if v.receives_spi and not v.dpa_requires_audit:
            results.append(CPRAGapItem(
                domain="vendor_management", risk_level="MEDIUM",
                gap=f"供应商'{v.name}'接收SPI但DPA缺少审计权",
                legal_basis="CPRA §1798.140(ag)",
                recommendation=f"在{v.name}的DPA中加入审计权条款",
                phase="mid_term", evidence_source="rule_inferred",
            ))
    return results


# ── 9. Dark Patterns ────────────────────────────────────────────────────

def check_dark_patterns(ui: CPRAConsentUI | None) -> list[CPRAGapItem]:
    results: list[CPRAGapItem] = []
    if ui is None:
        return results

    if ui.preselected_consent:
        results.append(CPRAGapItem(
            domain="consent_ui", risk_level="HIGH",
            gap="存在预选同意（pre-selected consent），可能构成暗模式",
            legal_basis="CPRA §1798.140(l), CPPA §7004",
            recommendation="取消预选，要求消费者主动选择同意",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if ui.bundled_consent:
        results.append(CPRAGapItem(
            domain="consent_ui", risk_level="HIGH",
            gap="存在捆绑同意（bundled consent），可能构成暗模式",
            legal_basis="CPRA §1798.140(l), CPPA §7004",
            recommendation="分离不同处理目的的同意，允许逐项选择",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if ui.accept_prominent and not ui.reject_equally_prominent:
        results.append(CPRAGapItem(
            domain="consent_ui", risk_level="MEDIUM",
            gap="接受按钮显著但拒绝按钮不显著，可能构成暗模式",
            legal_basis="CPRA §1798.140(l), CPPA §7004",
            recommendation="确保拒绝和接受选项同等显著",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if ui.refusal_more_steps:
        results.append(CPRAGapItem(
            domain="consent_ui", risk_level="MEDIUM",
            gap="拒绝路径比接受路径步骤更多，可能构成暗模式",
            legal_basis="CPRA §1798.140(l), CPPA §7004",
            recommendation="使拒绝和接受的步骤数量相等",
            phase="short_term", evidence_source="rule_inferred",
        ))
    if ui.confusing_language:
        results.append(CPRAGapItem(
            domain="consent_ui", risk_level="MEDIUM",
            gap="同意界面使用混淆性或不清晰的语言",
            legal_basis="CPRA §1798.140(l), CPPA §7004",
            recommendation="使用清晰、通俗的语言描述数据实践",
            phase="short_term", evidence_source="rule_inferred",
        ))
    return results


# ── 10. Exemptions ──────────────────────────────────────────────────────

def check_exemptions(info: CPRAApplicabilityInfo | None, items: list[CPRADataItem]) -> list[CPRAGapItem]:
    results: list[CPRAGapItem] = []
    if info is None or not info.possible_exemptions:
        return results

    exemptions = set(e.lower() for e in info.possible_exemptions)
    phi_items = [i for i in items if "health" in i.category.lower() or "medical" in i.category.lower()]
    fin_items = [i for i in items if "financial" in i.category.lower() or "credit" in i.category.lower()]

    if "hipaa" in exemptions and phi_items:
        results.append(CPRAGapItem(
            domain="exemptions", risk_level="LOW",
            gap="HIPAA受保护健康信息可能部分豁免CPRA",
            legal_basis="CPRA §1798.145(c) HIPAA exemption",
            recommendation="确认健康数据是否为HIPAA PHI并按相应法规处理",
            phase="long_term", evidence_source="rule_inferred",
        ))
    if "glba" in exemptions and fin_items:
        results.append(CPRAGapItem(
            domain="exemptions", risk_level="LOW",
            gap="GLBA金融服务数据可能部分豁免CPRA",
            legal_basis="CPRA §1798.145(e) GLBA exemption",
            recommendation="确认金融数据是否适用GLBA豁免",
            phase="long_term", evidence_source="rule_inferred",
        ))
    return results


# ── Aggregator ──────────────────────────────────────────────────────────

def run_all_rules(
    applicability: CPRAApplicabilityInfo | None,
    business_text: str,
    notice_text: str,
    dsr: CPRADSRMechanism | None,
    dsr_text: str,
    opt_out_text: str,
    data_items: list[CPRADataItem],
    vendors: list[CPRAVendorInfo],
    consent_ui: CPRAConsentUI | None,
) -> list[CPRAGapItem]:
    """Run all 10 rule functions and return combined gap items."""
    items: list[CPRAGapItem] = []
    items.extend(check_applicability(applicability, business_text))
    items.extend(check_business_role(business_text, vendors))
    items.extend(check_notice(notice_text))
    items.extend(check_data_mapping(data_items))
    has_spi = any(i.is_sensitive for i in data_items)
    items.extend(check_dsr(dsr, dsr_text, has_spi))
    items.extend(check_opt_out(opt_out_text, data_items, dsr))
    items.extend(check_spi(data_items, dsr, consent_ui))
    items.extend(check_vendor(vendors))
    items.extend(check_dark_patterns(consent_ui))
    items.extend(check_exemptions(applicability, data_items))
    return items
