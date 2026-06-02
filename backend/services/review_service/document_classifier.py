"""DocumentClassifier — identify document type from text content."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from backend.schemas.review import DocumentClassification, DocumentType

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

# ── Keyword heuristics per document type ─────────────────────────────────

_PRIVACY_POLICY_SIGNALS = [
    "隐私政策", "隐私权政策", "个人信息保护政策", "privacy policy", "privacy notice",
    "个人信息收集使用", "信息收集与使用", "收集.*个人信息", "信息处理规则",
    "第三方分享", "Cookie", "SDK", "撤回同意",
]

_SCC_SIGNALS = [
    "标准合同", "个人信息出境标准合同", "standard contractual clauses",
    "数据出境合同", "跨境提供", "境外接收方", "附录一", "附录二",
    "个人信息保护影响评估", "安全评估申报", "数据出境安全评估",
]

_DPA_SIGNALS = [
    "数据处理协议", "委托处理协议", "data processing agreement", "DPA",
    "受托处理", "委托方", "受托方", "数据处理者.*受托",
    "数据安全保密协议", "保密协议.*数据",
]

_OTHER_SIGNALS = [
    "内部管理制度", "数据安全管理制度", "操作规程", "应急响应预案",
    "网络安全等级保护", "等保", "incident response plan",
]

_EU_JURISDICTION_SIGNALS = [
    "gdpr", "edpb", "eea", "european union", "binding corporate rules",
    "bcr", "schrems", "article 46", "supplementary measures",
]

_US_JURISDICTION_SIGNALS = [
    "cpra", "ccpa", "california", "privacy notice", "vendor agreement",
    "data brokerage", "eo 14117", "doj rule", "sensitive personal information",
]

_CN_JURISDICTION_SIGNALS = [
    "个人信息保护法", "数据安全法", "网络安全法", "标准合同", "数据出境",
    "个人信息出境", "国家网信部门", "重要数据",
]


class DocumentClassifier:
    """Classify document type from text content, filename, and optional user hint.

    Strategy (in priority order):
    1. User-provided document_type, if high-confidence text match → confirm
    2. Keyword heuristics (Chinese + English signals)
    3. LLM lightweight classification for ambiguous cases
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def classify(
        self,
        text: str,
        user_document_type: str | None = None,
        filename: str | None = None,
    ) -> DocumentClassification:
        """Classify *text* into a DocumentType with confidence and evidence."""
        # 1. Try user hint first
        if user_document_type:
            conf = self._confidence_for(text, user_document_type)
            if conf >= 0.5:
                detected_jurisdiction = self._detect_jurisdiction(text, filename, user_document_type)
                return self._build_result(
                    user_document_type, conf,
                    [f"用户选择: {user_document_type}"],
                    detected_jurisdiction=detected_jurisdiction,
                )

        # 2. Keyword heuristics
        scores = self._score_all(text, filename)
        best_type, best_score = max(scores.items(), key=lambda kv: kv[1])

        if best_score >= 3:
            evidence = self._list_evidence(text, best_type)
            return self._build_result(
                best_type,
                min(0.5 + best_score * 0.08, 0.95),
                evidence,
                detected_jurisdiction=self._detect_jurisdiction(text, filename, best_type),
            )

        # 3. LLM fallback for ambiguous cases
        if self.llm_client and self.llm_client.enabled and len(text) >= 200:
            llm_type = self._classify_with_llm(text, filename)
            if llm_type:
                return self._build_result(
                    llm_type,
                    0.6,
                    ["LLM 辅助判断"],
                    detected_jurisdiction=self._detect_jurisdiction(text, filename, llm_type),
                )

        # 4. Default
        if best_score > 0:
            return self._build_result(
                best_type,
                0.4,
                ["低置信度关键词匹配"],
                detected_jurisdiction=self._detect_jurisdiction(text, filename, best_type),
            )
        return DocumentClassification(
            document_type=DocumentType.OTHER,
            confidence=0.3,
            evidence=["无法确定文档类型"],
            detected_jurisdiction=self._detect_jurisdiction(text, filename, None),
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_all(self, text: str, filename: str | None) -> dict[str, int]:
        """Score each document type against the text."""
        text_lower = text.lower()[:6000]
        fname = (filename or "").lower()
        combined = text_lower + " " + fname

        return {
            DocumentType.PRIVACY_POLICY.value: self._count_signals(combined, _PRIVACY_POLICY_SIGNALS),
            DocumentType.SCC_CONTRACT.value: self._count_signals(combined, _SCC_SIGNALS),
            DocumentType.DPA.value: self._count_signals(combined, _DPA_SIGNALS),
            DocumentType.OTHER.value: self._count_signals(combined, _OTHER_SIGNALS),
        }

    @staticmethod
    def _count_signals(text: str, signals: list[str]) -> int:
        """Count how many signal patterns match."""
        count = 0
        for signal in signals:
            try:
                if re.search(signal, text, re.IGNORECASE):
                    count += 1
            except re.error:
                if signal.lower() in text:
                    count += 1
        return count

    @staticmethod
    def _confidence_for(text: str, doc_type: str) -> float:
        """Check if user-specified type matches text content."""
        signal_map = {
            DocumentType.PRIVACY_POLICY.value: _PRIVACY_POLICY_SIGNALS,
            DocumentType.SCC_CONTRACT.value: _SCC_SIGNALS,
            DocumentType.DPA.value: _DPA_SIGNALS,
            DocumentType.OTHER.value: _OTHER_SIGNALS,
        }
        signals = signal_map.get(doc_type, [])
        if not signals:
            return 0.6
        count = DocumentClassifier._count_signals(text[:4000].lower(), signals)
        if count == 0:
            return 0.4
        if count >= 3:
            return 0.9
        return 0.65

    # ------------------------------------------------------------------
    # Evidence gathering
    # ------------------------------------------------------------------

    @staticmethod
    def _list_evidence(text: str, doc_type: str) -> list[str]:
        """List matched signals as evidence."""
        signal_map = {
            DocumentType.PRIVACY_POLICY.value: _PRIVACY_POLICY_SIGNALS,
            DocumentType.SCC_CONTRACT.value: _SCC_SIGNALS,
            DocumentType.DPA.value: _DPA_SIGNALS,
            DocumentType.OTHER.value: _OTHER_SIGNALS,
        }
        signals = signal_map.get(doc_type, [])
        evidence: list[str] = []
        text_lower = text[:4000].lower()
        for signal in signals[:15]:
            try:
                if re.search(signal, text_lower, re.IGNORECASE):
                    evidence.append(f"匹配关键词: {signal}")
            except re.error:
                if signal.lower() in text_lower:
                    evidence.append(f"匹配关键词: {signal}")
        return evidence[:8] or ["关键词匹配"]

    # ------------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------------

    @staticmethod
    def _build_result(
        doc_type: str,
        confidence: float,
        evidence: list[str],
        detected_jurisdiction: str,
    ) -> DocumentClassification:
        try:
            dt = DocumentType(doc_type)
        except ValueError:
            dt = DocumentType.OTHER
        return DocumentClassification(
            document_type=dt,
            confidence=round(confidence, 2),
            evidence=evidence,
            detected_jurisdiction=detected_jurisdiction,
        )

    @staticmethod
    def _detect_jurisdiction(
        text: str,
        filename: str | None,
        doc_type: str | None,
    ) -> str:
        combined = f"{text[:6000]} {(filename or '')} {(doc_type or '')}".lower()
        if any(signal in combined for signal in _CN_JURISDICTION_SIGNALS):
            return "cn"
        if any(signal in combined for signal in _EU_JURISDICTION_SIGNALS):
            return "eu"
        if any(signal in combined for signal in _US_JURISDICTION_SIGNALS):
            return "us"
        if any("\u4e00" <= char <= "\u9fff" for char in combined):
            return "cn"
        return "eu" if doc_type == DocumentType.SCC_CONTRACT.value else "us"

    # ------------------------------------------------------------------
    # LLM classification (lightweight)
    # ------------------------------------------------------------------

    def _classify_with_llm(self, text: str, filename: str | None) -> str | None:
        if not self.llm_client or not self.llm_client.enabled:
            return None

        prompt = f"""分析以下文档片段，判断其文档类型。

文档名: {filename or 'unknown'}
片段:
{text[:500]}

请仅输出以下类型之一: privacy_policy, scc_contract, dpa, other

其中:
- privacy_policy = 隐私政策
- scc_contract = 个人信息出境标准合同
- dpa = 数据处理协议/委托处理协议
- other = 其他类型"""

        try:
            raw = self.llm_client.chat(
                system="你是一名中国数据合规专家。仅输出文档类型，不含其他文字。",
                user=prompt,
                temperature=0.0,
                max_tokens=20,
            )
            result = raw.strip().lower()
            for candidate in ["privacy_policy", "scc_contract", "dpa", "other"]:
                if candidate in result:
                    return candidate
            return None
        except Exception as exc:
            logger.warning("LLM document classification failed: %s", exc)
            return None
