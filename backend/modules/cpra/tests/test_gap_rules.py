"""Regression tests for CPRA gap rule engine — 3 test cases."""

from __future__ import annotations

import re

from backend.modules.cpra.gap_rules import run_all_rules
from backend.modules.cpra.schema import (
    CPRAApplicabilityInfo,
    CPRAConsentUI,
    CPRADataItem,
    CPRADSRMechanism,
    CPRAVendorInfo,
)

# ═══════════════════════════════════════════════════════════════════════
# Case 1: TrendyGoods.com
# ═══════════════════════════════════════════════════════════════════════

_CASE_1_EXPECTED = [
    "applicability|适用.*确认",               # annual_revenue > 25M, applicable
    "opt.?out|选择退出|请勿出售",             # 缺标准opt-out链接
    "免费电话|toll.?free",                   # 缺免费电话DSR
    "暗模式|dark.*pattern|拒绝.*不显著",      # Cookie暗模式
    "opt.?out|选择退出.*合同|contract.*opt", # 广告合同未要求opt-out
    "留存.*评估|retention.*assess",          # 13个月留存需评估
]


# ═══════════════════════════════════════════════════════════════════════
# Case 2: DataFlow Analytics
# ═══════════════════════════════════════════════════════════════════════

_CASE_2_EXPECTED = [
    "服务提供商|service.*provider",           # role = service_provider
    "客户合同|client.*contract",             # client contract missing CPRA clauses
    "DPA|data.*processing.*agreement",       # DPA相关
    "适用.*确认|applicability|适用性.*确认",  # applicability uncertain
]


# ═══════════════════════════════════════════════════════════════════════
# Case 3: FitLife AI
# ═══════════════════════════════════════════════════════════════════════

_CASE_3_EXPECTED = [
    "SPI|敏感.*个人信息|sensitive.*personal",   # 健康/生物/位置→SPI
    "超出.*范围|over.?scope|超范围|limit.*use", # SPI超范围用于营销
    "暗模式|dark.*pattern|invalid.*consent|无效.*同意", # 暗模式同意
    "limit.*sensitive|限制.*敏感",             # 缺少Limit SPI入口
    "opt.?out|选择退出|请勿出售",              # 缺少opt-out
    "立即停止|应当.*停止|suspend.*immediately", # 应立即停止共享
    "第三方.*共享|third.*party.*share",        # 向第三方共享健康衍生数据
]


# ═══════════════════════════════════════════════════════════════════════

def _check_hits(items, expected_patterns):
    all_text = " ".join(f"{g.domain} {g.gap} {g.recommendation} {g.legal_basis}" for g in items)
    hits = {}
    for pat in expected_patterns:
        hits[pat] = bool(re.search(pat, all_text, re.IGNORECASE))
    return hits


def test_regression_case_1_trendy_goods():
    gaps = run_all_rules(
        applicability=CPRAApplicabilityInfo(annual_revenue_usd=30_000_000, operates_in_california=True),
        business_text="电商平台，年收入约3000万美元，面向加州消费者",
        notice_text="隐私告知缺失",
        dsr=CPRADSRMechanism(has_web_form=True, has_email=True, supports_opt_out=False, is_easy_to_find=False),
        dsr_text="目前仅邮箱接收",
        opt_out_text="存在广告网络共享，有basic opt-out但非标准Do Not Sell链接，未支持GPC",
        data_items=[
            CPRADataItem(category="浏览日志", is_sensitive=False, sale_or_share=True,
                         recipient_type="advertising_network", retention="13个月"),
            CPRADataItem(category="交易记录", is_sensitive=False, retention="7年"),
        ],
        vendors=[
            CPRAVendorInfo(name="AdNetwork Alpha", vendor_type="ad_partner",
                           sale_or_share=True, receives_pi=True, dpa_honors_opt_out=False),
        ],
        consent_ui=CPRAConsentUI(has_cookie_banner=True, accept_prominent=True,
                                 reject_equally_prominent=False),
    )
    hits = _check_hits(gaps, _CASE_1_EXPECTED)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 1 hits: {hit_count}/{len(_CASE_1_EXPECTED)}")
    for pat, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pat}")
    assert hit_count >= 4, f"Expected ≥4 hits, got {hit_count}"


def test_regression_case_2_dataflow():
    gaps = run_all_rules(
        applicability=CPRAApplicabilityInfo(annual_revenue_usd=15_000_000, ca_consumer_count=120_000),
        business_text="SaaS数据分析服务提供商，客户为零售商，处理加州消费者数据但不直接面向消费者",
        notice_text="数据通过客户收集",
        dsr=CPRADSRMechanism(has_email=True, supports_access=True, supports_delete=True),
        dsr_text="协助客户响应DSR",
        opt_out_text="不直接处理opt-out，由客户管理",
        data_items=[
            CPRADataItem(category="分析数据", is_sensitive=False, purpose="analytics",
                         recipient_type="service_provider"),
        ],
        vendors=[],
        consent_ui=None,
    )
    hits = _check_hits(gaps, _CASE_2_EXPECTED)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 2 hits: {hit_count}/{len(_CASE_2_EXPECTED)}")
    for pat, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pat}")
    assert hit_count >= 3, f"Expected ≥3 hits, got {hit_count}"


def test_regression_case_3_fitlife_ai():
    gaps = run_all_rules(
        applicability=CPRAApplicabilityInfo(annual_revenue_usd=5_000_000),
        business_text="健康健身App，处理健康数据、生物特征、精确位置，向第三方共享健康衍生数据用于广告和保险推荐",
        notice_text="注册时要求同意所有条款，不接受则无法使用",
        dsr=CPRADSRMechanism(has_web_form=True, has_email=True, supports_opt_out=False,
                             supports_limit_spi=False, is_easy_to_find=False),
        dsr_text="DSR入口隐藏在设置深层",
        opt_out_text="向广告商和保险公司共享健康衍生数据，无opt-out",
        data_items=[
            CPRADataItem(category="health_data", is_sensitive=True, spi_type="health_data",
                         purpose="insurance_recommendation", recipient_type="third_party",
                         sale_or_share=True),
            CPRADataItem(category="biometric_information", is_sensitive=True,
                         spi_type="biometric_data"),
            CPRADataItem(category="precise_geolocation", is_sensitive=True,
                         spi_type="geolocation", recipient_type="advertising_network",
                         sale_or_share=True),
        ],
        vendors=[
            CPRAVendorInfo(name="HealthSupps", vendor_type="third_party",
                           receives_pi=True, receives_spi=True, sale_or_share=True,
                           dpa_honors_opt_out=False),
            CPRAVendorInfo(name="QuickInsure", vendor_type="third_party",
                           receives_pi=True, receives_spi=True, sale_or_share=True),
        ],
        consent_ui=CPRAConsentUI(bundled_consent=True, preselected_consent=True,
                                 confusing_language=True),
    )
    hits = _check_hits(gaps, _CASE_3_EXPECTED)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 3 hits: {hit_count}/{len(_CASE_3_EXPECTED)}")
    for pat, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pat}")
    assert hit_count >= 5, f"Expected ≥5 hits, got {hit_count}"
