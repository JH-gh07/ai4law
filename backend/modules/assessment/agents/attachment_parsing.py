"""Agent 2: Deep attachment parsing — extracts quotable evidence from uploaded files.

Responsible for:
- Contract clause-level evidence extraction (6 core clauses per Assessment Measures Art.9)
- Consent record verification
- Certification/audit report key finding extraction
- Data inventory structured parsing

Does NOT:
- Judge overall compliance
- Determine risk levels
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ClauseEvidence:
    clause_name: str
    status: str  # covered | partial | missing | unclear
    evidence_quote: str = ""
    paragraph_ref: str = ""
    confidence: float = 0.8
    observation: str = ""


@dataclass
class AttachmentEvidence:
    file_path: str
    document_type: str  # contract | privacy_policy | consent_record | certification | audit_report | data_inventory
    clauses: list[ClauseEvidence] = field(default_factory=list)
    key_excerpts: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    overall_confidence: float = 0.8


class AttachmentParsingAgent:
    """Deep attachment parser — extracts structured evidence from uploaded files."""

    # 6 core clauses from Data Export Security Assessment Measures Art.9
    SIX_CORE_CLAUSES = [
        "purpose_method_scope",           # 数据出境目的、方式、范围
        "overseas_retention_location_period",  # 境外保存地点、期限、到期处理措施
        "onward_transfer_constraint",     # 再转移约束
        "legal_environment_change_response",  # 法律环境变化应对措施
        "breach_liability_dispute_resolution", # 违约责任、补救措施、争议解决
        "incident_response_and_individual_rights", # 应急处置和个人权益保障
    ]

    CLAUSE_KEYWORDS: dict[str, list[str]] = {
        "purpose_method_scope": ["purpose", "目的", "scope", "范围", "method", "方式", "processing", "处理"],
        "overseas_retention_location_period": ["retention", "保留", "保存", "location", "地点", "overseas", "境外", "period", "期限"],
        "onward_transfer_constraint": ["onward transfer", "再转移", "sub-processor", "subprocessor", "转委托", "再转让", "further transfer"],
        "legal_environment_change_response": ["legal environment", "法律环境", "change", "变化", "不可抗力", "force majeure", "material adverse"],
        "breach_liability_dispute_resolution": ["breach", "违约", "liability", "责任", "indemnif", "赔偿", "dispute", "争议", "arbitration", "仲裁"],
        "incident_response_and_individual_rights": ["incident", "事件", "breach notification", "泄露通知", "data subject", "数据主体", "rights", "权利", "complaint", "投诉"],
    }

    CONSENT_KEYWORDS = ["separate consent", "单独同意", "explicit consent", "明示同意", "opted in", "opt-in", "consent record", "同意记录"]

    def run(self, file_path: str, content: str, doc_type: str = "unknown") -> AttachmentEvidence:
        """Parse a single attachment and extract structured evidence.

        Args:
            file_path: Path to the uploaded file
            content: Full text content of the file
            doc_type: Pre-classified document type
        """
        evidence = AttachmentEvidence(
            file_path=file_path,
            document_type=doc_type,
        )

        if doc_type in ("contract", "dpa", "scc", "unknown"):
            evidence.clauses = self._extract_contract_clauses(content)
            evidence.missing_items = [c.clause_name for c in evidence.clauses if c.status in ("missing", "unclear")]
            evidence.overall_confidence = sum(c.confidence for c in evidence.clauses) / max(len(evidence.clauses), 1)

        if doc_type in ("consent_record", "privacy_policy", "unknown"):
            evidence.key_excerpts = self._extract_consent_evidence(content)

        return evidence

    def _extract_contract_clauses(self, content: str) -> list[ClauseEvidence]:
        """Extract evidence for each of the 6 core clauses."""
        clauses: list[ClauseEvidence] = []
        content_lower = content.lower()

        for clause_name in self.SIX_CORE_CLAUSES:
            keywords = self.CLAUSE_KEYWORDS.get(clause_name, [])
            hits = [kw for kw in keywords if kw.lower() in content_lower]

            if len(hits) >= 3:
                status = "covered"
                confidence = 0.85
            elif len(hits) >= 1:
                status = "partial"
                confidence = 0.65
            else:
                status = "unclear"
                confidence = 0.3

            clauses.append(ClauseEvidence(
                clause_name=clause_name,
                status=status,
                evidence_quote=f"Keywords matched: {', '.join(hits[:3])}" if hits else "No keywords matched",
                confidence=confidence,
                observation=f"Clause coverage: {status} (matched {len(hits)}/{len(keywords)} keywords)",
            ))

        return clauses

    def _extract_consent_evidence(self, content: str) -> list[str]:
        """Extract consent-related evidence from privacy policy or consent records."""
        excerpts: list[str] = []
        content_lower = content.lower()

        for kw in self.CONSENT_KEYWORDS:
            if kw.lower() in content_lower:
                # Find surrounding context
                idx = content_lower.find(kw.lower())
                start = max(0, idx - 100)
                end = min(len(content), idx + 200)
                excerpts.append(content[start:end].strip())

        return excerpts[:5]

    def run_with_llm(self, file_path: str, content: str, llm_client: Any, doc_type: str = "unknown") -> AttachmentEvidence:
        """Enhanced parsing with LLM for ambiguous clauses.

        Falls back to deterministic parsing when LLM is unavailable.
        """
        evidence = self.run(file_path, content, doc_type)

        if not llm_client or not getattr(llm_client, "enabled", False):
            return evidence

        # Only use LLM for unclear clauses
        unclear = [c for c in evidence.clauses if c.status in ("unclear", "partial")]
        if not unclear:
            return evidence

        clause_list = "\n".join(f"- {c.clause_name}: {c.status}" for c in unclear)
        prompt = (
            f"Review this contract excerpt for the following SCC clause coverage:\n{clause_list}\n\n"
            f"Contract text (excerpt):\n{content[:3000]}\n\n"
            "For each clause, return a JSON object with:\n"
            "- clause_name: the clause identifier\n"
            "- status: covered/partial/missing/unclear\n"
            "- evidence_quote: a short quote from the text (if found)\n"
            "- observation: one sentence observation\n"
            "Return as a JSON array."
        )

        try:
            raw = llm_client.chat(system="You are a legal contract analyst.", user=prompt, temperature=0.1, max_tokens=500)
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                for item in parsed:
                    for c in evidence.clauses:
                        if c.clause_name == item.get("clause_name"):
                            c.status = item.get("status", c.status)
                            c.evidence_quote = item.get("evidence_quote", c.evidence_quote)
                            c.observation = item.get("observation", c.observation)
        except (json.JSONDecodeError, Exception):
            pass

        return evidence


def create_attachment_parsing_agent() -> AttachmentParsingAgent:
    """Factory function for AttachmentParsingAgent."""
    return AttachmentParsingAgent()
