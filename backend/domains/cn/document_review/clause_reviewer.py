"""Enhanced clause reviewer with DSL rules, issue‑aware RAG, structured citations,
suggested revisions, and uncertainty tagging."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING
from uuid import uuid4

from backend.schemas.review import (
    ClassifiedClause,
    ClauseType,
    ReviewDepth,
    ReviewIssue,
    ReviewMethod,
    ReviewSeverity,
    StructuredCitation,
    SuggestedRevision,
)
from backend.domains.cn.document_review.rag_provider import LocalRegulationKnowledgeBase
from backend.domains.cn.document_review.rulebook_loader import RulebookLoader
from backend.domains.cn.document_review.standard_clause import StandardClauseDiffer, StandardClauseLocator
from backend.common.knowledge.v2 import KnowledgeChunkV2
from backend.common.knowledge.registry import ensure_source_registry

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient
    from backend.domains.cn.document_review.specialized_reviewers.base_reviewer import BaseSpecializedReviewer

logger = logging.getLogger(__name__)

# Canonical source title/id maps for citation name normalization. The rulebook
# uses short names ("个人信息保护法") while the RAG hits carry full registered
# names ("中华人民共和国个人信息保护法"); without a shared map both spellings
# end up side by side in a report. We also keep source_kind so templates and
# court cases can be rejected before they reach the "法规依据" field.
_SOURCE_TITLE_TO_IDS: dict[str, str] = {}
_SOURCE_CANONICAL_TITLES: dict[str, str] = {}
_SOURCE_ID_TO_ENTRY = {entry.source_id: entry for entry in ensure_source_registry()}
for _entry in _SOURCE_ID_TO_ENTRY.values():
    _clean = _entry.title.replace("《", "").replace("》", "").strip()
    _variants = [_clean]
    if _clean.startswith("中华人民共和国"):
        _variants.append(_clean[len("中华人民共和国"):])
    for _variant in _variants:
        _SOURCE_TITLE_TO_IDS.setdefault(_variant, _entry.source_id)
    _SOURCE_CANONICAL_TITLES[_entry.source_id] = _clean

# source_kind values that are never legal citations ("法规依据").
_NON_CITATION_KINDS = frozenset({"case", "case_reference", "template_slot", "official_template", "example_template"})
_MAX_CITATIONS_PER_ISSUE = 8

_REVIEW_SYSTEM_PROMPT = (
    "你是一名专注于中国个人信息保护合规的资深律师，深度掌握《个人信息保护法》"
    "《数据安全法》《网络安全法》及相关配套法规。"
    "请分析合同条款的合规问题。"
    "输出结构化JSON数组，不包含任何其他文字。"
    "如需标记不确定事实，添加 facts_uncertain 和 uncertainty_rationale 字段。"
    "如能提供修改建议，输出 original_text 和 suggested_text。"
)

_SEVERITY_MAP = {
    "HIGH": ReviewSeverity.HIGH,
    "MEDIUM": ReviewSeverity.MEDIUM,
    "LOW": ReviewSeverity.LOW,
}


class ClauseReviewer:
    """Review clauses using DSL rules + LLM with rule‑based fallback.

    Enhancements over v1:
    - DSL rule engine evaluates pattern‑based checks from rulebook
    - Issue‑aware RAG queries embed clause type + detected issues
    - Structured citations extracted from RAG hits
    - Suggested revisions via LLM (original_text → suggested_text)
    - Uncertainty tagging for facts that need user confirmation
    - Specialized reviewer delegation based on document_type
    """

    def __init__(
        self,
        knowledge_base: LocalRegulationKnowledgeBase,
        llm_client: LLMClient | None = None,
        rulebook_loader: RulebookLoader | None = None,
        specialized_reviewers: dict[str, BaseSpecializedReviewer] | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client
        self.rulebook = rulebook_loader or RulebookLoader()
        self.specialized_reviewers = specialized_reviewers or {}
        self.standard_clause_locator = StandardClauseLocator()
        self.standard_clause_differ = StandardClauseDiffer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(
        self,
        clause: ClassifiedClause,
        use_llm: bool = True,
        document_type: str = "other",
        scenario_context: dict | None = None,
        jurisdiction: str = "cn",
        module: str | None = None,
    ) -> list[ReviewIssue]:
        """Review a single classified clause.

        Returns list of ReviewIssue (may be empty if no issues found).
        """
        config = self.knowledge_base.lookup(
            clause.clause_type,
            clause.text,
            enrich=bool(clause.text and clause.text.strip()),
            jurisdiction=jurisdiction,
            module=module,
            document_type=document_type,
        )

        issues: list[ReviewIssue] = []

        # 1. DSL rule checks (always run, even with LLM)
        dsl_issues = self._evaluate_dsl_checks(clause, config)
        issues.extend(dsl_issues)

        # 1.5 Standard clause diff checks
        diff_issues = self._evaluate_standard_clause_diff(clause, config)
        issues.extend(diff_issues)

        # 2. Specialized reviewer (document‑type‑specific checks)
        reviewer = self.specialized_reviewers.get(document_type)
        if reviewer:
            try:
                specialized_issues = reviewer.review(clause, config)
                issues.extend(specialized_issues)
            except Exception as exc:
                logger.warning(
                    "Specialized reviewer %s failed for clause %s: %s",
                    document_type, clause.clause_id, exc,
                )

        # 3. LLM review (primary path)
        if use_llm and self.llm_client and self.llm_client.enabled:
            llm_issues = self._review_with_llm(clause, config, scenario_context)
            if llm_issues is not None:
                issues.extend(llm_issues)
            else:
                # LLM failed → add rule‑based fallback
                issues.extend(self._review_with_rules(clause, config))
        else:
            # No LLM → rule‑based
            issues.extend(self._review_with_rules(clause, config))

        # 4. Enrich issues that lack citations with the clause-type's precise
        #    rulebook citations + RAG top-k hits (deduped, template/case-free,
        #    capped). Never blind-attach a whole-source citation dump.
        for issue in issues:
            if not issue.structured_citations:
                issue.structured_citations = self._build_structured_citations(
                    config.get("citations", []),
                    config.get("structured_citations", []),
                )
            # Sync citation_sources for backward compatibility
            if not issue.citation_sources:
                issue.citation_sources = [
                    f"《{c.source_title}》{c.article}".strip()
                    for c in issue.structured_citations
                ]

        return issues

    def _evaluate_standard_clause_diff(
        self,
        clause: ClassifiedClause,
        config: dict,
    ) -> list[ReviewIssue]:
        candidate_dicts = config.get("standard_clause_candidates", []) or []
        if not candidate_dicts:
            return []
        candidates = [KnowledgeChunkV2.model_validate(item) for item in candidate_dicts]
        matched = self.standard_clause_locator.locate(clause, candidates)
        diff = self.standard_clause_differ.diff(clause, matched)
        if not diff.matched_chunk:
            return []

        citations = self._build_structured_citations(
            config.get("citations", []),
            config.get("structured_citations", []),
            standard_clause=diff.matched_chunk,
        )
        issues: list[ReviewIssue] = []

        if diff.missing_obligations:
            issues.append(
                ReviewIssue(
                    issue_id=f"STD-MISS-{uuid4().hex[:10]}",
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.HIGH,
                    title="标准条款义务缺失",
                    problem_type="MISSING_REQUIREMENT",
                    risk_analysis=f"当前条款未覆盖以下标准义务：{', '.join(diff.missing_obligations)}。",
                    original_excerpt=clause.text[:240],
                    recommendation="建议补齐对应的标准义务，不应以概括性文字替代核心保护要求。",
                    position=clause.position,
                    structured_citations=citations,
                    citation_sources=[f"《{c.source_title}》{c.article}".strip() for c in citations],
                    review_method=ReviewMethod.HYBRID,
                    review_confidence=0.88,
                    review_depth=ReviewDepth.STANDARD,
                )
            )
        if diff.weakened_obligations:
            issues.append(
                ReviewIssue(
                    issue_id=f"STD-WEAK-{uuid4().hex[:10]}",
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.HIGH,
                    title="标准条款义务被弱化",
                    problem_type="NON_COMPLIANT",
                    risk_analysis=f"当前条款可能弱化以下标准义务：{', '.join(diff.weakened_obligations)}。",
                    original_excerpt=clause.text[:240],
                    recommendation="建议恢复标准条款的完整义务，不得通过酌情、暂缓、责任上限等表述削弱保护强度。",
                    position=clause.position,
                    structured_citations=citations,
                    citation_sources=[f"《{c.source_title}》{c.article}".strip() for c in citations],
                    review_method=ReviewMethod.HYBRID,
                    review_confidence=0.9,
                    review_depth=ReviewDepth.STANDARD,
                )
            )
        if diff.added_risky_modifications:
            issues.append(
                ReviewIssue(
                    issue_id=f"STD-RISK-{uuid4().hex[:10]}",
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.HIGH,
                    title="标准条款中存在高风险新增修改",
                    problem_type="NON_COMPLIANT",
                    risk_analysis=f"识别到以下高风险修改信号：{', '.join(diff.added_risky_modifications)}。",
                    original_excerpt=clause.text[:240],
                    recommendation="建议移除与标准义务冲突的优先级、免责、延迟处理或责任限制性表述。",
                    position=clause.position,
                    structured_citations=citations,
                    citation_sources=[f"《{c.source_title}》{c.article}".strip() for c in citations],
                    review_method=ReviewMethod.HYBRID,
                    review_confidence=0.9,
                    review_depth=ReviewDepth.STANDARD,
                )
            )
        return issues

    # ------------------------------------------------------------------
    # DSL rule evaluation
    # ------------------------------------------------------------------

    def _evaluate_dsl_checks(
        self, clause: ClassifiedClause, config: dict,
    ) -> list[ReviewIssue]:
        """Evaluate DSL checks from rulebook configuration."""
        issues: list[ReviewIssue] = []
        text = clause.text

        dsl_checks = config.get("dsl_checks", [])
        if not dsl_checks:
            # Try loading from rulebook directly (primary type)
            dsl_checks = self.rulebook.get_dsl_checks(clause.clause_type.value)

        # ── Also check DSL rules from secondary types ──
        for st in clause.secondary_types:
            secondary_dsl = self.rulebook.get_dsl_checks(st.value)
            for ck in secondary_dsl:
                if ck not in dsl_checks:
                    dsl_checks.append(ck)

        for check in dsl_checks:
            triggered = False
            match_text = ""

            # Positive pattern match
            pattern = check.get("pattern", "")
            if pattern:
                try:
                    m = re.search(pattern, text)
                    if m:
                        triggered = True
                        match_text = m.group(0)[:80]
                except re.error:
                    if pattern in text:
                        triggered = True
                        match_text = pattern

            # Negative pattern (pattern_missing — all must be absent to trigger)
            pattern_missing = check.get("pattern_missing", [])
            if pattern_missing and not triggered:
                if not any(pm in text for pm in pattern_missing):
                    triggered = True
                    match_text = "、".join(pattern_missing[:3])

            if not triggered:
                continue

            # Build issue from template
            severity = _SEVERITY_MAP.get(
                check.get("severity", "MEDIUM"), ReviewSeverity.MEDIUM
            )
            title = check.get("title_template", "合规问题").format(match=match_text)
            risk = check.get("risk_analysis_template", "").format(match=match_text)
            recommendation = check.get("recommendation_template", "").format(match=match_text)

            issues.append(
                ReviewIssue(
                    issue_id=f"DSL-{check.get('id', uuid4().hex[:6])}-{uuid4().hex[:6]}",
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=severity,
                    title=title,
                    problem_type=check.get("problem_type", "NON_COMPLIANT"),
                    risk_analysis=risk or f"条款存在合规风险: {title}",
                    original_excerpt=clause.text[:240],
                    recommendation=recommendation or "请结合具体业务场景审查并补充相关约定。",
                    position=clause.position,
                    review_method=ReviewMethod.RULE,
                    review_confidence=0.85,
                    review_depth=ReviewDepth.STANDARD,
                )
            )

        return issues

    # ------------------------------------------------------------------
    # LLM review
    # ------------------------------------------------------------------

    def _review_with_llm(
        self,
        clause: ClassifiedClause,
        config: dict,
        scenario_context: dict | None = None,
    ) -> list[ReviewIssue] | None:
        """Review clause with LLM, returning None on failure (triggers rule fallback)."""
        citations_text = "\n".join(f"- {c}" for c in config.get("citations", []))
        scenario_block = ""
        if scenario_context:
            scenario_block = (
                "\n\n【业务场景】\n"
                + "\n".join(f"- {k}: {v}" for k, v in scenario_context.items() if v)
            )

        user_prompt = (
            f"条款类型：{clause.clause_type.value}\n"
            f"条款文本：\n{clause.text[:800]}\n\n"
            f"适用法规参考：\n{citations_text or '（无）'}\n"
            f"{scenario_block}\n\n"
            "请分析该条款是否存在合规问题。\n"
            "输出格式（JSON数组，无问题则返回[]）：\n"
            '[\n  {\n'
            '    "severity": "HIGH|MEDIUM|LOW",\n'
            '    "title": "问题标题",\n'
            '    "problem_type": "MISSING_REQUIREMENT|AMBIGUOUS_LANGUAGE|NON_COMPLIANT",\n'
            '    "risk_analysis": "风险说明",\n'
            '    "recommendation": "整改建议",\n'
            '    "facts_uncertain": true|false,\n'
            '    "uncertainty_rationale": "不确定原因（如无不确定则为空字符串）",\n'
            '    "original_text": "原文中需要修改的部分",\n'
            '    "suggested_text": "建议修改后的文本",\n'
            '    "revision_rationale": "修改理由"\n'
            '  }\n]'
        )

        try:
            raw = self.llm_client.chat(
                system=_REVIEW_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.1,
                max_tokens=1200,
            )
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1 or end == 0:
                return None
            parsed = json.loads(raw[start:end])
        except Exception as exc:
            logger.warning("LLM clause review failed, falling back to rules: %s", exc)
            return None

        if not isinstance(parsed, list):
            return None

        issues: list[ReviewIssue] = []
        citations = self._build_structured_citations(config.get("citations", []), config.get("structured_citations", []))

        for item in parsed:
            if not isinstance(item, dict):
                continue
            severity = _SEVERITY_MAP.get(item.get("severity", "LOW"), ReviewSeverity.LOW)

            # Suggested revision
            suggested = None
            orig = item.get("original_text", "")
            sugg = item.get("suggested_text", "")
            if orig and sugg:
                suggested = SuggestedRevision(
                    original_text=str(orig),
                    suggested_text=str(sugg),
                    revision_rationale=str(item.get("revision_rationale", "")),
                )

            issues.append(
                ReviewIssue(
                    issue_id=f"LLM-{uuid4().hex[:12]}",
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=severity,
                    title=str(item.get("title", "合规问题")),
                    problem_type=str(item.get("problem_type", "NON_COMPLIANT")),
                    risk_analysis=str(item.get("risk_analysis", "")),
                    original_excerpt=clause.text[:240],
                    recommendation=str(item.get("recommendation", "")),
                    position=clause.position,
                    structured_citations=citations,
                    citation_sources=[
                        f"《{c.source_title}》{c.article}".strip()
                        for c in citations
                    ],
                    suggested_revision=suggested,
                    facts_uncertain=bool(item.get("facts_uncertain", False)),
                    uncertainty_rationale=item.get("uncertainty_rationale") or None,
                    review_method=ReviewMethod.LLM,
                    review_confidence=0.85,
                    review_depth=ReviewDepth.STANDARD,
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Rule‑based fallback review
    # ------------------------------------------------------------------

    def _review_with_rules(
        self, clause: ClassifiedClause, config: dict,
    ) -> list[ReviewIssue]:
        """Rule‑based review (fallback path)."""
        issues: list[ReviewIssue] = []
        text = clause.text
        citations = self._build_structured_citations(config.get("citations", []), config.get("structured_citations", []))

        # 1. Required keyword group checks
        for group in config.get("required_groups", []):
            if not any(keyword in text for keyword in group):
                missing_label = "/".join(group)
                severity = self._severity_for(clause.clause_type)
                issues.append(
                    ReviewIssue(
                        issue_id=f"RULE-{uuid4().hex[:12]}",
                        clause_id=clause.clause_id,
                        file_id=clause.file_id,
                        clause_type=clause.clause_type,
                        severity=severity,
                        title=f"缺少关键信息：{missing_label}",
                        problem_type="MISSING_REQUIREMENT",
                        risk_analysis=f"当前条款未清晰体现「{missing_label}」，可能导致该类合规义务表达不完整。",
                        original_excerpt=text[:240],
                        recommendation=f"建议补充与「{missing_label}」相关的明确约定。",
                        position=clause.position,
                        structured_citations=citations,
                        citation_sources=[
                            f"《{c.source_title}》{c.article}".strip()
                            for c in citations
                        ],
                        review_method=ReviewMethod.RULE,
                        review_confidence=0.6,
                        review_depth=ReviewDepth.STANDARD,
                    )
                )

        # 2. Ambiguous language detection (expanded from v1)
        ambiguous_patterns = [
            ("尽最大努力", "模糊义务表述"),
            ("必要时", "条件性义务"),
            ("酌情", "裁量空间过大"),
            ("根据情况", "缺乏客观标准"),
            ("包括但不限于", "兜底条款可能过度宽泛"),
        ]
        for keyword, label in ambiguous_patterns:
            if keyword in text:
                issues.append(
                    ReviewIssue(
                        issue_id=f"RULE-AMB-{uuid4().hex[:8]}",
                        clause_id=clause.clause_id,
                        file_id=clause.file_id,
                        clause_type=clause.clause_type,
                        severity=ReviewSeverity.LOW,
                        title=f"表述存在模糊空间（{label}）",
                        problem_type="AMBIGUOUS_LANGUAGE",
                        risk_analysis=f"条款包含「{keyword}」等模糊表述，执行和追责口径可能不够清晰。",
                        original_excerpt=text[:240],
                        recommendation="建议将模糊性表述改为可验证、可执行的具体义务或时间要求。",
                        position=clause.position,
                        structured_citations=citations,
                        citation_sources=[
                            f"《{c.source_title}》{c.article}".strip()
                            for c in citations
                        ],
                        review_method=ReviewMethod.RULE,
                        review_confidence=0.7,
                        review_depth=ReviewDepth.STANDARD,
                    )
                )
                break  # one ambiguity issue per clause is sufficient

        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_structured_citations(
        self,
        raw_citations: list[str],
        structured_seed: list[dict] | None = None,
        standard_clause: KnowledgeChunkV2 | None = None,
    ) -> list[StructuredCitation]:
        """Build citable legal citations, dropping templates/cases and capping.

        Only statute/regulation/standard/guideline sources may enter
        ``structured_citations`` (and therefore "法规依据"). Court cases and
        templates are excluded; per-issue cardinality is capped so a single issue
        never carries an entire statute.
        """
        result: list[StructuredCitation] = []
        seen: set[str] = set()

        def _append(citation: StructuredCitation) -> None:
            if len(result) >= _MAX_CITATIONS_PER_ISSUE:
                return
            if not self._is_citable_source(citation.source_id):
                return
            key = f"{citation.source_title}::{citation.article}"
            if key in seen:
                return
            seen.add(key)
            result.append(citation)

        if standard_clause is not None:
            _append(StructuredCitation(
                source_id=standard_clause.source_id,
                source_title=standard_clause.title,
                article=standard_clause.citation_anchor or standard_clause.article_no,
                snippet=standard_clause.content[:200],
                source_type=str(standard_clause.source_kind or "standard_clause"),
            ))

        for item in structured_seed or []:
            source_id = str(item.get("source_id", ""))
            _, canonical_title = self._resolve_source(
                str(item.get("source_title", "")), source_id
            )
            _append(StructuredCitation(
                source_id=source_id,
                source_title=canonical_title,
                article=str(item.get("article", "")),
                snippet=str(item.get("snippet", "")),
                source_type=str(item.get("source_type", "statute")),
            ))

        for raw in raw_citations:
            if not raw:
                continue
            if self._looks_like_case(raw):
                continue

            # Parse "《source》article" format
            source_title = ""
            article = ""
            m = re.match(r"《(.+?)》(.*)", raw)
            if m:
                source_title = m.group(1).strip()
                article = m.group(2).strip()
            else:
                source_title = raw[:80]

            source_id, canonical_title = self._resolve_source(source_title, raw)
            _append(StructuredCitation(
                source_id=source_id,
                source_title=canonical_title,
                article=article,
                snippet=raw[:200],
                source_type="statute",
            ))
        return result

    @staticmethod
    def _resolve_source(source_title: str, raw: str = "") -> tuple[str, str]:
        """Return (source_id, canonical_title) for a citation source name.

        Maps short names ("个人信息保护法") to the canonical registered title
        ("中华人民共和国个人信息保护法") so one statute never renders under two
        spellings in the same report.
        """
        clean = (source_title or "").replace("《", "").replace("》", "").strip()
        source_id = _SOURCE_TITLE_TO_IDS.get(clean)
        if source_id:
            return source_id, _SOURCE_CANONICAL_TITLES.get(source_id, clean)
        return f"cite-{hash(raw or clean) & 0xFFFFFFFF:08x}", clean

    @staticmethod
    def _is_citable_source(source_id: str) -> bool:
        entry = _SOURCE_ID_TO_ENTRY.get(source_id)
        if entry is None:
            # Synthetic standard_clause chunks and unresolved fallbacks are
            # acceptable; real templates/cases are always in the registry and
            # rejected by the checks below.
            return True
        return entry.source_kind not in _NON_CITATION_KINDS and entry.layer != "L4_template"

    @staticmethod
    def _looks_like_case(raw: str) -> bool:
        """Heuristic for court-case strings leaked into citations.

        DeliLegal cases were historically formatted as ``"{court}: {title}"``
        (e.g. "大理白族自治州中级人民法院: 赵某；董某…判决书") with no 《》 marks.
        They are never a legal citation; treat that shape as a case and drop it.
        """
        text = raw.strip()
        if text.startswith("《") or "》" in text:
            return False
        return "法院" in text and any(token in text for token in ("判决", "裁定", "诉"))

    @staticmethod
    def _severity_for(clause_type: ClauseType) -> ReviewSeverity:
        """Determine rule‑based severity for a clause type."""
        high_types = {"CONSENT_NOTICE", "CROSS_BORDER_TRANSFER", "SENSITIVE_PI",
                       "ONWARD_TRANSFER", "MINOR_PROTECTION"}
        medium_types = {"SECURITY_MEASURES", "RIGHTS_REQUEST", "INCIDENT_RESPONSE",
                         "THIRD_PARTY_SHARING", "ENTRUSTED_PROCESSING",
                         "RETENTION_DELETION"}
        if clause_type.value in high_types:
            return ReviewSeverity.HIGH
        if clause_type.value in medium_types:
            return ReviewSeverity.MEDIUM
        return ReviewSeverity.LOW
