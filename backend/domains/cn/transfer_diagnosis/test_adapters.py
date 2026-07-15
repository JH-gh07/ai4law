from backend.domains.cn.transfer_diagnosis.adapters import facts_from_module
from backend.domains.cn.transfer_diagnosis.models import FactSource, TriState
from backend.modules.diagnosis.schema import DiagnosisAnswers, YesNoUnknown


def test_module_answers_map_without_estimation() -> None:
    facts = facts_from_module(
        DiagnosisAnswers(
            q1_is_ciio=YesNoUnknown.NO,
            q2_has_important_data=YesNoUnknown.UNKNOWN,
            q3_pii_count=0,
            q4_spi_count=0,
            m3_data_volume_range="large",
        )
    )

    assert facts.contains_important_data == TriState.UNKNOWN
    assert facts.personal_info_count == 0
    assert (
        facts.source_for("personal_info_count")
        == FactSource.USER
    )
    assert facts.source_for("receiver_type") == FactSource.DEFAULT
