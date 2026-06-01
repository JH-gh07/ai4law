"""CrossDocConsistencyChecker — detect inconsistencies across multiple documents."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.schemas.review import ClassifiedClause, ReviewIssue

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class DocumentWithClauses:
    """A document with its classified clauses for cross‑document comparison."""

    file_id: str
    filename: str
    document_type: str
    clauses: list[ClassifiedClause] = field(default_factory=list)
    issues: list[ReviewIssue] = field(default_factory=list)


class CrossDocConsistencyChecker:
    """Check for consistency across multiple uploaded documents.

    Detects:
    - Contradictory retention periods
    - Contradictory security measure descriptions
    - Jurisdiction / dispute resolution conflicts
    - Cross‑border disclosure contradictions (privacy policy says no, SCC says yes)
    - Third‑party sharing list gaps
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def check(self, documents: list[DocumentWithClauses]) -> list[str]:
        """Check cross‑document consistency, returning warning messages."""
        if len(documents) < 2:
            return []

        warnings: list[str] = []

        # 1. Extract key fields from each document
        profiles = [self._extract_profile(doc) for doc in documents]

        # 2. Cross‑border contradiction: privacy policy vs contract
        pp = next((p for p in profiles if p.get("doc_type") == "privacy_policy"), None)
        scc = next((p for p in profiles if p.get("doc_type") == "scc_contract"), None)
        dpa = next((p for p in profiles if p.get("doc_type") == "dpa"), None)

        if pp and (scc or dpa):
            contract = scc or dpa
            # If privacy policy says "we don't transfer data overseas" but SCC/DPA exists
            pp_cb = pp.get("cross_border_mentioned", "unknown")
            if pp_cb == "false" and contract:
                warnings.append(
                    f"隐私政策（{pp['filename']}）未提及数据出境，"
                    f"但{contract['filename']}涉及数据出境传输。"
                    "建议在隐私政策中同步披露数据出境情况。"
                )

        # 3. Retention period consistency
        retention_periods = {}
        for p in profiles:
            rp = p.get("retention_period")
            if rp:
                retention_periods[p["filename"]] = rp
        if len(retention_periods) >= 2:
            periods = set(retention_periods.values())
            if len(periods) > 1:
                warnings.append(
                    f"不同文档中的保存期限约定不一致: "
                    + "; ".join(f"{fn}: {rp}" for fn, rp in retention_periods.items())
                )

        # 4. Jurisdiction conflicts
        jurisdictions = {}
        for p in profiles:
            jur = p.get("dispute_jurisdiction")
            if jur:
                jurisdictions[p["filename"]] = jur
        if len(jurisdictions) >= 2:
            j_set = set(jurisdictions.values())
            if len(j_set) > 1:
                warnings.append(
                    f"不同文档中的争议解决管辖约定不一致: "
                    + "; ".join(f"{fn}: {jur}" for fn, jur in jurisdictions.items())
                )

        # 5. LLM deep check if available
        if self.llm_client and self.llm_client.enabled and len(warnings) < 5:
            llm_warnings = self._llm_consistency_check(documents)
            if llm_warnings:
                warnings.extend(llm_warnings)

        return list(dict.fromkeys(warnings))  # dedup preserve order

    # ------------------------------------------------------------------
    # Profile extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_profile(doc: DocumentWithClauses) -> dict[str, str]:
        """Extract key comparison fields from a document."""
        combined_text = " ".join(c.text for c in doc.clauses)[:4000]
        profile: dict[str, str] = {
            "filename": doc.filename,
            "doc_type": doc.document_type,
        }

        # Cross‑border mention
        if any(kw in combined_text for kw in ["出境", "跨境", "境外", "overseas", "cross-border"]):
            profile["cross_border_mentioned"] = "true"
        else:
            profile["cross_border_mentioned"] = "false"

        # Retention period
        import re
        m = re.search(
            r"(?:保存期限|存储期限|保留.*期限|保存.{0,5}期).{0,20}?(\d+[年个月天]|[0-9]{4}[-/][0-9]{1,2})",
            combined_text,
        )
        if m:
            profile["retention_period"] = m.group(0)[:60]

        # Jurisdiction
        m = re.search(
            r"(?:管辖|仲裁|诉讼|争议解决).{0,20}?(中国|香港|新加坡|美国|英国|内地)",
            combined_text,
        )
        if m:
            profile["dispute_jurisdiction"] = m.group(1)

        return profile

    # ------------------------------------------------------------------
    # LLM‑based deep check
    # ------------------------------------------------------------------

    def _llm_consistency_check(
        self, documents: list[DocumentWithClauses],
    ) -> list[str]:
        """Use LLM to detect subtle cross‑document inconsistencies."""
        if not self.llm_client or not self.llm_client.enabled:
            return []

        docs_summary = []
        for doc in documents:
            issues_text = "、".join(i.title[:60] for i in doc.issues[:5])
            docs_summary.append(
                f"{doc.filename} ({doc.document_type}): "
                f"{len(doc.clauses)}个条款, 发现{len(doc.issues)}个问题"
                + (f", 如: {issues_text}" if issues_text else "")
            )

        prompt = (
            "以下是同一企业提交的多份文档的审查摘要。"
            "请检查是否存在跨文档的矛盾或不一致。仅输出发现的不一致项，无问题则输出'无'。\n\n"
            + "\n".join(docs_summary)
        )

        try:
            raw = self.llm_client.chat(
                system="你是一名数据合规审查专家。分析跨文档一致性。",
                user=prompt,
                temperature=0.1,
                max_tokens=300,
            )
            if raw.strip() == "无":
                return []
            # Split by newlines or numbered items
            lines = [l.strip("- 123456789.、") for l in raw.split("\n") if l.strip() and l.strip() != "无"]
            return [l for l in lines if len(l) > 20]
        except Exception as exc:
            logger.warning("LLM cross‑doc check failed: %s", exc)
            return []
