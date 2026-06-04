#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common.knowledge.registry import build_source_registry_from_sources_csv

DOC_ROOT = ROOT / "doc"
KNOWLEDGE_ROOT = DOC_ROOT / "knowledge"
LEGACY_KNOWLEDGE_ROOT = KNOWLEDGE_ROOT
SPEC_ROOT = DOC_ROOT / "数规通功能路径描述（含reference）、流程描述、测试案例"

NEW_INDEX_DIR = KNOWLEDGE_ROOT / "_index"
NEW_REGISTRY_DIR = KNOWLEDGE_ROOT / "_registry"
NEW_EVALUATION_DIR = KNOWLEDGE_ROOT / "_evaluation"

MODULES = {
    "cn-diagnosis": {
        "specs": [
            SPEC_ROOT / "中国数据出境路径/任务1：“合规路径诊断”路径描述及测试案例/“合规路径诊断”功能说明与路径描述（标注Reference）.docx",
            SPEC_ROOT / "中国数据出境路径/任务1：“合规路径诊断”路径描述及测试案例/我国数据出境三条路径的流程描述.docx",
        ],
        "tests": [
            SPEC_ROOT / "中国数据出境路径/任务1：“合规路径诊断”路径描述及测试案例/“合规路径诊断”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "中国数据出境路径/中国数据出境路径reference库/中国数据出境路径reference文件库",
    },
    "cn-assessment": {
        "specs": [
            SPEC_ROOT / "中国数据出境路径/任务2：“安全评估路径”路径描述及测试案例/“安全评估路径”功能说明与路径描述（标注Reference）.docx",
        ],
        "tests": [
            SPEC_ROOT / "中国数据出境路径/任务2：“安全评估路径”路径描述及测试案例/“安全评估路径”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "中国数据出境路径/中国数据出境路径reference库/中国数据出境路径reference文件库",
    },
    "cn-review": {
        "specs": [
            SPEC_ROOT / "中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”功能说明与路径描述.docx",
        ],
        "tests": [
            SPEC_ROOT / "中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出/“文档专项智能审查”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出",
    },
    "cn-pipia": {
        "specs": [
            SPEC_ROOT / "中国数据出境路径/任务3：“认证标准合同路径”路径描述及测试案例/“认证_标准合同路径”功能说明与路径描述（标注Reference）.docx",
        ],
        "tests": [
            SPEC_ROOT / "中国数据出境路径/任务3：“认证标准合同路径”路径描述及测试案例/“认证_标准合同路径”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "中国数据出境路径/中国数据出境路径reference库/中国数据出境路径reference文件库",
    },
    "eu-scc": {
        "specs": [
            SPEC_ROOT / "欧盟数据出境路径/任务1：“SCC审查”路径描述及测试案例/“SCC审查”功能说明与路径描述.docx",
        ],
        "tests": [
            SPEC_ROOT / "欧盟数据出境路径/任务1：“SCC审查”路径描述及测试案例/“SCC审查”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "欧盟数据出境路径/欧盟数据出境路径Reference库/欧盟数据出境reference文件库",
    },
    "eu-bcr": {
        "specs": [
            SPEC_ROOT / "欧盟数据出境路径/任务2：“BCR审核”路径描述及测试案例/“BCR审核”功能说明与路径描述.docx",
        ],
        "tests": [
            SPEC_ROOT / "欧盟数据出境路径/任务2：“BCR审核”路径描述及测试案例/“BCR审核”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "欧盟数据出境路径/欧盟数据出境路径Reference库/欧盟数据出境reference文件库",
    },
    "eu-dpia": {
        "specs": [
            SPEC_ROOT / "欧盟数据出境路径/任务3：“DPIA草案生成”路径描述及测试案例/“DPIA草案生成”功能说明与路径描述.docx",
        ],
        "tests": [
            SPEC_ROOT / "欧盟数据出境路径/任务3：“DPIA草案生成”路径描述及测试案例/“DPIA草案生成”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "欧盟数据出境路径/欧盟数据出境路径Reference库/欧盟数据出境reference文件库",
    },
    "eu-tia": {
        "specs": [
            SPEC_ROOT / "欧盟数据出境路径/任务4：“TIA草案生成”路径描述及测试案例/“TIA草案生成”功能说明与路径描述.docx",
        ],
        "tests": [
            SPEC_ROOT / "欧盟数据出境路径/任务4：“TIA草案生成”路径描述及测试案例/“TIA草案生成”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "欧盟数据出境路径/欧盟数据出境路径Reference库/欧盟数据出境reference文件库",
    },
    "us-14117": {
        "specs": [
            SPEC_ROOT / "美国（加州）数据出境路径/任务1：“14117行政令合规”路径描述及测试案例/“14117行政令合规”功能说明与路径描述.docx",
        ],
        "tests": [
            SPEC_ROOT / "美国（加州）数据出境路径/任务1：“14117行政令合规”路径描述及测试案例/“14117行政令合规”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "美国（加州）数据出境路径/美国数据出境路径Reference库/美国数据出境路径reference文件库",
    },
    "us-cpra": {
        "specs": [
            SPEC_ROOT / "美国（加州）数据出境路径/任务2：“CPRA合规”路径描述及测试案例/“CPRA合规”功能说明与路径描述（标注Reference）.docx",
        ],
        "tests": [
            SPEC_ROOT / "美国（加州）数据出境路径/任务2：“CPRA合规”路径描述及测试案例/“CPRA合规”测试案例及预期输出.docx",
        ],
        "references_dir": SPEC_ROOT / "美国（加州）数据出境路径/美国数据出境路径Reference库/美国数据出境路径reference文件库",
    },
}

RAW_MODULE_MAP = {
    "doc/knowledge/raw/cn_regulations": ["cn-diagnosis", "cn-assessment", "cn-review", "cn-pipia"],
    "doc/knowledge/raw/eu_regulations": ["eu-scc", "eu-bcr", "eu-dpia", "eu-tia"],
    "doc/knowledge/raw/us_regulations": ["us-14117", "us-cpra"],
}

CASE_ROUTE_KEYWORDS = {
    "eu_gdpr_art35": "eu-dpia",
    "eu_gdpr_art47": "eu-bcr",
    "eu_edpb_012020": "eu-tia",
    "us_cpra": "us-cpra",
    "us_eo_14117": "us-14117",
}

SOURCE_MODULE_OVERRIDES = {
    "CN-LAW-001": "cn-diagnosis",
    "CN-LAW-002": "cn-diagnosis",
    "CN-LAW-003": "cn-diagnosis",
    "CN-REG-004": "cn-assessment",
    "CN-REG-005": "cn-review",
    "CN-REG-006": "cn-diagnosis",
    "CN-REG-007": "cn-diagnosis",
    "CN-REG-008": "cn-diagnosis",
    "CN-GUIDE-009": "cn-assessment",
    "CN-GUIDE-010": "cn-review",
    "CN-QA-011": "cn-review",
    "CN-QA-012": "cn-assessment",
    "CN-QA-013": "cn-assessment",
    "CN-OPS-014": "cn-assessment",
    "CN-GOV-015": "cn-review",
    "EU-LAW-001": "eu-dpia",
    "EU-GUIDE-002": "eu-tia",
    "US-FED-001": "us-14117",
    "US-CA-001": "us-cpra",
}

CASE_FILE_MODULE_OVERRIDES = {
    "beijing_2024_first_security_assessment_and_standard_contract_case.html": "cn-assessment",
    "beijing_2025_03_bayer_green_channel_case.html": "cn-assessment",
    "beijing_2025_03_crossborder_reform_2_0_stats.html": "cn-assessment",
    "beijing_2025_06_automotive_ota_crossborder_case.html": "cn-review",
    "gdzf_2024_guangzhou_hotel_crossborder_personal_info_case.html": "cn-review",
    "gdjubao_2022_guangzhou_personal_info_typical_cases.html": "cn-review",
    "cac_2025_04_09_policy_qa.html": "cn-assessment",
    "eu_gdpr_art35_reference.md": "eu-dpia",
    "eu_gdpr_art47_bcr_reference.md": "eu-bcr",
    "eu_edpb_012020_tia_reference.md": "eu-tia",
    "us_eo_14117_reference.md": "us-14117",
    "us_cpra_reference.md": "us-cpra",
}

CASE_ID_MODULE_OVERRIDES = {
    "CN-CASE-001": "cn-assessment",
    "CN-CASE-002": "cn-assessment",
    "CN-CASE-003": "cn-assessment",
    "CN-CASE-004": "cn-review",
    "CN-CASE-005": "cn-review",
    "CN-CASE-006": "cn-review",
    "CN-CASE-007": "cn-assessment",
    "EU-CASE-001": "eu-dpia",
    "EU-CASE-002": "eu-bcr",
    "EU-CASE-003": "eu-tia",
    "US-CASE-001": "us-14117",
    "US-CASE-002": "us-cpra",
}

SOURCE_DETAIL_OVERRIDES = {
    "CN-LAW-001": {
        "suitable_for": "路径判断、文档审查、评估申报",
        "report_usage": "可直接引用条文号",
        "summary": "网络安全法是中国数据跨境合规的基础法之一，用于界定关键信息基础设施、网络运行安全义务和跨境场景中的底层安全要求。",
    },
    "CN-LAW-002": {
        "suitable_for": "路径判断、评估申报、文档审查",
        "report_usage": "可直接引用条文号",
        "summary": "数据安全法提供数据分类分级、重要数据识别和数据安全治理的一般框架，是判断重要数据出境义务的核心依据。",
    },
    "CN-LAW-003": {
        "suitable_for": "路径判断、文档审查、评估申报、标准合同",
        "report_usage": "可直接引用条文号",
        "summary": "个人信息保护法是个人信息跨境处理的总法基础，用于判断个人信息定义、敏感个人信息、单独同意、个人权利和跨境提供规则。",
    },
    "CN-REG-004": {
        "suitable_for": "评估申报",
        "report_usage": "可直接引用条文号",
        "summary": "《数据出境安全评估办法》是中国安全评估路径的核心规范，用于判定触发门槛、申报义务和审查重点。",
    },
    "CN-REG-005": {
        "suitable_for": "标准合同、文档审查",
        "report_usage": "可直接引用条文号",
        "summary": "《个人信息出境标准合同办法》规定了标准合同路径的适用条件、备案义务和配套评估要求，是标准合同审查与备案的主依据。",
    },
    "CN-REG-006": {
        "suitable_for": "路径判断",
        "report_usage": "可直接引用条文号",
        "summary": "《促进和规范数据跨境流动规定》发布页用于确认新规出台背景与生效口径，可辅助说明路径调整依据。",
    },
    "CN-REG-007": {
        "suitable_for": "路径判断、评估申报、标准合同",
        "report_usage": "可直接引用条文号",
        "summary": "《促进和规范数据跨境流动规定》全文是当前中国数据出境三条路径分流判断的核心依据，应用于豁免、标准合同和安全评估的路径判断。",
    },
    "CN-REG-008": {
        "suitable_for": "路径判断、文档审查",
        "report_usage": "可直接引用条文号",
        "summary": "《网络数据安全管理条例》补充了网络数据处理活动中的安全治理边界，适合用于合同条款审查和一般性合规论证。",
    },
    "CN-GUIDE-009": {
        "suitable_for": "评估申报",
        "report_usage": "可附带解释说明",
        "summary": "《数据出境安全评估申报指南（第三版）》细化了申报流程、材料准备和表单口径，是安全评估交付物组织的重要操作性依据。",
    },
    "CN-GUIDE-010": {
        "suitable_for": "标准合同、文档审查",
        "report_usage": "可附带解释说明",
        "summary": "《个人信息出境标准合同备案指南（第二版）》细化了标准合同备案流程、材料要求和格式口径，用于支持标准合同路径落地。",
    },
    "CN-QA-011": {
        "suitable_for": "标准合同、文档审查",
        "report_usage": "可辅助解释条文，但不宜单独作为核心依据",
        "summary": "《个人信息出境标准合同办法》答记者问用于解释标准合同路径的适用边界、制度目的和备案实践中的常见理解问题。",
    },
    "CN-QA-012": {
        "suitable_for": "评估申报、路径判断",
        "report_usage": "可辅助解释条文，但不宜单独作为核心依据",
        "summary": "2025年4月政策问答提供阶段性统计和政策解释，可用于补充说明安全评估路径的监管关注点与实践趋势。",
    },
    "CN-QA-013": {
        "suitable_for": "评估申报、路径判断",
        "report_usage": "可辅助解释条文，但不宜单独作为核心依据",
        "summary": "2025年5月政策问答提供更新的政策解释口径和阶段性数据，适合作为安全评估项目中的辅助说明材料。",
    },
    "CN-OPS-014": {
        "suitable_for": "评估申报、标准合同",
        "report_usage": "用于流程执行，不直接作为法律论证",
        "summary": "各地省级网信部门申报/备案联系方式属于流程执行层资料，用于项目落地和实际申报沟通，不作为法律结论主依据。",
    },
    "CN-GOV-015": {
        "suitable_for": "标准合同、文档审查",
        "report_usage": "可附带解释说明",
        "summary": "中国政府网转载版《个人信息出境标准合同办法》可作为交叉校验口径，用于提高标准合同条文引用的稳健性。",
    },
    "EU-LAW-001": {
        "suitable_for": "DPIA草案、BCR审核、SCC审查、TIA草案",
        "report_usage": "可直接引用条文号",
        "summary": "GDPR 是欧盟跨境数据保护合规的总法基础，用于 DPIA、BCR、SCC 和 TIA 等多个模块中的核心法条引用。",
    },
    "EU-GUIDE-002": {
        "suitable_for": "TIA草案、SCC审查、BCR审核",
        "report_usage": "可附带解释说明",
        "summary": "EDPB Recommendations 01/2020 提供了 transfer impact assessment 和补充措施分析框架，是 TIA 草案生成和欧盟传输审查的重要解释性依据。",
    },
    "US-FED-001": {
        "suitable_for": "EO14117合规",
        "report_usage": "可直接引用条文号",
        "summary": "美国司法部 EO 14117 实施规则用于界定受限交易、受规制对象和对华敏感数据流动限制，是美国路径中的核心联邦依据。",
    },
    "US-CA-001": {
        "suitable_for": "CPRA合规",
        "report_usage": "可直接引用条文号",
        "summary": "California CPRA/CCPA 是加州隐私合规的核心法律依据，用于解释消费者权利、敏感个人信息限制使用和企业义务。",
    },
}

CASE_DETAIL_OVERRIDES = {
    "CN-CASE-001": {
        "suitable_for": "评估申报、标准合同、路径判断",
        "summary": "该案例展示了中国首个公开落地的安全评估与标准合同实践，可用于说明路径选择与落地办理的现实样态。",
    },
    "CN-CASE-002": {
        "suitable_for": "评估申报",
        "summary": "拜耳案例适合作为安全评估绿色通道与企业申报落地节奏的实践说明材料。",
    },
    "CN-CASE-003": {
        "suitable_for": "评估申报、标准合同",
        "summary": "北京数据跨境便利化2.0统计材料适合作为实践趋势、场景覆盖面和制度推进效果的辅助说明。",
    },
    "CN-CASE-004": {
        "suitable_for": "标准合同、文档审查",
        "summary": "汽车OTA场景案例可用于说明标准合同备案类场景的行业化适用路径和办理方式。",
    },
    "CN-CASE-005": {
        "suitable_for": "文档审查、一般合规",
        "summary": "广州互联网法院判决案例用于补充个人信息跨境争议中的司法观点，但并非标准合同备案的直接实践样本。",
    },
    "CN-CASE-006": {
        "suitable_for": "文档审查、一般合规",
        "summary": "典型案例集适合作为个人信息保护审查中的司法态度参考，不宜直接替代跨境路径规范依据。",
    },
    "CN-CASE-007": {
        "suitable_for": "评估申报、路径判断",
        "summary": "政策问答中的统计口径可用于说明全国层面的安全评估推进情况和监管重点变化。",
    },
    "EU-CASE-001": {
        "suitable_for": "DPIA草案",
        "summary": "GDPR Article 35 参考材料用于 DPIA 触发条件、必要性与相称性分析的案例化说明。",
    },
    "EU-CASE-002": {
        "suitable_for": "BCR审核",
        "summary": "GDPR Article 47 / BCR 参考材料用于 BCR 审核中的条文映射和结构性要求说明。",
    },
    "EU-CASE-003": {
        "suitable_for": "TIA草案",
        "summary": "EDPB 01/2020 参考材料用于 TIA 方法论、补充措施和第三国法律分析步骤说明。",
    },
    "US-CASE-001": {
        "suitable_for": "EO14117合规",
        "summary": "EO 14117 参考材料用于美国联邦限制交易规则和敏感个人数据类别的解释说明。",
    },
    "US-CASE-002": {
        "suitable_for": "CPRA合规",
        "summary": "CPRA 参考材料用于说明加州敏感个人信息限制使用和消费者权利实现路径。",
    },
}

JURISDICTION_LABELS = {
    "cn": "中国",
    "eu": "欧盟",
    "us": "美国",
}

DOC_TYPE_CATEGORY_MAP = {
    "law": "核心法律",
    "administrative_regulation": "部门规章",
    "guide": "官方指南",
    "qa": "官方问答",
    "contact_list": "流程清单",
    "gov_republish": "官方转载",
}

USAGE_MAP = {
    "P0": "审查基准",
    "P1": "条文匹配",
    "P2": "知识增强",
    "P3": "参考引用",
}

AUTHORITY_MAP = {
    "official": "high",
    "authoritative": "high",
    "high": "high",
    "recommended": "medium",
    "medium": "medium",
    "low": "low",
}

PUBLISHER_MAP = {
    "CAC": "国家互联网信息办公室",
    "gov.cn": "中国政府网",
    "EUR-Lex": "EUR-Lex",
    "EDPB": "欧洲数据保护委员会",
    "Federal Register": "Federal Register",
    "California AG": "California Attorney General",
    "TJCAC(转载中国网信网)": "天津网信办（转载中国网信网）",
}

VISIBLE_SOURCE_FILENAME_MAP = {
    "网络安全法.pdf": ["CN-LAW-001"],
    "中华人民共和国数据安全法.pdf": ["CN-LAW-002"],
    "中华人民共和国个人信息保护法.pdf": ["CN-LAW-003"],
    "数据出境安全评估办法.pdf": ["CN-REG-004"],
    "个人信息出境标准合同办法_中央网络安全和信息化委员会办公室.pdf": ["CN-REG-005"],
    "促进和规范数据跨境流动规定_中央网络安全和信息化委员会办公室.pdf": ["CN-REG-006", "CN-REG-007"],
    "网络数据安全管理条例.pdf": ["CN-REG-008"],
    "数据出境安全评估申报指南（第三版） (1).docx": ["CN-GUIDE-009"],
    "数据出境安全评估申报指南（第三版） (2).docx": ["CN-GUIDE-009"],
    "个人信息出境标准合同备案指南（第二版） (1).docx": ["CN-GUIDE-010"],
    "CELEX_32016R0679_EN_TXT.pdf": ["EU-LAW-001"],
    "edpb_recommendations_202001vo.2.0_supplementarymeasurestransferstools_en.pdf": ["EU-GUIDE-002"],
    "2024-04573.pdf": ["US-FED-001"],
    "The California Privacy Rights Act of 2020 (1).pdf": ["US-CA-001"],
}


@dataclass
class MigrationSummary:
    copied_specs: int = 0
    copied_tests: int = 0
    copied_references: int = 0
    copied_snapshots: int = 0
    generated_index_rows: int = 0
    generated_case_rows: int = 0


SPEC_MANIFEST_ROWS = [
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务1：“合规路径诊断”路径描述及测试案例/“合规路径诊断”功能说明与路径描述（标注Reference）.docx",
        "asset_type": "spec",
        "jurisdiction_family": "cn",
        "target_module": "cn-diagnosis",
        "target_layer": "spec",
        "target_path": "doc/knowledge/cn-diagnosis/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务1：“合规路径诊断”路径描述及测试案例/“合规路径诊断”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "cn",
        "target_module": "cn-diagnosis",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/cn-diagnosis/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务1：“合规路径诊断”路径描述及测试案例/我国数据出境三条路径的流程描述.docx",
        "asset_type": "flow_spec",
        "jurisdiction_family": "cn",
        "target_module": "cn-diagnosis",
        "target_layer": "spec",
        "target_path": "doc/knowledge/cn-diagnosis/spec.md",
        "sync_status": "synced",
        "notes": "流程说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务2：“安全评估路径”路径描述及测试案例/“安全评估路径”功能说明与路径描述（标注Reference）.docx",
        "asset_type": "spec",
        "jurisdiction_family": "cn",
        "target_module": "cn-assessment",
        "target_layer": "spec",
        "target_path": "doc/knowledge/cn-assessment/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务2：“安全评估路径”路径描述及测试案例/“安全评估路径”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "cn",
        "target_module": "cn-assessment",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/cn-assessment/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务3：“认证标准合同路径”路径描述及测试案例/“认证_标准合同路径”功能说明与路径描述（标注Reference）.docx",
        "asset_type": "spec",
        "jurisdiction_family": "cn",
        "target_module": "cn-pipia",
        "target_layer": "spec",
        "target_path": "doc/knowledge/cn-pipia/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务3：“认证标准合同路径”路径描述及测试案例/“认证_标准合同路径”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "cn",
        "target_module": "cn-pipia",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/cn-pipia/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”功能说明与路径描述.docx",
        "asset_type": "spec",
        "jurisdiction_family": "cn",
        "target_module": "cn-review",
        "target_layer": "spec",
        "target_path": "doc/knowledge/cn-review/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出/“文档专项智能审查”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "cn",
        "target_module": "cn-review",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/cn-review/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出/个人信息出境标准合同【模板】.docx",
        "asset_type": "template_sample",
        "jurisdiction_family": "cn",
        "target_module": "cn-review",
        "target_layer": "references",
        "target_path": "doc/knowledge/cn-review/references/个人信息出境标准合同【模板】.docx",
        "sync_status": "synced",
        "notes": "保留为文审样例模板",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出/数据处理协议样例.pdf",
        "asset_type": "sample_doc",
        "jurisdiction_family": "cn",
        "target_module": "cn-review",
        "target_layer": "references",
        "target_path": "doc/knowledge/cn-review/references/数据处理协议样例.pdf",
        "sync_status": "synced",
        "notes": "保留为文审样例文书",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出/数据安全及保密协议（模板） (1).docx",
        "asset_type": "template_sample",
        "jurisdiction_family": "cn",
        "target_module": "cn-review",
        "target_layer": "references",
        "target_path": "doc/knowledge/cn-review/references/数据安全及保密协议（模板） (1).docx",
        "sync_status": "synced",
        "notes": "保留为文审样例模板",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出/隐私政策样例.PNG",
        "asset_type": "sample_image",
        "jurisdiction_family": "cn",
        "target_module": "cn-review",
        "target_layer": "references",
        "target_path": "doc/knowledge/cn-review/references/隐私政策样例.PNG",
        "sync_status": "synced",
        "notes": "保留为文审图像样例",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/中国数据出境路径reference库/中国数据出境路径Reference库清单.docx",
        "asset_type": "reference_catalog",
        "jurisdiction_family": "cn",
        "target_module": "shared-cn",
        "target_layer": "_index",
        "target_path": "doc/knowledge/_index/spec_asset_manifest.csv",
        "sync_status": "indexed_only",
        "notes": "作为来源清单依据，已纳入资产清单，不单独前端展示",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/中国数据出境路径/中国数据出境路径reference库/中国数据出境路径reference文件库/*",
        "asset_type": "reference_source",
        "jurisdiction_family": "cn",
        "target_module": "shared-cn",
        "target_layer": "references",
        "target_path": "doc/knowledge/cn-diagnosis|cn-assessment|cn-pipia/references",
        "sync_status": "partially_indexed",
        "notes": "原始依据文件已迁入模块 references，但仅核心条目进入 sources.csv",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务1：“SCC审查”路径描述及测试案例/“SCC审查”功能说明与路径描述.docx",
        "asset_type": "spec",
        "jurisdiction_family": "eu",
        "target_module": "eu-scc",
        "target_layer": "spec",
        "target_path": "doc/knowledge/eu-scc/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务1：“SCC审查”路径描述及测试案例/“SCC审查”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "eu",
        "target_module": "eu-scc",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/eu-scc/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务2：“BCR审核”路径描述及测试案例/“BCR审核”功能说明与路径描述.docx",
        "asset_type": "spec",
        "jurisdiction_family": "eu",
        "target_module": "eu-bcr",
        "target_layer": "spec",
        "target_path": "doc/knowledge/eu-bcr/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务2：“BCR审核”路径描述及测试案例/“BCR审核”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "eu",
        "target_module": "eu-bcr",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/eu-bcr/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务3：“DPIA草案生成”路径描述及测试案例/“DPIA草案生成”功能说明与路径描述.docx",
        "asset_type": "spec",
        "jurisdiction_family": "eu",
        "target_module": "eu-dpia",
        "target_layer": "spec",
        "target_path": "doc/knowledge/eu-dpia/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务3：“DPIA草案生成”路径描述及测试案例/“DPIA草案生成”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "eu",
        "target_module": "eu-dpia",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/eu-dpia/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务4：“TIA草案生成”路径描述及测试案例/“TIA草案生成”功能说明与路径描述.docx",
        "asset_type": "spec",
        "jurisdiction_family": "eu",
        "target_module": "eu-tia",
        "target_layer": "spec",
        "target_path": "doc/knowledge/eu-tia/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/任务4：“TIA草案生成”路径描述及测试案例/“TIA草案生成”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "eu",
        "target_module": "eu-tia",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/eu-tia/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/欧盟数据出境路径Reference库/欧盟数据出境路径Reference库清单.docx",
        "asset_type": "reference_catalog",
        "jurisdiction_family": "eu",
        "target_module": "shared-eu",
        "target_layer": "_index",
        "target_path": "doc/knowledge/_index/spec_asset_manifest.csv",
        "sync_status": "indexed_only",
        "notes": "作为来源清单依据，已纳入资产清单，不单独前端展示",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/欧盟数据出境路径/欧盟数据出境路径Reference库/欧盟数据出境reference文件库/*",
        "asset_type": "reference_source",
        "jurisdiction_family": "eu",
        "target_module": "shared-eu",
        "target_layer": "references",
        "target_path": "doc/knowledge/eu-scc|eu-bcr|eu-dpia|eu-tia/references",
        "sync_status": "partially_indexed",
        "notes": "原始依据文件已迁入模块 references，但仅核心条目进入 sources.csv",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/美国（加州）数据出境路径/任务1：“14117行政令合规”路径描述及测试案例/“14117行政令合规”功能说明与路径描述.docx",
        "asset_type": "spec",
        "jurisdiction_family": "us",
        "target_module": "us-14117",
        "target_layer": "spec",
        "target_path": "doc/knowledge/us-14117/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/美国（加州）数据出境路径/任务1：“14117行政令合规”路径描述及测试案例/“14117行政令合规”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "us",
        "target_module": "us-14117",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/us-14117/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/美国（加州）数据出境路径/任务2：“CPRA合规”路径描述及测试案例/“CPRA合规”功能说明与路径描述（标注Reference）.docx",
        "asset_type": "spec",
        "jurisdiction_family": "us",
        "target_module": "us-cpra",
        "target_layer": "spec",
        "target_path": "doc/knowledge/us-cpra/spec.md",
        "sync_status": "synced",
        "notes": "功能说明并入模块 spec",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/美国（加州）数据出境路径/任务2：“CPRA合规”路径描述及测试案例/“CPRA合规”测试案例及预期输出.docx",
        "asset_type": "test_case",
        "jurisdiction_family": "us",
        "target_module": "us-cpra",
        "target_layer": "test-cases",
        "target_path": "doc/knowledge/us-cpra/test-cases.md",
        "sync_status": "synced",
        "notes": "测试案例并入模块 test-cases",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/美国（加州）数据出境路径/美国数据出境路径Reference库/美国数据出境路径Reference库清单.docx",
        "asset_type": "reference_catalog",
        "jurisdiction_family": "us",
        "target_module": "shared-us",
        "target_layer": "_index",
        "target_path": "doc/knowledge/_index/spec_asset_manifest.csv",
        "sync_status": "indexed_only",
        "notes": "作为来源清单依据，已纳入资产清单，不单独前端展示",
    },
    {
        "source_path": "doc/数规通功能路径描述（含reference）、流程描述、测试案例/美国（加州）数据出境路径/美国数据出境路径Reference库/美国数据出境路径reference文件库/*",
        "asset_type": "reference_source",
        "jurisdiction_family": "us",
        "target_module": "shared-us",
        "target_layer": "references",
        "target_path": "doc/knowledge/us-14117|us-cpra/references",
        "sync_status": "partially_indexed",
        "notes": "原始依据文件已迁入模块 references，但仅核心条目进入 sources.csv",
    },
]


def ensure_layout() -> None:
    for directory in (NEW_INDEX_DIR, NEW_REGISTRY_DIR, NEW_EVALUATION_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    for module_name in MODULES:
        module_root = KNOWLEDGE_ROOT / module_name
        for child in ("references", "snapshots"):
            (module_root / child).mkdir(parents=True, exist_ok=True)


def extract_docx_text(path: Path) -> str:
    if not path.exists():
        return f"# Missing Source\n\n- expected: `{path}`\n"
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    text = result.stdout.replace("\r\n", "\n").replace("\r", "\n").strip()
    title = path.stem
    return f"# {title}\n\n{text}\n"


def write_combined_markdown(sources: list[Path], output_path: Path) -> int:
    chunks = [extract_docx_text(source) for source in sources]
    output_path.write_text("\n\n---\n\n".join(chunks), encoding="utf-8")
    return len([source for source in sources if source.exists()])


def copy_tree_files(source_dir: Path, target_dir: Path) -> int:
    if not source_dir.exists():
        return 0
    count = 0
    for path in sorted(source_dir.iterdir()):
        if path.is_dir():
            continue
        destination = target_dir / path.name
        shutil.copy2(path, destination)
        count += 1
    return count


def migrate_module_docs(summary: MigrationSummary) -> None:
    for module_name, config in MODULES.items():
        module_root = KNOWLEDGE_ROOT / module_name
        summary.copied_specs += write_combined_markdown(config["specs"], module_root / "spec.md")
        summary.copied_tests += write_combined_markdown(config["tests"], module_root / "test-cases.md")
        summary.copied_references += copy_tree_files(config["references_dir"], module_root / "references")


def copy_snapshot_to_modules(relative_path: str, modules: list[str]) -> None:
    source = ROOT / relative_path
    if not source.exists():
        return
    for module_name in modules:
        target = KNOWLEDGE_ROOT / module_name / "snapshots" / source.name
        if not target.exists():
            shutil.copy2(source, target)


def migrate_raw_assets(summary: MigrationSummary) -> None:
    for raw_dir, modules in RAW_MODULE_MAP.items():
        source_dir = ROOT / raw_dir
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.iterdir()):
            if path.is_dir():
                continue
            copy_snapshot_to_modules(str(path.relative_to(ROOT)), modules)
            summary.copied_snapshots += len(modules)

    cases_dir = ROOT / "doc/knowledge/raw/cases"
    if not cases_dir.exists():
        return
    for path in sorted(cases_dir.iterdir()):
        if path.is_dir():
            continue
        module_name = CASE_FILE_MODULE_OVERRIDES.get(path.name, "cn-review")
        for keyword, candidate in CASE_ROUTE_KEYWORDS.items():
            if keyword in path.name:
                module_name = candidate
                break
        copy_snapshot_to_modules(str(path.relative_to(ROOT)), [module_name])
        summary.copied_snapshots += 1


def remap_snapshot_path(snapshot_path: str, jurisdiction: str, path_value: str, module_name: str = "") -> str:
    source_name = Path(snapshot_path).name
    if module_name:
        return f"doc/knowledge/{module_name}/snapshots/{source_name}"
    jurisdiction = (jurisdiction or "").strip().lower()
    path_value = (path_value or "").strip().lower()

    if jurisdiction == "cn":
        module = "cn-diagnosis"
        if "assessment" in path_value:
            module = "cn-assessment"
        elif "scc" in path_value:
            module = "cn-review"
        return f"doc/knowledge/{module}/snapshots/{source_name}"

    if jurisdiction == "eu":
        if "bcr" in path_value:
            module = "eu-bcr"
        elif "dpia" in path_value:
            module = "eu-dpia"
        elif "tia" in path_value:
            module = "eu-tia"
        else:
            module = "eu-scc"
        return f"doc/knowledge/{module}/snapshots/{source_name}"

    if jurisdiction == "us":
        module = "us-cpra" if "cpra" in snapshot_path.lower() or "privacy" in path_value else "us-14117"
        return f"doc/knowledge/{module}/snapshots/{source_name}"

    return snapshot_path


def module_from_source_row(source_id: str, jurisdiction: str, path_value: str, snapshot_path: str) -> str:
    explicit = SOURCE_MODULE_OVERRIDES.get((source_id or "").strip())
    if explicit:
        return explicit
    jurisdiction = (jurisdiction or "").strip().lower()
    path_value = (path_value or "").strip().lower()
    snapshot_lower = (snapshot_path or "").lower()
    if jurisdiction == "cn":
        if "assessment" in path_value:
            return "cn-assessment"
        if "scc" in path_value:
            return "cn-review"
        return "cn-diagnosis"
    if jurisdiction == "eu":
        if "bcr" in path_value:
            return "eu-bcr"
        if "dpia" in path_value:
            return "eu-dpia"
        if "tia" in path_value:
            return "eu-tia"
        return "eu-scc"
    if jurisdiction == "us":
        if "cpra" in snapshot_lower or "privacy" in path_value:
            return "us-cpra"
        return "us-14117"
    return ""


def binding_force_from_doc_type(doc_type: str) -> str:
    value = (doc_type or "").strip().lower()
    if value in {"law", "administrative_regulation"}:
        return "mandatory"
    if value in {"guide", "qa", "contact_list", "gov_republish"}:
        return "recommended"
    return "reference"


def category_from_source_row(doc_type: str, title: str) -> str:
    if "模板" in title:
        return "模板文书"
    return DOC_TYPE_CATEGORY_MAP.get((doc_type or "").strip().lower(), "知识材料")


def suitable_for_from_source_row(module_name: str, title: str) -> str:
    options: list[str] = []
    if module_name == "cn-diagnosis":
        options.append("路径判断")
    elif module_name == "cn-assessment":
        options.append("评估申报")
    elif module_name == "cn-review":
        options.append("文档审查")
        options.append("标准合同")
    elif module_name == "cn-pipia":
        options.append("认证与标准合同路径")
    elif module_name == "eu-scc":
        options.append("SCC审查")
    elif module_name == "eu-bcr":
        options.append("BCR审核")
    elif module_name == "eu-dpia":
        options.append("DPIA草案")
    elif module_name == "eu-tia":
        options.append("TIA草案")
    elif module_name == "us-14117":
        options.append("EO14117合规")
    elif module_name == "us-cpra":
        options.append("CPRA合规")
    if "标准合同" in title and "标准合同" not in options:
        options.append("标准合同")
    if "评估" in title and "评估申报" not in options:
        options.append("评估申报")
    return "、".join(dict.fromkeys(options))


def suitable_for_from_source_id(source_id: str, fallback: str) -> str:
    detail = SOURCE_DETAIL_OVERRIDES.get((source_id or "").strip(), {})
    return str(detail.get("suitable_for") or fallback)


def report_usage_from_row(doc_type: str, title: str) -> str:
    if "问答" in title:
        return "可辅助解释条文，但不宜单独作为核心依据"
    if "联系方式" in title:
        return "用于流程执行，不直接作为法律论证"
    if "模板" in title:
        return "用于结构参照，不直接作为法律依据"
    if doc_type in {"law", "administrative_regulation"}:
        return "可直接引用条文号"
    return "可附带解释说明"


def summary_from_source_row(title: str, jurisdiction: str, module_name: str, notes: str) -> str:
    label = JURISDICTION_LABELS.get((jurisdiction or "").strip().lower(), jurisdiction or "未标注法域")
    base = f"{title}，用于{label}模块 {module_name} 的合规判断与引用。"
    if notes:
        return f"{base}{notes}"
    return base


def category_from_case_title(title: str) -> str:
    if "统计" in title:
        return "实践统计"
    if "判决" in title or "法院" in title:
        return "司法案例"
    return "典型案例"


def suitable_for_from_case_modules(expected_modules: list[str]) -> str:
    labels: list[str] = []
    for module in expected_modules:
        if "assessment" in module:
            labels.append("评估申报")
        elif "review" in module or module in {"scc", "bcr"}:
            labels.append("文档审查")
        elif "diagnosis" in module:
            labels.append("路径判断")
        elif "dpia" in module:
            labels.append("DPIA草案")
        elif "tia" in module:
            labels.append("TIA草案")
        elif "cpra" in module:
            labels.append("CPRA合规")
        elif "cn_flow" in module:
            labels.append("EO14117合规")
    return "、".join(dict.fromkeys(labels)) or "业务参考"


def explicit_case_suitable_for(case_id: str, fallback: str) -> str:
    detail = CASE_DETAIL_OVERRIDES.get((case_id or "").strip(), {})
    return str(detail.get("suitable_for") or fallback)


def remap_case_snapshot_path(snapshot_path: str) -> str:
    source_name = Path(snapshot_path).name
    explicit_module = CASE_FILE_MODULE_OVERRIDES.get(source_name)
    if explicit_module:
        return f"doc/knowledge/{explicit_module}/snapshots/{source_name}"
    for keyword, module in CASE_ROUTE_KEYWORDS.items():
        if keyword in source_name:
            return f"doc/knowledge/{module}/snapshots/{source_name}"
    return f"doc/knowledge/cn-review/snapshots/{source_name}"


def migrate_index_files(summary: MigrationSummary) -> None:
    legacy_sources = LEGACY_KNOWLEDGE_ROOT / "index" / "sources.csv"
    legacy_cases = LEGACY_KNOWLEDGE_ROOT / "index" / "practice_cases.csv"

    with legacy_sources.open("r", encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    for row in source_rows:
        jurisdiction = row.get("jurisdiction", "")
        path_value = row.get("path", "")
        title = row.get("title", "")
        doc_type = row.get("doc_type", "")
        original_snapshot = row.get("snapshot_path", "")
        module_name = module_from_source_row(row.get("source_id", ""), jurisdiction, path_value, original_snapshot)
        row["module"] = module_name
        row["snapshot_path"] = remap_snapshot_path(original_snapshot, jurisdiction, path_value, module_name)
        row["category"] = category_from_source_row(doc_type, title)
        row["usage"] = USAGE_MAP.get(row.get("usage_priority", ""), "参考引用")
        row["binding_force"] = binding_force_from_doc_type(doc_type)
        row["authority"] = AUTHORITY_MAP.get((row.get("authority_level") or "").strip().lower(), "medium")
        row["publisher"] = PUBLISHER_MAP.get(row.get("source_org", ""), row.get("source_org", ""))
        row["suitable_for"] = suitable_for_from_source_id(
            row.get("source_id", ""),
            suitable_for_from_source_row(module_name, title),
        )
        source_detail = SOURCE_DETAIL_OVERRIDES.get(row.get("source_id", "").strip(), {})
        row["report_usage"] = str(source_detail.get("report_usage") or report_usage_from_row(doc_type, title))
        row["summary"] = str(source_detail.get("summary") or summary_from_source_row(title, jurisdiction, module_name, row.get("notes", "")))
        row["knowledge_url"] = f"/knowledge/sources/{row.get('source_id', '').strip()}"
    source_fields = list(source_rows[0].keys()) if source_rows else []
    with (NEW_INDEX_DIR / "sources.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=source_fields)
        writer.writeheader()
        writer.writerows(source_rows)
    summary.generated_index_rows = len(source_rows)

    with legacy_cases.open("r", encoding="utf-8", newline="") as handle:
        case_rows = list(csv.DictReader(handle))
    for row in case_rows:
        expected_modules = [item.strip() for item in row.get("expected_module", "").split("|") if item.strip()]
        row["snapshot_path"] = remap_case_snapshot_path(row.get("snapshot_path", ""))
        row["publisher"] = row.get("source_org", "")
        row["category"] = category_from_case_title(row.get("case_title", ""))
        row["usage"] = "案例参考"
        case_detail = CASE_DETAIL_OVERRIDES.get(row.get("case_id", "").strip(), {})
        row["report_usage"] = "不直接写入正式报告"
        row["summary"] = str(case_detail.get("summary") or row.get("available_artifacts", "") or row.get("limitations", "") or row.get("case_title", ""))
        row["suitable_for"] = explicit_case_suitable_for(
            row.get("case_id", ""),
            suitable_for_from_case_modules(expected_modules),
        )
        row["module"] = CASE_ID_MODULE_OVERRIDES.get(row.get("case_id", "").strip(), "")
        row["knowledge_url"] = f"/knowledge/cases/{row.get('case_id', '').strip()}"
    case_fields = list(case_rows[0].keys()) if case_rows else []
    with (NEW_INDEX_DIR / "practice_cases.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=case_fields)
        writer.writeheader()
        writer.writerows(case_rows)
    summary.generated_case_rows = len(case_rows)


def migrate_registry_and_evaluation() -> None:
    shutil.copy2(LEGACY_KNOWLEDGE_ROOT / "registry" / "module_catalog.v1.json", NEW_INDEX_DIR / "module_catalog.v1.json")
    shutil.copy2(LEGACY_KNOWLEDGE_ROOT / "normalized" / "regulation_articles.jsonl", NEW_REGISTRY_DIR / "regulation_articles.jsonl")
    shutil.copy2(LEGACY_KNOWLEDGE_ROOT / "normalized" / "regulation_article.schema.json", NEW_REGISTRY_DIR / "regulation_article.schema.json")

    evaluation_dir = LEGACY_KNOWLEDGE_ROOT / "evaluation"
    for path in sorted(evaluation_dir.iterdir()):
        if path.is_file():
            shutil.copy2(path, NEW_EVALUATION_DIR / path.name)


def regenerate_source_registry() -> None:
    entries = build_source_registry_from_sources_csv()
    payload = {
        "version": "v1",
        "generated_from": str(NEW_INDEX_DIR / "sources.csv"),
        "entries": [entry.model_dump() for entry in entries],
    }
    (NEW_REGISTRY_DIR / "source_registry.v1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_summary(summary: MigrationSummary) -> None:
    payload = {
        "spec_modules": list(MODULES.keys()),
        "copied_specs": summary.copied_specs,
        "copied_tests": summary.copied_tests,
        "copied_references": summary.copied_references,
        "copied_snapshots": summary.copied_snapshots,
        "generated_index_rows": summary.generated_index_rows,
        "generated_case_rows": summary.generated_case_rows,
    }
    (NEW_INDEX_DIR / "migration_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _jurisdiction_of_path(path: Path) -> str:
    raw = str(path)
    if "中国数据出境路径" in raw:
        return "cn"
    if "欧盟数据出境路径" in raw:
        return "eu"
    return "us"


def _find_module_for_asset(path: Path) -> str:
    for module_name, config in MODULES.items():
        if path in config["specs"] or path in config["tests"]:
            return module_name
        try:
            path.relative_to(Path(config["references_dir"]))
            return module_name
        except ValueError:
            continue

    raw = str(path)
    if "中国数据出境路径" in raw:
        if "任务1" in raw:
            return "cn-diagnosis"
        if "任务2" in raw:
            return "cn-assessment"
        if "任务3" in raw:
            return "cn-pipia"
        if "任务4" in raw:
            return "cn-review"
    if "欧盟数据出境路径" in raw:
        if "任务1" in raw:
            return "eu-scc"
        if "任务2" in raw:
            return "eu-bcr"
        if "任务3" in raw:
            return "eu-dpia"
        if "任务4" in raw:
            return "eu-tia"
    if "美国（加州）数据出境路径" in raw:
        if "任务1" in raw:
            return "us-14117"
        if "任务2" in raw:
            return "us-cpra"
    return ""


def _asset_type_for_manifest(path: Path, module_name: str) -> str:
    if path in MODULES.get(module_name, {}).get("specs", []):
        return "flow_spec" if "流程描述" in path.name else "spec"
    if path in MODULES.get(module_name, {}).get("tests", []):
        return "test_case"
    if "Reference库清单" in path.name:
        return "reference_catalog"
    lowered = path.name.lower()
    if "样例" in path.name or "模板" in path.name:
        if lowered.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return "sample_image"
        return "template_sample"
    return "reference_source"


def _target_for_manifest(path: Path, module_name: str) -> tuple[str, str]:
    module_root = KNOWLEDGE_ROOT / module_name if module_name else KNOWLEDGE_ROOT
    if path in MODULES.get(module_name, {}).get("specs", []):
        return "spec", _rel(module_root / "spec.md")
    if path in MODULES.get(module_name, {}).get("tests", []):
        return "test-cases", _rel(module_root / "test-cases.md")
    if "Reference库清单" in path.name:
        return "_index", _rel(NEW_INDEX_DIR / "spec_asset_manifest.csv")
    return "references", _rel(module_root / "references" / path.name)


def _notes_for_manifest(asset_type: str) -> str:
    if asset_type in {"spec", "flow_spec", "test_case"}:
        return "已纳入模块正文资产"
    if asset_type in {"template_sample", "sample_image"}:
        return "已作为文审/模板样例迁入 references"
    if asset_type == "reference_catalog":
        return "资产清单依据文件，仅用于追踪与核对"
    return "已纳入模块 references；是否前端可见取决于是否进入索引与知识展示层"


def build_spec_asset_manifest_rows() -> list[dict[str, str]]:
    visible_source_ids = {
        row.get("source_id", "").strip()
        for row in load_sources_index_rows()
        if row.get("source_id", "").strip()
    }
    rows: list[dict[str, str]] = []
    for path in sorted(p for p in SPEC_ROOT.rglob("*") if p.is_file()):
        module_name = _find_module_for_asset(path)
        asset_type = _asset_type_for_manifest(path, module_name)
        target_layer, target_path = _target_for_manifest(path, module_name)
        notes = _notes_for_manifest(asset_type)

        if asset_type == "reference_catalog":
            sync_status = "tracked_only"
        else:
            target_exists = (ROOT / target_path).exists()
            sync_status = "synced" if target_exists else "pending"

        mapped_source_ids = VISIBLE_SOURCE_FILENAME_MAP.get(path.name, [])
        if any(source_id in visible_source_ids for source_id in mapped_source_ids):
            sync_status = "frontend_visible"
            notes = "该资产对应的知识条目已进入前端知识库中心可见层"

        rows.append(
            {
                "source_path": _rel(path),
                "asset_type": asset_type,
                "jurisdiction_family": _jurisdiction_of_path(path),
                "target_module": module_name or "unmapped",
                "target_layer": target_layer,
                "target_path": target_path,
                "sync_status": sync_status,
                "notes": notes,
            }
        )
    return rows


def load_sources_index_rows() -> list[dict[str, str]]:
    path = NEW_INDEX_DIR / "sources.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_spec_asset_manifest() -> None:
    output = NEW_INDEX_DIR / "spec_asset_manifest.csv"
    fieldnames = [
        "source_path",
        "asset_type",
        "jurisdiction_family",
        "target_module",
        "target_layer",
        "target_path",
        "sync_status",
        "notes",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(build_spec_asset_manifest_rows())


def main() -> None:
    summary = MigrationSummary()
    ensure_layout()
    migrate_module_docs(summary)
    migrate_raw_assets(summary)
    migrate_index_files(summary)
    migrate_registry_and_evaluation()
    regenerate_source_registry()
    write_spec_asset_manifest()
    write_summary(summary)
    print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
