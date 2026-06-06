"""Representative test payloads — one per module — for the evaluation runner.

Payloads are translated from frontend/src/lib/dev-test-cases.ts.
Each payload targets the module's async endpoint directly.
"""

import json
import os
import sys

BACKEND_URL = os.environ.get("AI4LAW_BACKEND_URL", "http://127.0.0.1:8000")

# (module_key, endpoint_suffix, payload, label)
# fmt: off
PAYLOADS = [
    # ── CN ─────────────────────────────────────────────────────
    (
        "assessment",
        "assessment",
        {
            "company_name": "东方信托有限责任公司",
            "industry": "金融科技",
            "is_ciio": True,
            "contains_important_data": True,
            "pii_count": 80000,
            "spi_count": 80000,
            "transfer_purpose": "跨境集团财务报告与风险管理",
            "receiver_country": "香港",
            "force_override_path": True,
        },
        "assessment (CIIO financial trust)"
    ),
    (
        "pipia",
        "pipia",
        {
            "route_type": "scc_filing",
            "company_profile": {
                "company_name": "跨境优品（深圳）电子商务有限公司",
                "industry": "电商零售",
                "is_ciio": False,
                "processing_person_count": 500000,
                "outbound_pi_count": 500000,
                "outbound_spi_count": 0,
            },
            "transfer_context": {
                "purpose": "订单数据同步至新加坡亚太数据中心",
                "recipient_name": "跨境优品（香港）国际有限公司",
                "recipient_country_region": "新加坡",
                "legal_basis": "履行合同所必需+用户同意",
            },
            "personal_info_scope": {
                "pi_categories": ["姓名", "手机号", "收货地址"],
                "spi_categories": [],
                "subject_volume": 450000,
            },
            "rights_protection": {
                "notice_mechanism": "APP注册时弹窗告知",
                "consent_mechanism": "用户下单时弹窗单独同意",
                "dsar_channel": "privacy@example.com",
                "retention_policy": "订单数据保留3年",
            },
            "emergency_plan": {
                "incident_response_sla_hours": 24,
                "escalation_path": "安全事件→数据安全专员→CRO→CEO→网信办",
            },
            "attachments": [
                {"file_role": "scc_contract", "file_name": "scc_draft.docx",
                 "file_format": "docx", "storage_uri": "storage/uploads/scc_draft.docx"}
            ],
        },
        "pipia (standard contract filing)"
    ),
    (
        "scc",
        "scc",
        {
            "company_name": "数字支付科技（深圳）有限公司",
            "receiver_name": "PayTech Singapore Pte Ltd",
            "receiver_country": "新加坡",
            "transfer_purpose": "为新加坡客户提供支付处理服务的境外技术支持",
            "pii_count": 500000,
            "spi_count": 120000,
            "has_scc_draft": True,
        },
        "scc (payment processor to Singapore)"
    ),
    (
        "review",
        "review",
        {
            "company_name": "华东云链科技（测试）",
            "document_type": "privacy_policy",
            "receiver_name": "OceanStar Technology Pte. Ltd.",
            "receiver_country": "新加坡",
            "transfer_purpose": "跨境客服工单处理和统一运维支持",
            "pii_count": 280000,
            "spi_count": 5000,
            "review_focus": "重点核查跨境传输告知、敏感信息处理、用户权利行使路径",
        },
        "review (privacy policy review)"
    ),
    # ── EU ─────────────────────────────────────────────────────
    (
        "eu_scc",
        "eu_scc",
        {
            "project_name": "电商平台云服务数据处理",
            "scc_text": ("MODULE TWO: Transfer controller to processor\\n\\n"
                         "Data exporter: E-Commerce GmbH, Berlin\\n"
                         "Data importer: CloudServe Inc., Delaware\\n"
                         "Categories of personal data: Name, email, shipping address\\n"
                         "Purpose: Cloud hosting and infrastructure services"),
            "declared_module_type": "C2P",
            "exporter_role": "controller",
            "importer_role": "processor",
            "company_name": "E-Commerce GmbH",
        },
        "eu_scc (German ecommerce to US cloud)"
    ),
    (
        "bcr",
        "bcr",
        {
            "company_name": "GlobalTech Inc.",
            "review_items": [
                {"code": "3.2-C5", "title": "Onward Transfer",
                 "evidence": "Allows transfers to 'trusted partners' without requiring equivalent protection",
                 "score": "partial"},
            ],
        },
        "bcr (GlobalTech medium risk)"
    ),
    (
        "dpia",
        "dpia",
        {
            "project_name": "AI招聘筛选与候选人评估系统",
            "project_goal": "通过自动化分析求职者多维度数据提高招聘效率",
            "processing_flow_description": "数据从求职者→招聘网站→AWS EU服务器→AI模型→HR系统",
            "data_categories": ["身份信息", "联系方式", "教育背景", "视频/音频记录"],
            "special_category_data": True,
            "cross_border_transfer": True,
            "automated_decision_making": True,
            "systematic_monitoring": True,
            "large_scale_processing": True,
            "new_technology": True,
        },
        "dpia (AI recruitment system)"
    ),
    (
        "tia",
        "tia",
        {
            "transfer_tool": "scc",
            "data_exporter_profile": "TechInnovate Ireland Ltd，SaaS平台，控制者",
            "data_importer_profile": "AnalyticsPro India Pvt Ltd，数据处理者",
            "third_country_assessment": "印度未获欧盟充分性认定，IT法第69条赋予政府广泛监控权",
            "supplementary_measures": "端到端加密,密钥分离,定期审计",
            "final_conclusion": "在实施补充措施后可继续传输",
            "attachments": [
                {"file_role": "tia_main_report", "file_name": "tia.docx",
                 "file_format": "docx", "storage_uri": "storage/uploads/tia.docx"}
            ],
        },
        "tia (SCC to India)"
    ),
    # ── US ─────────────────────────────────────────────────────
    (
        "cn_flow",
        "cn-flow",
        {
            "company_name": "GlobalShop Inc.",
            "transfer_purpose": "向中国供应商传输订单信息",
            "data_categories": ["客户姓名", "收货地址", "联系电话", "商品订单号"],
            "sensitive_data_flags": ["无敏感信息"],
            "transfer_chain": "美国总部→AWS美东区→加密API→中国供应商ERP",
            "recipient_entities": [
                {"entity_name": "深圳智能制造有限公司", "country_region": "中国",
                 "entity_role": "vendor", "is_restricted_party": False},
            ],
            "attachments": [
                {"file_role": "data_inventory", "file_name": "data.xlsx",
                 "file_format": "xlsx", "storage_uri": "storage/uploads/data.xlsx"},
                {"file_role": "entity_inventory", "file_name": "entity.xlsx",
                 "file_format": "xlsx", "storage_uri": "storage/uploads/entity.xlsx"},
            ],
        },
        "cn_flow (US ecommerce to China vendor)"
    ),
    (
        "us_14117",
        "us_14117",
        {
            "project_name": "国际合作基因组研究",
            "transaction_description": "与深圳华大基因合作，传输5万份去标识化基因组数据",
            "transaction_type": "cooperative_research",
            "company_name": "American Genomics Research Institute",
            "data_items": [
                {"data_item_name": "人类全基因组测序数据",
                 "data_description": "5万份BAM格式",
                 "doj_data_category": "human_genomic_data",
                 "us_person_count": 50000}
            ],
            "recipient_entities": [
                {"entity_name": "深圳华大基因研究院",
                 "country_of_registration": "中国",
                 "government_control": False,
                 "entity_role": "processor"}
            ],
            "security_measures": [],
        },
        "us_14117 (genomics to China)"
    ),
    (
        "cpra",
        "cpra",
        {
            "company_name": "TrendyGoods Inc.",
            "business_model": "线上时尚零售商，年收入约3000万美元",
            "data_lifecycle": "收集→分析→个性化推荐→与第三方广告网络共享",
            "notice_and_consent": "Cookie横幅仅提供'接受'按钮",
            "consumer_rights_process": "提供在线表单和邮箱渠道",
            "opt_out_and_sale_sharing": "与AdNetwork共享用户浏览行为数据",
            "vendor_management": "与AdNetwork合同未包含opt-out条款",
            "attachments": [
                {"file_role": "privacy_policy", "file_name": "policy.url",
                 "file_format": "url", "storage_uri": "https://trendygoods.com/privacy"}
            ],
        },
        "cpra (TrendyGoods ecommerce)"
    ),
]
# fmt: on


def get_payloads():
    """Return list of (module_key, endpoint_suffix, payload_dict, label)."""
    return PAYLOADS
