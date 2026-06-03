"""Agent 1: Input normalization — maps user input to official template schema.

Responsible for:
- Reading raw user input + attachment summaries
- Mapping free-text fields to structured template slots
- Marking field status: provided | missing | ambiguous | inferred | conflicting
- Generating clarification questions for missing key fields

Does NOT:
- Judge compliance
- Determine risk levels
- Decide regulatory paths
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldStatus:
    field_path: str
    status: str  # provided | missing | ambiguous | inferred | conflicting
    source: str = ""  # user_input | attachment | inferred | default
    value: Any = None
    note: str = ""


@dataclass
class NormalizedInput:
    field_statuses: list[FieldStatus] = field(default_factory=list)
    missing_critical_fields: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    enriched_facts: dict[str, Any] = field(default_factory=dict)


class InputNormalizationAgent:
    """Maps user input + attachment data to official template fields."""

    # Official template required fields
    OFFICIAL_TEMPLATE_FIELDS = {
        "basic_info.company_name": "企业名称",
        "basic_info.industry": "行业",
        "basic_info.is_ciio": "是否为CIIO",
        "basic_info.contains_important_data": "是否涉及重要数据",
        "transfer_scenario.purpose": "出境目的",
        "transfer_scenario.receiver_country": "接收方国家/地区",
        "data_inventory": "数据出境清单",
        "recipient.name": "境外接收方名称",
        "recipient.role": "境外接收方角色",
        "recipient.security_evidence": "接收方安全能力证明",
        "legal_document.coverage": "法律文件六项条款覆盖情况",
        "security_measures.technical": "技术安全措施",
        "security_measures.organizational": "管理安全措施",
        "consent.separate_consent": "单独同意记录",
        "compliance_history": "历史合规记录",
    }

    def run(self, payload: Any, attachment_notes: list[str] | None = None) -> NormalizedInput:
        """Run input normalization and return structured field status.

        Args:
            payload: AssessmentRequest or dict with user input fields
            attachment_notes: Parsed attachment summaries
        """
        field_statuses: list[FieldStatus] = []
        missing_critical: list[str] = []
        questions: list[str] = []

        payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else (payload if isinstance(payload, dict) else {})

        # Check each expected field
        for field_path, label in self.OFFICIAL_TEMPLATE_FIELDS.items():
            value = self._get_nested(payload_dict, field_path)

            if value is not None and value != "" and value != [] and value != {}:
                field_statuses.append(FieldStatus(
                    field_path=field_path, status="provided",
                    source="user_input", value=value,
                ))
            else:
                # Check if it can be inferred from attachments
                inferred = self._try_infer(field_path, attachment_notes or [])
                if inferred:
                    field_statuses.append(FieldStatus(
                        field_path=field_path, status="inferred",
                        source="attachment", value=inferred,
                        note="从附件中推断",
                    ))
                else:
                    field_statuses.append(FieldStatus(
                        field_path=field_path, status="missing",
                        note=f"缺少: {label}",
                    ))
                    # Is this a critical field?
                    if field_path in self._critical_fields():
                        missing_critical.append(field_path)
                        questions.append(f"请提供{label}信息。")

        return NormalizedInput(
            field_statuses=field_statuses,
            missing_critical_fields=missing_critical,
            clarification_questions=questions,
            enriched_facts=self._build_enriched_facts(payload_dict, attachment_notes or []),
        )

    def run_with_llm(self, payload: Any, llm_client: Any, attachment_notes: list[str] | None = None) -> NormalizedInput:
        """Run with LLM assistance for ambiguous fields.

        When LLM is available, use it to resolve ambiguous field mappings
        that rules cannot handle deterministically.
        """
        # First run deterministic normalization
        result = self.run(payload, attachment_notes)

        if not llm_client or not getattr(llm_client, "enabled", False):
            return result

        # Use LLM to resolve ambiguities
        ambiguous = [fs for fs in result.field_statuses if fs.status == "missing"]
        if not ambiguous:
            return result

        ambiguous_fields = "\n".join(f"- {self.OFFICIAL_TEMPLATE_FIELDS.get(fs.field_path, fs.field_path)}" for fs in ambiguous[:5])
        user_input_summary = json.dumps(self._summarize_payload(payload), ensure_ascii=False, indent=2)

        prompt = (
            "You are a data compliance input analyst. Below is user input for a security assessment.\n"
            f"User input summary:\n{user_input_summary}\n\n"
            f"The following official template fields are missing:\n{ambiguous_fields}\n\n"
            "Please analyze whether any of these fields can be reasonably inferred from the user input. "
            "Return a JSON object with field_path -> inferred_value mappings (only for fields you can infer, skip the rest). "
            "Do NOT fabricate information. Use null if you cannot infer."
        )

        try:
            raw = llm_client.chat(system="You are a legal data analyst.", user=prompt, temperature=0.1, max_tokens=500)
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict):
                result.enriched_facts.update(parsed)
        except (json.JSONDecodeError, Exception):
            pass  # Fallback to deterministic result

        return result

    @staticmethod
    def _critical_fields() -> set[str]:
        return {
            "basic_info.company_name",
            "transfer_scenario.purpose",
            "transfer_scenario.receiver_country",
            "basic_info.contains_important_data",
        }

    @staticmethod
    def _get_nested(d: dict, path: str) -> Any:
        keys = path.split(".")
        current: Any = d
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current

    @staticmethod
    def _try_infer(field_path: str, notes: list[str]) -> Any:
        """Try to infer a field value from attachment notes."""
        combined = " ".join(notes).lower()
        inferences = {
            "data_inventory": "data_inventory" if any(kw in combined for kw in ("data inventory", "数据清单", "数据项")) else None,
            "recipient.name": "recipient_name" if any(kw in combined for kw in ("receiver", "接收方", "data importer")) else None,
            "security_measures.technical": "security_measures" if any(kw in combined for kw in ("encrypt", "tls", "加密", "aes")) else None,
        }
        return inferences.get(field_path)

    @staticmethod
    def _summarize_payload(payload: Any) -> dict:
        if hasattr(payload, "model_dump"):
            d = payload.model_dump()
        elif isinstance(payload, dict):
            d = payload
        else:
            return {}
        # Return only non-empty fields
        return {k: v for k, v in d.items() if v not in (None, "", [], {})}

    @staticmethod
    def _build_enriched_facts(payload_dict: dict, notes: list[str]) -> dict[str, Any]:
        """Build enriched facts from payload + notes."""
        enriched: dict[str, Any] = {}
        # Carry forward structured fields from the extended AssessmentRequest
        structured_keys = [
            "data_inventory_items", "recipient_info", "downstream_processors",
            "legal_document_review", "security_capability", "compliance_history",
            "personal_info_protection", "system_link", "self_assessment_info",
        ]
        for key in structured_keys:
            if key in payload_dict and payload_dict[key] is not None:
                enriched[key] = payload_dict[key]
        return enriched
