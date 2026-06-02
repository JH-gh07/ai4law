"""BCRLiabilityChecker — specialized liability + third-party beneficiary check."""

from __future__ import annotations

import re
from uuid import uuid4

from backend.modules.bcr.bcr_document_parser import BCRStructuredDocument
from backend.modules.bcr.schema import BCRFinding


class BCRLiabilityChecker:
    _CHECKS = [
        ("(?:established in|located in|registered in|seat in).*(?:EU|European Union|Germany|France|Ireland|Netherlands|Spain|Italy|Belgium|Austria|Poland|Sweden|Denmark|Finland|Portugal|Greece)", "HIGH",
         "未明确指定 EU 责任主体",
         "BCR 文档未明确指定一个在欧盟境内设立的实体作为承担合规责任的 liability entity",
         "必须指定一个欧盟实体，接受对非欧盟成员违反 BCR 的责任并承担赔偿责任"),
        ("(?:accept.*liability|liable.*for.*breach|compensat|redress|remedy|damage|responsible.*for.*non.compliance)", "MEDIUM",
         "EU 责任主体未明确承诺责任/赔偿",
         "未说明 EU 责任主体是否接受对非欧盟成员违规行为的法律责任和赔偿责任",
         "应明确 EU 责任主体将对非欧盟成员的 BCR 违规行为承担赔偿责任"),
        ("(?:data subject.*may.*enforce|enforce.*these BCR|enforce.*the BCR|beneficiary.*right|third.party.*beneficiary|directly.*enforce)", "HIGH",
         "未赋予数据主体第三方受益人权利",
         "BCR 文档未明确赋予数据主体第三方受益人权利以直接强制执行 BCR",
         "应增加独立条款，明确数据主体作为第三方受益人有权强制执行 BCR 条款"),
        ("(?:compensat|damage|redress|remedy|judicial.*remedy|administrative.*remedy)", "MEDIUM",
         "缺少数据主体救济渠道说明",
         "BCR 文档未说明数据主体可获得的有效救济渠道（司法或行政）",
         "应说明数据主体可获得的有效救济渠道"),
    ]

    def check(self, doc: BCRStructuredDocument) -> list[BCRFinding]:
        findings: list[BCRFinding] = []
        text = doc.plain_text.lower()

        for pattern, severity, title, finding_desc, recommendation in self._CHECKS:
            if not re.search(pattern, text, re.IGNORECASE):
                findings.append(BCRFinding(
                    finding_id=f"BCR-LIAB-{uuid4().hex[:8]}",
                    requirement_id="BCR-C-1.3",
                    title=title,
                    risk_level=severity,
                    finding=f"{finding_desc}。",
                    legal_basis=["GDPR Article 47(1)(b), 47(2)(f)", "EDPB Recommendations 1/2022"],
                    recommendation=recommendation,
                    review_confidence=0.9,
                ))

        # Also check for third party beneficiary specifically
        return findings
