"""CrossDocConsistencyChecker — detect inconsistencies across multiple documents.

9 comparison fields: cross_border_mentioned, retention_period, dispute_jurisdiction,
data_types, processing_purpose, third_party_sharing, rights_response_time,
incident_timeline, storage_location.

Comparison strategy: extract short, normalized key values per field, then
compare across documents via simple string equality.
"""

from __future__ import annotations

import logging
import re as _re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.schemas.review import ClassifiedClause, ReviewIssue

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class DocumentWithClauses:
    file_id: str
    filename: str
    document_type: str
    clauses: list[ClassifiedClause] = field(default_factory=list)
    issues: list[ReviewIssue] = field(default_factory=list)


class CrossDocConsistencyChecker:

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, documents: list[DocumentWithClauses]) -> list[str]:
        if len(documents) < 2:
            return []

        warnings: list[str] = []
        profiles = [self._extract_profile(doc) for doc in documents]

        pp = next((p for p in profiles if p.get("doc_type") == "privacy_policy"), None)
        scc = next((p for p in profiles if p.get("doc_type") == "scc_contract"), None)
        dpa = next((p for p in profiles if p.get("doc_type") == "dpa"), None)

        # 1. Cross-border contradiction
        if pp and (scc or dpa):
            contract = scc or dpa
            if pp.get("cross_border_mentioned") == "false":
                warnings.append(
                    f"Privacy policy ({pp['filename']}) does not mention cross-border "
                    f"transfer, but {contract['filename']} involves it."
                )

        # 2-9. Key-value field consistency (compare normalized short values)
        fields = [
            ("retention_period", "retention period"),
            ("dispute_jurisdiction", "dispute jurisdiction"),
            ("data_types", "data types"),
            ("processing_purpose", "processing purpose"),
            ("rights_response_time", "rights response time"),
            ("incident_timeline", "incident notification timeline"),
            ("storage_location", "storage location"),
        ]
        for field, label in fields:
            warnings.extend(self._check_key_value(profiles, field, label))

        # 10. Third-party sharing coverage (structural)
        if pp and (scc or dpa):
            contract = scc or dpa
            if pp.get("third_party_sharing") and not contract.get("third_party_sharing"):
                warnings.append(
                    f"Privacy policy ({pp['filename']}) mentions third-party sharing, "
                    f"but {contract['filename']} does not list the same recipients."
                )

        # 11. LLM deep check
        if self.llm_client and self.llm_client.enabled and len(warnings) < 5:
            llm_w = self._llm_consistency_check(documents)
            if llm_w:
                warnings.extend(llm_w)

        return list(dict.fromkeys(warnings))

    # ------------------------------------------------------------------
    # Key-value comparison
    # ------------------------------------------------------------------

    @staticmethod
    def _check_key_value(
        profiles: list[dict], field: str, label: str,
    ) -> list[str]:
        """Compare normalized key values across docs; flag if >=2 differ."""
        vals: dict[str, str] = {}
        for p in profiles:
            v = p.get(field)
            if v:
                vals[p["filename"]] = str(v)
        if len(vals) < 2:
            return []
        unique = set(vals.values())
        if len(unique) > 1:
            items = "; ".join(f"{fn}: {v}" for fn, v in vals.items())
            return [f"Inconsistent {label}: {items}"]
        return []

    # ------------------------------------------------------------------
    # Profile extraction (9 fields, each produces a normalized key value)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_profile(doc: DocumentWithClauses) -> dict[str, str]:
        t = " ".join(c.text for c in doc.clauses)[:6000]
        p: dict[str, str] = {"filename": doc.filename, "doc_type": doc.document_type}

        # 1. cross_border_mentioned
        p["cross_border_mentioned"] = (
            "true" if any(kw in t for kw in ["出境", "跨境", "境外", "overseas", "cross-border"])
            else "false"
        )

        # 2. retention_period → normalized number
        m = _re.search(r"(?:保存期限|存储期限|保留.{0,3}期限).{0,15}?(\d+)\s*([年个月天])", t)
        if m:
            p["retention_period"] = f"{m.group(1)}{m.group(2)}"

        # 3. dispute_jurisdiction → entity name only (tight proximity)
        m = _re.search(
            r"(北京|上海|深圳|广州|杭州|中国|香港|新加坡|美国|英国|内地|日本|韩国|德国|法国|澳大利亚)"
            r"(?:法院|仲裁|管辖)",
            t,
        )
        if m:
            p["dispute_jurisdiction"] = m.group(1)
        else:
            m = _re.search(
                r"(?:管辖|仲裁|诉讼|法院)"
                r"(北京|上海|深圳|广州|杭州|中国|香港|新加坡|美国|英国|内地|日本|韩国|德国|法国|澳大利亚)",
                t,
            )
            if m:
                p["dispute_jurisdiction"] = m.group(1)

        # 4. data_types → first 3 type keywords
        types: list[str] = []
        for kw in ["消费记录", "门禁", "行踪", "生物识别", "金融", "健康", "教育",
                     "浏览记录", "支付", "身份信息", "通信", "位置", "图书"]:
            if kw in t:
                types.append(kw)
        if types:
            p["data_types"] = "/".join(types[:5])

        # 5. processing_purpose → first 30 meaningful chars
        m = _re.search(r"(?:处理目的|出境目的|使用目的)[：:\s]*([^。；\n]{4,100})", t)
        if m:
            val = m.group(1).strip()
            # Normalize: keep first 30 chars
            p["processing_purpose"] = val[:30]

        # 6. third_party_sharing
        if any(kw in t for kw in ["第三方", "共享", "SDK", "合作伙伴", "转让", "公开披露"]):
            p["third_party_sharing"] = "detected"

        # 7. rights_response_time → number only
        m = _re.search(r"(\d+)\s*[日个天]\s*(?:内|之内|以内).{0,10}?(?:处理|响应|回复)", t)
        if m:
            p["rights_response_time"] = f"{m.group(1)}日"

        # 8. incident_timeline → number + unit
        m = _re.search(r"(\d+)\s*(小时|日|天).{0,10}?(?:通知|报告)", t)
        if m:
            p["incident_timeline"] = f"{m.group(1)}{m.group(2)}"

        # 9. storage_location → country/region name only
        m = _re.search(
            r"(?:存储地点|保存地点|数据中心|服务器).{0,30}?"
            r"(中国|香港|新加坡|美国|英国|日本|韩国|德国|法国|澳大利亚|印度|马来西亚|泰国|开曼)",
            t,
        )
        if m:
            p["storage_location"] = m.group(1)

        return p

    # ------------------------------------------------------------------
    # LLM deep check
    # ------------------------------------------------------------------

    def _llm_consistency_check(self, documents: list[DocumentWithClauses]) -> list[str]:
        if not self.llm_client or not self.llm_client.enabled:
            return []
        docs_summary = []
        for doc in documents:
            issues_text = "、".join(i.title[:60] for i in doc.issues[:5])
            docs_summary.append(
                f"{doc.filename} ({doc.document_type}): "
                f"{len(doc.clauses)} clauses, {len(doc.issues)} issues"
                + (f", e.g.: {issues_text}" if issues_text else "")
            )
        prompt = (
            "Below are review summaries for multiple documents from the same company. "
            "Check for cross-document contradictions. Output only the inconsistencies found, "
            "or output 'NONE' if there are none.\n\n"
            + "\n".join(docs_summary)
        )
        try:
            raw = self.llm_client.chat(
                system="You are a data compliance review expert. Analyze cross-document consistency.",
                user=prompt, temperature=0.1, max_tokens=300,
            )
            if raw.strip() == "NONE":
                return []
            lines = [l.strip("- 123456789.、") for l in raw.split("\n") if l.strip() and l.strip() != "NONE"]
            return [l for l in lines if len(l) > 20]
        except Exception as exc:
            logger.warning("LLM cross-doc check failed: %s", exc)
            return []
