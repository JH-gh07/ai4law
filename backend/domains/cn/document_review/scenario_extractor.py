"""ScenarioExtractor — extract business facts and scenario context from documents."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from backend.schemas.review import (
    DocumentClassification,
    DocumentType,
    ReviewScenarioContext,
)
from backend.domains.cn.document_review.scenario_graph_builder import (
    ScenarioGraphBuilder,
)

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

# ── Country / region detection ──────────────────────────────────────────

_COUNTRY_PATTERNS = [
    (r"(?:服务器|数据中心|机房|存储).{0,10}(新加坡|香港|美国|日本|韩国|英国|德国|法国|澳大利亚|印度|马来西亚|泰国|越南|印尼|菲律宾|台湾|澳门)", "服务器地点"),
    (r"(?:位于|部署在|设在).{0,10}(新加坡|香港|美国|日本|韩国|英国|德国|法国|澳大利亚)", "部署地点"),
    (r"(?:跨境|传出|出境|传输.{0,5}(?:至|到|给)).{0,10}(新加坡|香港|美国|日本|韩国|英国|德国|法国|澳大利亚)", "数据出境"),
    (r"(新加坡|香港|美国|日本|韩国|英国|德国|法国|澳大利亚).{0,8}(?:数据中心|服务器|机房|节点)", "服务器地点"),
]

# ── Data category patterns ──────────────────────────────────────────────

_DATA_CATEGORY_PATTERNS = [
    (r"(?:消费记录|购买记录|订单信息|交易记录)", "消费数据"),
    (r"(?:门禁记录|考勤记录|出入记录|访客记录)", "门禁考勤"),
    (r"(?:位置|行踪|轨迹|定位|GPS|经纬度)", "行踪轨迹"),
    (r"(?:图书.*借阅|借阅记录|阅读记录)", "借阅记录"),
    (r"(?:支付|银行卡|账号.*信息|金融|财产)", "金融信息"),
    (r"(?:生物识别|指纹|人脸|声纹|虹膜|步态)", "生物识别信息"),
    (r"(?:健康|医疗|病历|就诊|体检)", "健康医疗信息"),
    (r"(?:身份证|护照|驾驶证|社保)", "身份信息"),
    (r"(?:通讯录|通话记录|短信|邮件)", "通信信息"),
    (r"(?:上网记录|浏览记录|搜索记录|Cookie)", "网络行为"),
    (r"(?:教育|学历|学校|成绩)", "教育信息"),
    (r"(?:未成年人|儿童|学生.*信息|14岁)", "未成年人信息"),
]

# ── Sensitive data patterns ─────────────────────────────────────────────

_SENSITIVE_DATA_PATTERNS = [
    (r"生物识别|指纹|人脸|声纹|虹膜", "生物识别信息"),
    (r"行踪轨迹|精确定位|实时位置", "行踪轨迹"),
    (r"健康.*信息|医疗.*信息|病历|就诊", "医疗健康信息"),
    (r"金融.*账户|银行.*账户|支付.*信息|财产.*信息", "金融账户信息"),
    (r"未.*14|十四.*周.*岁|未成年.*信息|儿童.*信息", "未成年人信息"),
    (r"身份证.*号码|身份证号|护照.*号码", "身份证件信息"),
    (r"宗教信仰|民族|种族|政治.*观点|性.*取向", "敏感个人信息"),
]

# ── Cross-border indicators ─────────────────────────────────────────────

_CROSS_BORDER_PATTERNS = [
    r"(?:境外|跨境|数据出境|传输.*境外|出境.*数据|域外)",
    r"(?:服务器|数据|信息).{0,15}(?:新加坡|香港|美国|境外|海外|日本|韩国|英国|德国|法国|澳大利亚)",
    r"(?:SCC|标准合同|安全评估|保护认证).{0,15}(?:数据传输|数据出境)",
    r"(?:数据.*存储|备份).{0,15}(?:境外|海外|新加坡|香港|美国)",
    r"(?:远程.*访问|运维).{0,15}(?:境外|海外)",
]

# ── Company name / entity patterns ──────────────────────────────────────

_COMPANY_PATTERNS = [
    r"甲方[：:]\s*(.+?)(?:有限公司|股份公司|集团|公司)",
    r"(?:公司[名称称]?|企业[名称称]?|个人信息处理者)[：:]\s*(.+?)(?:有限公司|股份公司|集团|公司)",
    r"(.+?(?:有限公司|股份公司|集团|公司))\s*(?:与|和)\s*(.+?(?:有限公司|股份公司|集团|公司))",
]

# ── Processing purpose patterns ─────────────────────────────────────────

_PURPOSE_PATTERNS = [
    r"(?:处理目的|出境目的|使用目的|目的)[：:]\s*(.+?)(?:[。；\n]|$)",
    r"(?:用于|用于以下目的|为了)\s*(.+?)(?:[。；\n]|$)",
]

# ── Uncertain fact patterns ─────────────────────────────────────────────

_UNCERTAINTY_PATTERNS = [
    (r"(?:如果|若|如|假如|假设|倘若).{0,30}(?:涉及|包含|含有|传输|出境|处理.*敏感)", "条件性出境/敏感数据"),
    (r"(?:可能|或将|预计|计划).{0,30}(?:涉及|传输|出境|共享|提供.*第三方)", "可能涉及传输/共享"),
    (r"(?:详见|参见|参考|另行|另见|见).{0,20}(?:附件|附录|协议|合同|政策)", "引用外部文件"),
    (r"(?:不?确定|未明确|待确认|尚不确定|待定)", "未确认信息"),
]


class ScenarioExtractor:
    """Extract business scenario context from document text.

    Merges user-provided context with auto-extracted facts.
    Uses regex heuristics as primary method, with LLM for deep extraction.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client
        self.graph_builder = ScenarioGraphBuilder(llm_client=llm_client)

    def extract(
        self,
        text: str,
        user_context: ReviewScenarioContext | None = None,
        document_classification: DocumentClassification | None = None,
    ) -> ReviewScenarioContext:
        """Extract scenario context, merging user input with auto-extraction."""
        base = user_context or ReviewScenarioContext()

        # Fill in document type from classification if not provided
        if base.auto_document_type is None and document_classification is not None:
            base.auto_document_type = document_classification.document_type

        # Auto-extract from text
        extracted = self._extract_from_text(text)

        # Merge: user context takes priority over auto-extracted
        if not base.company_name:
            base.company_name = extracted.get("company_name")
        if not base.receiver_country:
            base.receiver_country = extracted.get("receiver_country")
        if not base.transfer_purpose:
            base.transfer_purpose = extracted.get("transfer_purpose")

        # Auto-detected facts are always added
        base.auto_extracted_facts = {
            k: v for k, v in extracted.items()
            if v and k not in ("company_name", "receiver_country", "transfer_purpose")
        }

        # Cross-border indicators
        cb_indicators = self._extract_cross_border_indicators(text)
        existing = set(base.cross_border_indicators)
        for ind in cb_indicators:
            if ind not in existing:
                base.cross_border_indicators.append(ind)

        # Uncertain facts
        base.uncertain_facts = self._extract_uncertain_facts(text)

        # ── Scenario graph (structured actor‑data flow graph) ──
        graph = self.graph_builder.build(text)
        # Inject graph facts into auto_extracted_facts for downstream use
        if graph.actors:
            base.auto_extracted_facts["scenario_actors"] = str(
                [a["name"] for a in graph.actors]
            )
        if graph.data_flows:
            base.auto_extracted_facts["scenario_data_flows"] = str(
                [f"{f['from_actor']}→{f['to_actor_or_location']}" for f in graph.data_flows[:3]]
            )
        if graph.legal_grounds:
            base.auto_extracted_facts["scenario_legal_grounds"] = "、".join(graph.legal_grounds)
        # Merge cross-border indicators from graph
        for ind in graph.cross_border_indicators:
            if ind not in base.cross_border_indicators:
                base.cross_border_indicators.append(ind)
        # Merge uncertain facts from graph
        for f in graph.uncertain_facts:
            if f not in base.uncertain_facts:
                base.uncertain_facts.append(f)

        return base

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_from_text(self, text: str) -> dict[str, str]:
        """Extract structured facts from text using regex heuristics."""
        result: dict[str, str] = {}
        text_sample = text[:6000]

        # Company name
        for pattern in _COMPANY_PATTERNS:
            m = re.search(pattern, text_sample)
            if m:
                result["company_name"] = m.group(1).strip()
                break

        # Data categories
        categories = []
        for pattern, label in _DATA_CATEGORY_PATTERNS:
            if re.search(pattern, text_sample):
                categories.append(label)
        if categories:
            result["data_categories"] = "、".join(categories)

        # Sensitive data
        sensitive = []
        for pattern, label in _SENSITIVE_DATA_PATTERNS:
            if re.search(pattern, text_sample):
                sensitive.append(label)
        if sensitive:
            result["sensitive_data_types"] = "、".join(sensitive)

        # Cross-border indicators
        for pattern in _CROSS_BORDER_PATTERNS[:2]:
            m = re.search(pattern, text_sample)
            if m:
                result["cross_border_indicator"] = m.group(0)[:80]
                break

        # Country detection
        for pattern, label in _COUNTRY_PATTERNS:
            m = re.search(pattern, text_sample)
            if m:
                result["receiver_country"] = m.group(1)
                break

        # Processing purpose
        for pattern in _PURPOSE_PATTERNS:
            m = re.search(pattern, text_sample)
            if m:
                purpose = m.group(1).strip()[:120]
                result["transfer_purpose"] = purpose
                break

        return result

    @staticmethod
    def _extract_cross_border_indicators(text: str) -> list[str]:
        """Find cross-border transfer indicators."""
        indicators = []
        text_sample = text[:6000]
        for pattern in _CROSS_BORDER_PATTERNS:
            for m in re.finditer(pattern, text_sample, re.IGNORECASE):
                indicator = m.group(0)[:100]
                if indicator not in indicators:
                    indicators.append(indicator)
        return indicators[:8]

    @staticmethod
    def _extract_uncertain_facts(text: str) -> list[str]:
        """Detect facts that need user confirmation."""
        uncertain = []
        text_sample = text[:6000]
        for pattern, label in _UNCERTAINTY_PATTERNS:
            if re.search(pattern, text_sample, re.IGNORECASE):
                uncertain.append(label)
        return list(dict.fromkeys(uncertain))  # dedup, preserve order
