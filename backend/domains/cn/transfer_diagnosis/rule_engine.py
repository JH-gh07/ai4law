from __future__ import annotations

from pydantic import BaseModel, Field

from backend.domains.cn.transfer_diagnosis.models import DiagnosisFacts, DiagnosisPath


class RuleMatch(BaseModel):
    rule_id: str
    path: DiagnosisPath
    legal_basis: list[str] = Field(default_factory=list)
    description: str = ""
    is_default: bool = False
    condition_fields: list[str] = Field(default_factory=list)


class DiagnosisRuleEngine:
    """Evaluate the versioned diagnosis rule table without LLM inference."""

    def __init__(self, rule_table: dict) -> None:
        self._validate_rule_table(rule_table)
        self.rule_table = rule_table

    @staticmethod
    def _validate_rule_table(rule_table: dict) -> None:
        allowed_conditions = {
            "q1_is_ciio",
            "q2_has_important_data",
            "q3_pii_count_gte",
            "q3_pii_count_lt",
            "q4_spi_count_gte",
            "q4_spi_count_lt",
            "q5_no_personal_info",
            "q6_scenario",
            "q7_receiver_type",
        }
        if not isinstance(rule_table.get("rules"), list) or "default" not in rule_table:
            raise ValueError("Diagnosis rule table must define 'rules' and 'default'.")
        for rule in rule_table["rules"]:
            unknown = set(rule.get("when", {})) - allowed_conditions
            if unknown:
                raise ValueError(
                    f"Rule {rule.get('id', '<unknown>')} has unsupported conditions: "
                    f"{sorted(unknown)}"
                )

    def evaluate(self, facts: DiagnosisFacts) -> RuleMatch:
        if facts.no_personal_info.value == "yes" and (
            facts.contains_important_data.value == "yes"
            or facts.personal_info_count > 0
            or facts.sensitive_personal_info_count > 0
        ):
            return RuleMatch(
                rule_id="conflicting_facts",
                path=DiagnosisPath.MANUAL_REVIEW,
                description=(
                    "No-personal-information declaration conflicts with "
                    "important-data or personal-information facts."
                ),
                condition_fields=[
                    "q2_has_important_data",
                    "q3_pii_count_gte",
                    "q4_spi_count_gte",
                    "q5_no_personal_info",
                ],
            )
        for rule in self.rule_table.get("rules", []):
            if self._matches(rule.get("when", {}), facts):
                return RuleMatch(
                    rule_id=str(rule.get("id", "")),
                    path=DiagnosisPath(rule["path"]),
                    legal_basis=list(rule.get("legal_basis", [])),
                    description=str(rule.get("description", "")),
                    condition_fields=list(rule.get("when", {})),
                )

        default = self.rule_table["default"]
        return RuleMatch(
            rule_id="default",
            path=DiagnosisPath(default["path"]),
            legal_basis=list(default.get("legal_basis", [])),
            description="No explicit rule matched.",
            is_default=True,
        )

    @staticmethod
    def _matches(conditions: dict, facts: DiagnosisFacts) -> bool:
        exact_values = {
            "q1_is_ciio": facts.is_ciio.value,
            "q2_has_important_data": facts.contains_important_data.value,
            "q5_no_personal_info": facts.no_personal_info.value,
            "q6_scenario": facts.transfer_scenario,
            "q7_receiver_type": facts.receiver_type,
        }
        for condition, value in exact_values.items():
            if condition in conditions and value not in conditions[condition]:
                return False

        numeric_values = {
            "q3_pii_count": facts.personal_info_count,
            "q4_spi_count": facts.sensitive_personal_info_count,
        }
        for prefix, value in numeric_values.items():
            lower_bound = conditions.get(f"{prefix}_gte")
            if lower_bound is not None and value < int(lower_bound):
                return False
            upper_bound = conditions.get(f"{prefix}_lt")
            if upper_bound is not None and value >= int(upper_bound):
                return False
        return True
