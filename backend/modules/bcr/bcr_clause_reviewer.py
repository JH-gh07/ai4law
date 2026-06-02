"""BCRClauseReviewer — clause-level compliance review with BCR-specific DSL rules."""

from __future__ import annotations

import logging
import re
from uuid import uuid4

from backend.modules.bcr.bcr_rulebook_loader import BCRRulebookLoader
from backend.modules.bcr.schema import BCRFinding

logger = logging.getLogger(__name__)

# ── Vague expressions (English + Chinese) ──
_VAGUE_EN = [
    (r"as\s+appropriate", "as appropriate"),
    (r"where\s+feasible", "where feasible"),
    (r"reasonable\s+efforts", "reasonable efforts"),
    (r"to\s+the\s+extent\s+possible", "to the extent possible"),
    (r"as\s+soon\s+as\s+reasonably\s+practicable", "模糊时限表述"),
    (r"substantially\s+similar|essentially\s+equivalent", "substantially similar"),
]
_VAGUE_CN = [
    (r"及时(?!.*小时内|.*日内)", "及时"),
    (r"尽快", "尽快"),
    (r"尽可能", "尽可能"),
    (r"合理努力", "合理努力"),
    (r"适当情况下", "适当情况下"),
    (r"在法律允许范围内", "在法律允许范围内"),
]

# ── BCR-specific DSL rules ──
_DSL_RULES = [
    # Onward Transfer
    (r"(?:only written|in writing.*subprocessors|written authorisation|prior.*authorisation)",
     "missing", "HIGH", "subprocessor_auth",
     "转委托处理缺乏书面授权机制",
     "未要求子处理者转委托须经事先书面授权",
     "建议要求所有转委托须经事先书面授权"),
    # TIA completeness
    (r"(?:EDPB|six.step|transfer impact assessment|structured.*assessment)",
     "missing", "MEDIUM", "tia_incomplete",
     "TIA 评估方法不够完整",
     "TIA 描述未涵盖EDPB六步法或周期性审查",
     "建议涵盖EDPB六步法、周期性审查、补充措施和当地法律实践评估"),
    # Complaint timeline
    (r"(?:one month|30 days|without undue delay|specified.*time|specific.*timeline)",
     "missing", "MEDIUM", "complaint_timeline_vague",
     "投诉处理时限未明确",
     "投诉处理条款未明确响应和处理时限",
     "建议明确承诺在一个月内响应和调查投诉"),
    # Government access
    (r"(?:review.*legality|challenge.*request|notify.*data subject|transparency.*report)",
     "match", "MEDIUM", "gov_access_weak",
     "政府访问披露条款过于宽泛",
     "政府访问条款仅引用'to the extent permitted by law'，未说明审查请求合法性或通知义务",
     "建议增加审查访问请求合法性、通知数据主体的义务"),
    # Binding mechanism
    (r"(?:intra-group agreement|internal binding agreement|binding corporate instrument)",
     "missing", "HIGH", "binding_vague",
     "缺少法律约束力文书具体说明",
     "未提及集团内协议或其他具有法律约束力的内部文书",
     "应说明BCR通过何种法律文书对所有成员产生约束力"),
    # Data protection impact — vague
    (r"(?:implemented as appropriate|appropriate technical|organisational measures as appropriate)",
     "match", "MEDIUM", "dp_measures_vague",
     "数据保护措施表述模糊",
     "使用'as appropriate'修饰安全措施，无法保证达到GDPR要求的最低保护水平",
     "建议明确具体的技术和组织措施，而非使用'适当'等修饰词"),
    # Sub-processor notification
    (r"(?:inform.*controller|notify.*controller|controller.*informed.*before)",
     "missing", "MEDIUM", "subprocessor_notice",
     "缺少子处理者变更通知机制",
     "未说明子处理者变更时是否通知控制者",
     "应明确承诺在子处理者变更前通知控制者并给予反对机会"),
]

class BCRClauseReviewer:
    def __init__(self, llm_client=None, rulebook: BCRRulebookLoader | None = None) -> None:
        self.llm_client = llm_client
        self.rulebook = rulebook or BCRRulebookLoader()

    def review_clause(
        self, clause_text: str, requirement: dict, bcr_type: str, legal_refs: list[dict] | None = None,
    ) -> list[BCRFinding]:
        findings: list[BCRFinding] = []
        req_id = requirement["requirement_id"]
        refs = legal_refs or []

        # 1. Vague language (English)
        for pat, label in _VAGUE_EN:
            if re.search(pat, clause_text, re.IGNORECASE):
                findings.append(self._make_finding(req_id, clause_text, requirement, refs,
                    f"表述存在模糊空间 ({label})", "MEDIUM",
                    f"使用了 '{label}' 等模糊表述，可能导致执行和追责标准不明确。",
                    "建议将模糊性表述替换为具体的、可验证的义务描述。"))
                break

        # 2. Vague language (Chinese)
        for pat, label in _VAGUE_CN:
            if re.search(pat, clause_text):
                findings.append(self._make_finding(req_id, clause_text, requirement, refs,
                    f"表述存在模糊空间 ({label})", "MEDIUM",
                    f"使用了 '{label}' 等模糊表述，可能导致执行标准不明确。",
                    "建议将模糊性表述替换为具体的、可验证的义务描述。"))
                break

        # 3. BCR-specific DSL rules
        for pat, pat_type, severity, check_id, title, finding_desc, recommendation in _DSL_RULES:
            if pat_type == "missing" and not re.search(pat, clause_text, re.IGNORECASE):
                findings.append(self._make_finding(req_id, clause_text, requirement, refs,
                    title, severity, finding_desc, recommendation))
            elif pat_type == "match" and re.search(pat, clause_text, re.IGNORECASE):
                findings.append(self._make_finding(req_id, clause_text, requirement, refs,
                    title, severity, finding_desc, recommendation))

        # 4. Key content summary check
        keywords = requirement.get("check_keywords", [])
        if keywords and not any(kw.lower() in clause_text.lower() for kw in keywords[:3]):
            findings.append(self._make_finding(req_id, clause_text, requirement, refs,
                f"{requirement['title']} 描述不够具体", "MEDIUM",
                f"未能涵盖 '{requirement['title']}' 的核心要素。",
                f"建议补充 {requirement['title']} 的详细描述。"))

        return findings

    def _make_finding(self, req_id, clause_text, requirement, refs, title, severity, finding, recommendation):
        return BCRFinding(
            finding_id=f"BCR-CL-{uuid4().hex[:8]}",
            requirement_id=req_id,
            clause_excerpt=clause_text[:200],
            title=title,
            risk_level=severity,
            finding=finding,
            legal_basis=[r.get("source", "") for r in refs[:2]],
            recommendation=recommendation,
            review_confidence=0.82,
        )
