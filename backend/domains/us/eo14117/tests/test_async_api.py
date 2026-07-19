"""Test US 14117 async API flow."""

import time

from backend.core.resource_paths import report_template_path
from backend.domains.us.eo14117.schema import US14117Request
from backend.domains.us.eo14117.service import US14117Service


class _DisabledLLM:
    enabled = False


def _install_test_templates() -> None:
    md_template = report_template_path("us", "4.2_us_14117_compliance_template_v0.md")
    md_template.parent.mkdir(parents=True, exist_ok=True)
    if not md_template.exists():
        md_template.write_text(
            "# {{overall_conclusion}}\n\n"
            "**红黄绿**: {{traffic_light_label}}\n\n"
            "{{traffic_light_summary}}\n\n"
            "## 风险详情\n\n{{risk_details}}\n\n"
            "## 合规措施\n\n{{compliance_actions}}\n\n",
            encoding="utf-8",
        )


def _build_valid_payload() -> US14117Request:
    return US14117Request.model_validate({
        "project_name": "异步测试项目",
        "transaction_description": "测试异步流程的数据传输分析",
        "transaction_type": "vendor_agreement",
        "data_items": [
            {
                "data_item_name": "生物识别数据",
                "data_description": "员工指纹数据",
                "us_person_count": 2000,
                "data_subject_type": "employee",
                "doj_data_category": "biometric_identifiers",
                "is_government_related": False,
            }
        ],
        "recipient_entities": [
            {
                "entity_name": "测试中国科技公司",
                "country_of_registration": "China",
                "governing_law": "中国法律",
                "government_control": False,
                "entity_role": "processor",
            }
        ],
        "access_persons": [],
        "security_measures": [
            {
                "measure_name": "encryption_at_rest",
                "category": "encryption",
                "status": "implemented",
            }
        ],
        "attachments": [],
        "company_name": "异步测试企业",
    })


def test_async_flow_completes() -> None:
    """Verify async submission, polling, and completion."""
    _install_test_templates()
    payload = _build_valid_payload()
    service = US14117Service(llm_client=_DisabledLLM())

    # Submit async
    accepted = service.submit_async(payload)
    assert accepted.state in {"PENDING", "RUNNING", "COMPLETED"}
    task_id = accepted.task_id

    # Poll until complete
    max_attempts = 300
    for _ in range(max_attempts):
        status = service.get_async_status(task_id)
        if status.state == "COMPLETED":
            break
        if status.state == "FAILED":
            raise AssertionError(f"Task failed: {status.error}")
        time.sleep(0.1)
    else:
        raise AssertionError(f"Task did not complete within {max_attempts} polling attempts")

    assert status.state == "COMPLETED"
    assert status.result is not None
    result = status.result
    assert result.overall_traffic_light in {"RED", "YELLOW", "GREEN"}
    assert len(result.chapters) == 4
    assert "markdown" in result.output_files
    assert "zip" in result.output_files
