import json
from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.json_utils import dumps, loads
from backend.models.diagnosis import DiagnosisSessionModel
from backend.repositories.diagnosis_repository import DiagnosisRepository
from backend.schemas.diagnosis import (
    AssessmentHandoffResponse,
    DiagnosisAnswerSet,
    DiagnosisCitation,
    DiagnosisContextResponse,
    DiagnosisOutcome,
    DiagnosisReportResponse,
    DiagnosisResult,
    SCCHandoffResponse,
    DiagnosisSessionCreateResponse,
    DiagnosisSessionResponse,
    DiagnosisSessionStatus,
)
from backend.services.report_service import ReportService
from backend.services.session_service import SessionService
from backend.services.legal_api_service import DeliLegalService


class DiagnosisNarrativeGenerator:
    def build_summary(self, answers: DiagnosisAnswerSet, result: DiagnosisResult) -> str:
        return (
            f"根据当前填写信息，系统判定企业当前更适合走“{result.outcome.value}”路径。"
            f" 关键因素包括：{'; '.join(result.hit_rules)}。"
        )


class DiagnosisService:
    def __init__(self, report_service: ReportService, session_service: SessionService, legal_api_service: DeliLegalService) -> None:
        self.repository = DiagnosisRepository()
        self.report_service = report_service
        self.session_service = session_service
        self.legal_api_service = legal_api_service
        self.narrative_generator = DiagnosisNarrativeGenerator()
        self._citations = self._load_citations()

    def create_session(self, db: Session) -> DiagnosisSessionCreateResponse:
        record = self.repository.create(db)
        return DiagnosisSessionCreateResponse(id=record.id, status=DiagnosisSessionStatus(record.status))

    def submit_answers(self, db: Session, session_id: str, answers: DiagnosisAnswerSet) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id)
        result = self._evaluate(answers)
        record.status = DiagnosisSessionStatus.COMPLETED.value
        record.answers_json = dumps(answers.model_dump())
        record.result_json = dumps(result.model_dump())
        record.context_json = dumps(self.session_service.build_prefill_context(result.outcome.value, answers.model_dump()))
        record = self.repository.save(db, record)
        return self._to_response(record)

    def get_result(self, db: Session, session_id: str) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id)
        return self._to_response(record)

    def get_context(self, db: Session, session_id: str) -> DiagnosisContextResponse:
        record = self._require_session(db, session_id)
        result = self._deserialize_result(record)
        answers = self._deserialize_answers(record)
        return DiagnosisContextResponse(
            session_id=record.id,
            outcome=result.outcome if result else None,
            company_profile=self._company_profile(answers) if answers else {},
            prefill_context=loads(record.context_json, {}),
        )

    def get_assessment_handoff(self, db: Session, session_id: str) -> AssessmentHandoffResponse:
        record = self._require_session(db, session_id)
        answers = self._deserialize_answers(record)
        result = self._deserialize_result(record)
        if not answers or not result:
            raise ValueError("Diagnosis session is incomplete")
        payload = self.session_service.build_assessment_handoff(record.id, result.outcome.value, answers.model_dump())
        return AssessmentHandoffResponse.model_validate(payload)

    def get_scc_handoff(self, db: Session, session_id: str) -> SCCHandoffResponse:
        record = self._require_session(db, session_id)
        answers = self._deserialize_answers(record)
        result = self._deserialize_result(record)
        if not answers or not result:
            raise ValueError("Diagnosis session is incomplete")
        payload = self.session_service.build_scc_handoff(record.id, result.outcome.value, answers.model_dump())
        return SCCHandoffResponse.model_validate(payload)

    def generate_report(self, db: Session, session_id: str) -> DiagnosisReportResponse:
        record = self._require_session(db, session_id)
        answers = self._deserialize_answers(record)
        result = self._deserialize_result(record)
        if not answers or not result:
            raise ValueError("Diagnosis session is incomplete")

        html = self._build_html(record.id, answers, result)
        preview = {
            "summary": result.summary,
            "outcome": result.outcome.value,
            "next_actions": result.next_actions,
        }
        html_report = self.report_service.create_html_report(
            db, "diagnosis", record.id, "diagnosis_report.html", html, preview
        )
        pdf_lines = [
            "AI4Law 合规路径诊断报告",
            f"会话ID: {record.id}",
            f"结论: {result.outcome.value}",
            f"摘要: {result.summary}",
            "命中规则:",
            *result.hit_rules,
            "后续行动:",
            *result.next_actions,
        ]
        pdf_report = self.report_service.create_pdf_report(
            db, "diagnosis", record.id, "diagnosis_report.pdf", pdf_lines, preview
        )
        return DiagnosisReportResponse(html_report=html_report, pdf_report=pdf_report)

    def _evaluate(self, answers: DiagnosisAnswerSet) -> DiagnosisResult:
        hit_rules: list[str] = []
        outcome = DiagnosisOutcome.EXEMPTION

        if answers.is_ciio.value == "YES":
            hit_rules.append("CIIO 身份命中安全评估强制条件")
            outcome = DiagnosisOutcome.SECURITY_ASSESSMENT
        elif answers.contains_important_data.value == "YES":
            hit_rules.append("涉及重要数据出境，命中安全评估强制条件")
            outcome = DiagnosisOutcome.SECURITY_ASSESSMENT
        elif answers.personal_info_count >= 1_000_000:
            hit_rules.append("累计向境外提供个人信息达到 100 万人门槛")
            outcome = DiagnosisOutcome.SECURITY_ASSESSMENT
        elif answers.sensitive_personal_info_count >= 10_000:
            hit_rules.append("累计向境外提供敏感个人信息达到 1 万人门槛")
            outcome = DiagnosisOutcome.SECURITY_ASSESSMENT
        elif answers.personal_info_count >= 100_000:
            hit_rules.append("个人信息数量处于 10 万至 100 万区间")
            outcome = DiagnosisOutcome.SCC_OR_CERTIFICATION
        else:
            hit_rules.append("个人信息与敏感个人信息规模均未达到强制评估门槛")
            outcome = DiagnosisOutcome.EXEMPTION

        suggested_next_module = None
        next_actions = [
            "核对业务场景、数据类型和数量统计口径，保留内部留痕。",
            "结合律师或合规团队意见复核最终路径判断。",
        ]

        if outcome == DiagnosisOutcome.SECURITY_ASSESSMENT:
            suggested_next_module = "assessment"
            next_actions.insert(0, "准备安全评估申报所需材料，并进入安全评估路径模块。")
        elif outcome == DiagnosisOutcome.SCC_OR_CERTIFICATION:
            suggested_next_module = "scc"
            next_actions.insert(0, "进一步判断更适合标准合同备案还是个人信息出境认证路径。")
        else:
            suggested_next_module = "general"
            next_actions.insert(0, "确认是否适用豁免路径，并持续关注法规更新与场景变化。")

        placeholder = DiagnosisResult(
            outcome=outcome,
            summary="",
            hit_rules=hit_rules,
            citations=self._build_citations(answers, outcome),
            next_actions=next_actions,
            suggested_next_module=suggested_next_module,
        )
        placeholder.summary = self.narrative_generator.build_summary(answers, placeholder)
        return placeholder

    def _build_html(self, session_id: str, answers: DiagnosisAnswerSet, result: DiagnosisResult) -> str:
        answer_lines = [
            f"<li>是否为 CIIO：{answers.is_ciio.value}</li>",
            f"<li>是否包含重要数据：{answers.contains_important_data.value}</li>",
            f"<li>普通个人信息数量：{answers.personal_info_count}</li>",
            f"<li>敏感个人信息数量：{answers.sensitive_personal_info_count}</li>",
            f"<li>出境目的：{answers.transfer_purpose or '未填写'}</li>",
        ]
        rule_lines = "".join(f"<li>{rule}</li>" for rule in result.hit_rules)
        citation_lines = "".join(
            f"<li>{citation.source} {citation.article}：{citation.note}</li>"
            for citation in result.citations
        )
        action_lines = "".join(f"<li>{action}</li>" for action in result.next_actions)
        return f"""
        <html lang="zh-CN">
          <body>
            <h1>AI4Law 合规路径诊断报告</h1>
            <p>会话 ID：{session_id}</p>
            <h2>诊断结论</h2>
            <p>{result.outcome.value}</p>
            <p>{result.summary}</p>
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

    def _to_response(self, record: DiagnosisSessionModel) -> DiagnosisSessionResponse:
        answers = self._deserialize_answers(record)
        result = self._deserialize_result(record)
        return DiagnosisSessionResponse(
            id=record.id,
            status=DiagnosisSessionStatus(record.status),
            answers=answers,
            result=result,
        )

    def _deserialize_answers(self, record: DiagnosisSessionModel) -> DiagnosisAnswerSet | None:
        data = loads(record.answers_json, {})
        return DiagnosisAnswerSet.model_validate(data) if data else None

    def _deserialize_result(self, record: DiagnosisSessionModel) -> DiagnosisResult | None:
        data = loads(record.result_json, {})
        return DiagnosisResult.model_validate(data) if data else None

    def _company_profile(self, answers: DiagnosisAnswerSet) -> dict:
        return {
            "is_ciio": answers.is_ciio.value,
            "contains_important_data": answers.contains_important_data.value,
            "personal_info_count": answers.personal_info_count,
            "sensitive_personal_info_count": answers.sensitive_personal_info_count,
            "transfer_purpose": answers.transfer_purpose,
        }

    def _require_session(self, db: Session, session_id: str) -> DiagnosisSessionModel:
        record = self.repository.get(db, session_id)
        if not record:
            raise ValueError("Diagnosis session not found")
        return record

    def _load_citations(self) -> list[DiagnosisCitation]:
        path = Path(__file__).resolve().parent.parent / "data" / "diagnosis_citations.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [DiagnosisCitation.model_validate(item) for item in payload]

    def _build_citations(self, answers: DiagnosisAnswerSet, outcome: DiagnosisOutcome) -> list[DiagnosisCitation]:
        citations = list(self._citations)
        purpose = answers.transfer_purpose or outcome.value
        remote_hits = self.legal_api_service.search_cases(f"数据出境 {purpose}", size=2)
        for hit in remote_hits:
            citations.append(
                DiagnosisCitation(
                    source=hit["source"],
                    article=hit["title"],
                    note=(hit["summary"] or "来自得理法搜的补充检索结果")[:120],
                )
            )
        return citations
