r"""Regression test matrix for document review pipeline.

Encodes the expected compliance issues for 3 standard test cases
to verify the enhanced review pipeline hits the correct findings.
"""

from __future__ import annotations

from backend.services.review_service.clause_classifier import ClauseClassifier
from backend.services.review_service.clause_segmenter import ClauseSegmenter
from backend.services.review_service.document_classifier import DocumentClassifier
from backend.services.review_service.missing_item_checker import MissingItemChecker
from backend.services.review_service.rag_provider import LocalRegulationKnowledgeBase
from backend.services.review_service.clause_reviewer import ClauseReviewer
from backend.services.review_service.review_aggregator import ReviewAggregator
from backend.services.review_service.risk_scorer import RiskScorer
from backend.services.review_service.rulebook_loader import RulebookLoader
from backend.services.review_service.specialized_reviewers import (
    DataSecurityAgreementReviewer,
    DpaReviewer,
    PrivacyPolicyReviewer,
    SccContractReviewer,
)


class _DisabledLLM:
    enabled = False


def _make_reviewer(rulebook):
    kb = LocalRegulationKnowledgeBase(legal_api_service=None)
    return ClauseReviewer(
        kb,
        llm_client=_DisabledLLM(),
        rulebook_loader=rulebook,
        specialized_reviewers={
            "privacy_policy": PrivacyPolicyReviewer(rulebook_loader=rulebook),
            "scc_contract": SccContractReviewer(rulebook_loader=rulebook),
            "dpa": DpaReviewer(rulebook_loader=rulebook),
            "other": DataSecurityAgreementReviewer(rulebook_loader=rulebook),
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# Test Case 1: 数据安全及保密协议
# ═══════════════════════════════════════════════════════════════════════

_TEST_CASE_1 = """数据安全及保密协议

甲方：智选电商有限公司
乙方：数海科技有限公司

第一条 保密范围
本协议所指保密信息包括甲方提供给乙方的用户消费记录、门禁出入记录和图书借阅记录。

第二条 数据处理
乙方可在其位于新加坡的服务器上处理前述数据，用于数据分析与运维支持。

第三条 安全措施
乙方应采取加密措施保护数据安全；发生数据安全事件时，乙方应及时通知甲方。

第四条 违约责任
任何一方违反本协议约定的，应当承担相应的违约责任。
因本协议产生的争议，由乙方所在地有管辖权的法院管辖。

第五条 其他
本协议自双方签署之日起生效，有效期为三年。
"""

_TEST_CASE_1_EXPECTED_ISSUES = [
    "处理地点|存储地点|数据处理地点",  # 未明确数据存储和处理地点
    "跨境|境外|传输",  # 隐含出境风险（新加坡服务器）
    "安全事件.*时限|安全事件.*小时|通知.*时限",  # 安全事件通知时限模糊
    "区分.*个人信息|个人信息.*敏感.*重要数据|不同级别.*数据",  # 未区分数据类别
    "审计|检查权|核查",  # 缺少审计监督权
    "管辖.*不利|管辖.*委托方|境外.*管辖|法院.*管辖",  # 管辖权对委托方不利
]


# ═══════════════════════════════════════════════════════════════════════
# Test Case 2: 数据委托处理服务合同
# ═══════════════════════════════════════════════════════════════════════

_TEST_CASE_2 = """数据委托处理服务合同

委托方（甲方）：某某科技有限公司
受托方（乙方）：云端数据服务有限公司

一、委托内容
甲方委托乙方处理用户行为数据，包括但不限于设备信息、浏览记录和购买记录。

二、数据处理方式
乙方根据甲方指示进行数据分析、存储和运维。乙方可利用其香港数据中心存储和处理数据。

三、合规责任
乙方作为受托方，应负责依照中国法律法规完成数据出境安全评估申报、订立个人信息出境标准合同等合规手续。

四、数据安全
乙方应采取必要的技术和组织措施保障数据安全，包括访问控制和加密存储。

五、数据保存与销毁
委托关系终止后，乙方应在五年内完成数据销毁。

六、其他约定
本合同中如有与标准合同正文不一致之处，以本合同为准。
"""

_TEST_CASE_2_EXPECTED_ISSUES = [
    "合规责任|labor misalloc",  # 出境合规责任错配（推给受托方）
    "标准合同",  # 缺少标准合同关键条款
    "脱敏|匿名化",  # 脱敏/匿名化表述不清
    "删除.*证明|销毁.*证明|返还.*证明|删除.*返还",  # 未约定数据删除/返还的证明机制
    "合同.*优先|不一致.*为准|其他.*协议",  # 合同优先于标准合同正文
]


# ═══════════════════════════════════════════════════════════════════════
# Test Case 3: 个人信息出境标准合同
# ═══════════════════════════════════════════════════════════════════════

_TEST_CASE_3 = """个人信息出境标准合同

甲方（个人信息处理者）：某某科技有限公司
乙方（境外接收方）：Singapore Data Analytics Pte Ltd

附录一 个人信息出境说明

处理目的：根据业务需要处理个人信息
处理方式：自动化处理、存储与分析
出境个人信息规模：约500万人
个人信息种类：用户注册信息、消费记录、设备标识符
敏感个人信息种类：行踪轨迹信息
境外接收方：详见附件
传输方式：通过加密网络传输
保存期限：长期保存，直到业务不再需要
保存地点：新加坡数据中心、美国备份中心

附录二 双方约定的其他条款

1. 因本协议产生的争议，提交香港国际仲裁中心仲裁。
2. 乙方对甲方的赔偿责任总额不超过年度服务费的二倍。
3. 如本协议约定与双方签署的《主服务协议》不一致的，以《主服务协议》为准。
4. 乙方收到个人信息主体的权利请求后，可视情况暂缓处理。
"""

_TEST_CASE_3_EXPECTED_ISSUES = [
    "处理目的.*宽泛|处理目的.*模糊|漏洞|过宽",  # 处理目的过宽泛
    "保存期限.*过长|保存期限.*不当|期限.*长期",  # 保存期限不当
    "美国.*评估|第三国|境外.*法律.*影响|境外.*环境",  # 第三国保存地点缺乏评估
    "香港.*管辖|境外.*管辖|香港.*仲裁|境外.*法院|外国.*法院",  # 境外管辖冲突
    "暂缓|暂缓.*请求|暂缓.*处理|延迟.*权利",  # 暂缓主体权利请求
    "责任.*上限|赔偿.*上限|责任.*限额",  # 责任上限
    "主协议.*优先|其他.*协议.*优先|不一致.*为准",  # 其他协议优先
]


# ═══════════════════════════════════════════════════════════════════════
# Test runner
# ═══════════════════════════════════════════════════════════════════════

def _run_pipeline(text: str, doc_type: str):
    """Run the enhanced pipeline on text and return extracted issues."""
    rulebook = RulebookLoader()
    segmenter = ClauseSegmenter()
    classifier = ClauseClassifier(rulebook_loader=rulebook)
    doc_classifier = DocumentClassifier()
    checker = MissingItemChecker(rulebook_loader=rulebook)
    reviewer = _make_reviewer(rulebook)
    scorer = RiskScorer(rulebook_loader=rulebook)
    aggregator = ReviewAggregator(risk_scorer=scorer, rulebook_loader=rulebook)

    # Document classification
    dc = doc_classifier.classify(text, user_document_type=doc_type)

    # Segmentation
    clauses = segmenter.segment("f1", text)

    # Classification
    classified = [classifier.classify(c) for c in clauses]

    # Missing check
    missing = checker.check(classified, dc.document_type.value)

    # Review
    issues = []
    for clause in classified:
        issues.extend(reviewer.review(
            clause, use_llm=False,
            document_type=dc.document_type.value,
        ))

    # Aggregation
    agg = aggregator.aggregate(
        issues, missing_items=missing,
        classified_clauses=classified,
        document_type=dc.document_type.value,
    )

    return agg


def _check_hits(agg, expected_patterns: list[str]) -> dict:
    """Check whether expected issue patterns are found in the aggregated review."""
    all_text = agg.summary
    for issue in agg.issues:
        all_text += f" {issue.title} {issue.risk_analysis} {issue.recommendation}"
    for m in agg.missing_items:
        all_text += f" {m.title} {m.description}"

    import re
    results = {}
    for pattern in expected_patterns:
        hits = re.findall(pattern, all_text, re.IGNORECASE)
        results[pattern] = bool(hits)
    return results


def test_regression_case_1_data_security_agreement():
    """Verify expected issues for data security agreement."""
    agg = _run_pipeline(_TEST_CASE_1, "other")
    hits = _check_hits(agg, _TEST_CASE_1_EXPECTED_ISSUES)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 1 hits: {hit_count}/{len(_TEST_CASE_1_EXPECTED_ISSUES)}")
    for pattern, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pattern}")
    assert hit_count >= 4, f"Expected ≥4 hits, got {hit_count}"


def test_regression_case_2_dpa():
    """Verify expected issues for data processing agreement."""
    agg = _run_pipeline(_TEST_CASE_2, "dpa")
    hits = _check_hits(agg, _TEST_CASE_2_EXPECTED_ISSUES)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 2 hits: {hit_count}/{len(_TEST_CASE_2_EXPECTED_ISSUES)}")
    for pattern, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pattern}")
    assert hit_count >= 4, f"Expected ≥4 hits, got {hit_count}"


def test_regression_case_3_scc():
    """Verify expected issues for standard contractual clauses."""
    agg = _run_pipeline(_TEST_CASE_3, "scc_contract")
    hits = _check_hits(agg, _TEST_CASE_3_EXPECTED_ISSUES)
    hit_count = sum(1 for v in hits.values() if v)
    print(f"  Case 3 hits: {hit_count}/{len(_TEST_CASE_3_EXPECTED_ISSUES)}")
    for pattern, found in hits.items():
        print(f"    {'✓' if found else '✗'} {pattern}")
    assert hit_count >= 4, f"Expected ≥4 hits, got {hit_count}"
