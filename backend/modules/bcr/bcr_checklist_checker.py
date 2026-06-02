"""BCRChecklistChecker — 5-state EDPB mandatory requirement check."""

from __future__ import annotations

import re
from uuid import uuid4

from backend.modules.bcr.bcr_document_parser import BCRStructuredDocument
from backend.modules.bcr.bcr_rulebook_loader import BCRRulebookLoader
from backend.modules.bcr.schema import BCRFinding

CoverageStatus = str  # "FULLY_COVERED" | "PARTIALLY_COVERED" | "VAGUE" | "MISSING" | "INCORRECT"


class BCRChecklistChecker:
    def __init__(self, rulebook_loader: BCRRulebookLoader | None = None) -> None:
        self.rulebook = rulebook_loader or BCRRulebookLoader()

    def check(self, doc: BCRStructuredDocument, bcr_type: str) -> tuple[list[BCRFinding], list[str]]:
        requirements = self.rulebook.get_all_requirements(bcr_type)
        findings: list[BCRFinding] = []
        missing: list[str] = []

        for req in requirements:
            status, evidence = self._check_requirement(doc, req)
            req_id = req["requirement_id"]

            if status == "FULLY_COVERED":
                continue

            if status == "MISSING":
                findings.append(self._build_finding(req_id, req, "MISSING", evidence))
                missing.append(req_id)
            elif status == "PARTIALLY_COVERED":
                findings.append(self._build_finding(req_id, req, "PARTIALLY_COVERED", evidence))
            elif status == "VAGUE":
                findings.append(self._build_finding(req_id, req, "VAGUE", evidence))
            elif status == "INCORRECT":
                findings.append(self._build_finding(req_id, req, "INCORRECT", evidence))
                missing.append(req_id)

        return findings, missing

    def _check_requirement(self, doc: BCRStructuredDocument, req: dict) -> tuple[CoverageStatus, list[str]]:
        """5-state check for a single requirement."""
        text = doc.plain_text.lower()
        keywords = req.get("check_keywords", [])
        structure_kw = req.get("check_structure", [])
        thresholds = req.get("coverage_thresholds", {"keywords_min": 1, "structure_match": False})
        dsl_checks = req.get("dsl_checks", [])
        title_text = " ".join(ch.title.lower() for ch in doc.chapters)

        # Count keyword hits
        kw_hits = [kw for kw in keywords if kw.lower() in text]
        kw_count = len(kw_hits)
        struct_matched = any(sk.lower() in title_text for sk in structure_kw)

        evidence: list[str] = []
        if kw_hits:
            evidence.append(f"命中关键词: {kw_hits[:3]}")
        if struct_matched:
            evidence.append(f"章节匹配: {[sk for sk in structure_kw if sk.lower() in title_text]}")

        # ── DSL checks (vague / incorrect) ──
        for dsl in dsl_checks:
            pat = dsl.get("pattern", "")
            pat_type = dsl.get("pattern_type", "match")
            if pat_type == "match" and pat and re.search(pat, text, re.IGNORECASE):
                return ("VAGUE", [dsl.get("finding", dsl.get("title", ""))])
            if pat_type == "missing" and pat and not re.search(pat, text, re.IGNORECASE):
                return ("PARTIALLY_COVERED", [dsl.get("finding", dsl.get("title", ""))])

        # ── State decision ──
        if kw_count >= thresholds.get("keywords_min", 1) and struct_matched:
            return ("FULLY_COVERED", evidence)
        if kw_count >= 1 or struct_matched:
            return ("PARTIALLY_COVERED", evidence)
        return ("MISSING", evidence)

    def _build_finding(self, req_id: str, req: dict, status: str, evidence: list[str]) -> BCRFinding:
        risk_str = req.get("severity_if_missing", "MEDIUM")
        from backend.modules.bcr.schema import BCRRiskLevel
        risk_level: BCRRiskLevel = "HIGH" if risk_str == "HIGH" else "MEDIUM" if risk_str == "MEDIUM" else "LOW"

        title_map = {
            "MISSING": f"缺失 {req['title']}",
            "PARTIALLY_COVERED": f"{req['title']} 覆盖不完整",
            "VAGUE": f"{req['title']} 表述模糊",
            "INCORRECT": f"{req['title']} 内容不当",
        }
        finding_map = {
            "MISSING": f"未在文档中找到 {req['title']} 的相关内容",
            "PARTIALLY_COVERED": f"{req['title']} 部分覆盖但缺少关键要素",
            "VAGUE": f"{req['title']} 使用了模糊表述，未达到具体可执行标准",
            "INCORRECT": f"{req['title']} 内容与BCR类型或GDPR要求不符",
        }

        return BCRFinding(
            finding_id=f"BCR-CHECK-{uuid4().hex[:8]}",
            requirement_id=req_id,
            location="全文" if status == "MISSING" else "",
            title=title_map.get(status, title_map["MISSING"]),
            risk_level=risk_level,
            finding=f"{finding_map.get(status, '')}. 依据：{req.get('gdpr_basis', '')}，{req.get('source', '')}。证据：{'; '.join(evidence)}",
            legal_basis=[req.get("gdpr_basis", ""), req.get("source", "")],
            recommendation=req.get("recommendation_template", f"应补充 {req['title']} 的完整内容。"),
            review_confidence=0.9,
        )
