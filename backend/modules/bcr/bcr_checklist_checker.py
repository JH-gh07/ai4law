"""BCRChecklistChecker — check EDPB mandatory requirements against parsed BCR."""

from __future__ import annotations

from uuid import uuid4

from backend.modules.bcr.bcr_document_parser import BCRStructuredDocument
from backend.modules.bcr.bcr_rulebook_loader import BCRRulebookLoader
from backend.modules.bcr.schema import BCRFinding


class BCRChecklistChecker:
    def __init__(self, rulebook_loader: BCRRulebookLoader | None = None) -> None:
        self.rulebook = rulebook_loader or BCRRulebookLoader()

    def check(self, doc: BCRStructuredDocument, bcr_type: str) -> tuple[list[BCRFinding], list[str]]:
        requirements = self.rulebook.get_all_requirements(bcr_type)
        findings: list[BCRFinding] = []
        missing: list[str] = []

        for req in requirements:
            req_id = req["requirement_id"]
            keywords = req.get("check_keywords", [])
            structure_kw = req.get("check_structure", [])

            text_covered = any(kw.lower() in doc.plain_text.lower() for kw in keywords)
            structure_covered = any(
                any(sk in ch.title.lower() for sk in structure_kw)
                for ch in doc.chapters
            )

            if text_covered or structure_covered:
                continue

            severity = req.get("severity_if_missing", "MEDIUM")
            findings.append(BCRFinding(
                finding_id=f"BCR-CHECK-{uuid4().hex[:8]}",
                requirement_id=req_id,
                location="全文",
                title=f"缺失 {req['title']}",
                risk_level=severity,
                finding=f"未在文档中找到 {req['title']} 的相关内容。依据：{req.get('gdpr_basis', '')}，{req.get('source', '')}",
                legal_basis=[req.get("gdpr_basis", ""), req.get("source", "")],
                recommendation=f"应在 BCR 文档中新增 {req['title']} 的专门章节。",
                review_confidence=0.9,
            ))
            missing.append(req_id)

        return findings, missing
