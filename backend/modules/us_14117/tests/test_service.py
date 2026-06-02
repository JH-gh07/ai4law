"""Test US 14117 service with all three traffic light scenarios (without LLM)."""

from pathlib import Path

from backend.modules.us_14117.schema import US14117Request
from backend.modules.us_14117.service import US14117Service


class _DisabledLLM:
    enabled = False


def _install_test_templates() -> None:
    """Create minimal templates for testing."""
    template_dir = Path("doc/v2/assets/templates")
    template_dir.mkdir(parents=True, exist_ok=True)
    md_template = template_dir / "4.2_us_14117_compliance_template_v0.md"
    if not md_template.exists():
        md_template.write_text(
            "# {{overall_conclusion}}\n\n"
            "**红黄绿**: {{traffic_light_label}}\n\n"
            "{{traffic_light_summary}}\n\n"
            "## 风险详情\n\n{{risk_details}}\n\n"
            "## 合规措施\n\n{{compliance_actions}}\n\n",
            encoding="utf-8",
        )


# ── Test data ──

def _build_red_scenario_payload() -> US14117Request:
    """Scenario 1 (RED): Human genomic data + covered person (China entity)."""
    return US14117Request.model_validate({
        "project_name": "基因数据分析合作项目",
        "transaction_description": (
            "向中国控股的生物科技公司华源生命科学有限公司提供"
            "10,000名美国人的全基因组测序原始数据进行联合研究分析"
        ),
        "transaction_type": "vendor_agreement",
        "data_items": [
            {
                "data_item_name": "全基因组测序原始数据",
                "data_description": "10,000名美国人的全基因组测序原始数据（FASTQ格式）",
                "business_context": "合作研发药物基因组学分析",
                "is_personal_info": True,
                "is_sensitive_personal_info": True,
                "us_person_count": 10000,
                "data_subject_type": "patient",
                "doj_data_category": "human_genomic_data",
                "precision_level": "raw",
                "is_government_related": False,
                "export_necessity": "合作研发必须",
            }
        ],
        "recipient_entities": [
            {
                "entity_name": "华源生命科学有限公司",
                "country_of_registration": "China",
                "tax_id": "91440300MA5XXXX",
                "ownership_structure": "70%由中国国有生物科技集团持有，30%为民营资本",
                "governing_law": "中华人民共和国法律",
                "government_control": True,
                "government_investment": "接受中国科技部重大专项资金",
                "parent_company": "中国国有生物科技集团",
                "entity_role": "processor",
            }
        ],
        "access_persons": [
            {
                "person_name": "张伟",
                "nationality": "中国",
                "country_of_residence": "中国",
                "department": "研发部",
                "position": "高级生物信息学工程师",
                "employer": "华源生命科学有限公司",
                "has_actual_access": True,
                "access_type": "direct",
            }
        ],
        "security_measures": [],
        "onward_transfer": False,
        "onward_transfer_description": "",
        "attachments": [],
        "company_name": "美国基因组研究所",
    })


def _build_yellow_scenario_payload() -> US14117Request:
    """Scenario 2 (YELLOW): Precise geolocation + covered person + vendor agreement."""
    return US14117Request.model_validate({
        "project_name": "位置数据分析平台项目",
        "transaction_description": (
            "通过供应商协议向中国AI公司深度洞察人工智能有限公司提供"
            "150,000名美国人的精确地理位置数据用于算法训练"
        ),
        "transaction_type": "vendor_agreement",
        "data_items": [
            {
                "data_item_name": "精确GPS轨迹数据",
                "data_description": "150,000名美国人的实时GPS轨迹数据（精度<10米）",
                "business_context": "AI模型训练——位置预测算法",
                "is_personal_info": True,
                "is_sensitive_personal_info": True,
                "us_person_count": 150000,
                "data_subject_type": "consumer",
                "doj_data_category": "precise_geolocation_data",
                "precision_level": "raw",
                "is_government_related": False,
                "export_necessity": "算法训练所需训练数据",
            }
        ],
        "recipient_entities": [
            {
                "entity_name": "深度洞察人工智能有限公司",
                "country_of_registration": "China",
                "tax_id": "",
                "ownership_structure": "创始人持股60%，中国风投资本40%",
                "governing_law": "中华人民共和国法律",
                "government_control": False,
                "government_investment": "",
                "parent_company": "",
                "entity_role": "processor",
            }
        ],
        "access_persons": [
            {
                "person_name": "王芳",
                "nationality": "中国",
                "country_of_residence": "中国",
                "department": "AI研发部",
                "position": "机器学习工程师",
                "employer": "深度洞察人工智能有限公司",
                "has_actual_access": True,
                "access_type": "remote",
            }
        ],
        "security_measures": [
            {
                "measure_name": "logical_isolation_of_covered_data",
                "category": "access_control",
                "status": "missing",
                "description": "尚未建立隔离工作区",
            },
        ],
        "onward_transfer": False,
        "onward_transfer_description": "",
        "attachments": [],
        "company_name": "美国位置服务公司",
    })


def _build_green_scenario_payload() -> US14117Request:
    """Scenario 3 (GREEN): Non-covered person + city-level location + below threshold."""
    return US14117Request.model_validate({
        "project_name": "设备维护数据分析项目",
        "transaction_description": (
            "向英国设备公司提供5,000名用户的设备维护数据，"
            "包括邮箱地址和城市级地理位置（非精确GPS）"
        ),
        "transaction_type": "vendor_agreement",
        "data_items": [
            {
                "data_item_name": "用户邮箱地址",
                "data_description": "5,000个用户的电子邮箱地址",
                "business_context": "维护通知和客户服务",
                "is_personal_info": True,
                "is_sensitive_personal_info": False,
                "us_person_count": 5000,
                "data_subject_type": "consumer",
                "doj_data_category": "",
                "precision_level": "",
                "is_government_related": False,
                "export_necessity": "设备维护必须的客户联系信息",
            }
        ],
        "recipient_entities": [
            {
                "entity_name": "英国设备有限公司",
                "country_of_registration": "United Kingdom",
                "tax_id": "GB123456789",
                "ownership_structure": "100%英国私人资本",
                "governing_law": "英格兰和威尔士法律",
                "government_control": False,
                "government_investment": "",
                "parent_company": "",
                "entity_role": "processor",
            }
        ],
        "access_persons": [],
        "security_measures": [
            {
                "measure_name": "encryption_at_rest",
                "category": "encryption",
                "status": "implemented",
                "description": "AES-256静态加密已部署",
            },
            {
                "measure_name": "access_controls",
                "category": "access_control",
                "status": "implemented",
                "description": "RBAC和MFA已实施",
            },
        ],
        "onward_transfer": False,
        "onward_transfer_description": "",
        "attachments": [],
        "company_name": "美国设备制造商",
    })


# ── Tests ──

def test_red_scenario_human_genomic_data() -> None:
    """Scenario 1: Human genomic data + covered person → RED."""
    _install_test_templates()
    payload = _build_red_scenario_payload()
    service = US14117Service(llm_client=_DisabledLLM())
    result = service.generate_report(payload)

    assert result.overall_traffic_light == "RED"
    assert result.traffic_light_result.is_prohibited is True
    assert len(result.traffic_light_result.prohibition_reasons) > 0
    assert result.report_path  # report was generated
    assert "markdown" in result.output_files
    assert len(result.chapters) == 4
    assert len(result.risk_matrix) > 0
    assert len(result.rule_hits) > 0

    # Verify risk matrix has RED entries
    red_rows = [r for r in result.risk_matrix if r.traffic_light == "RED"]
    assert len(red_rows) > 0


def test_yellow_scenario_precise_geolocation() -> None:
    """Scenario 2: Precise geolocation + covered person + vendor → YELLOW."""
    _install_test_templates()
    payload = _build_yellow_scenario_payload()
    service = US14117Service(llm_client=_DisabledLLM())
    result = service.generate_report(payload)

    assert result.overall_traffic_light == "YELLOW"
    assert result.traffic_light_result.is_restricted is True
    assert len(result.traffic_light_result.restriction_reasons) > 0
    assert len(result.traffic_light_result.missing_security_measures) > 0
    assert len(result.chapters) == 4
    assert len(result.risk_matrix) > 0

    # Verify risk matrix has YELLOW entries
    yellow_rows = [r for r in result.risk_matrix if r.traffic_light == "YELLOW"]
    assert len(yellow_rows) > 0


def test_green_scenario_low_risk() -> None:
    """Scenario 3: Non-covered person + city-level data + below threshold → GREEN."""
    _install_test_templates()
    payload = _build_green_scenario_payload()
    service = US14117Service(llm_client=_DisabledLLM())
    result = service.generate_report(payload)

    assert result.overall_traffic_light == "GREEN"
    assert result.traffic_light_result.is_prohibited is False
    assert result.traffic_light_result.is_restricted is False
    assert len(result.chapters) == 4
    assert len(result.risk_matrix) > 0

    # Verify all risk matrix rows are GREEN
    non_green = [r for r in result.risk_matrix if r.traffic_light != "GREEN"]
    assert len(non_green) == 0


def test_request_parses_correctly() -> None:
    """Verify US14117Request model validation."""
    payload = _build_red_scenario_payload()
    assert payload.project_name == "基因数据分析合作项目"
    assert len(payload.data_items) == 1
    assert payload.data_items[0].us_person_count == 10000
    assert payload.data_items[0].doj_data_category == "human_genomic_data"
    assert len(payload.recipient_entities) == 1
    assert payload.recipient_entities[0].country_of_registration == "China"
    assert payload.recipient_entities[0].government_control is True


def test_rule_engine_classification() -> None:
    """Verify rule engine classifies data and entities correctly."""
    from backend.modules.us_14117.rule_engine import run_rule_engine

    # RED scenario
    result = run_rule_engine(_build_red_scenario_payload())
    assert result.traffic_light.overall_light == "RED"
    assert result.traffic_light.is_prohibited is True
    assert result.transaction_classification["involves_covered_person"] is True
    assert any(
        dc["doj_category"] == "human_genomic_data" and dc["threshold_hit"]
        for dc in result.data_classifications
    )

    # YELLOW scenario
    result_yellow = run_rule_engine(_build_yellow_scenario_payload())
    assert result_yellow.traffic_light.overall_light == "YELLOW"
    assert result_yellow.traffic_light.is_restricted is True
    assert result_yellow.security_gap_report["missing"]  # has missing measures

    # GREEN scenario
    result_green = run_rule_engine(_build_green_scenario_payload())
    assert result_green.traffic_light.overall_light == "GREEN"
    assert result_green.traffic_light.is_prohibited is False
    assert result_green.traffic_light.is_restricted is False


def test_mixed_scenario_worst_case() -> None:
    """Verify worst-case resolution when multiple entities/data have different results."""
    payload = US14117Request.model_validate({
        "project_name": "混合场景测试",
        "transaction_description": "测试混合实体和数据场景",
        "transaction_type": "vendor_agreement",
        "data_items": [
            {
                "data_item_name": "全基因组",
                "data_description": "人类基因组数据",
                "us_person_count": 10000,
                "data_subject_type": "patient",
                "doj_data_category": "human_genomic_data",
                "is_government_related": False,
            },
            {
                "data_item_name": "邮箱地址",
                "data_description": "普通邮箱",
                "us_person_count": 5000,
                "data_subject_type": "consumer",
                "is_government_related": False,
            },
        ],
        "recipient_entities": [
            {
                "entity_name": "中国实体A",
                "country_of_registration": "China",
                "governing_law": "中国法律",
                "government_control": True,
                "entity_role": "processor",
            },
            {
                "entity_name": "英国实体B",
                "country_of_registration": "United Kingdom",
                "governing_law": "英格兰法律",
                "government_control": False,
                "entity_role": "processor",
            },
        ],
        "access_persons": [],
        "security_measures": [],
        "attachments": [],
        "company_name": "测试公司",
    })

    from backend.modules.us_14117.rule_engine import run_rule_engine
    result = run_rule_engine(payload)

    # Worst case should be RED (genomic data + covered person)
    assert result.traffic_light.overall_light == "RED"
    # Per-entity: China entity should be RED, UK entity could be GREEN
    assert "中国实体A" in result.traffic_light.per_entity_lights
    assert result.traffic_light.per_entity_lights["中国实体A"] == "RED"


def test_fact_builder_extracts_all_categories() -> None:
    """Verify fact builder extracts facts across all categories."""
    from backend.modules.us_14117.fact_builder import build_us_14117_facts
    from backend.modules.us_14117.rule_engine import run_rule_engine

    payload = _build_red_scenario_payload()
    rule_result = run_rule_engine(payload)
    facts = build_us_14117_facts(payload, rule_result)

    fact_ids = {f.fact_id for f in facts}
    assert any("request-project-name" in fid for fid in fact_ids)
    assert any("classification" in fid for fid in fact_ids)
    assert any("assessment" in fid for fid in fact_ids)
    assert any("traffic-light" in fid for fid in fact_ids)

    # Derived facts should have source_type="derived"
    derived = [f for f in facts if f.source_type == "derived"]
    assert len(derived) > 0


def test_issue_builder_identifies_expected_issues() -> None:
    """Verify issue builder creates correct issues for each scenario."""
    from backend.modules.us_14117.fact_builder import build_us_14117_facts
    from backend.modules.us_14117.issue_builder import build_us_14117_issues
    from backend.modules.us_14117.rule_engine import run_rule_engine

    # RED scenario
    payload = _build_red_scenario_payload()
    rule_result = run_rule_engine(payload)
    facts = build_us_14117_facts(payload, rule_result)
    issues = build_us_14117_issues(facts, rule_result, [])

    issue_ids = {i.issue_id for i in issues}
    assert "US14117-ISSUE-PROHIBITED-TRANSACTION" in issue_ids
    assert any("COVERED" in iid for iid in issue_ids)
    assert any("THRESHOLD" in iid for iid in issue_ids)

    # GREEN scenario
    payload_green = _build_green_scenario_payload()
    rule_green = run_rule_engine(payload_green)
    facts_green = build_us_14117_facts(payload_green, rule_green)
    issues_green = build_us_14117_issues(facts_green, rule_green, [])

    green_issue_ids = {i.issue_id for i in issues_green}
    assert "US14117-ISSUE-NO-TRIGGER" in green_issue_ids


def test_evidence_builder_links_properly() -> None:
    """Verify evidence chain links issues to facts with correct confidence."""
    from backend.modules.us_14117.evidence_builder import build_us_14117_evidence
    from backend.modules.us_14117.fact_builder import build_us_14117_facts
    from backend.modules.us_14117.issue_builder import build_us_14117_issues
    from backend.modules.us_14117.rule_engine import run_rule_engine

    payload = _build_yellow_scenario_payload()
    rule_result = run_rule_engine(payload)
    facts = build_us_14117_facts(payload, rule_result)
    issues = build_us_14117_issues(facts, rule_result, [])
    updated_issues, evidence_chain = build_us_14117_evidence(facts, issues, [])

    assert len(evidence_chain) > 0
    for ev in evidence_chain:
        assert ev.evidence_id.startswith("US14117-EVIDENCE-")
        assert ev.claim
        assert ev.conclusion
        assert 0 <= ev.confidence <= 1.0
        assert len(ev.fact_refs) > 0


def test_output_files_generated() -> None:
    """Verify all expected output files are produced."""
    _install_test_templates()
    payload = _build_red_scenario_payload()
    service = US14117Service(llm_client=_DisabledLLM())
    result = service.generate_report(payload)

    expected_keys = [
        "markdown", "pdf", "xlsx", "zip",
        "issue_list_json", "evidence_chain_json", "facts_json",
        "rule_engine_result_json",
    ]
    for key in expected_keys:
        assert key in result.output_files, f"Missing output key: {key}"

    assert result.report_path.endswith(".md")
