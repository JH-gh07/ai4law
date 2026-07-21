class SessionService:
    def build_prefill_context(self, outcome: str, answers: dict) -> dict:
        if outcome == "SECURITY_ASSESSMENT":
            next_module = "assessment"
        elif outcome == "SCC_OR_CERTIFICATION":
            next_module = "pipia"
        elif outcome == "EXEMPTION":
            next_module = "general"
        else:
            next_module = None

        return {
            "diagnosis_outcome": outcome,
            "suggested_next_module": next_module,
            "answers": answers,
        }

    def build_assessment_handoff(self, session_id: str, outcome: str, answers: dict) -> dict:
        recommended = outcome == "SECURITY_ASSESSMENT"
        return {
            "session_id": session_id,
            "source_module": "diagnosis",
            "target_module": "assessment",
            "recommended": recommended,
            "diagnosis_outcome": outcome,
            "transfer_purpose": answers.get("transfer_purpose"),
            "company_profile": {
                "is_ciio": answers.get("is_ciio"),
                "contains_important_data": answers.get("contains_important_data"),
                "personal_info_count": answers.get("personal_info_count", 0),
                "sensitive_personal_info_count": answers.get("sensitive_personal_info_count", 0),
            },
            "prefill_form": {
                "trigger_reason": self._build_trigger_reason(outcome, answers),
                "transfer_purpose": answers.get("transfer_purpose"),
                "contains_important_data": answers.get("contains_important_data") == "YES",
                "personal_info_count": answers.get("personal_info_count", 0),
                "sensitive_personal_info_count": answers.get("sensitive_personal_info_count", 0),
            },
            "notes": [
                "该接口供模块②安全评估路径页面直接预填使用。",
                "如果 recommended=false，前端应提示用户当前路径通常不优先进入安全评估流程。",
            ],
        }

    def build_pipia_handoff(self, session_id: str, outcome: str, answers: dict) -> dict:
        recommended = outcome == "SCC_OR_CERTIFICATION"
        return {
            "session_id": session_id,
            "source_module": "diagnosis",
            "target_module": "pipia",
            "recommended": recommended,
            "diagnosis_outcome": outcome,
            "transfer_purpose": answers.get("transfer_purpose"),
            "company_profile": {
                "is_ciio": answers.get("is_ciio"),
                "contains_important_data": answers.get("contains_important_data"),
                "personal_info_count": answers.get("personal_info_count", 0),
                "sensitive_personal_info_count": answers.get("sensitive_personal_info_count", 0),
            },
            "prefill_form": {
                "suggested_path": "standard_contract_or_certification",
                "transfer_purpose": answers.get("transfer_purpose"),
                "is_ciio": answers.get("is_ciio") == "YES",
                "personal_info_count": answers.get("personal_info_count", 0),
                "sensitive_personal_info_count": answers.get("sensitive_personal_info_count", 0),
                "contains_important_data": answers.get("contains_important_data") == "YES",
            },
            "notes": [
                "该接口供模块③认证/标准合同路径页面直接预填使用。",
                "如果 recommended=false，前端应提示用户该会话更可能进入其他路径。",
            ],
        }

    def _build_trigger_reason(self, outcome: str, answers: dict) -> str:
        if outcome != "SECURITY_ASSESSMENT":
            return "diagnosis_not_primary_assessment_path"
        if answers.get("is_ciio") == "YES":
            return "ciio"
        if answers.get("contains_important_data") == "YES":
            return "important_data"
        if answers.get("personal_info_count", 0) >= 1_000_000:
            return "personal_info_threshold"
        if answers.get("sensitive_personal_info_count", 0) >= 10_000:
            return "sensitive_personal_info_threshold"
        return "security_assessment_required"
