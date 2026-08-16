"""CitationRelevanceChecker — validate that citations actually support the issues."""

from __future__ import annotations

import re

from backend.schemas.review import ReviewIssue, StructuredCitation

# Corrupted locators that leaked from scripts/fix_cn_law_001_duplicates.py into
# ``article_ref`` ("处罚-17-1", "第X条-处罚-1", "第X条-ext-1"). They are never a
# legal article number and must fail relevance / be surfaced as a defect.
_INVALID_ARTICLE_PATTERN = re.compile(r"(处罚\s*[-—])|(-处罚)|(-ext-)")


class CitationRelevanceChecker:
    """Check citation relevance to ensure regulatory references match issue types.

    Validates:
    1. Issue type vs citation type (e.g., cross‑border issue should cite PiPL Art.38,
       not unrelated articles)
    2. Keyword overlap between issue title/description and citation snippet
    3. Binding force classification (mandatory law, regulation, standard, guideline)
    4. Mismatch detection (cited law doesn't actually address the problem)
    """

    # ── Issue‑type → expected citation source keywords ──────────────────
    _RELEVANCE_MAP: dict[str, list[str]] = {
        "CROSS_BORDER_TRANSFER": ["出境", "跨境", "境外", "第38条", "安全评估办法", "标准合同办法"],
        "CONSENT_NOTICE": ["第39条", "告知", "同意", "境外接收方"],
        "SECURITY_MEASURES": ["第38条", "安全措施", "数据安全法", "保护"],
        "SENSITIVE_PI": ["第28条", "第29条", "敏感", "单独同意"],
        "MINOR_PROTECTION": ["第31条", "未成年人", "儿童", "14"],
        "LIABILITY": ["合同编", "民法典", "争议解决", "管辖"],
        "ONWARD_TRANSFER": ["第38条", "再转移", "转委托", "标准合同办法"],
        "RIGHTS_REQUEST": ["第44条", "第45条", "第46条", "第47条", "查阅", "删除"],
        "RETENTION_DELETION": ["第19条", "第47条", "保存期限", "删除"],
        "THIRD_PARTY_SHARING": ["第23条", "第三方", "共享", "提供"],
        "ENTRUSTED_PROCESSING": ["第21条", "委托", "受托"],
        "DATA_PROCESSING_SCOPE": ["第6条", "第13条", "第17条", "处理目的", "范围"],
        "DATA_BREACH_NOTIFICATION": ["第57条", "泄露", "通知"],
        "INCIDENT_RESPONSE": ["第57条", "安全事件", "数据安全法", "应急"],
    }

    # ── Binding force classification ────────────────────────────────────
    _BINDING_KEYWORDS: dict[str, str] = {
        "法": "mandatory_law",
        "条例": "regulation",
        "办法": "regulation",
        "规定": "regulation",
        "标准": "standard",
        "GB/T": "standard",
        "指南": "guideline",
        "指引": "guideline",
        "规范": "standard",
    }

    def check(self, issue: ReviewIssue) -> dict:
        """Check a single issue's citation relevance.

        Returns a dict with relevance assessment.
        """
        result: dict = {
            "issue_id": issue.issue_id,
            "relevant": True,
            "relevance_score": 0.5,
            "issues": [],
        }

        if not issue.structured_citations and not issue.citation_sources:
            result["relevant"] = False
            result["relevance_score"] = 0.0
            result["issues"].append("缺少法规引用")
            return result

        # Format gate: a corrupted locator ("处罚-17-1" / "-ext-1") is always a
        # defect, regardless of keyword relevance. Never let it pass silently.
        for sc in issue.structured_citations:
            if self._is_corrupted_article(sc.article):
                result["relevant"] = False
                result["relevance_score"] = min(result["relevance_score"], 0.0)
                result["issues"].append(
                    f"引用「{sc.source_title}」包含非法条号「{sc.article}」"
                )
        for raw in issue.citation_sources:
            if self._is_corrupted_article(raw):
                result["relevant"] = False
                result["relevance_score"] = min(result["relevance_score"], 0.0)
                result["issues"].append(f"引用包含非法条号「{raw}」")

        ct = issue.clause_type.value if issue.clause_type else "OTHER"
        expected = self._RELEVANCE_MAP.get(ct, [])
        scores: list[float] = []

        for sc in issue.structured_citations:
            if self._is_corrupted_article(sc.article):
                continue
            score = self._score_citation(sc, expected, issue)
            scores.append(score)

            # Classify binding force
            force = self._classify_binding(sc.source_title)
            if score < 0.3:
                result["issues"].append(
                    f"引用「{sc.source_title}」{sc.article}与问题类型({ct})关联度低"
                )
            result.setdefault("citations_detail", []).append({
                "citation_id": sc.source_id,
                "source": f"{sc.source_title}{sc.article}",
                "relevance": round(score, 2),
                "binding_force": force,
            })

        if scores:
            result["relevance_score"] = round(sum(scores) / len(scores), 2)
        if result["relevance_score"] < 0.4:
            result["relevant"] = False

        # Empty-gap fix: ``relevant=False`` must always carry a human-readable
        # reason. The old code could set relevant=False with issues=[] (when every
        # citation scored >= 0.3 individually but the average dropped below 0.4),
        # which rendered a blank "引用相关性警告：".
        if not result["relevant"] and not result["issues"]:
            result["issues"].append(
                f"引用与问题类型({ct})整体相关性不足（平均 {result['relevance_score']}）"
            )

        return result

    @staticmethod
    def _is_corrupted_article(text: str) -> bool:
        """True if *text* carries a corrupted article locator suffix."""
        if not text:
            return False
        return bool(_INVALID_ARTICLE_PATTERN.search(text))

    def _score_citation(
        self, sc: StructuredCitation, expected: list[str], issue: ReviewIssue,
    ) -> float:
        """Score a single citation's relevance (0–1)."""
        score = 0.3  # base score

        combined = f"{sc.source_title}{sc.article}{sc.snippet}"
        # Keyword match against expected terms
        matches = sum(1 for kw in expected if kw in combined)
        if matches > 0:
            score += min(matches * 0.15, 0.45)

        # Check if citation keywords overlap with issue keywords
        issue_text = f"{issue.title}{issue.risk_analysis}"
        issue_kw = set(issue_text)
        citation_kw = set(combined[:200])
        overlap = len(issue_kw & citation_kw) / max(len(issue_kw | citation_kw), 1)
        score += overlap * 0.2

        return min(score, 1.0)

    @classmethod
    def _classify_binding(cls, source_title: str) -> str:
        """Classify the binding force of a citation by its source title."""
        for keyword, force in cls._BINDING_KEYWORDS.items():
            if keyword in source_title:
                return force
        return "reference"
