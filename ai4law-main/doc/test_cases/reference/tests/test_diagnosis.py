def build_questionnaire(**overrides):
    payload = {
        "enterprise_name": "示例科技",
        "q1_2_industry": "电商零售",
        "q1_3_business_modes": ["线上平台", "跨境服务"],
        "q1_4_service_targets": "个人用户",
        "q1_5_enterprise_size": "中型 (员工 51-200 人)",
        "q1_6_is_ciio": "NO",
        "q2_1_compliance_goals": ["识别业务合规风险点", "合规审计 / 备案"],
        "q2_2_has_incidents": "NO",
        "q2_3_urgency": "一般需求 (1-3 个月)",
        "q3_1_handles_personal_info": True,
        "q3_2_personal_info_types": ["姓名", "手机号"],
        "q3_3_handles_important_data": False,
        "q3_3_important_data_types": [],
        "q3_4_data_sources": ["用户主动提交"],
        "q3_5_processing_actions": ["收集", "存储", "传输", "跨境传输"],
        "q3_6_data_volume": "10-100 万条",
        "q3_7_handles_enterprise_or_public_data": False,
        "q3_8_retention_policy": "业务必要期限内留存",
        "q4_1_shares_with_third_parties": False,
        "q4_2_cross_border_transfer": True,
        "q4_2_countries": ["新加坡"],
        "q4_2_exemption_scenarios": [],
        "q4_3_monetization": False,
        "q4_4_entrusted_processing": False,
        "q4_5_authorization_mechanism": "单独点击“同意”按钮",
        "q5_1_systems": ["自有 APP", "官方网站"],
        "q5_2_security_measures": ["数据加密", "访问权限控制"],
        "q5_3_compliance_documents": ["隐私政策", "用户协议"],
        "q5_4_penalty_or_complaint_status": "无相关记录",
    }
    payload.update(overrides)
    return payload


def create_and_evaluate(client, questionnaire):
    session_id = client.post("/api/v1/diagnosis/sessions").json()["id"]
    submit = client.put(f"/api/v1/diagnosis/sessions/{session_id}/questionnaire", json=questionnaire)
    assert submit.status_code == 200
    evaluate = client.post(f"/api/v1/diagnosis/sessions/{session_id}/evaluate")
    assert evaluate.status_code == 200
    return session_id, evaluate.json()


def test_questionnaire_drives_scc_or_certification_path(client):
    session_id, body = create_and_evaluate(client, build_questionnaire())
    assert body["result"]["outcome"] == "SCC_OR_CERTIFICATION"
    assert body["result"]["risk_level"] in {"HIGH", "MEDIUM"}
    assert body["questionnaire"]["q3_6_data_volume"] == "10-100 万条"

    profile_response = client.get(f"/api/v1/diagnosis/sessions/{session_id}/profile")
    assert profile_response.status_code == 200
    assert profile_response.json()["data_flow_profile"]["cross_border_transfer"] is True


def test_questionnaire_critical_security_assessment_flow(client):
    questionnaire = build_questionnaire(
        q1_6_is_ciio="YES",
        q3_3_handles_important_data=True,
        q3_3_important_data_types=["金融交易数据"],
        q3_6_data_volume="1000 万条以上",
        q3_2_personal_info_types=["姓名", "手机号", "身份证号"],
        q4_5_authorization_mechanism="无授权机制",
        q5_3_compliance_documents=["无"],
        q5_2_security_measures=["无"],
    )
    session_id, body = create_and_evaluate(client, questionnaire)
    assert body["result"]["outcome"] == "SECURITY_ASSESSMENT"
    assert body["result"]["risk_level"] == "CRITICAL"
    assert any("CIIO" in rule for rule in body["result"]["hit_rules"])

    report_response = client.post(f"/api/v1/diagnosis/sessions/{session_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["html_report"]["artifact_type"] == "html"


def test_questionnaire_handoff_contains_full_profile_and_evaluation(client):
    session_id, body = create_and_evaluate(client, build_questionnaire())
    assert body["result"]["outcome"] == "SCC_OR_CERTIFICATION"

    assessment_handoff = client.get(f"/api/v1/diagnosis/sessions/{session_id}/handoff/assessment")
    assert assessment_handoff.status_code == 200
    assert assessment_handoff.json()["recommended"] is False
    assert "questionnaire" in assessment_handoff.json()
    assert "evaluation" in assessment_handoff.json()

    scc_handoff = client.get(f"/api/v1/diagnosis/sessions/{session_id}/handoff/scc")
    assert scc_handoff.status_code == 200
    assert scc_handoff.json()["recommended"] is True
    assert scc_handoff.json()["profile"]["business_overview"]["business_modes"] == ["线上平台", "跨境服务"]
    assert scc_handoff.json()["prefill_form"]["transfer_purpose"] == "跨境业务 / 数据出境"


def test_legacy_answers_endpoint_still_maps_to_questionnaire_flow(client):
    session_id = client.post("/api/v1/diagnosis/sessions").json()["id"]
    payload = {
        "is_ciio": "NO",
        "contains_important_data": "NO",
        "personal_info_count": 99999,
        "sensitive_personal_info_count": 0,
        "transfer_purpose": "客户服务",
    }
    response = client.put(f"/api/v1/diagnosis/sessions/{session_id}/answers", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["deprecated_answers"]["transfer_purpose"] == "客户服务"
    assert body["questionnaire"]["q3_6_data_volume"] == "10 万条以下"
    assert body["result"]["outcome"] in {"EXEMPTION", "SCC_OR_CERTIFICATION"}


def test_exemption_no_cross_border_does_not_handoff_to_downstream_modules(client):
    session_id, body = create_and_evaluate(
        client,
        build_questionnaire(
            q4_2_cross_border_transfer=False,
            q1_3_business_modes=["纯内部使用"],
            q3_1_handles_personal_info=False,
            q3_2_personal_info_types=[],
            q3_3_handles_important_data=False,
        ),
    )
    assert body["result"]["outcome"] == "EXEMPTION"
    assert body["result"]["suggested_next_module"] is None
    assert "豁免" in body["evaluation"]["path_conclusion"]

    assessment_handoff = client.get(f"/api/v1/diagnosis/sessions/{session_id}/handoff/assessment").json()
    scc_handoff = client.get(f"/api/v1/diagnosis/sessions/{session_id}/handoff/scc").json()
    assert assessment_handoff["recommended"] is False
    assert scc_handoff["recommended"] is False


def test_exemption_low_volume_cross_border_non_sensitive_outputs_report_only(client):
    session_id, body = create_and_evaluate(
        client,
        build_questionnaire(
            q3_6_data_volume="10 万条以下",
            q3_2_personal_info_types=["姓名", "手机号"],
            q3_3_handles_important_data=False,
            q4_2_cross_border_transfer=True,
        ),
    )
    assert body["result"]["outcome"] == "EXEMPTION"
    assert body["result"]["suggested_next_module"] is None
    assert any("10 万" in rule or "少于 10 万" in rule for rule in body["result"]["hit_rules"])

    report_response = client.post(f"/api/v1/diagnosis/sessions/{session_id}/report")
    assert report_response.status_code == 200


def test_exemption_special_business_scenario_skips_module_two_three(client):
    _, body = create_and_evaluate(
        client,
        build_questionnaire(
            q3_6_data_volume="10-100 万条",
            q4_2_cross_border_transfer=True,
            q4_2_exemption_scenarios=["国际贸易", "自由贸易试验区负面清单机制"],
        ),
    )
    assert body["result"]["outcome"] == "EXEMPTION"
    assert body["result"]["suggested_next_module"] is None
    assert any("特定豁免场景" in rule or "国际贸易" in rule for rule in body["result"]["hit_rules"])
