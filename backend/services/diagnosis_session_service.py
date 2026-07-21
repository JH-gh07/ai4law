from __future__ import annotations

from html import escape

from sqlalchemy.orm import Session

from backend.common.llm.client import LLMClient
from backend.core.json_utils import dumps, loads
from backend.models.diagnosis import DiagnosisSessionModel
from backend.domains.cn.transfer_diagnosis.schema import (
    DiagnosisAnswers as ModuleDiagnosisAnswers,
)
from backend.domains.cn.transfer_diagnosis.schema import (
    DiagnosisResult as ModuleDiagnosisResult,
)
from backend.domains.cn.transfer_diagnosis.service import DiagnosisService as TransferDiagnosisService
from backend.repositories.diagnosis_repository import DiagnosisRepository
from backend.schemas.diagnosis import (
    AssessmentHandoffResponse,
    DiagnosisAnswerSet,
    DiagnosisCitation,
    DiagnosisContextResponse,
    DiagnosisOutcome,
    DiagnosisReportResponse,
    DiagnosisResult,
    DiagnosisSessionCreateResponse,
    DiagnosisSessionResponse,
    DiagnosisSessionStatus,
    PIPIAHandoffResponse,
)
from backend.integrations.delilegal import DeliLegalService
from backend.services.report_service import ReportService
from backend.services.session_service import SessionService

_TRI_STATE_TO_MODULE = {
    "YES": "yes",
    "NO": "no",
    "UNCERTAIN": "unknown",
}
_PATH_TO_OUTCOME = {
    "security_assessment": DiagnosisOutcome.SECURITY_ASSESSMENT,
    "scc_or_certification": DiagnosisOutcome.SCC_OR_CERTIFICATION,
    "exemption": DiagnosisOutcome.EXEMPTION,
    "manual_review": DiagnosisOutcome.MANUAL_REVIEW,
    "insufficient_facts": DiagnosisOutcome.MANUAL_REVIEW,
}

_OUTCOME_LABELS = {
    DiagnosisOutcome.SECURITY_ASSESSMENT: "安全评估路径",
    DiagnosisOutcome.SCC_OR_CERTIFICATION: "标准合同/个人信息保护认证路径",
    DiagnosisOutcome.EXEMPTION: "豁免路径（无需向监管机构申报）",
    DiagnosisOutcome.MANUAL_REVIEW: "人工复核",
}


class DiagnosisSessionService:
    """Persistence compatibility layer backed by the canonical diagnosis evaluator."""

    def __init__(
        self,
        report_service: ReportService,
        session_service: SessionService,
        legal_api_service: DeliLegalService,
        llm_client: LLMClient | None = None,
        evaluator: TransferDiagnosisService | None = None,
    ) -> None:
        self.repository = DiagnosisRepository()
        self.report_service = report_service
        self.session_service = session_service
        self.legal_api_service = legal_api_service
        self.evaluator = evaluator or TransferDiagnosisService(llm_client=llm_client)

    def create_session(
        self,
        db: Session,
        user_id: str,
    ) -> DiagnosisSessionCreateResponse:
        record = self.repository.create(db, user_id)
        return DiagnosisSessionCreateResponse(
            id=record.id,
            status=DiagnosisSessionStatus(record.status),
        )

    def submit_answers(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        answers: DiagnosisAnswerSet,
    ) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id, user_id)
        result = self._evaluate(answers)
        record.status = DiagnosisSessionStatus.COMPLETED.value
        record.answers_json = dumps(answers.model_dump())
        record.result_json = dumps(result.model_dump())
        record.context_json = dumps(
            self.session_service.build_prefill_context(
                result.outcome.value,
                answers.model_dump(),
            )
        )
        record = self.repository.save(db, record)
        return self._to_response(record)

    def get_result(
        self,
        db: Session,
        user_id: str,
        session_id: str,
    ) -> DiagnosisSessionResponse:
        return self._to_response(self._require_session(db, session_id, user_id))

    def get_context(
        self,
        db: Session,
        user_id: str,
        session_id: str,
    ) -> DiagnosisContextResponse:
        record = self._require_session(db, session_id, user_id)
        result = self._deserialize_result(record)
        answers = self._deserialize_answers(record)
        return DiagnosisContextResponse(
            session_id=record.id,
            outcome=result.outcome if result else None,
            company_profile=self._company_profile(answers) if answers else {},
            prefill_context=loads(record.context_json, {}),
        )

    def get_assessment_handoff(
        self,
        db: Session,
        user_id: str,
        session_id: str,
    ) -> AssessmentHandoffResponse:
        record = self._require_session(db, session_id, user_id)
        answers, result = self._require_completed_session(record)
        payload = self.session_service.build_assessment_handoff(
            record.id,
            result.outcome.value,
            answers.model_dump(),
        )
        return AssessmentHandoffResponse.model_validate(payload)

    def get_pipia_handoff(
        self,
        db: Session,
        user_id: str,
        session_id: str,
    ) -> PIPIAHandoffResponse:
        record = self._require_session(db, session_id, user_id)
        answers, result = self._require_completed_session(record)
        payload = self.session_service.build_pipia_handoff(
            record.id,
            result.outcome.value,
            answers.model_dump(),
        )
        return PIPIAHandoffResponse.model_validate(payload)

    def generate_report(
        self,
        db: Session,
        user_id: str,
        session_id: str,
    ) -> DiagnosisReportResponse:
        record = self._require_session(db, session_id, user_id)
        answers, result = self._require_completed_session(record)

        preview = {
            "summary": result.summary,
            "outcome": result.outcome.value,
            "next_actions": result.next_actions,
        }
        html_report = self.report_service.create_html_report(
            db,
            user_id,
            "diagnosis",
            record.id,
            "diagnosis_report.html",
            self._build_html(record.id, answers, result),
            preview,
        )
        pdf_report = self.report_service.create_pdf_report(
            db,
            user_id,
            "diagnosis",
            record.id,
            "diagnosis_report.pdf",
            [
                "DataComplyFlow 合规路径诊断报告",
                f"会话ID: {record.id}",
                f"结论: {result.outcome.value}",
                f"摘要: {result.summary}",
                "命中规则:",
                *result.hit_rules,
                "后续行动:",
                *result.next_actions,
            ],
            preview,
        )
        return DiagnosisReportResponse(
            html_report=html_report,
            pdf_report=pdf_report,
        )

    def _evaluate(self, answers: DiagnosisAnswerSet) -> DiagnosisResult:
        module_result = self.evaluator.evaluate(self._to_module_answers(answers))
        outcome = _PATH_TO_OUTCOME.get(
            module_result.recommended_path,
            DiagnosisOutcome.MANUAL_REVIEW,
        )
        hit_rules = self._build_hit_rules(module_result)
        citations = self._build_citations(
            answers,
            outcome,
            module_result.legal_basis,
        )
        return DiagnosisResult(
            outcome=outcome,
            summary=module_result.final_explanation or module_result.rationale,
            hit_rules=hit_rules,
            citations=citations,
            next_actions=module_result.action_items,
            suggested_next_module=self._suggested_next_module(outcome),
        )

    @staticmethod
    def _to_module_answers(
        answers: DiagnosisAnswerSet,
    ) -> ModuleDiagnosisAnswers:
        return ModuleDiagnosisAnswers(
            q1_is_ciio=_TRI_STATE_TO_MODULE[answers.is_ciio.value],
            q2_has_important_data=(
                _TRI_STATE_TO_MODULE[answers.contains_important_data.value]
            ),
            q3_pii_count=answers.personal_info_count,
            q4_spi_count=answers.sensitive_personal_info_count,
            q5_no_personal_info=(
                _TRI_STATE_TO_MODULE[answers.no_personal_info.value]
            ),
            q6_scenario=answers.transfer_scenario.value,
            q7_receiver_type=answers.receiver_type.value,
            q8_purpose=answers.transfer_purpose or "",
        )

    @staticmethod
    def _build_hit_rules(result: ModuleDiagnosisResult) -> list[str]:
        items: list[str] = []
        if result.matched_rule_id:
            items.append(f"规则ID：{result.matched_rule_id}")
        items.append(result.rationale)
        items.extend(result.uncertainty_notes)
        return list(dict.fromkeys(item for item in items if item))

    @staticmethod
    def _suggested_next_module(
        outcome: DiagnosisOutcome,
    ) -> str | None:
        if outcome == DiagnosisOutcome.SECURITY_ASSESSMENT:
            return "assessment"
        if outcome == DiagnosisOutcome.SCC_OR_CERTIFICATION:
            return "pipia"
        if outcome == DiagnosisOutcome.EXEMPTION:
            return "general"
        return None

    def _build_citations(
        self,
        answers: DiagnosisAnswerSet,
        outcome: DiagnosisOutcome,
        legal_basis: list[str],
    ) -> list[DiagnosisCitation]:
        citations = [
            DiagnosisCitation(
                source="DataComplyFlow 规则表",
                article=item,
                note="当前路径判定命中的法律依据。",
            )
            for item in legal_basis
        ]
        purpose = answers.transfer_purpose or outcome.value

        for hit in self.legal_api_service.search_cases(
            f"数据出境 {purpose}",
            size=2,
        ):
            citations.append(
                DiagnosisCitation(
                    source=hit["source"],
                    article=hit["title"],
                    note=(hit["summary"] or "外部案例补充检索结果")[:120],
                )
            )
        for hit in self.legal_api_service.search_laws(
            f"数据出境 {purpose} 合规路径",
            size=3,
        ):
            citations.append(
                DiagnosisCitation(
                    source=hit["source"],
                    article=hit["title"],
                    note=(hit["summary"] or "外部法条补充检索结果")[:120],
                )
            )
        return citations

    @staticmethod
    def _build_html(
        session_id: str,
        answers: DiagnosisAnswerSet,
        result: DiagnosisResult,
    ) -> str:
        scenario_labels = {
            "contract_performance": "履行合同/服务消费者",
            "hr_management": "跨国公司内部人力资源管理",
            "emergency": "紧急情况保护生命健康财产",
            "legal_duty": "履行法定职责义务",
            "other": "其他商业目的",
        }
        answer_lines = [
            f"<li>是否为 CIIO：{escape(answers.is_ciio.value)}</li>",
            f"<li>是否包含重要数据：{escape(answers.contains_important_data.value)}</li>",
            f"<li>普通个人信息数量：{answers.personal_info_count:,} 人</li>",
            f"<li>敏感个人信息数量：{answers.sensitive_personal_info_count:,} 人</li>",
            (
                "<li>出境场景："
                f"{escape(scenario_labels.get(answers.transfer_scenario.value, answers.transfer_scenario.value))}"
                "</li>"
            ),
            f"<li>出境目的：{escape(answers.transfer_purpose or '未填写')}</li>",
        ]
        rule_lines = "".join(
            f"<li>{escape(rule)}</li>"
            for rule in result.hit_rules
        )
        citation_lines = "".join(
            (
                f"<li>{escape(citation.source)} "
                f"{escape(citation.article)}：{escape(citation.note)}</li>"
            )
            for citation in result.citations
        )
        action_lines = "".join(
            f"<li>{escape(action)}</li>"
            for action in result.next_actions
        )
        outcome_label = _OUTCOME_LABELS.get(
            result.outcome,
            result.outcome.value,
        )
        return f"""
        <html lang="zh-CN">
          <body>
            <h1>DataComplyFlow 合规路径诊断报告</h1>
            <p>会话 ID：{escape(session_id)}</p>
            <h2>诊断结论</h2>
            <p><strong>{escape(outcome_label)}</strong></p>
            <p>{escape(result.summary)}</p>
            <h2>用户回答摘要</h2>
            <ul>{''.join(answer_lines)}</ul>
            <h2>命中规则链</h2>
            <ul>{rule_lines}</ul>
            <h2>法规依据</h2>
            <ul>{citation_lines}</ul>
            <h2>后续行动清单</h2>
            <ul>{action_lines}</ul>
          </body>
        </html>
        """

    def _require_session(
        self,
        db: Session,
        session_id: str,
        user_id: str,
    ) -> DiagnosisSessionModel:
        record = self.repository.get(db, session_id, user_id)
        if not record:
            raise ValueError("Diagnosis session not found")
        return record

    def _require_completed_session(
        self,
        record: DiagnosisSessionModel,
    ) -> tuple[DiagnosisAnswerSet, DiagnosisResult]:
        answers = self._deserialize_answers(record)
        result = self._deserialize_result(record)
        if not answers or not result:
            raise ValueError("Diagnosis session is incomplete")
        return answers, result

    def _to_response(
        self,
        record: DiagnosisSessionModel,
    ) -> DiagnosisSessionResponse:
        return DiagnosisSessionResponse(
            id=record.id,
            status=DiagnosisSessionStatus(record.status),
            answers=self._deserialize_answers(record),
            result=self._deserialize_result(record),
        )

    @staticmethod
    def _deserialize_answers(
        record: DiagnosisSessionModel,
    ) -> DiagnosisAnswerSet | None:
        data = loads(record.answers_json, {})
        return DiagnosisAnswerSet.model_validate(data) if data else None

    @staticmethod
    def _deserialize_result(
        record: DiagnosisSessionModel,
    ) -> DiagnosisResult | None:
        data = loads(record.result_json, {})
        return DiagnosisResult.model_validate(data) if data else None

    @staticmethod
    def _company_profile(
        answers: DiagnosisAnswerSet,
    ) -> dict:
        return {
            "is_ciio": answers.is_ciio.value,
            "contains_important_data": answers.contains_important_data.value,
            "personal_info_count": answers.personal_info_count,
            "sensitive_personal_info_count": answers.sensitive_personal_info_count,
            "transfer_purpose": answers.transfer_purpose,
            "transfer_scenario": answers.transfer_scenario.value,
        }
