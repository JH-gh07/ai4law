#!/usr/bin/env python3
"""Re-run all modules with LLM enabled, write fresh outputs to tmp/.

Usage: python scripts/rerun_all_modules.py [--modules pipia,dpia,us_14117,...]
"""

import json, sys, shutil, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def run_pipia():
    from backend.domains.cn.pipia.schema import PIPIARequest
    from backend.domains.cn.pipia.service import PIPIAService

    print("[pipia] Creating service with LLM...")
    svc = PIPIAService()
    payload = PIPIARequest.model_validate({
        "route_type": "scc_filing",
        "company_profile": {
            "company_name": "测试公司", "company_uscc": "91310000XXXXXXXXXX",
            "is_ciio": False, "processing_person_count": 230000,
            "outbound_pi_count": 46000, "outbound_spi_count": 2500,
            "industry": "互联网SaaS",
        },
        "transfer_context": {
            "purpose": "境外客服与系统运维",
            "recipient_name": "OceanStar Technology Inc.",
            "recipient_country_region": "美国加州",
            "legal_basis": "合同履行必要",
        },
        "personal_info_scope": {
            "pi_categories": ["账户信息", "联系方式", "日志信息"],
            "spi_categories": ["身份认证信息"],
            "subject_volume": 46000,
        },
        "rights_protection": {
            "notice_mechanism": "隐私政策+弹窗",
            "consent_mechanism": "单独同意",
            "dsar_channel": "privacy@example.com",
            "retention_policy": "到期删除+最短必要",
        },
        "emergency_plan": {
            "incident_response_sla_hours": 24,
            "escalation_path": "DPO -> 法务 -> 管理层",
        },
        "attachments": [{
            "file_role": "scc_contract",
            "file_name": "标准合同模板_v2.docx",
            "file_format": "docx",
            "storage_uri": "/uploads/scc_template_v2.docx",
            "size_bytes": 245760,
        }],
    })

    print("[pipia] Running generate_report...")
    result = svc.generate_report(payload)
    return save_output("pipia", result)


def run_dpia():
    from backend.domains.eu.dpia.schema import DPIARequest
    from backend.domains.eu.dpia.service import DPIAService

    print("[dpia] Creating service with LLM...")
    svc = DPIAService()
    payload = DPIARequest.model_validate({
        "project_name": "员工健康评估系统",
        "project_description": "收集并处理员工健康数据用于健康风险评估和保险计划定制",
        "project_goal": "通过分析员工健康数据，优化企业健康保险方案并降低整体医疗成本",
        "processing_flow_description": "员工通过Web平台提交健康问卷和体检报告 → 系统对数据进行脱敏处理后存入加密数据库 → 健康分析引擎基于风险模型生成个人健康评分 → HR部门查看聚合报告（不含个人标识信息）→ 保险合作方接收匿名化统计数据用于保费计算",
        "company_name": "HealthTech GmbH",
        "company_country": "Germany",
        "data_controller": "HealthTech GmbH",
        "data_categories": ["health data", "biometric data", "employee records"],
        "special_category_data": True,
        "data_subjects": ["employees", "contractors"],
        "subject_count": 1500,
        "processing_purpose": "Employee health risk assessment and insurance plan optimization",
        "legal_basis": "Explicit consent (Article 9(2)(a)), Employment obligations (Article 88)",
        "data_recipients": ["Third-party health analytics provider - US-based"],
        "cross_border_transfers": True,
        "third_countries": ["United States"],
        "safeguards": ["Standard Contractual Clauses (EU 2021/914)"],
        "retention_period": "Duration of employment + 10 years",
        "technical_measures": ["Encryption at rest (AES-256)", "Encryption in transit (TLS 1.3)", "Access controls (RBAC)", "Audit logging"],
        "organizational_measures": ["Data protection training", "DPO appointed", "Regular audits", "DPIA review cycle - 2 years"],
        "risk_assessment": {
            "likelihood": "medium",
            "impact": "high",
            "identified_risks": ["Unauthorized access to health data", "Cross-border transfer to non-adequate country", "Insufficient consent mechanisms"],
        },
        "attachments": [],
    })

    print("[dpia] Running generate_report...")
    result = svc.generate_report(payload)
    return save_output("dpia", result)


def run_us_14117():
    from backend.domains.us.eo14117.schema import US14117Request
    from backend.domains.us.eo14117.service import US14117Service

    print("[us_14117] Creating service with LLM...")
    svc = US14117Service()
    payload = US14117Request.model_validate({
        "company_name": "SinoGenomics Inc.",
        "project_name": "US-China Genomic Research Partnership",
        "transaction_description": "Joint research collaboration involving transfer of human genomic sequences and health metadata from US-based subjects to Chinese research institutions for bioinformatics analysis and drug target discovery",
        "transaction_type": "joint_research",
        "data_items": [
            {"data_item_name": "human genomic sequences", "doj_category": "human omic data",
             "us_person_count": 5000, "bulk_threshold": 1000, "threshold_hit": True},
            {"data_item_name": "health metadata", "doj_category": "human biospecimen data",
             "us_person_count": 3000, "bulk_threshold": 100, "threshold_hit": True},
        ],
        "recipient_entities": [
            {"entity_name": "Beijing Genomics Institute", "country_of_registration": "China", "role": "research_partner"},
            {"entity_name": "Wuhan University Lab", "country_of_registration": "China", "role": "academic_collaborator"},
        ],
        "attachments": [],
    })

    print("[us_14117] Running generate_report...")
    result = svc.generate_report(payload)
    return save_output("us_14117", result)


def run_cpra():
    from backend.domains.us.cpra.schema import CPRARequest
    from backend.domains.us.cpra.service import CPRAService

    print("[cpra] Creating service with LLM...")
    svc = CPRAService()
    payload = CPRARequest.model_validate({
        "company_name": "California Health Analytics Inc.",
        "assessment_type": "data_protection_assessment",
        "business_model": "B2C健康数据分析SaaS平台，年收入约2500万美元，通过分析消费者健康数据提供个性化健康风险评估和保险推荐服务",
        "data_lifecycle": "数据通过Web表单和第三方健康API收集 → 实时流处理管道进行匿名化 → 存储在AWS GovCloud加密数据库中 → 分析引擎生成健康评分 → 结果通过安全API分发至合作伙伴 → 保留期7年后自动删除",
        "notice_and_consent": "在用户注册时通过分层隐私声明收集明确同意，提供加州消费者隐私声明（CCPA通知），支持按数据类别选择性同意，每12个月重新确认",
        "consumer_rights_process": "通过privacy@ca-health.com邮箱和在线门户接收DSAR请求，45天内响应，支持数据访问/删除/更正/可携带性请求，身份验证通过双因素认证",
        "opt_out_and_sale_sharing": "网站首页提供'Do Not Sell or Share My Personal Information'链接，支持Global Privacy Control信号自动响应，15天内处理退出请求",
        "data_processing_activities": [
            {"activity_name": "health_risk_modeling", "data_categories": ["health_information", "geolocation"],
             "purpose": "Developing health risk prediction models", "sensitive_data": True},
            {"activity_name": "consumer_profiling", "data_categories": ["personal_identifiers", "commercial_information"],
             "purpose": "Targeted health plan recommendations", "sensitive_data": False},
        ],
        "attachments": [{
            "file_role": "privacy_policy",
            "file_name": "CA_Health_Privacy_Policy_2026.pdf",
            "file_format": "pdf",
            "storage_uri": "/uploads/privacy_policy_2026.pdf",
            "size_bytes": 512000,
        }],
    })

    print("[cpra] Running generate_report...")
    result = svc.generate_report(payload)
    return save_output("cpra", result)


def save_output(module: str, result: object) -> dict:
    out_dir = ROOT / "tmp" / module
    out_dir.mkdir(parents=True, exist_ok=True)

    info = {"module": module, "state": getattr(result, "state", "N/A"),
            "chapters": len(getattr(result, "chapters", [])),
            "report_path": getattr(result, "report_path", "")}

    # Find and copy markdown
    output_files = getattr(result, "output_files", {}) or {}
    md_path = output_files.get("markdown", "")
    if md_path:
        md_file = Path(md_path)
        if md_file.exists():
            dest = out_dir / "markdown.md"
            shutil.copy2(md_file, dest)
            text = dest.read_text(encoding="utf-8")
            info["markdown_lines"] = len(text.split("\n"))
            info["markdown_chars"] = len(text)
            info["has_placeholder"] = "占位" in text or "LLM未配置" in text
            info["has_cit_truncated"] = "{{CIT-" in text
            print(f"[{module}] markdown: {info['markdown_lines']}L/{info['markdown_chars']}c, "
                  f"placeholder={info['has_placeholder']}, cit_truncated={info['has_cit_truncated']}")
        else:
            print(f"[{module}] markdown file not found at {md_path}")
    else:
        print(f"[{module}] no markdown in output_files: {list(output_files.keys())[:5]}")

    # Write _result.json
    try:
        result_json = out_dir / "_result.json"
        data = result.model_dump(mode="json") if hasattr(result, "model_dump") else {"state": str(getattr(result, "state", ""))}
        # For _result.json, keep chapter content but strip to first 500 chars each
        if "chapters" in data:
            for ch in data["chapters"]:
                if isinstance(ch, dict) and "content" in ch:
                    ch["content"] = ch["content"][:500] + ("..." if len(ch.get("content","") or "") > 500 else "")
        result_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[{module}] _result.json write error: {e}")

    print(f"[{module}] state={info['state']}, chapters={info['chapters']}")
    return info


def run_eu_scc():
    from backend.domains.eu.scc_review.schema import SCCReviewRequest
    from backend.domains.eu.scc_review.service import EU_SCCService

    print("[eu_scc] Creating service with LLM...")
    svc = EU_SCCService()
    payload = SCCReviewRequest.model_validate({
        "project_name": "SCC Compliance Review",
        "scc_text": (
            "STANDARD CONTRACTUAL CLAUSES\n\n"
            "SECTION I\nClause 1\nPurpose and scope\n"
            "(a) The purpose of these standard contractual clauses is to ensure "
            "compliance with the requirements of Regulation (EU) 2016/679...\n\n"
            "Clause 7\nDocking clause\n"
            "(a) Any entity that is not a Party to these Clauses may, with the "
            "agreement of the Parties, accede to these Clauses at any time...\n\n"
            "Clause 14\nLocal laws and practices affecting compliance with the Clauses\n"
            "(a) The Parties warrant that they have no reason to believe that the laws "
            "and practices in the third country of destination applicable to the "
            "processing of the personal data by the data importer...\n\n"
            "Clause 15\nObligations of the data importer in case of access by public authorities\n"
            "(a) The data importer shall promptly notify the data exporter if it "
            "receives a legally binding request from a public authority...\n\n"
        ),
        "declared_module_type": "Module Two",
        "exporter_role": "controller",
        "importer_role": "processor",
        "has_tia": True,
        "has_supplementary_measures": True,
        "company_name": "DataComply Europe GmbH",
    })

    print("[eu_scc] Running generate_report...")
    result = svc.generate_report(payload)
    return save_output("eu_scc", result)


def main():
    argv = sys.argv[1:]
    default_modules = ["pipia", "dpia", "us_14117", "cpra"]
    if not argv:
        modules = default_modules
    elif argv[0] == "--modules":
        modules = [m for m in argv[1].split(",") if m.strip()] if len(argv) > 1 else default_modules
    else:
        modules = [m for m in argv[0].split(",") if m.strip()]
    results = {}

    runners = {
        "pipia": run_pipia,
        "dpia": run_dpia,
        "us_14117": run_us_14117,
        "cpra": run_cpra,
        "eu_scc": run_eu_scc,
    }

    for mod in modules:
        mod = mod.strip()
        if mod not in runners:
            print(f"[SKIP] Unknown module: {mod}")
            continue
        print(f"\n{'='*60}")
        print(f"  Re-running: {mod}")
        print(f"{'='*60}")
        try:
            results[mod] = runners[mod]()
        except Exception as e:
            print(f"[{mod}] FAILED: {e}")
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for mod, info in results.items():
        flags = []
        if info.get("has_placeholder"): flags.append("⚠PLACEHOLDER")
        if info.get("has_cit_truncated"): flags.append("⚠CIT")
        lines = info.get("markdown_lines", "?")
        chars = info.get("markdown_chars", "?")
        print(f"  {mod:15s} {str(lines):>4s}L {str(chars):>5s}c  {' '.join(flags) if flags else '✅'}")

    print("\nDone. Run cross-verification:")
    print("  python scripts/check_cross_verification.py --output tmp/verify/cross_verification_rerun.json")


if __name__ == "__main__":
    main()
