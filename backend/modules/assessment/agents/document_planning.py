"""Agent 5: Document generation planning — plans each official template section before LLM writes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SectionPlan:
    section_id: str
    section_title: str
    must_cover: list[str] = field(default_factory=list)
    confirmed_facts: list[str] = field(default_factory=list)
    issues_to_disclose: list[str] = field(default_factory=list)
    allowed_positive_claims: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    required_citations: list[str] = field(default_factory=list)
    writing_instruction: str = ""


class DocumentPlanningAgent:
    """Plans each official template section with precise content instructions."""

    OFFICIAL_SECTIONS = {
        "一、自评估工作情况": {
            "must_cover": ["自评估起止时间", "参与部门", "自评估工作方法", "自评估结论初判"],
            "required_citations": ["数据出境安全评估办法 第五条"],
        },
        "二（一）数据处理者基本情况": {
            "must_cover": ["企业名称", "注册地", "股权结构", "实际控制人", "数据安全组织架构"],
            "required_citations": ["数据出境安全评估办法 第五条"],
        },
        "二（二）拟出境数据情况": {
            "must_cover": ["数据项清单", "数据主体类别", "数据规模", "是否涉及重要数据", "是否涉及敏感个人信息"],
            "required_citations": ["数据出境安全评估办法 第四条", "个人信息保护法 第二十八条"],
        },
        "二（三）数据处理者数据安全保障能力情况": {
            "must_cover": ["管理措施", "技术措施", "认证情况", "合规历史"],
            "required_citations": ["数据出境安全评估办法 第五条", "个人信息保护法 第五十一条"],
        },
        "二（四）境外接收方情况": {
            "must_cover": ["接收方名称", "所在国家/地区", "数据处理角色", "安全保障能力", "法律环境"],
            "required_citations": ["数据出境安全评估办法 第五条"],
        },
        "二（五）法律文件约定数据安全保护责任义务的情况": {
            "must_cover": ["六项核心条款覆盖状态", "缺失条款", "待补充内容"],
            "required_citations": ["数据出境安全评估办法 第九条"],
        },
        "三、出境活动的风险自评估情况及结论": {
            "must_cover": ["风险识别", "风险等级", "整改措施", "剩余风险", "综合结论"],
            "required_citations": ["数据出境安全评估办法 第五条", "数据出境安全评估办法 第八条"],
        },
    }

    GLOBAL_FORBIDDEN = [
        "完全合规", "材料齐备", "无风险", "已充分证明", "必然合法",
        "已完全覆盖", "已充分保障", "不存在任何合规问题",
    ]

    def run(self, facts: list, issues: list, generation_basis_pack: dict | None = None) -> list[SectionPlan]:
        """Generate section-level writing plans."""
        issue_ids = {getattr(i, "issue_id", str(i)) for i in issues}
        fact_texts = [getattr(f, "field_path", "") for f in facts if hasattr(f, "field_path")]
        plans: list[SectionPlan] = []

        for section_title, config in self.OFFICIAL_SECTIONS.items():
            plans.append(SectionPlan(
                section_id=section_title,
                section_title=section_title,
                must_cover=list(config["must_cover"]),
                confirmed_facts=[t for t in fact_texts if any(kw in t for kw in ("company", "industry", "transfer", "pii", "spi"))][:5],
                issues_to_disclose=[iid for iid in issue_ids if "HIGH" in iid or "BLOCKER" in iid][:3],
                allowed_positive_claims=["用户已提供相关信息" if fact_texts else "当前材料条件下"],
                forbidden_claims=list(self.GLOBAL_FORBIDDEN),
                required_citations=list(config.get("required_citations", [])),
                writing_instruction="采用审慎表述，明确已提供信息和待补充内容的边界。",
            ))

        return plans

    def run_with_llm(self, facts: list, issues: list, llm_client: Any, generation_basis_pack: dict | None = None) -> list[SectionPlan]:
        """Enhanced planning with LLM."""
        plans = self.run(facts, issues, generation_basis_pack)

        if not llm_client or not getattr(llm_client, "enabled", False):
            return plans

        plans_json = json.dumps([{
            "section_id": p.section_id,
            "must_cover": p.must_cover,
            "confirmed_facts": p.confirmed_facts,
            "issues_to_disclose": p.issues_to_disclose,
        } for p in plans], ensure_ascii=False)

        prompt = (
            f"Review these section plans for a Chinese data export security assessment report:\n{plans_json}\n\n"
            "For each section, add specific writing_instruction in Chinese and identify any additional "
            "forbidden_claims that should be avoided. Return JSON array with section_id, writing_instruction, "
            "and additional_forbidden_claims fields."
        )

        try:
            raw = llm_client.chat(system="You are a Chinese legal document drafting expert.", user=prompt, temperature=0.2, max_tokens=800)
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                for item in parsed:
                    for p in plans:
                        if p.section_id == item.get("section_id"):
                            p.writing_instruction = item.get("writing_instruction", p.writing_instruction)
                            p.forbidden_claims.extend(item.get("additional_forbidden_claims", []))
        except (json.JSONDecodeError, Exception):
            pass

        return plans
