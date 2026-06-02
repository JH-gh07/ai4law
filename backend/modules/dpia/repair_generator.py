"""DPIA repair generator — targeted fixes for DPIA consistency check issues.

Classifies issues as repairable (text-level fixes) or blocking (requires human intervention).
Applies fixes and re-checks, with configurable max-retry limit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from backend.modules.dpia.schema import DPIAChapterContent, DPIAProjectProfile

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient
    from backend.common.workflow import GenerationContextPack

_REPAIRABLE_PATTERNS: dict[str, str] = {
    "has no citations": "citation_missing",
    "has no citation": "citation_missing",
    "does not mention path warning": "path_warning_missing",
    "Forbidden expression": "forbidden_expression",
    "Forbidden DPIA expression": "forbidden_expression",
    "Internal expression leaked": "internal_leakage",
    "may be based on user_claim_only": "user_claim_positive",
    "DPIA trigger reasons should reference": "trigger_ref_missing",
    "lack:": "description_incomplete",
    "Vague mitigation phrasing detected": "vague_mitigation",
    "DPO opinion should be referenced": "dpo_mention_missing",
    "Art 36 is not mentioned": "art36_missing",
}

_BLOCKING_PATTERNS: dict[str, str] = {
    "references missing facts": "missing_fact_ref",
    "references missing rules": "missing_rule_ref",
    "references missing evidence": "missing_evidence_ref",
    "not mentioned in report": "missing_high_issue",
    "leaked into external report": "case_in_external",
}


@dataclass
class DPIARepairResult:
    chapters: list[DPIAChapterContent]
    issues_before: list[str]
    issues_after: list[str]
    repairs_applied: list[str] = field(default_factory=list)
    blocked: bool = False
    attempts: int = 0


class DPIARepairGenerator:
    """Applies targeted fixes to DPIA chapter content based on consistency issues."""

    _FIXABLE_MARKERS = {
        "citation_missing",
        "path_warning_missing",
        "forbidden_expression",
        "internal_leakage",
        "user_claim_positive",
        "trigger_ref_missing",
        "description_incomplete",
        "vague_mitigation",
        "dpo_mention_missing",
        "art36_missing",
    }

    _BLOCKING_MARKERS = {
        "missing_fact_ref",
        "missing_rule_ref",
        "missing_evidence_ref",
        "missing_high_issue",
        "case_in_external",
    }

    def __init__(self, llm_client: "LLMClient | None" = None, max_retries: int = 3) -> None:
        self.llm_client = llm_client
        self.max_retries = max_retries

    def repair(
        self,
        *,
        chapters: list[DPIAChapterContent],
        consistency_issues: list[str],
        profile: DPIAProjectProfile,
        context_pack: "GenerationContextPack",
    ) -> DPIARepairResult:
        current_chapters = list(chapters)
        current_issues = list(consistency_issues)
        all_repairs: list[str] = []
        blocked = False

        for attempt in range(1, self.max_retries + 1):
            if not current_issues:
                break

            classified = self._classify_issues(current_issues)
            fixable = [c for c in classified if c["marker"] in self._FIXABLE_MARKERS]
            blockers = [c for c in classified if c["marker"] in self._BLOCKING_MARKERS]

            for item in fixable:
                repair_desc = self._apply_repair(item, current_chapters, profile, context_pack)
                if repair_desc:
                    all_repairs.append(repair_desc)

            if fixable:
                from backend.modules.dpia.consistency_checker import DPIAConsistencyChecker

                checker = DPIAConsistencyChecker()
                current_issues = checker.check_with_context(profile, current_chapters, context_pack)
            else:
                current_issues = [item["original"] for item in blockers]

            remaining_markers = {self._classify_single(issue) for issue in current_issues}
            if remaining_markers and remaining_markers.issubset(self._BLOCKING_MARKERS):
                blocked = True
                break

        return DPIARepairResult(
            chapters=current_chapters,
            issues_before=list(consistency_issues),
            issues_after=current_issues,
            repairs_applied=all_repairs,
            blocked=blocked,
            attempts=min(self.max_retries, len(all_repairs) or 1) if not blocked else self.max_retries,
        )

    def _classify_issues(self, issues: list[str]) -> list[dict[str, str]]:
        return [{"original": issue, "marker": self._classify_single(issue)} for issue in issues]

    @staticmethod
    def _classify_single(issue: str) -> str:
        for pattern, marker in _REPAIRABLE_PATTERNS.items():
            if pattern in issue:
                return marker
        for pattern, marker in _BLOCKING_PATTERNS.items():
            if pattern in issue:
                return marker
        return "unknown"

    def _apply_repair(
        self,
        classified: dict[str, str],
        chapters: list[DPIAChapterContent],
        profile: DPIAProjectProfile,
        context_pack: "GenerationContextPack",
    ) -> str | None:
        marker = classified["marker"]

        if marker == "citation_missing":
            return self._fix_citation_missing(classified["original"], chapters)
        if marker == "forbidden_expression":
            return self._fix_forbidden_expression(classified["original"], chapters)
        if marker == "internal_leakage":
            return self._fix_internal_leakage(classified["original"], chapters)
        if marker == "user_claim_positive":
            return self._fix_user_claim_positive(classified["original"], chapters)
        if marker == "trigger_ref_missing":
            return self._fix_trigger_ref_missing(chapters)
        if marker == "description_incomplete":
            return self._fix_description_incomplete(classified["original"], chapters)
        if marker == "vague_mitigation":
            return self._fix_vague_mitigation(classified["original"], chapters)
        if marker == "dpo_mention_missing":
            return self._fix_dpo_mention_missing(chapters)
        if marker == "art36_missing":
            return self._fix_art36_missing(chapters)

        return None

    @staticmethod
    def _find_chapter_by_no(chapters: list[DPIAChapterContent], chapter_no: int) -> DPIAChapterContent | None:
        for ch in chapters:
            if ch.chapter_no == chapter_no:
                return ch
        return None

    def _fix_citation_missing(self, issue: str, chapters: list[DPIAChapterContent]) -> str | None:
        match = re.search(r"Chapter (\d+) has no citations?", issue)
        if not match:
            return None
        chapter_no = int(match.group(1))
        chapter = self._find_chapter_by_no(chapters, chapter_no)
        if chapter is None:
            return None
        note = "【依据：本章暂未引用GDPR或相关指引条文，建议补充具体法律依据。】"
        if note not in chapter.content:
            chapter.content += f"\n\n{note}"
        if not chapter.citations:
            chapter.citations = ["_repair_citation_placeholder"]
        return f"Added citation note to DPIA chapter {chapter_no}"

    def _fix_forbidden_expression(self, issue: str, chapters: list[DPIAChapterContent]) -> str | None:
        match = re.search(r"Forbidden (?:DPIA )?expression (?:in external report )?detected: '([^']+)'", issue)
        if not match:
            # Try alternative pattern: from writing strategy
            match = re.search(r"Forbidden expression from writing strategy detected: '([^']+)'", issue)
        if not match:
            return None
        forbidden = match.group(1)
        obfuscated = "⋯".join(forbidden)
        replacement = f"【已移除禁用措辞：{obfuscated}】"
        for chapter in chapters:
            if forbidden in chapter.content and replacement not in chapter.content:
                chapter.content = chapter.content.replace(forbidden, replacement)
                return f"Replaced forbidden DPIA expression '{forbidden[:30]}...'"
        return None

    def _fix_internal_leakage(self, issue: str, chapters: list[DPIAChapterContent]) -> str | None:
        match = re.search(
            r"Internal expression leaked into external report for ([^:]+): '([^']+)'", issue
        )
        if not match:
            return None
        leaked_text = match.group(2).rstrip(".")
        if len(leaked_text) < 10:
            return None
        replacement = "【内部表述已移除】"
        for chapter in chapters:
            if leaked_text in chapter.content:
                chapter.content = chapter.content.replace(leaked_text, replacement)
                return f"Removed internal expression leakage: '{leaked_text[:40]}...'"
        return None

    def _fix_user_claim_positive(self, issue: str, chapters: list[DPIAChapterContent]) -> str | None:
        match = re.search(r"Positive claim '([^']+)' may be based on user_claim_only fact", issue)
        if not match:
            return None
        marker = match.group(1)
        caveat = (
            f"\n> **注意**：上文中「{marker}」的判断所依据的材料来自企业自述"
            "（证据状态：user_claim_only），尚未通过第三方验证或附件佐证，"
            "正式结论须基于可验证证据。"
        )
        for chapter in chapters:
            if marker in chapter.content:
                chapter.content = chapter.content.replace(
                    marker,
                    f"{marker}【依据为企业自述，须进一步验证】",
                )
                return f"Added user_claim_only caveat for '{marker}'"
        return None

    def _fix_trigger_ref_missing(self, chapters: list[DPIAChapterContent]) -> str | None:
        """Add WP248 reference to the need identification chapter."""
        for chapter in chapters:
            if "need_identification" in chapter.title or "识别需求" in chapter.title:
                note = (
                    "\n\n**【依据补充】** 本DPIA依据GDPR Article 35及WP248高风险处理活动标准触发。"
                    "WP248列举了9项可能产生高风险的处理活动标准，包括评估/评分、自动决策、"
                    "系统性监控、敏感数据、大规模处理、数据匹配、弱势数据主体、"
                    "创新技术使用和数据跨境传输。"
                )
                if "WP248" not in chapter.content:
                    chapter.content += note
                    return "Added WP248 reference to need identification chapter"
        return None

    def _fix_description_incomplete(self, issue: str, chapters: list[DPIAChapterContent]) -> str | None:
        """Annotate the processing description chapter with a completeness note."""
        match = re.search(r"lack: ([\w\s/]+)", issue)
        if not match:
            return None
        missing_aspect = match.group(1).strip()
        for chapter in chapters:
            if "processing_description" in chapter.title or "描述处理活动" in chapter.title:
                note = f"\n\n**【需补充】** 本章节缺少 {missing_aspect} 相关描述，建议补充。"
                chapter.content += note
                return f"Added completeness note for '{missing_aspect}' to processing description chapter"
        return None

    def _fix_vague_mitigation(self, issue: str, chapters: list[DPIAChapterContent]) -> str | None:
        """Replace a vague mitigation phrase with a more specific call to action."""
        match = re.search(r"Vague mitigation phrasing detected: '([^']+)'", issue)
        if not match:
            return None
        vague_term = match.group(1)
        for chapter in chapters:
            if "mitigation" in chapter.title or "降低风险" in chapter.title:
                specific_note = (
                    f"\n\n**【缓解措施具体化要求】** 原文中「{vague_term}」过于笼统。"
                    "请补充具体行动方案、负责部门/人员、实施时间表和可验证的完成标准。"
                )
                if specific_note not in chapter.content:
                    chapter.content += specific_note
                    return f"Added mitigation specificity note for '{vague_term}'"
        return None

    def _fix_dpo_mention_missing(self, chapters: list[DPIAChapterContent]) -> str | None:
        """Add DPO opinion placeholder to the signoff chapter."""
        for chapter in chapters:
            if "signoff" in chapter.title or "签署与记录" in chapter.title:
                note = (
                    "\n\n**【待补充】** DPO（数据保护官）审查意见尚未出具。"
                    "依据GDPR Art 35(2)和Art 39，DPO应在DPIA签署前审查草案并提供书面意见。"
                )
                if "DPO" not in chapter.content:
                    chapter.content += note
                    return "Added DPO opinion placeholder to signoff chapter"
        return None

    def _fix_art36_missing(self, chapters: list[DPIAChapterContent]) -> str | None:
        """Add GDPR Art 36 prior consultation reference to the signoff chapter."""
        for chapter in chapters:
            if "signoff" in chapter.title or "签署与记录" in chapter.title:
                note = (
                    "\n\n**【事先咨询建议】** 鉴于本项目涉及多项高风险处理活动且残余风险"
                    "可能无法完全消除，建议依据GDPR Article 36向相关数据保护监管机构"
                    "进行事先咨询。若决定不进行事先咨询，应书面记录理由并保留备查。"
                )
                if "Article 36" not in chapter.content and "Art 36" not in chapter.content:
                    chapter.content += note
                    return "Added Art 36 prior consultation reference to signoff chapter"
        return None


def run_dpia_repair_pass(
    *,
    chapters: list[DPIAChapterContent],
    consistency_issues: list[str],
    profile: DPIAProjectProfile,
    context_pack: "GenerationContextPack",
    llm_client: "LLMClient | None" = None,
    max_retries: int = 3,
) -> tuple[list[DPIAChapterContent], list[str], bool]:
    """Convenience wrapper: runs the DPIA repair loop.

    Returns (chapters, remaining_issues, blocked).
    """
    if not consistency_issues:
        return list(chapters), [], False

    generator = DPIARepairGenerator(llm_client=llm_client, max_retries=max_retries)
    result = generator.repair(
        chapters=chapters,
        consistency_issues=consistency_issues,
        profile=profile,
        context_pack=context_pack,
    )
    return result.chapters, result.issues_after, result.blocked
