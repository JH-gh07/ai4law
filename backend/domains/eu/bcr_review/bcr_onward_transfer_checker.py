"""BCROnwardTransferChecker — specialized onward transfer compliance check."""

from __future__ import annotations

import re
from uuid import uuid4

from backend.domains.eu.bcr_review.bcr_document_parser import BCRStructuredDocument
from backend.domains.eu.bcr_review.schema import BCRFinding


class BCROnwardTransferChecker:
    _CHECKS = [
        ("adequate safeguard|appropriate safeguard|sufficient.*protection|adequate.*level.*protection|SCC|standard contractual clause|BCR|adequacy decision|binding corporate|derogation", "HIGH",
         "未明确 Onward Transfer 的保护工具",
         "BCR 文档未说明向非 BCR 成员传输个人数据时采用的法律保护工具（SCC / 充分性认定 / 例外）",
         "应明确列举向集团外第三方传输可用的法律工具，并说明每种情况下如何确保保护水平"),
        ("restrict.*transfer|limit.*transfer|prohibit.*transfer|no.*transfer.*outside|shall.*not.*transfer.*third|may.*transfer.*only", "MEDIUM",
         "未明确限制向非 BCR 成员传输",
         "BCR 文档未明确限制向非 BCR 成员或集团外第三方的数据传输",
         "应增加明确条款，限制向非 BCR 成员传输数据，除非有合法依据和保护措施"),
        ("without.*authorisation|prior.*written.*consent|pre-approved|general.*authorisation|specific.*authorisation", "MEDIUM",
         "缺少转委托授权机制",
         "未说明向第三方传输是否需要事先书面授权或预先批准",
         "建议增加转委托的授权机制"),
    ]

    def check(self, doc: BCRStructuredDocument) -> list[BCRFinding]:
        findings: list[BCRFinding] = []
        text = doc.plain_text.lower()

        for pattern, severity, title, finding_desc, recommendation in self._CHECKS:
            if not re.search(pattern, text, re.IGNORECASE):
                findings.append(BCRFinding(
                    finding_id=f"BCR-OT-{uuid4().hex[:8]}",
                    requirement_id="BCR-C-1.8",
                    title=title,
                    risk_level=severity,
                    finding=f"{finding_desc}。",
                    legal_basis=["GDPR Chapter V", "EDPB Recommendations 1/2022"],
                    recommendation=recommendation,
                    review_confidence=0.88,
                ))

        return findings
