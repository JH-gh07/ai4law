import json
from pathlib import Path

from sqlalchemy.orm import Session

from backend.common.llm.client import LLMClient
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
    TransferScenario,
    DiagnosisSessionCreateResponse,
    DiagnosisSessionResponse,
    DiagnosisSessionStatus,
)
from backend.services.report_service import ReportService
from backend.services.session_service import SessionService
from backend.services.legal_api_service import DeliLegalService

_EXEMPTION_REASON_MAP = {
    TransferScenario.CONTRACT_PERFORMANCE: (
        "本次出境属于履行合同或向消费者提供服务所必需，"
        "依据《促进和规范数据跨境流动规定》第5条第(一)项，符合豁免申报条件。"
    ),
    TransferScenario.HR_MANAGEMENT: (
        "本次出境属于跨国公司依法开展的内部人力资源管理，"
        "依据《促进和规范数据跨境流动规定》第5条第(二)项，符合豁免申报条件。"
        "注意：须确保接收方为集团内关联公司，且满足个人信息保护同等水平要求。"
    ),
    TransferScenario.EMERGENCY: (
        "本次出境属于紧急情况下保护自然人生命、健康或财产安全所必需，"
        "依据《促进和规范数据跨境流动规定》第5条第(三)项，符合豁免申报条件。"
    ),
    TransferScenario.LEGAL_DUTY: (
        "本次出境属于依法履行法定职责或法定义务所必需，"
        "依据《促进和规范数据跨境流动规定》第5条第(四)项，符合豁免申报条件。"
    ),
}

_OUTCOME_LABELS = {
    DiagnosisOutcome.SECURITY_ASSESSMENT: "安全评估路径",
    DiagnosisOutcome.SCC_OR_CERTIFICATION: "标准合同/个人信息保护认证路径",
    DiagnosisOutcome.EXEMPTION: "豁免路径（无需向监管机构申报）",
}

_SYSTEM_PROMPT = (
    "你是一名精通中国数据出境合规的资深律师，熟悉《个人信息保护法》《数据安全法》"
    "《数据出境安全评估办法》《个人信息出境标准合同办法》《促进和规范数据跨境流动规定》等法规。"
    "请用专业、简洁的中文回答，不超过200字。"
)


class DiagnosisService:
    def __init__(
        self,
        report_service: ReportService,
        session_service: SessionService,
        legal_api_service: DeliLegalService,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.repository = DiagnosisRepository()
        self.report_service = report_service
        self.session_service = session_service
        self.legal_api_service = legal_api_service
        self.llm_client = llm_client
        self._citations = self._load_citations()

    def create_session(self, db: Session, user_id: str) -> DiagnosisSessionCreateResponse:
        record = self.repository.create(db, user_id)
        return DiagnosisSessionCreateResponse(id=record.id, status=DiagnosisSessionStatus(record.status))

    def submit_answers(self, db: Session, user_id: str, session_id: str, answers: DiagnosisAnswerSet) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id, user_id)
        result = self._evaluate(answers)
        record.status = DiagnosisSessionStatus.COMPLETED.value
        record.answers_json = dumps(answers.model_dump())
        record.result_json = dumps(result.model_dump())
        record.context_json = dumps(self.session_service.build_prefill_context(result.outcome.value, answers.model_dump()))
        record = self.repository.save(db, record)
        return self._to_response(record)

    def get_result(self, db: Session, user_id: str, session_id: str) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id, user_id)
        return self._to_response(record)

    def get_context(self, db: Session, user_id: str, session_id: str) -> DiagnosisContextResponse:
        record = self._require_session(db, session_id, user_id)
        result = self._deserialize_result(record)
        answers = self._deserialize_answers(record)
        return DiagnosisContextResponse(
            session_id=record.id,
            outcome=result.outcome if result else None,
            company_profile=self._company_profile(answers) if answers else {},
            prefill_context=loads(record.context_json, {}),
        )

    def get_assessment_handoff(self, db: Session, user_id: str, session_id: str) -> AssessmentHandoffResponse:
        record = self._require_session(db, session_id, user_id)
        answers = self._deserialize_answers(record)
        result = self._deserialize_result(record)
        if not answers or not result:
            raise ValueError("Diagnosis session is incomplete")
        payload = self.session_service.build_assessment_handoff(record.id, result.outcome.value, answers.model_dump())
        return AssessmentHandoffResponse.model_validate(payload)

    def get_scc_handoff(self, db: Session, user_id: str, session_id: str) -> SCCHandoffResponse:
        record = self._require_session(db, session_id, user_id)
        answers = self._deserialize_answers(record)
        result = self._deserialize_result(record)
        if not answers or not result:
            raise ValueError("Diagnosis session is incomplete")
        payload = self.session_service.build_scc_handoff(record.id, result.outcome.value, answers.model_dump())
        return SCCHandoffResponse.model_validate(payload)

    def generate_report(self, db: Session, user_id: str, session_id: str) -> DiagnosisReportResponse:
        record = self._require_session(db, session_id, user_id)
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
            db, user_id, "diagnosis", record.id, "diagnosis_report.html", html, preview
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
            db, user_id, "diagnosis", record.id, "diagnosis_report.pdf", pdf_lines, preview
        )
        return DiagnosisReportResponse(html_report=html_report, pdf_report=pdf_report)

    # ── 核心评估逻辑 ────────────────────────────────────────────────

    def _evaluate(self, answers: DiagnosisAnswerSet) -> DiagnosisResult:
        hit_rules: list[str] = []
        outcome, exemption_reason = self._determine_outcome(answers, hit_rules)

        suggested_next_module, next_actions = self._build_next_actions(outcome)

        summary = self._generate_summary(answers, outcome, hit_rules, exemption_reason)

        return DiagnosisResult(
            outcome=outcome,
            summary=summary,
            hit_rules=hit_rules,
            citations=self._build_citations(answers, outcome),
            next_actions=next_actions,
            suggested_next_module=suggested_next_module,
        )

    def _determine_outcome(
        self, answers: DiagnosisAnswerSet, hit_rules: list[str]
    ) -> tuple[DiagnosisOutcome, str]:
        # 优先级0：不含个人信息和重要数据 → 直接豁免
        if answers.no_personal_info.value == "YES":
            hit_rules.append("出境数据不含个人信息且不涉及重要数据，无需申报（《促进和规范数据跨境流动规定》第4条）")
            return DiagnosisOutcome.EXEMPTION, "不含个人信息和重要数据，依法免于申报。"

        is_ciio = answers.is_ciio.value == "YES"
        has_important_data = answers.contains_important_data.value == "YES"
        pii = answers.personal_info_count
        spi = answers.sensitive_personal_info_count
        scenario = answers.transfer_scenario
        is_intra_group = answers.receiver_type.value == "intra_group"

        # 豁免情形（仅在未触发强制评估门槛时适用）
        _below_mandatory_threshold = (
            not is_ciio
            and not has_important_data
            and pii < 1_000_000
            and spi < 10_000
        )

        if _below_mandatory_threshold:
            if scenario == TransferScenario.CONTRACT_PERFORMANCE:
                hit_rules.append("履行合同/服务消费者场景，规模未触发强制评估门槛（《促进和规范数据跨境流动规定》第5条第(一)项）")
                return DiagnosisOutcome.EXEMPTION, _EXEMPTION_REASON_MAP[scenario]
            if scenario == TransferScenario.HR_MANAGEMENT and is_intra_group:
                hit_rules.append("跨国公司内部人力资源管理+集团内传输，规模未触发强制评估门槛（《促进和规范数据跨境流动规定》第5条第(二)项）")
                return DiagnosisOutcome.EXEMPTION, _EXEMPTION_REASON_MAP[scenario]
            if scenario == TransferScenario.EMERGENCY:
                hit_rules.append("紧急情况保护生命健康财产安全场景（《促进和规范数据跨境流动规定》第5条第(三)项）")
                return DiagnosisOutcome.EXEMPTION, _EXEMPTION_REASON_MAP[scenario]
            if scenario == TransferScenario.LEGAL_DUTY:
                hit_rules.append("依法履行法定职责或法定义务（《促进和规范数据跨境流动规定》第5条第(四)项）")
                return DiagnosisOutcome.EXEMPTION, _EXEMPTION_REASON_MAP[scenario]

        # 强制安全评估条件
        if is_ciio:
            hit_rules.append("CIIO 身份命中安全评估强制条件（《个人信息保护法》第40条）")
            return DiagnosisOutcome.SECURITY_ASSESSMENT, ""
        if has_important_data:
            hit_rules.append("涉及重要数据出境（《数据安全法》第21条，《数据出境安全评估办法》第4条）")
            return DiagnosisOutcome.SECURITY_ASSESSMENT, ""
        if pii >= 1_000_000:
            hit_rules.append(f"累计向境外提供个人信息 {pii:,} 人，达到100万人门槛（《数据出境安全评估办法》第4条）")
            return DiagnosisOutcome.SECURITY_ASSESSMENT, ""
        if spi >= 10_000:
            hit_rules.append(f"累计向境外提供敏感个人信息 {spi:,} 人，达到1万人门槛（《数据出境安全评估办法》第4条）")
            return DiagnosisOutcome.SECURITY_ASSESSMENT, ""

        # 兜底：标准合同/认证路径
        if pii > 0 or spi > 0:
            hit_rules.append("个人信息规模未达强制评估门槛，适用标准合同备案或个人信息保护认证路径")
        else:
            hit_rules.append("数量规模暂未填写，建议核实后按标准合同/认证路径准备材料")
        return DiagnosisOutcome.SCC_OR_CERTIFICATION, ""

    def _generate_summary(
        self,
        answers: DiagnosisAnswerSet,
        outcome: DiagnosisOutcome,
        hit_rules: list[str],
        exemption_reason: str,
    ) -> str:
        if self.llm_client and self.llm_client.enabled:
            user_prompt = (
                f"企业数据出境合规路径诊断结果如下，请生成一段专业的诊断说明（150字以内）：\n"
                f"- 诊断结论：{_OUTCOME_LABELS.get(outcome, outcome.value)}\n"
                f"- 命中规则：{'；'.join(hit_rules)}\n"
                f"- 出境场景：{answers.transfer_scenario.value}\n"
                f"- 个人信息数量：{answers.personal_info_count:,}人\n"
                f"- 敏感个人信息数量：{answers.sensitive_personal_info_count:,}人\n"
                f"- 出境目的：{answers.transfer_purpose or '未填写'}\n"
                + (f"- 豁免依据：{exemption_reason}\n" if exemption_reason else "")
            )
            return self.llm_client.chat(
                system=_SYSTEM_PROMPT,
                user=user_prompt,
                max_tokens=300,
            )
        # 降级：模板文本
        label = _OUTCOME_LABELS.get(outcome, outcome.value)
        key_rules = "；".join(hit_rules[:2])
        return f"根据当前填写信息，系统判定企业应走\"{label}\"。关键因素：{key_rules}。"

    @staticmethod
    def _build_next_actions(outcome: DiagnosisOutcome) -> tuple[str | None, list[str]]:
        base = [
            "核对业务场景、数据类型和数量统计口径，保留内部留痕。",
            "结合律师或合规团队意见复核最终路径判断。",
        ]
        if outcome == DiagnosisOutcome.SECURITY_ASSESSMENT:
            return "assessment", ["准备安全评估申报所需材料，并进入安全评估路径模块。"] + base
        elif outcome == DiagnosisOutcome.SCC_OR_CERTIFICATION:
            return "scc", ["进一步判断更适合标准合同备案还是个人信息出境认证路径。"] + base
        else:
            return "general", [
                "确认豁免情形适用性，留存适用豁免路径的内部论证文件。",
                "即使豁免申报，仍须履行告知同意（《个保法》第39条）和PIPIA评估（第55条）义务。",
            ] + base

    def _build_html(self, session_id: str, answers: DiagnosisAnswerSet, result: DiagnosisResult) -> str:
        scenario_labels = {
            "contract_performance": "履行合同/服务消费者",
            "hr_management": "跨国公司内部人力资源管理",
            "emergency": "紧急情况保护生命健康财产",
            "legal_duty": "履行法定职责义务",
            "other": "其他商业目的",
        }
        answer_lines = [
            f"<li>是否为 CIIO：{answers.is_ciio.value}</li>",
            f"<li>是否包含重要数据：{answers.contains_important_data.value}</li>",
            f"<li>普通个人信息数量：{answers.personal_info_count:,} 人</li>",
            f"<li>敏感个人信息数量：{answers.sensitive_personal_info_count:,} 人</li>",
            f"<li>出境场景：{scenario_labels.get(answers.transfer_scenario.value, answers.transfer_scenario.value)}</li>",
            f"<li>出境目的：{answers.transfer_purpose or '未填写'}</li>",
        ]
        rule_lines = "".join(f"<li>{rule}</li>" for rule in result.hit_rules)
        citation_lines = "".join(
            f"<li>{citation.source} {citation.article}：{citation.note}</li>"
            for citation in result.citations
        )
        action_lines = "".join(f"<li>{action}</li>" for action in result.next_actions)
        outcome_label = _OUTCOME_LABELS.get(result.outcome, result.outcome.value)
        return f"""
        <html lang="zh-CN">
          <body>
            <h1>AI4Law 合规路径诊断报告</h1>
            <p>会话 ID：{session_id}</p>
            <h2>诊断结论</h2>
            <p><strong>{outcome_label}</strong></p>
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
            "transfer_scenario": answers.transfer_scenario.value,
        }

    def _require_session(self, db: Session, session_id: str, user_id: str) -> DiagnosisSessionModel:
        record = self.repository.get(db, session_id, user_id)
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

        # 案例检索
        remote_hits = self.legal_api_service.search_cases(f"数据出境 {purpose}", size=2)
        for hit in remote_hits:
            citations.append(
                DiagnosisCitation(
                    source=hit["source"],
                    article=hit["title"],
                    note=(hit["summary"] or "来自得理法搜的补充检索结果")[:120],
                )
            )

        # 法条检索（V2新增）
        law_hits = self.legal_api_service.search_laws(f"数据出境 {purpose} 合规路径", size=3)
        for hit in law_hits:
            citations.append(
                DiagnosisCitation(
                    source=hit["source"],
                    article=hit["title"],
                    note=(hit["summary"] or "来自得理法搜的法条检索结果")[:120],
                )
            )

        return citations
