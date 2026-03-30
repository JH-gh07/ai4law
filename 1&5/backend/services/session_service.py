from backend.schemas.diagnosis import ComplianceProfileDraft, ComplianceQuestionnaire, DiagnosisOutcome, RiskLevel, RuleEvaluationResult


class SessionService:
    def build_prefill_context(
        self,
        outcome: str,
        questionnaire: dict,
        profile: dict,
        evaluation: dict,
    ) -> dict:
        if outcome == DiagnosisOutcome.SECURITY_ASSESSMENT.value:
            next_module = "assessment"
        elif outcome == DiagnosisOutcome.SCC_OR_CERTIFICATION.value:
            next_module = "scc"
        else:
            next_module = "general"

        return {
            "diagnosis_outcome": outcome,
            "risk_level": evaluation.get("risk_level"),
            "suggested_next_module": next_module,
            "questionnaire": questionnaire,
            "profile": profile,
            "evaluation": evaluation,
        }

    def build_assessment_handoff(
        self,
        session_id: str,
        questionnaire: ComplianceQuestionnaire,
        profile: ComplianceProfileDraft,
        evaluation: RuleEvaluationResult,
    ) -> dict:
        recommended = evaluation.outcome == DiagnosisOutcome.SECURITY_ASSESSMENT
        return {
            "session_id": session_id,
            "source_module": "diagnosis",
            "target_module": "assessment",
            "recommended": recommended,
            "diagnosis_outcome": evaluation.outcome.value,
            "risk_level": evaluation.risk_level.value,
            "transfer_purpose": self._extract_transfer_purpose(questionnaire),
            "questionnaire": questionnaire.model_dump(),
            "profile": profile.model_dump(),
            "evaluation": evaluation.model_dump(),
            "company_profile": profile.enterprise_attributes,
            "prefill_form": {
                "trigger_reason": self._build_trigger_reason(evaluation),
                "transfer_purpose": self._extract_transfer_purpose(questionnaire),
                "cross_border_transfer": questionnaire.q4_2_cross_border_transfer,
                "countries": questionnaire.q4_2_countries,
                "contains_important_data": questionnaire.q3_3_handles_important_data,
                "data_volume": questionnaire.q3_6_data_volume,
                "personal_info_types": questionnaire.q3_2_personal_info_types,
                "priority_actions": evaluation.priority_actions,
            },
            "notes": [
                "模块②直接复用完整问卷、自画像与规则评估结果做预填。",
                "若 recommended=false，可展示但不应默认引导进入安全评估路径。",
            ],
        }

    def build_scc_handoff(
        self,
        session_id: str,
        questionnaire: ComplianceQuestionnaire,
        profile: ComplianceProfileDraft,
        evaluation: RuleEvaluationResult,
    ) -> dict:
        recommended = evaluation.outcome == DiagnosisOutcome.SCC_OR_CERTIFICATION
        return {
            "session_id": session_id,
            "source_module": "diagnosis",
            "target_module": "scc",
            "recommended": recommended,
            "diagnosis_outcome": evaluation.outcome.value,
            "risk_level": evaluation.risk_level.value,
            "transfer_purpose": self._extract_transfer_purpose(questionnaire),
            "questionnaire": questionnaire.model_dump(),
            "profile": profile.model_dump(),
            "evaluation": evaluation.model_dump(),
            "company_profile": profile.enterprise_attributes,
            "prefill_form": {
                "suggested_path": "standard_contract_or_certification",
                "transfer_purpose": self._extract_transfer_purpose(questionnaire),
                "cross_border_transfer": questionnaire.q4_2_cross_border_transfer,
                "countries": questionnaire.q4_2_countries,
                "data_volume": questionnaire.q3_6_data_volume,
                "personal_info_types": questionnaire.q3_2_personal_info_types,
                "authorization_mechanism": questionnaire.q4_5_authorization_mechanism,
                "priority_actions": evaluation.priority_actions,
            },
            "notes": [
                "模块③直接复用完整问卷、自画像与规则评估结果做预填。",
                "若 recommended=false，可展示但不应默认引导进入认证/标准合同路径。",
            ],
        }

    def _build_trigger_reason(self, evaluation: RuleEvaluationResult) -> str:
        if evaluation.outcome != DiagnosisOutcome.SECURITY_ASSESSMENT:
            return "diagnosis_not_primary_assessment_path"
        if evaluation.hit_rules:
            return evaluation.hit_rules[0].code
        return "security_assessment_required"

    def _extract_transfer_purpose(self, questionnaire: ComplianceQuestionnaire) -> str | None:
        if questionnaire.q4_2_cross_border_transfer:
            return "跨境业务 / 数据出境"
        if "跨境服务" in questionnaire.q1_3_business_modes:
            return "跨境服务"
        return None
