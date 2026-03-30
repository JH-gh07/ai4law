import json
from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.json_utils import dumps, loads
from backend.models.diagnosis import DiagnosisSessionModel
from backend.repositories.diagnosis_repository import DiagnosisRepository
from backend.schemas.diagnosis import (
    AssessmentHandoffResponse,
    ComplianceProfileDraft,
    ComplianceQuestionnaire,
    DiagnosisAnswerSet,
    DiagnosisAssessmentReport,
    DiagnosisCitation,
    DiagnosisContextResponse,
    DiagnosisOutcome,
    DiagnosisReportResponse,
    DiagnosisResult,
    DiagnosisSessionCreateResponse,
    DiagnosisSessionResponse,
    DiagnosisSessionStatus,
    PriorityLevel,
    RiskLevel,
    RuleEvaluationResult,
    RuleHit,
    SCCHandoffResponse,
    TriState,
)
from backend.services.legal_api_service import DeliLegalService
from backend.services.report_service import ReportService
from backend.services.session_service import SessionService


class QuestionnaireNormalizer:
    def normalize(self, payload: ComplianceQuestionnaire | dict) -> ComplianceQuestionnaire:
        if isinstance(payload, ComplianceQuestionnaire):
            return payload
        return ComplianceQuestionnaire.model_validate(payload)

    def from_legacy_answers(self, answers: DiagnosisAnswerSet) -> ComplianceQuestionnaire:
        personal_types = ["姓名", "手机号"] if answers.personal_info_count > 0 else []
        if answers.sensitive_personal_info_count > 0:
            personal_types.append("身份证号")
        return ComplianceQuestionnaire(
            enterprise_name=None,
            q1_2_industry="其他",
            q1_3_business_modes=["跨境服务"] if answers.transfer_purpose else ["其他"],
            q1_4_service_targets="个人用户和企业用户两者都有",
            q1_5_enterprise_size="未填写",
            q1_6_is_ciio=answers.is_ciio,
            q2_1_compliance_goals=["不确定业务是否需要做数据合规"],
            q2_2_has_incidents="UNCLEAR",
            q2_3_urgency="一般需求 (1-3 个月)",
            q3_1_handles_personal_info=answers.personal_info_count > 0 or answers.sensitive_personal_info_count > 0,
            q3_2_personal_info_types=personal_types,
            q3_3_handles_important_data=answers.contains_important_data == TriState.YES,
            q3_3_important_data_types=["其他"] if answers.contains_important_data == TriState.YES else [],
            q3_4_data_sources=["用户主动提交"],
            q3_5_processing_actions=["收集", "存储", "传输"] + (["跨境传输"] if answers.transfer_purpose else []),
            q3_6_data_volume=self._volume_bucket(answers.personal_info_count),
            q3_7_handles_enterprise_or_public_data=False,
            q3_8_retention_policy="业务必要期限内留存",
            q4_1_shares_with_third_parties=False,
            q4_2_cross_border_transfer=bool(answers.transfer_purpose),
            q4_2_countries=[],
            q4_3_monetization=False,
            q4_4_entrusted_processing=False,
            q4_5_authorization_mechanism="弹窗勾选同意",
            q5_1_systems=["官方网站"],
            q5_2_security_measures=[],
            q5_3_compliance_documents=[],
            q5_4_penalty_or_complaint_status="无相关记录",
        )

    def _volume_bucket(self, personal_info_count: int) -> str:
        if personal_info_count < 100_000:
            return "10 万条以下"
        if personal_info_count < 1_000_000:
            return "10-100 万条"
        if personal_info_count < 10_000_000:
            return "100-1000 万条"
        return "1000 万条以上"


class ProfileDraftBuilder:
    def build(self, questionnaire: ComplianceQuestionnaire) -> ComplianceProfileDraft:
        enterprise_attributes = {
            "enterprise_name": questionnaire.enterprise_name,
            "industry": questionnaire.q1_2_industry,
            "enterprise_size": questionnaire.q1_5_enterprise_size,
            "service_targets": questionnaire.q1_4_service_targets,
            "is_ciio": questionnaire.q1_6_is_ciio.value,
        }
        business_overview = {
            "business_modes": questionnaire.q1_3_business_modes,
            "systems": questionnaire.q5_1_systems,
            "urgency": questionnaire.q2_3_urgency,
        }
        compliance_needs = {
            "goals": questionnaire.q2_1_compliance_goals,
            "incidents": questionnaire.q2_2_has_incidents,
            "incident_description": questionnaire.q2_2_incident_description,
        }
        data_profile = {
            "handles_personal_info": questionnaire.q3_1_handles_personal_info,
            "personal_info_types": questionnaire.q3_2_personal_info_types,
            "handles_important_data": questionnaire.q3_3_handles_important_data,
            "important_data_types": questionnaire.q3_3_important_data_types,
            "data_sources": questionnaire.q3_4_data_sources,
            "processing_actions": questionnaire.q3_5_processing_actions,
            "data_volume": questionnaire.q3_6_data_volume,
            "retention_policy": questionnaire.q3_8_retention_policy,
        }
        data_flow_profile = {
            "shares_with_third_parties": questionnaire.q4_1_shares_with_third_parties,
            "third_party_detail": questionnaire.q4_1_third_party_detail,
            "cross_border_transfer": questionnaire.q4_2_cross_border_transfer,
            "countries": questionnaire.q4_2_countries,
            "monetization": questionnaire.q4_3_monetization,
            "entrusted_processing": questionnaire.q4_4_entrusted_processing,
            "authorization_mechanism": questionnaire.q4_5_authorization_mechanism,
        }
        governance_profile = {
            "security_measures": questionnaire.q5_2_security_measures,
            "compliance_documents": questionnaire.q5_3_compliance_documents,
            "penalty_or_complaint_status": questionnaire.q5_4_penalty_or_complaint_status,
            "penalty_or_complaint_detail": questionnaire.q5_4_penalty_or_complaint_detail,
        }
        narrative_summary = (
            f"企业属于{questionnaire.q1_2_industry}行业，主要通过{','.join(questionnaire.q1_3_business_modes) or '未填写'}开展业务；"
            f"当前数据规模为{questionnaire.q3_6_data_volume}，"
            f"{'涉及' if questionnaire.q4_2_cross_border_transfer else '暂不涉及'}跨境传输，"
            f"{'存在' if questionnaire.q4_1_shares_with_third_parties or questionnaire.q4_4_entrusted_processing else '暂未明显体现'}第三方流转。"
        )
        return ComplianceProfileDraft(
            enterprise_name=questionnaire.enterprise_name,
            enterprise_attributes=enterprise_attributes,
            business_overview=business_overview,
            compliance_needs=compliance_needs,
            data_profile=data_profile,
            data_flow_profile=data_flow_profile,
            governance_profile=governance_profile,
            narrative_summary=narrative_summary,
        )


class RuleEvaluationEngine:
    def evaluate(self, questionnaire: ComplianceQuestionnaire) -> RuleEvaluationResult:
        hits: list[RuleHit] = []
        has_sensitive_info = any(
            item in questionnaire.q3_2_personal_info_types
            for item in ["身份证号", "人脸 / 指纹 / 声纹", "健康信息", "金融账户信息", "未成年人信息", "精准位置信息"]
        )
        no_authorization = questionnaire.q4_5_authorization_mechanism in {"无授权机制", "继续使用即视为同意"}
        lacks_documents = not questionnaire.q5_3_compliance_documents or "无" in questionnaire.q5_3_compliance_documents
        lacks_core_security = not questionnaire.q5_2_security_measures or "无" in questionnaire.q5_2_security_measures
        no_policy = not questionnaire.q5_3_compliance_documents or "隐私政策" not in questionnaire.q5_3_compliance_documents
        no_agreement = questionnaire.q4_1_shares_with_third_parties and lacks_documents
        volume_value = self._volume_to_count(questionnaire.q3_6_data_volume)
        sensitive_count = 10_000 if has_sensitive_info and volume_value >= 100_000 else 0

        if questionnaire.q1_6_is_ciio == TriState.YES:
            hits.append(RuleHit(code="Q1-6_CIIO", question_refs=["Q1-6"], trigger_summary="企业被识别为 CIIO 主体", legal_basis=["《数据出境安全评估办法》第4条第2项"], risk_level=RiskLevel.CRITICAL, priority=PriorityLevel.HIGHEST))
        if questionnaire.q3_3_handles_important_data:
            hits.append(RuleHit(code="Q3-3_IMPORTANT_DATA", question_refs=["Q3-3"], trigger_summary="业务处理重要数据", legal_basis=["《数据安全法》第21条", "《数据出境安全评估办法》第4条第1项"], risk_level=RiskLevel.CRITICAL, priority=PriorityLevel.HIGHEST))
        if questionnaire.q4_2_cross_border_transfer and volume_value >= 1_000_000 and questionnaire.q3_1_handles_personal_info:
            hits.append(RuleHit(code="Q4-2_Q3-6_PERSONAL_INFO_CROSS_BORDER_1M", question_refs=["Q4-2", "Q3-6", "Q3-1"], trigger_summary="跨境传输且个人信息规模达到100万条以上", legal_basis=["《数据出境安全评估办法》第4条第2项"], risk_level=RiskLevel.CRITICAL, priority=PriorityLevel.HIGHEST))
        if questionnaire.q4_2_cross_border_transfer and has_sensitive_info and sensitive_count >= 10_000:
            hits.append(RuleHit(code="Q4-2_Q3-2_SENSITIVE_CROSS_BORDER_10K", question_refs=["Q4-2", "Q3-2"], trigger_summary="跨境传输且涉及敏感个人信息，达到重点监管门槛", legal_basis=["《数据出境安全评估办法》第4条第3项"], risk_level=RiskLevel.CRITICAL, priority=PriorityLevel.HIGHEST))
        if has_sensitive_info and no_authorization:
            hits.append(RuleHit(code="Q3-2_Q4-5_SENSITIVE_NO_AUTH", question_refs=["Q3-2", "Q4-5"], trigger_summary="收集敏感个人信息但缺少单独同意", legal_basis=["《个人信息保护法》第29条"], risk_level=RiskLevel.HIGH, priority=PriorityLevel.HIGH))
        if volume_value >= 1_000_000 and not questionnaire.q4_2_cross_border_transfer and questionnaire.q3_1_handles_personal_info:
            hits.append(RuleHit(code="Q3-6_HIGH_VOLUME_DOMESTIC", question_refs=["Q3-6", "Q3-1"], trigger_summary="境内处理个人信息达到100万条以上", legal_basis=["《个人信息保护法》第9条", "《个人信息保护法》第52条"], risk_level=RiskLevel.HIGH, priority=PriorityLevel.HIGH))
        if questionnaire.q4_2_cross_border_transfer and 100_000 <= volume_value < 1_000_000 and not questionnaire.q3_3_handles_important_data:
            hits.append(RuleHit(code="Q4-2_Q3-6_SCC_PATH", question_refs=["Q4-2", "Q3-6"], trigger_summary="跨境传输且个人信息规模在10万到100万之间", legal_basis=["《个人信息出境标准合同办法》第2条"], risk_level=RiskLevel.HIGH, priority=PriorityLevel.HIGH))
        if (questionnaire.q4_1_shares_with_third_parties or questionnaire.q4_4_entrusted_processing) and (no_agreement or no_authorization or no_policy or lacks_core_security):
            elevated = has_sensitive_info or volume_value >= 1_000_000
            hits.append(RuleHit(code="Q4-1_Q4-4_Q4-5_Q5-3_THIRD_PARTY_GAPS", question_refs=["Q4-1", "Q4-4", "Q4-5", "Q5-3"], trigger_summary="第三方共享或委托处理中存在协议、授权或制度缺口", legal_basis=["《个人信息保护法》第13条", "《个人信息保护法》第17条", "《个人信息保护法》第21条"], risk_level=RiskLevel.HIGH if elevated else RiskLevel.MEDIUM, priority=PriorityLevel.HIGH if elevated else PriorityLevel.MEDIUM))
        if questionnaire.q3_1_handles_personal_info and 100_000 <= volume_value < 1_000_000:
            hits.append(RuleHit(code="Q3-1_Q3-6_PERSONAL_INFO_SCALE", question_refs=["Q3-1", "Q3-6"], trigger_summary="普通个人信息处理规模处于10万到100万之间", legal_basis=["《个人信息保护法》第6条"], risk_level=RiskLevel.MEDIUM, priority=PriorityLevel.MEDIUM))
        if no_policy:
            hits.append(RuleHit(code="Q5-3_NO_POLICY", question_refs=["Q5-3"], trigger_summary="缺少隐私政策或未覆盖核心义务", legal_basis=["《个人信息保护法》第17条"], risk_level=RiskLevel.MEDIUM, priority=PriorityLevel.MEDIUM))
        if no_authorization and questionnaire.q3_1_handles_personal_info and not has_sensitive_info:
            hits.append(RuleHit(code="Q4-5_NO_LEGAL_BASIS", question_refs=["Q4-5"], trigger_summary="处理个人信息但缺少明确授权基础", legal_basis=["《个人信息保护法》第13条"], risk_level=RiskLevel.HIGH, priority=PriorityLevel.HIGH))
        if not questionnaire.q3_1_handles_personal_info and not questionnaire.q3_3_handles_important_data and not questionnaire.q4_2_cross_border_transfer and "纯内部使用" in questionnaire.q1_3_business_modes:
            hits.append(RuleHit(code="Q3-1_Q3-3_Q4-2_INTERNAL_EXEMPT", question_refs=["Q3-1", "Q3-3", "Q4-2", "Q1-3"], trigger_summary="无个人信息、无重要数据、无跨境且纯内部使用", legal_basis=["《数据安全法》第27条"], risk_level=RiskLevel.LOW, priority=PriorityLevel.LOW))

        risk_level = self._resolve_risk_level(hits, questionnaire, volume_value, has_sensitive_info)
        outcome = self._resolve_outcome(questionnaire, volume_value, has_sensitive_info)
        legal_summary = list(dict.fromkeys(item for hit in hits for item in hit.legal_basis))
        compliance_conclusion = self._build_compliance_conclusion(risk_level, hits)
        path_conclusion = self._build_path_conclusion(outcome, questionnaire)
        priority_actions = self._priority_actions(risk_level)
        return RuleEvaluationResult(risk_level=risk_level, outcome=outcome, hit_rules=hits, legal_summary=legal_summary, compliance_conclusion=compliance_conclusion, path_conclusion=path_conclusion, priority_actions=priority_actions, citations=[])

    def _resolve_risk_level(self, hits: list[RuleHit], questionnaire: ComplianceQuestionnaire, volume_value: int, has_sensitive_info: bool) -> RiskLevel:
        if any(hit.risk_level == RiskLevel.CRITICAL for hit in hits):
            return RiskLevel.CRITICAL
        if any(hit.risk_level == RiskLevel.HIGH for hit in hits):
            return RiskLevel.HIGH
        if any(hit.risk_level == RiskLevel.MEDIUM for hit in hits):
            return RiskLevel.MEDIUM
        if not questionnaire.q3_1_handles_personal_info and not questionnaire.q3_3_handles_important_data:
            return RiskLevel.LOW
        if volume_value < 100_000 and not questionnaire.q4_2_cross_border_transfer and not has_sensitive_info:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def _resolve_outcome(self, questionnaire: ComplianceQuestionnaire, volume_value: int, has_sensitive_info: bool) -> DiagnosisOutcome:
        if questionnaire.q4_2_cross_border_transfer:
            if questionnaire.q1_6_is_ciio == TriState.YES or questionnaire.q3_3_handles_important_data:
                return DiagnosisOutcome.SECURITY_ASSESSMENT
            if volume_value >= 1_000_000:
                return DiagnosisOutcome.SECURITY_ASSESSMENT
            if has_sensitive_info and volume_value >= 100_000:
                return DiagnosisOutcome.SECURITY_ASSESSMENT
            if volume_value >= 100_000 or has_sensitive_info:
                return DiagnosisOutcome.SCC_OR_CERTIFICATION
            if questionnaire.q4_2_exemption_scenarios:
                return DiagnosisOutcome.EXEMPTION
            return DiagnosisOutcome.EXEMPTION
        return DiagnosisOutcome.EXEMPTION

    def _build_compliance_conclusion(self, risk_level: RiskLevel, hits: list[RuleHit]) -> str:
        if not hits:
            return "当前未发现直接触发高风险规则的情形，建议保留基础合规管理台账并定期复核。"
        trigger = hits[0].trigger_summary
        if risk_level == RiskLevel.CRITICAL:
            return f"必须立即启动数据合规专项建设，核心触发情形为：{trigger}。"
        if risk_level == RiskLevel.HIGH:
            return f"需在1个月内完成核心合规整改，核心触发情形为：{trigger}。"
        if risk_level == RiskLevel.MEDIUM:
            return f"建议在3个月内完善合规体系，当前主要风险点为：{trigger}。"
        return f"当前整体风险较低，但仍需持续关注：{trigger}。"

    def _build_path_conclusion(self, outcome: DiagnosisOutcome, questionnaire: ComplianceQuestionnaire) -> str:
        if outcome == DiagnosisOutcome.SECURITY_ASSESSMENT:
            return "建议进入模块②安全评估路径，优先准备安全评估申报与PIA相关材料。"
        if outcome == DiagnosisOutcome.SCC_OR_CERTIFICATION:
            return "建议进入模块③认证/标准合同路径，进一步判断标准合同备案或个人信息保护认证。"
        if questionnaire.q4_2_cross_border_transfer:
            return "当前跨境行为可能存在豁免空间，但仍需结合具体场景复核。"
        return "当前可按豁免路径管理，暂不强制进入模块②/③。"

    def _priority_actions(self, risk_level: RiskLevel) -> list[str]:
        if risk_level == RiskLevel.CRITICAL:
            return ["立即停止新增高风险数据出境活动并保留留痕。", "启动数据出境安全评估与个人信息保护影响评估。", "补齐数据分类分级、安全制度、负责人指定与技术措施。"]
        if risk_level == RiskLevel.HIGH:
            return ["在1个月内补齐授权机制、隐私政策和第三方协议。", "视路径结果启动标准合同备案/认证或安全评估准备。", "补足核心安全技术措施和制度文件。"]
        if risk_level == RiskLevel.MEDIUM:
            return ["完善隐私政策、授权期限与第三方合作协议。", "建立基本的数据访问控制和日志留存机制。", "为未来跨境或规模扩张预留合规材料。"]
        return ["保留业务必要性说明和基础制度台账。", "定期复核数据规模、数据类型和流转方式变化。"]

    def _volume_to_count(self, volume: str) -> int:
        mapping = {"10 万条以下": 50_000, "10-100 万条": 500_000, "100-1000 万条": 5_000_000, "1000 万条以上": 20_000_000}
        return mapping.get(volume, 0)


class DiagnosisNarrativeGenerator:
    def build(self, profile: ComplianceProfileDraft, evaluation: RuleEvaluationResult, questionnaire: ComplianceQuestionnaire) -> DiagnosisAssessmentReport:
        profile_summary = profile.narrative_summary
        risk_analysis = f"系统综合问卷信息后，评定当前风险等级为 {evaluation.risk_level.value}。主要触发因素包括：{'; '.join(hit.trigger_summary for hit in evaluation.hit_rules[:3]) or '未命中高风险规则'}。"
        path_analysis = evaluation.path_conclusion
        executive_summary = f"该企业在{questionnaire.q1_2_industry}行业开展业务，{'涉及' if questionnaire.q4_2_cross_border_transfer else '暂不涉及'}跨境传输，当前建议路径为 {evaluation.outcome.value}。"
        return DiagnosisAssessmentReport(executive_summary=executive_summary, profile_summary=profile_summary, risk_analysis=risk_analysis, path_analysis=path_analysis, next_actions=evaluation.priority_actions)


class DiagnosisHandoffBuilder:
    def __init__(self, session_service: SessionService) -> None:
        self.session_service = session_service

    def build_assessment(self, session_id: str, questionnaire: ComplianceQuestionnaire, profile: ComplianceProfileDraft, evaluation: RuleEvaluationResult) -> AssessmentHandoffResponse:
        return AssessmentHandoffResponse.model_validate(self.session_service.build_assessment_handoff(session_id, questionnaire, profile, evaluation))

    def build_scc(self, session_id: str, questionnaire: ComplianceQuestionnaire, profile: ComplianceProfileDraft, evaluation: RuleEvaluationResult) -> SCCHandoffResponse:
        return SCCHandoffResponse.model_validate(self.session_service.build_scc_handoff(session_id, questionnaire, profile, evaluation))


class DiagnosisService:
    def __init__(self, report_service: ReportService, session_service: SessionService, legal_api_service: DeliLegalService) -> None:
        self.repository = DiagnosisRepository()
        self.report_service = report_service
        self.session_service = session_service
        self.legal_api_service = legal_api_service
        self.normalizer = QuestionnaireNormalizer()
        self.profile_builder = ProfileDraftBuilder()
        self.rule_engine = RuleEvaluationEngine()
        self.narrative_generator = DiagnosisNarrativeGenerator()
        self.handoff_builder = DiagnosisHandoffBuilder(session_service)
        self._citations = self._load_citations()

    def create_session(self, db: Session) -> DiagnosisSessionCreateResponse:
        record = self.repository.create(db)
        return DiagnosisSessionCreateResponse(id=record.id, status=DiagnosisSessionStatus(record.status))

    def submit_questionnaire(self, db: Session, session_id: str, questionnaire_payload: ComplianceQuestionnaire | dict) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id)
        questionnaire = self.normalizer.normalize(questionnaire_payload)
        profile = self.profile_builder.build(questionnaire)
        record.status = DiagnosisSessionStatus.ANSWERING.value
        record.answers_json = dumps(questionnaire.model_dump())
        record.context_json = dumps({"profile": profile.model_dump()})
        record = self.repository.save(db, record)
        return self._to_response(record, questionnaire=questionnaire, profile=profile)

    def evaluate_questionnaire(self, db: Session, session_id: str) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id)
        questionnaire = self._deserialize_questionnaire(record)
        if not questionnaire:
            raise ValueError("Diagnosis questionnaire is incomplete")
        profile = self.profile_builder.build(questionnaire)
        evaluation = self.rule_engine.evaluate(questionnaire)
        evaluation.citations = self._build_citations(questionnaire, evaluation)
        report_preview = self.narrative_generator.build(profile, evaluation, questionnaire)
        result = self._build_result(report_preview, evaluation)
        context = self.session_service.build_prefill_context(evaluation.outcome.value, questionnaire.model_dump(), profile.model_dump(), evaluation.model_dump())
        record.status = DiagnosisSessionStatus.COMPLETED.value
        record.result_json = dumps({"profile": profile.model_dump(), "evaluation": evaluation.model_dump(), "report_preview": report_preview.model_dump(), "result": result.model_dump()})
        record.context_json = dumps(context)
        record = self.repository.save(db, record)
        return self._to_response(record, questionnaire=questionnaire, profile=profile, evaluation=evaluation, report_preview=report_preview, result=result)

    def submit_answers(self, db: Session, session_id: str, answers: DiagnosisAnswerSet) -> DiagnosisSessionResponse:
        questionnaire = self.normalizer.from_legacy_answers(answers)
        self.submit_questionnaire(db, session_id, questionnaire)
        response = self.evaluate_questionnaire(db, session_id)
        response.deprecated_answers = answers
        return response

    def get_result(self, db: Session, session_id: str) -> DiagnosisSessionResponse:
        record = self._require_session(db, session_id)
        return self._to_response(record)

    def get_profile(self, db: Session, session_id: str) -> ComplianceProfileDraft:
        record = self._require_session(db, session_id)
        payload = loads(record.result_json, {})
        profile_data = payload.get("profile") or loads(record.context_json, {}).get("profile")
        if not profile_data:
            questionnaire = self._deserialize_questionnaire(record)
            if not questionnaire:
                raise ValueError("Diagnosis questionnaire is incomplete")
            return self.profile_builder.build(questionnaire)
        return ComplianceProfileDraft.model_validate(profile_data)

    def get_context(self, db: Session, session_id: str) -> DiagnosisContextResponse:
        record = self._require_session(db, session_id)
        result = self._deserialize_result(record)
        profile = self._deserialize_profile(record)
        return DiagnosisContextResponse(session_id=record.id, outcome=result.outcome if result else None, risk_level=result.risk_level if result else None, company_profile=profile.enterprise_attributes if profile else {}, prefill_context=loads(record.context_json, {}))

    def get_assessment_handoff(self, db: Session, session_id: str) -> AssessmentHandoffResponse:
        questionnaire, profile, evaluation = self._require_evaluated_session(db, session_id)
        return self.handoff_builder.build_assessment(session_id, questionnaire, profile, evaluation)

    def get_scc_handoff(self, db: Session, session_id: str) -> SCCHandoffResponse:
        questionnaire, profile, evaluation = self._require_evaluated_session(db, session_id)
        return self.handoff_builder.build_scc(session_id, questionnaire, profile, evaluation)

    def generate_report(self, db: Session, session_id: str) -> DiagnosisReportResponse:
        questionnaire, profile, evaluation = self._require_evaluated_session(db, session_id)
        record = self._require_session(db, session_id)
        report_preview = self._deserialize_report_preview(record)
        html = self._build_html(session_id, questionnaire, profile, evaluation, report_preview)
        preview = {"summary": report_preview.executive_summary, "outcome": evaluation.outcome.value, "risk_level": evaluation.risk_level.value, "next_actions": report_preview.next_actions}
        html_report = self.report_service.create_html_report(db, "diagnosis", session_id, "diagnosis_report.html", html, preview)
        pdf_lines = ["AI4Law 数据合规诊断评估报告", f"会话ID: {session_id}", f"风险等级: {evaluation.risk_level.value}", f"路径结论: {evaluation.outcome.value}", f"执行摘要: {report_preview.executive_summary}", "触发规则:", *[f"{hit.code}: {hit.trigger_summary}" for hit in evaluation.hit_rules], "优先行动:", *report_preview.next_actions]
        pdf_report = self.report_service.create_pdf_report(db, "diagnosis", session_id, "diagnosis_report.pdf", pdf_lines, preview)
        return DiagnosisReportResponse(html_report=html_report, pdf_report=pdf_report)

    def _build_result(self, report_preview: DiagnosisAssessmentReport, evaluation: RuleEvaluationResult) -> DiagnosisResult:
        suggested_next_module = "assessment" if evaluation.outcome == DiagnosisOutcome.SECURITY_ASSESSMENT else "scc" if evaluation.outcome == DiagnosisOutcome.SCC_OR_CERTIFICATION else "general"
        return DiagnosisResult(outcome=evaluation.outcome, risk_level=evaluation.risk_level, summary=report_preview.executive_summary, hit_rules=[hit.trigger_summary for hit in evaluation.hit_rules], citations=evaluation.citations, next_actions=report_preview.next_actions, suggested_next_module=suggested_next_module, profile_summary=report_preview.profile_summary, compliance_conclusion=evaluation.compliance_conclusion)

    def _build_html(self, session_id: str, questionnaire: ComplianceQuestionnaire, profile: ComplianceProfileDraft, evaluation: RuleEvaluationResult, report_preview: DiagnosisAssessmentReport) -> str:
        trigger_lines = "".join(f"<li>{hit.code} | {hit.trigger_summary} | {'；'.join(hit.legal_basis)}</li>" for hit in evaluation.hit_rules)
        citation_lines = "".join(f"<li>{citation.source} {citation.article}：{citation.note}</li>" for citation in evaluation.citations)
        action_lines = "".join(f"<li>{action}</li>" for action in report_preview.next_actions)
        return f"""
        <html lang="zh-CN">
          <body>
            <h1>AI4Law 数据合规诊断评估报告</h1>
            <p>会话 ID：{session_id}</p>
            <h2>业务数据合规自画像（草案）</h2>
            <p>{profile.narrative_summary}</p>
            <h2>风险等级与路径结论</h2>
            <p>风险等级：{evaluation.risk_level.value}</p>
            <p>路径结论：{evaluation.outcome.value}</p>
            <p>{evaluation.compliance_conclusion}</p>
            <p>{evaluation.path_conclusion}</p>
            <h2>关键问卷摘要</h2>
            <ul>
              <li>行业：{questionnaire.q1_2_industry}</li>
              <li>业务模式：{','.join(questionnaire.q1_3_business_modes)}</li>
              <li>数据规模：{questionnaire.q3_6_data_volume}</li>
              <li>是否跨境：{'是' if questionnaire.q4_2_cross_border_transfer else '否'}</li>
              <li>授权机制：{questionnaire.q4_5_authorization_mechanism}</li>
            </ul>
            <h2>触发规则链</h2>
            <ul>{trigger_lines}</ul>
            <h2>法规依据</h2>
            <ul>{citation_lines}</ul>
            <h2>评估摘要</h2>
            <p>{report_preview.executive_summary}</p>
            <p>{report_preview.risk_analysis}</p>
            <h2>后续行动</h2>
            <ul>{action_lines}</ul>
          </body>
        </html>
        """

    def _to_response(self, record: DiagnosisSessionModel, questionnaire: ComplianceQuestionnaire | None = None, profile: ComplianceProfileDraft | None = None, evaluation: RuleEvaluationResult | None = None, report_preview: DiagnosisAssessmentReport | None = None, result: DiagnosisResult | None = None) -> DiagnosisSessionResponse:
        payload = loads(record.result_json, {})
        return DiagnosisSessionResponse(
            id=record.id,
            status=DiagnosisSessionStatus(record.status),
            questionnaire=questionnaire or self._deserialize_questionnaire(record),
            profile=profile or (ComplianceProfileDraft.model_validate(payload["profile"]) if payload.get("profile") else None),
            evaluation=evaluation or (RuleEvaluationResult.model_validate(payload["evaluation"]) if payload.get("evaluation") else None),
            report_preview=report_preview or (DiagnosisAssessmentReport.model_validate(payload["report_preview"]) if payload.get("report_preview") else None),
            result=result or self._deserialize_result(record),
        )

    def _deserialize_questionnaire(self, record: DiagnosisSessionModel) -> ComplianceQuestionnaire | None:
        data = loads(record.answers_json, {})
        return ComplianceQuestionnaire.model_validate(data) if data else None

    def _deserialize_profile(self, record: DiagnosisSessionModel) -> ComplianceProfileDraft | None:
        payload = loads(record.result_json, {})
        profile_data = payload.get("profile") or loads(record.context_json, {}).get("profile")
        return ComplianceProfileDraft.model_validate(profile_data) if profile_data else None

    def _deserialize_result(self, record: DiagnosisSessionModel) -> DiagnosisResult | None:
        payload = loads(record.result_json, {})
        return DiagnosisResult.model_validate(payload["result"]) if payload.get("result") else None

    def _deserialize_report_preview(self, record: DiagnosisSessionModel) -> DiagnosisAssessmentReport:
        payload = loads(record.result_json, {})
        report_data = payload.get("report_preview")
        if not report_data:
            raise ValueError("Diagnosis session is incomplete")
        return DiagnosisAssessmentReport.model_validate(report_data)

    def _require_session(self, db: Session, session_id: str) -> DiagnosisSessionModel:
        record = self.repository.get(db, session_id)
        if not record:
            raise ValueError("Diagnosis session not found")
        return record

    def _require_evaluated_session(self, db: Session, session_id: str) -> tuple[ComplianceQuestionnaire, ComplianceProfileDraft, RuleEvaluationResult]:
        record = self._require_session(db, session_id)
        questionnaire = self._deserialize_questionnaire(record)
        payload = loads(record.result_json, {})
        profile = ComplianceProfileDraft.model_validate(payload["profile"]) if payload.get("profile") else None
        evaluation = RuleEvaluationResult.model_validate(payload["evaluation"]) if payload.get("evaluation") else None
        if not questionnaire or not profile or not evaluation:
            raise ValueError("Diagnosis session is incomplete")
        return questionnaire, profile, evaluation

    def _load_citations(self) -> list[DiagnosisCitation]:
        path = Path(__file__).resolve().parent.parent / "data" / "diagnosis_citations.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [DiagnosisCitation.model_validate(item) for item in payload]

    def _build_citations(self, questionnaire: ComplianceQuestionnaire, evaluation: RuleEvaluationResult) -> list[DiagnosisCitation]:
        citations = list(self._citations)
        for basis in evaluation.legal_summary:
            citations.append(DiagnosisCitation(source="规则引擎", article=basis, note="基于自动规则计算命中。"))
        remote_hits = self.legal_api_service.search_cases(f"{questionnaire.q1_2_industry} 数据合规 {evaluation.outcome.value}", size=2)
        for hit in remote_hits:
            citations.append(DiagnosisCitation(source=hit["source"], article=hit["title"], note=(hit["summary"] or "来自得理法搜的补充检索结果")[:120]))
        deduped: list[DiagnosisCitation] = []
        seen: set[tuple[str, str]] = set()
        for citation in citations:
            key = (citation.source, citation.article)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(citation)
        return deduped
