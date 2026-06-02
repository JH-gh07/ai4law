"""BCRTiaChecker — specialized Transfer Impact Assessment completeness check."""

from __future__ import annotations

import re
from uuid import uuid4

from backend.modules.bcr.bcr_document_parser import BCRStructuredDocument
from backend.modules.bcr.schema import BCRFinding


class BCRTiaChecker:
    _CHECKS = [
        ("transfer impact assessment|TIA|third country.*assessment", "MEDIUM",
         "未提及 Transfer Impact Assessment",
         "BCR 文档未提及对第三国法律进行 Transfer Impact Assessment",
         "应明确说明将对所有第三国接收方进行转移影响评估(TIA)"),
        ("EDPB|six.step|structured.*method.*assessment", "MEDIUM",
         "TIA 未引用 EDPB 结构化评估方法",
         "TIA 描述未引用 EDPB 01/2020 六步法或其他结构化评估方法",
         "建议按照 EDPB 01/2020 六步法进行第三国法律评估"),
        ("periodic.*review|regular.*review|annual|update.*assessment|review.*update", "MEDIUM",
         "TIA 缺少定期审查机制",
         "TIA 描述未说明评估的定期审查和更新频率",
         "应承诺至少每两年或在目标国法律发生重大变化时重新评估"),
        ("supplementary.*measure|additional.*protect|compensatory.*measure|extra.*safeguard", "MEDIUM",
         "TIA 未提及补充保护措施",
         "TIA 描述未说明在第三国保护水平不足时应采取的补充措施",
         "应说明当 TIA 识别出风险时，将采取哪些补充技术、组织或合同措施"),
        ("suspend|cease.*transfer|stop.*transfer|cannot.*mitigate|unable.*ensure|risk.*cannot", "MEDIUM",
         "TIA 缺少无法缓解风险时的中止条款",
         "TIA 描述未说明当风险无法通过补充措施缓解时，将暂停或中止数据传输",
         "应明确承诺当无法确保实质等同保护水平时，将暂停相关数据传输"),
    ]

    def check(self, doc: BCRStructuredDocument) -> list[BCRFinding]:
        findings: list[BCRFinding] = []
        text = doc.plain_text.lower()

        for pattern, severity, title, finding_desc, recommendation in self._CHECKS:
            if not re.search(pattern, text, re.IGNORECASE):
                findings.append(BCRFinding(
                    finding_id=f"BCR-TIA-{uuid4().hex[:8]}",
                    requirement_id="BCR-C-1.9",
                    title=title,
                    risk_level=severity,
                    finding=f"{finding_desc}。",
                    legal_basis=["Schrems II", "EDPB Recommendations 01/2020"],
                    recommendation=recommendation,
                    review_confidence=0.88,
                ))

        return findings
