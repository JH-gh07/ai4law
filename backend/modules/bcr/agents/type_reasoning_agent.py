"""Agent 1: BCRTypeReasoningAgent — resolve ambiguous BCR-C vs BCR-P.

Performs multi-signal type judgment:
- Extracts title, definitions, scope, liability, Article 28 / processor clauses
- Detects mixed BCR-C + BCR-P signals in same document
- Outputs type_judgment, confidence, reasoning_summary, recommended_path, risk_level
"""

from __future__ import annotations

import re

from backend.modules.bcr.agents import BCRAgentBase


class BCRTypeReasoningAgent(BCRAgentBase):
    agent_name = "bcr_type_reasoning"
    max_tokens = 500

    # BCR-C specific responsibility signals (controller-centric)
    _BCR_C_SIGNALS = [
        "controller", "controllers", "determines purposes", "data controller",
        "joint controller", "joint controllership", "as controller",
        "Binding Corporate Rules (Controllers)", "BCR-C", "BCR for Controllers",
        "data exporter", "group as controller", "group controller",
    ]

    # BCR-P specific responsibility signals (processor-centric)
    _BCR_P_SIGNALS = [
        "processor", "processors", "on behalf of", "according to instructions",
        "client controller", "representing", "Article 28", "data processor",
        "Binding Corporate Rules (Processors)", "BCR-P", "BCR for Processors",
        "process personal data on behalf", "following documented instructions",
        "as a processor", "acting as processor", "sub-processor",
    ]

    # Client instruction indicators (strong BCR-P signal)
    _CLIENT_INSTRUCTION_SIGNALS = [
        r"on\s+behalf\s+of\s+(?:the\s+)?client",
        r"according\s+to\s+(?:the\s+)?(?:client|controller)[´'']?s\s+instructions",
        r"following\s+documented\s+instructions",
        r"as\s+a\s+processor\s+(?:on\s+behalf|for)",
        r"Article\s+28\s+(?:of\s+the\s+)?GDPR",
    ]

    # Controller liability signals (strong BCR-C signal)
    _CONTROLLER_LIABILITY_SIGNALS = [
        r"determines?\s+(?:the\s+)?purposes?\s+(?:and|&)\s+(?:the\s+)?means",
        r"data\s+controller\s+(?:shall|will|must|has|is\s+responsible)",
        r"joint\s+controllership",
        r"group\s+(?:as\s+)?controller",
        r"as\s+(?:a\s+)?(?:data\s+)?controller",
    ]

    def run(self, text: str, declared_type: str, c_score: float, p_score: float,
            c_evidence: list[str], p_evidence: list[str],
            attachment_notes: str = "", rulebook_signals: dict | None = None) -> dict:
        """Determine BCR type using deterministic multi-signal analysis + LLM fallback.

        Triggered when actual=unknown or c_score and p_score are close (<2.0 apart).
        """
        text_lower = text[:8000].lower()
        att_lower = (attachment_notes or "").lower()

        # ── Deterministic signal extraction ──
        # Count C and P signal hits in title, definitions, scope, liability text
        c_hits_full = sum(1 for s in self._BCR_C_SIGNALS if s.lower() in text_lower)
        p_hits_full = sum(1 for s in self._BCR_P_SIGNALS if s.lower() in text_lower)

        # Check for strong controller signals
        controller_liability_hits = [p for p in self._CONTROLLER_LIABILITY_SIGNALS if re.search(p, text_lower)]
        client_instruction_hits = [p for p in self._CLIENT_INSTRUCTION_SIGNALS if re.search(p, text_lower)]

        # Check for Article 28 presence (strong processor signal)
        has_article_28 = "article 28" in text_lower or "Art. 28" in text_lower
        has_controller_in_title = any(kw in text[:500].lower() for kw in ["controller", "controllers"])
        has_processor_in_title = any(kw in text[:500].lower() for kw in ["processor", "processors"])

        # ── Determine type ──
        type_judgment = "unknown"
        confidence = 0.5
        reasoning_parts: list[str] = []

        c_strong = len(controller_liability_hits) >= 2
        p_strong = len(client_instruction_hits) >= 2 or (has_article_28 and has_processor_in_title)

        # Mixed detection: both strong C and strong P signals in same document
        c_doc_signals = c_hits_full + len(controller_liability_hits)
        p_doc_signals = p_hits_full + len(client_instruction_hits) + (3 if has_article_28 else 0)

        if c_strong and p_strong:
            type_judgment = "mixed"
            confidence = 0.75
            reasoning_parts.append(
                "Document contains both controller-specific liability language "
                f"(signals: {controller_liability_hits[:3]}) and processor-specific "
                f"client instruction clauses (signals: {client_instruction_hits[:3]}). "
                "This may indicate the BCR applies to both controller and processor roles."
            )
        elif c_strong or (c_doc_signals > p_doc_signals + 2):
            type_judgment = "BCR-C"
            confidence = 0.85 if c_strong else 0.70
            reasoning_parts.append(
                f"Strong controller signals detected: "
                f"{controller_liability_hits[:3] if controller_liability_hits else c_evidence[:3]}. "
                f"Document primarily addresses controller obligations."
            )
        elif p_strong or (p_doc_signals > c_doc_signals + 2):
            type_judgment = "BCR-P"
            confidence = 0.85 if p_strong else 0.70
            reasoning_parts.append(
                f"Strong processor signals detected: "
                f"{client_instruction_hits[:3] if client_instruction_hits else p_evidence[:3]}. "
                f"{'Article 28 references found.' if has_article_28 else ''}"
                f"Document primarily addresses processor obligations."
            )
        else:
            # Scores too close or both weak — try LLM
            pass  # fall through to LLM

        # ── Determine recommended path and risk ──
        if type_judgment == "mixed":
            recommended_path = "拆分BCR-C/BCR-P检查清单，分别审查控制者和处理者义务"
            risk_level = "MEDIUM"
        elif type_judgment in ("BCR-C", "BCR-P"):
            recommended_path = f"按{type_judgment} checklist进行后续审查"
            risk_level = "LOW"
        else:
            # Try LLM for uncertain cases
            llm_result = self._try_llm_reasoning(text, declared_type, c_score, p_score,
                                                  c_evidence, p_evidence)
            if llm_result:
                type_judgment = llm_result.get("type_judgment", "unknown")
                confidence = llm_result.get("confidence", 0.3)
                reasoning_parts.append(llm_result.get("reasoning_summary", ""))
                recommended_path = llm_result.get("recommended_path", "Manual review required.")
                risk_level = llm_result.get("risk_level", "MEDIUM")
            else:
                # Final fallback
                type_judgment = "unknown"
                confidence = 0.3
                reasoning_parts.append("Unable to determine BCR type from available signals. "
                                       "Scores too close and LLM unavailable.")
                recommended_path = "Manual review required — cannot determine BCR-C or BCR-P."
                risk_level = "MEDIUM"

        return {
            "type_judgment": type_judgment,
            "confidence": round(confidence, 2),
            "reasoning_summary": " ".join(reasoning_parts) if reasoning_parts else "Signals inconclusive.",
            "recommended_path": recommended_path,
            "risk_level": risk_level,
            "c_signals_count": c_doc_signals,
            "p_signals_count": p_doc_signals,
        }

    def _try_llm_reasoning(self, text: str, declared_type: str, c_score: float, p_score: float,
                           c_evidence: list[str], p_evidence: list[str]) -> dict | None:
        """LLM fallback for uncertain type judgment."""
        prompt = f"""Determine the correct BCR type based on text analysis.

Declared type: {declared_type}
C-score: {c_score} (signals: {c_evidence[:5]})
P-score: {p_score} (signals: {p_evidence[:5]})

Text excerpt (first 3000 chars):
{text[:3000]}

Return JSON:
{{
  "type_judgment": "BCR-C" | "BCR-P" | "mixed" | "unknown",
  "confidence": 0.0-1.0,
  "reasoning_summary": "<1 sentence>",
  "recommended_path": "<1 sentence action>",
  "risk_level": "LOW" | "MEDIUM" | "HIGH"
}}"""
        return self._call_llm(prompt)
