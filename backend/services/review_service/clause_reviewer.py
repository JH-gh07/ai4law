from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from backend.schemas.review import ClassifiedClause, ReviewIssue, ReviewSeverity
from backend.services.review_service.rag_provider import LocalRegulationKnowledgeBase

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

_REVIEW_SYSTEM_PROMPT = (
    "你是一名专注于中国个人信息保护合规的资深律师，深度掌握《个人信息保护法》"
    "《数据安全法》《网络安全法》及相关配套法规。"
    "请分析合同条款的合规问题，输出结构化JSON，不包含任何其他文字。"
)

_SEVERITY_MAP = {"HIGH": ReviewSeverity.HIGH, "MEDIUM": ReviewSeverity.MEDIUM, "LOW": ReviewSeverity.LOW}


class ClauseReviewer:
    def __init__(self, knowledge_base: LocalRegulationKnowledgeBase, llm_client: LLMClient | None = None) -> None:
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client

    def review(self, clause: ClassifiedClause, use_llm: bool = True) -> list[ReviewIssue]:
        config = self.knowledge_base.lookup(clause.clause_type, clause.text if use_llm else None, enrich=use_llm)
        if use_llm and self.llm_client and self.llm_client.enabled:
            issues = self._review_with_llm(clause, config)
            if issues is not None:
                return issues
        return self._review_with_rules(clause, config)

    def _review_with_llm(self, clause: ClassifiedClause, config: dict) -> list[ReviewIssue] | None:
        citations_text = "\n".join(f"- {c}" for c in config.get("citations", []))
        user_prompt = (
            f"条款类型：{clause.clause_type.value}\n"
            f"条款文本：\n{clause.text[:800]}\n\n"
            f"适用法规参考：\n{citations_text or '（无）'}\n\n"
            "请分析该条款是否存在合规问题。\n"
            "输出格式（JSON数组，无问题则返回[]）：\n"
            '[\n  {"severity": "HIGH|MEDIUM|LOW", "title": "问题标题", '
            '"problem_type": "MISSING_REQUIREMENT|AMBIGUOUS_LANGUAGE|NON_COMPLIANT", '
            '"risk_analysis": "风险说明", "recommendation": "整改建议"}\n]'
        )
        try:
            raw = self.llm_client.chat(
                system=_REVIEW_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.1,
                max_tokens=1200,
            )
            # extract JSON array from response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1 or end == 0:
                return None
            parsed = json.loads(raw[start:end])
        except Exception as exc:
            logger.warning("LLM clause review failed, falling back to rules: %s", exc)
            return None

        issues: list[ReviewIssue] = []
        for item in parsed:
            severity = _SEVERITY_MAP.get(item.get("severity", "LOW"), ReviewSeverity.LOW)
            issues.append(
                ReviewIssue(
                    issue_id=str(uuid4()),
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=severity,
                    title=item.get("title", "合规问题"),
                    problem_type=item.get("problem_type", "NON_COMPLIANT"),
                    risk_analysis=item.get("risk_analysis", ""),
                    original_excerpt=clause.text[:240],
                    citation_sources=config.get("citations", []),
                    recommendation=item.get("recommendation", ""),
                    position=clause.position,
                )
            )
        return issues

    def _review_with_rules(self, clause: ClassifiedClause, config: dict) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        text = clause.text

        for group in config.get("required_groups", []):
            if not any(keyword in text for keyword in group):
                missing_label = "/".join(group)
                severity = self._severity_for(clause.clause_type)
                issues.append(
                    ReviewIssue(
                        issue_id=str(uuid4()),
                        clause_id=clause.clause_id,
                        file_id=clause.file_id,
                        clause_type=clause.clause_type,
                        severity=severity,
                        title=f"缺少关键信息：{missing_label}",
                        problem_type="MISSING_REQUIREMENT",
                        risk_analysis=f"当前条款未清晰体现“{missing_label}”，可能导致该类合规义务表达不完整。",
                        original_excerpt=text[:240],
                        citation_sources=config.get("citations", []),
                        recommendation=f"建议补充与“{missing_label}”相关的明确约定，并结合实际业务补全责任边界与操作路径。",
                        position=clause.position,
                    )
                )

        if "尽最大努力" in text or "必要时" in text:
            issues.append(
                ReviewIssue(
                    issue_id=str(uuid4()),
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.LOW,
                    title="表述存在模糊空间",
                    problem_type="AMBIGUOUS_LANGUAGE",
                    risk_analysis="条款包含较模糊的义务表述，执行和追责口径可能不够清晰。",
                    original_excerpt=text[:240],
                    citation_sources=config.get("citations", []),
                    recommendation="建议将模糊性表述改为可验证、可执行的具体义务或时间要求。",
                    position=clause.position,
                )
            )

        return issues

    def _severity_for(self, clause_type):
        if clause_type.value in {"CONSENT_NOTICE", "CROSS_BORDER_TRANSFER"}:
            return ReviewSeverity.HIGH
        if clause_type.value in {"SECURITY_MEASURES", "RIGHTS_REQUEST"}:
            return ReviewSeverity.MEDIUM
        return ReviewSeverity.LOW
