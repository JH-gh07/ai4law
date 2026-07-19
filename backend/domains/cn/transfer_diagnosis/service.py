import json
import re
from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.risk.scoring import risk_level
from backend.core.settings import get_settings
from backend.common.trace.recorder import TraceRecorder
from backend.domains.cn.transfer_diagnosis.adapters import facts_from_module
from backend.domains.cn.transfer_diagnosis.models import DiagnosisFacts, FactSource
from backend.domains.cn.transfer_diagnosis.rule_engine import DiagnosisRuleEngine, RuleMatch
from backend.domains.cn.transfer_diagnosis.schema import DiagnosisAnswers, DiagnosisResult
from backend.domains.cn.transfer_diagnosis.agents import create_diag_agents


_RATIONALE_I18N = {
    "CIIO must apply for security assessment": "企业被识别为关键信息基础设施运营者，应优先走安全评估路径。",
    "Important data export must apply for security assessment": "涉及重要数据出境，按监管要求应优先走安全评估路径。",
    "PII count >= 1,000,000 must apply for security assessment": "个人信息处理规模达到法定门槛，应优先走安全评估路径。",
    "Sensitive PII count >= 10,000 must apply for security assessment": "敏感个人信息处理规模达到法定门槛，应优先走安全评估路径。",
    "Threshold not reached for mandatory security assessment.": "未触发强制安全评估门槛，可走标准合同备案或认证路径。",
}


class DiagnosisService:
    def __init__(
        self,
        tree_path: str | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.tree_path = tree_path or str(Path(__file__).with_name("decision_tree.json"))
        self._tree = self._load_tree(self.tree_path)
        self._rule_engine = DiagnosisRuleEngine(self._tree)
        self._llm_client = llm_client or LLMClient(get_settings())
        self.agents = create_diag_agents(self._llm_client)

    @staticmethod
    def _load_tree(tree_path: str) -> dict:
        with open(tree_path, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def evaluate(self, answers: DiagnosisAnswers, *, trace: TraceRecorder | None = None) -> DiagnosisResult:
        answers, provenance, missing_facts = self._resolve_answers(answers)

        if trace:
            trace.record("status", {"summary": "开始路径诊断", "detail": {"module": "diagnosis"}})

        # ── Agent-assisted fact clarification for unknown fields ──
        agent_trace: dict = {}
        payload = answers.model_dump()

        # Agent 2 (P0): ImportantDataAgent — when q2 is still unknown
        if answers.q2_has_important_data.value == "unknown":
            imp_result = self.agents["important_data"].run(
                industry=answers.m1_industry,
                data_desc=f"{answers.q8_purpose} {str(answers.m3_personal_info_types)}",
                data_types=list(answers.m3_personal_info_types or []),
                important_data_types=list(answers.m3_important_data_types or []),
                purpose=answers.q8_purpose,
                volume_range=str(answers.m3_data_volume_range or ""),
                processes_important_data=str(answers.m3_processes_important_data or ""),
            )
            if imp_result:
                if trace:
                    trace.record("thought", {"summary": "重要数据分析 Agent 完成"})
                agent_trace["important_data"] = imp_result
                suggested = imp_result.get("suggested_answer", "unknown")
                if suggested in ("yes", "no"):
                    payload["q2_has_important_data"] = suggested
                    answers = DiagnosisAnswers(**payload)
                    provenance["contains_important_data"] = FactSource.LLM_INFERENCE
                    if "contains_important_data" in missing_facts:
                        missing_facts.remove("contains_important_data")

        # Agent 3 (P2): PIClassifyAgent — when q5 is still unknown
        if answers.q5_no_personal_info.value == "unknown":
            pi_result = self.agents["pi_classify"].run(
                data_desc=f"{answers.q8_purpose} {str(answers.m3_personal_info_types)}",
                personal_info_types=list(answers.m3_personal_info_types or []),
                sensitive_info_types=list(answers.m3_sensitive_info_types or []),
                anonymization_desc=str(answers.m3_retention_desc or ""),
                processes_personal_info=str(answers.m3_processes_personal_info or ""),
                industry=answers.m1_industry,
                use_case=str(answers.q6_scenario.value),
            )
            if pi_result:
                if trace:
                    trace.record("thought", {"summary": "个人信息分类 Agent 完成"})
                agent_trace["pi_classify"] = pi_result
                suggested = pi_result.get("suggested_q5_no_personal_info", "unknown")
                if suggested in ("yes", "no"):
                    payload["q5_no_personal_info"] = suggested
                    answers = DiagnosisAnswers(**payload)
                    provenance["no_personal_info"] = FactSource.LLM_INFERENCE
                    if "no_personal_info" in missing_facts:
                        missing_facts.remove("no_personal_info")

        # Agent 4 (P3): ExemptionAgent — when scenario is "other" (may miss exemption)
        if answers.q6_scenario.value == "other":
            ex_result = self.agents["exemption"].run(
                scenario="other",
                purpose=answers.q8_purpose,
                data_desc=str(answers.m3_personal_info_types),
                receiver_type=answers.q7_receiver_type.value,
                receiver_name=str(answers.m4_cross_border_regions or ""),
                is_intra_group=answers.q7_receiver_type.value == "intra_group",
                pii_count=answers.q3_pii_count,
                spi_count=answers.q4_spi_count,
            )
            if ex_result:
                if trace:
                    trace.record("thought", {"summary": "豁免情形分析 Agent 完成"})
                agent_trace["exemption"] = ex_result

        agent_notes = self._build_agent_notes(agent_trace)
        facts = facts_from_module(
            answers,
            field_provenance=provenance,
            missing_facts=missing_facts,
        )
        validation_result = self._validate_fact_consistency(answers)
        if validation_result is not None:
            result = self._attach_fact_metadata(
                validation_result,
                facts,
                additional_notes=agent_notes,
            )
            if trace:
                trace.record(
                    "final",
                    {
                        "summary": "路径诊断因事实冲突转人工复核",
                        "detail": {"mode": "validation", "conflicts": result.uncertainty_notes},
                    },
                )
            return result

        # ── Decision tree ──
        rule_match = self._rule_engine.evaluate(facts)
        if not rule_match.is_default:
            result = self._build_rule_result(answers, rule_match)
            result = self._attach_fact_metadata(
                result,
                facts,
                rule_match=rule_match,
                additional_notes=agent_notes,
            )
            if trace:
                trace.record(
                    "final",
                    {
                        "summary": "路径诊断完成",
                        "detail": {
                            "matched_rule": rule_match.rule_id,
                            "recommended_path": rule_match.path.value,
                            "conclusion_source": result.conclusion_source,
                        },
                    },
                )
            return result

        # 明显信息不足时，走 AI 推测路径（并显式标注为推测结论）。
        if self._needs_ai_inference(answers):
            inferred = self._build_ai_inference_result(answers)
            if inferred is not None:
                inferred = self._attach_fact_metadata(
                    inferred,
                    facts,
                    additional_notes=agent_notes,
                )
                if trace:
                    trace.record(
                        "final",
                        {
                            "summary": "路径诊断完成",
                            "detail": {
                                "mode": "ai_inference",
                                "recommended_path": inferred.recommended_path,
                            },
                        },
                    )
                return inferred

        default = self._tree["default"]
        result = self._build_result(
            answers,
            default["path"],
            default["legal_basis"],
            _RATIONALE_I18N["Threshold not reached for mandatory security assessment."],
            conclusion_source="rule",
            confidence="MEDIUM",
            matched_rule_id="default",
            uncertainty_notes=agent_notes or None,
        )
        result = self._attach_fact_metadata(result, facts)
        if trace:
            trace.record(
                "final",
                {
                    "summary": "路径诊断完成",
                    "detail": {
                        "mode": "default",
                        "recommended_path": default.get("path", ""),
                    },
                },
            )
        return result

    @staticmethod
    def _contains_sensitive_personal_info(items: list[str]) -> bool:
        keywords = ("身份证", "人脸", "指纹", "声纹", "健康", "金融", "未成年人", "精准位")
        return any(any(key in item for key in keywords) for item in items)

    @staticmethod
    def _estimate_pii_count(volume_range: str) -> int:
        if volume_range == "1000万条以上":
            return 10_000_000
        if volume_range == "100-1000万条":
            return 2_000_000
        if volume_range == "10-100万条":
            return 300_000
        if volume_range == "10万条以下":
            return 50_000
        return 0

    def _normalize_answers(self, answers: DiagnosisAnswers) -> DiagnosisAnswers:
        normalized, _, _ = self._resolve_answers(answers)
        return normalized

    def _resolve_answers(
        self,
        answers: DiagnosisAnswers,
    ) -> tuple[DiagnosisAnswers, dict[str, FactSource], list[str]]:
        payload = answers.model_dump()
        explicit_fields = answers.model_fields_set
        module_to_canonical = {
            "q1_is_ciio": "is_ciio",
            "q2_has_important_data": "contains_important_data",
            "q3_pii_count": "personal_info_count",
            "q4_spi_count": "sensitive_personal_info_count",
            "q5_no_personal_info": "no_personal_info",
            "q6_scenario": "transfer_scenario",
            "q7_receiver_type": "receiver_type",
            "q8_purpose": "transfer_purpose",
        }
        provenance = {
            canonical: (
                FactSource.USER if module_field in explicit_fields else FactSource.DEFAULT
            )
            for module_field, canonical in module_to_canonical.items()
        }

        personal_types = [
            str(item)
            for item in payload.get("m3_personal_info_types", [])
            if str(item).strip()
        ]
        sensitive_types = [
            str(item)
            for item in payload.get("m3_sensitive_info_types", [])
            if str(item).strip()
        ]
        important_types = [
            str(item)
            for item in payload.get("m3_important_data_types", [])
            if str(item).strip()
        ]

        has_personal_info = (
            payload.get("m3_processes_personal_info") == "yes"
            or bool(personal_types)
        )
        has_sensitive_info = bool(
            sensitive_types
        ) or self._contains_sensitive_personal_info(personal_types)
        has_important_data = (
            payload.get("m3_processes_important_data") == "yes"
            or bool(important_types)
        )

        if payload.get("q2_has_important_data") == "unknown" and has_important_data:
            payload["q2_has_important_data"] = "yes"
            provenance["contains_important_data"] = FactSource.RULE
        elif (
            payload.get("q2_has_important_data") == "unknown"
            and payload.get("m3_processes_important_data") == "no"
        ):
            payload["q2_has_important_data"] = "no"
            provenance["contains_important_data"] = FactSource.RULE

        if payload.get("q5_no_personal_info") == "unknown":
            payload["q5_no_personal_info"] = (
                "yes" if not has_personal_info and not has_important_data else "no"
            )
            provenance["no_personal_info"] = FactSource.RULE

        if int(payload.get("q3_pii_count") or 0) == 0 and has_personal_info:
            estimated_count = self._estimate_pii_count(
                str(payload.get("m3_data_volume_range") or "")
            )
            if estimated_count:
                payload["q3_pii_count"] = estimated_count
                provenance["personal_info_count"] = FactSource.ESTIMATE

        if int(payload.get("q4_spi_count") or 0) == 0 and has_sensitive_info:
            volume_hint = str(payload.get("m3_data_volume_range") or "")
            payload["q4_spi_count"] = (
                12_000
                if volume_hint in {"1000万条以上", "100-1000万条"}
                else 2_000
            )
            provenance["sensitive_personal_info_count"] = FactSource.ESTIMATE

        normalized = DiagnosisAnswers(**payload)
        missing_facts = [
            canonical
            for module_field, canonical in (
                ("q1_is_ciio", "is_ciio"),
                ("q2_has_important_data", "contains_important_data"),
                ("q5_no_personal_info", "no_personal_info"),
            )
            if getattr(normalized, module_field).value == "unknown"
        ]
        return normalized, provenance, missing_facts

    @staticmethod
    def _build_agent_notes(agent_trace: dict) -> list[str]:
        notes: list[str] = []
        if agent_trace.get("important_data"):
            item = agent_trace["important_data"]
            notes.append(
                f"[Agent] 重要数据辅助判断: {item.get('result', '?')} "
                f"(置信度 {item.get('confidence', 0):.0%}), "
                f"建议值: q2={item.get('suggested_answer', '?')}"
            )
        if agent_trace.get("pi_classify"):
            item = agent_trace["pi_classify"]
            notes.append(
                f"[Agent] 个人信息辅助判断: "
                f"{item.get('personal_information_result', '?')}, "
                f"重识别风险: {item.get('re_identification_risk', '?')}"
            )
        if agent_trace.get("exemption"):
            candidates = agent_trace["exemption"].get("candidate_exemptions", [])
            if candidates:
                item = candidates[0]
                notes.append(
                    f"[Agent] 豁免情形辅助判断: {item.get('type', '?')} "
                    f"(置信度 {item.get('confidence', 0):.0%})"
                )
        return notes

    def _validate_fact_consistency(
        self,
        answers: DiagnosisAnswers,
    ) -> DiagnosisResult | None:
        claims_no_regulated_data = answers.q5_no_personal_info.value == "yes"
        has_personal_signals = (
            answers.q3_pii_count > 0
            or answers.q4_spi_count > 0
            or answers.m3_processes_personal_info == "yes"
            or bool(answers.m3_personal_info_types)
            or bool(answers.m3_sensitive_info_types)
        )
        has_important_signals = (
            answers.q2_has_important_data.value == "yes"
            or answers.m3_processes_important_data == "yes"
            or bool(answers.m3_important_data_types)
        )
        if not claims_no_regulated_data or not (
            has_personal_signals or has_important_signals
        ):
            return None

        conflicts = [
            "q5 声明不含个人信息且不涉及重要数据，但其他字段给出了相反事实。",
            "系统未执行豁免判定；请核实数据类型、人数规模与重要数据属性。",
        ]
        return DiagnosisResult(
            recommended_path="manual_review",
            legal_basis=[],
            rationale="输入事实存在直接冲突，无法可靠执行自动路径判定。",
            action_items=[
                "核实 q5 与个人信息、敏感个人信息、重要数据字段。",
                "由合规人员确认事实后重新运行路径诊断。",
            ],
            risk_level="HIGH",
            conclusion_source="validation",
            confidence="LOW",
            final_explanation="事实冲突已阻断自动结论并转人工复核。",
            uncertainty_notes=conflicts,
            requires_human_review=True,
        )

    @staticmethod
    def _attach_fact_metadata(
        result: DiagnosisResult,
        facts: DiagnosisFacts,
        *,
        rule_match: RuleMatch | None = None,
        additional_notes: list[str] | None = None,
    ) -> DiagnosisResult:
        result.fact_provenance = {
            field_name: source.value
            for field_name, source in facts.field_provenance.items()
        }
        result.missing_facts = list(facts.missing_facts)
        if additional_notes:
            result.uncertainty_notes.extend(
                note for note in additional_notes if note not in result.uncertainty_notes
            )

        condition_to_fact = {
            "q1_is_ciio": "is_ciio",
            "q2_has_important_data": "contains_important_data",
            "q3_pii_count_gte": "personal_info_count",
            "q3_pii_count_lt": "personal_info_count",
            "q4_spi_count_gte": "sensitive_personal_info_count",
            "q4_spi_count_lt": "sensitive_personal_info_count",
            "q5_no_personal_info": "no_personal_info",
            "q6_scenario": "transfer_scenario",
            "q7_receiver_type": "receiver_type",
        }
        decisive_facts = {
            condition_to_fact[field]
            for field in (rule_match.condition_fields if rule_match else [])
            if field in condition_to_fact
        }
        inferred_sources = {FactSource.LLM_INFERENCE, FactSource.ESTIMATE}
        inferred_decisive_facts = sorted(
            field
            for field in decisive_facts
            if facts.source_for(field) in inferred_sources
        )
        if result.conclusion_source == "rule" and inferred_decisive_facts:
            result.conclusion_source = "rule_with_inferred_facts"
            result.confidence = "MEDIUM"
            result.uncertainty_notes.append(
                "规则命中依赖推断或估算事实："
                + "、".join(inferred_decisive_facts)
                + "。"
            )
        if (
            inferred_decisive_facts
            or result.missing_facts
            or result.confidence.upper() == "LOW"
            or result.conclusion_source != "rule"
        ):
            result.requires_human_review = True
        return result

    def _build_rule_result(self, answers: DiagnosisAnswers, rule: RuleMatch) -> DiagnosisResult:
        result = self._build_result(
            answers,
            rule.path.value,
            rule.legal_basis,
            rule.description,
            conclusion_source="rule",
            confidence="HIGH",
            matched_rule_id=rule.rule_id,
        )
        result.final_explanation = self._build_rule_explanation(result, answers)
        return result

    def _build_rule_explanation(self, result: DiagnosisResult, answers: DiagnosisAnswers) -> str:
        if not self._llm_client.enabled:
            return result.rationale
        user_prompt = (
            "请基于以下规则判定结果，输出2-3句专业中文解释。要求："
            "1) 只能解释，不得改判推荐路径；2) 指出关键触发点；3) 给出一句行动建议。\n"
            f"推荐路径：{result.recommended_path}\n"
            f"风险等级：{result.risk_level}\n"
            f"规则依据：{'；'.join(result.legal_basis)}\n"
            f"判定说明：{result.rationale}\n"
            f"问卷答案：{answers.model_dump_json()}"
        )
        text = self._llm_client.chat(
            system="你是一名中国数据出境合规律师，仅负责解释规则结论，不改判。",
            user=user_prompt,
            temperature=0.2,
            max_tokens=300,
        ).strip()
        return text or result.rationale

    @staticmethod
    def _build_result(
        answers: DiagnosisAnswers,
        recommended_path: str,
        legal_basis: list[str],
        rationale: str,
        conclusion_source: str = "rule",
        confidence: str = "HIGH",
        matched_rule_id: str | None = None,
        uncertainty_notes: list[str] | None = None,
        final_explanation: str = "",
    ) -> DiagnosisResult:
        rationale = _RATIONALE_I18N.get(rationale, rationale)
        level = risk_level(
            is_ciio=answers.q1_is_ciio.value == "yes",
            contains_important_data=answers.q2_has_important_data.value == "yes",
            pii_count=answers.q3_pii_count,
            spi_count=answers.q4_spi_count,
        )
        if recommended_path == "security_assessment":
            action_items = [
                "整理数据出境清单与处理活动映射。",
                "生成《数据出境风险自评估报告》草案并补齐附件。",
                "按属地网信要求提交安全评估申报材料。",
            ]
        else:
            action_items = [
                "在标准合同备案与个人信息保护认证之间确定实施路径。",
                "生成 PIPIA 报告及标准合同配套附件。",
                "准备省级网信备案/留档材料并完成内部审批。",
            ]

        return DiagnosisResult(
            recommended_path=recommended_path,
            legal_basis=legal_basis,
            rationale=rationale,
            action_items=action_items,
            risk_level=level,
            conclusion_source=conclusion_source,
            confidence=confidence,
            matched_rule_id=matched_rule_id,
            final_explanation=final_explanation or rationale,
            uncertainty_notes=uncertainty_notes or [],
        )

    @staticmethod
    def _needs_ai_inference(answers: DiagnosisAnswers) -> bool:
        # 规则无法可靠收敛的典型信号：关键布尔位不确定，且出境规模信息较弱。
        uncertain_flags = (
            answers.q1_is_ciio.value == "unknown"
            or answers.q2_has_important_data.value == "unknown"
            or answers.q5_no_personal_info.value == "unknown"
        )
        weak_volume_signal = answers.q3_pii_count == 0 and answers.q4_spi_count == 0
        # 若问卷明确填写了核心处理事实，不应因 q 字段缺失而轻易走 AI 推测。
        has_structured_signals = (
            answers.m3_processes_personal_info in {"yes", "no"}
            or answers.m3_processes_important_data in {"yes", "no"}
            or len(answers.m3_personal_info_types) > 0
            or len(answers.m3_important_data_types) > 0
        )
        if has_structured_signals and not weak_volume_signal:
            return False
        return uncertain_flags or weak_volume_signal

    def _build_ai_inference_result(self, answers: DiagnosisAnswers) -> DiagnosisResult | None:
        # 检查LLM客户端是否启用
        if not self._llm_client.enabled:
            # 如果LLM客户端未启用，构建一个保守推测结果
            return self._build_result(
                answers,
                recommended_path="scc_or_certification",  # 推荐路径设为标准合同/认证
                legal_basis=self._tree["default"]["legal_basis"],  # 使用默认法律依据
                rationale="当前关键字段存在不确定项，暂按标准合同/认证路径进行保守推测，需人工复核。",  # 推理说明
                conclusion_source="ai_inference",  # 结论来源为AI推理
                confidence="LOW",  # 置信度为低
                matched_rule_id=None,  # 无匹配规则ID
                uncertainty_notes=[  # 不确定性说明
                    "关键字段含 unknown 或缺乏规模信息。",
                    "LLM 未配置，未能生成更细化推测。",
                ],
                final_explanation="该结论为推测结论，不可直接作为最终法律意见，请补充信息后复判。",  # 最终解释
            )
        # 构建提示词，指导AI进行数据跨境合规分析

        prompt = (
            "你是中国数据跨境合规律师。请基于给定问答做“推测结论”，仅在规则不足时使用。"
            "请返回JSON，不要额外文本。字段："
            "recommended_path(仅可为security_assessment/scc_or_certification/exemption),"
            "rationale, risk_level(LOW/MEDIUM/HIGH), legal_basis(string数组), action_items(string数组，最多4条),"
            "confidence(LOW/MEDIUM), uncertainty_notes(string数组), final_explanation。\n"
            f"输入：{answers.model_dump_json(ensure_ascii=False)}"
        )
        raw = self._llm_client.chat(
            system="你是一名严谨的中国数据出境合规律师，只输出JSON。",
            user=prompt,
            temperature=0.1,
            max_tokens=800,
        )
        parsed = self._parse_json_object(raw)
        if not isinstance(parsed, dict):
            return self._build_result(
                answers,
                recommended_path="scc_or_certification",
                legal_basis=self._tree["default"]["legal_basis"],
                rationale="关键字段不完整，已触发AI推测，但解析失败，采用保守推测路径。",
                conclusion_source="ai_inference",
                confidence="LOW",
                uncertainty_notes=["AI 输出无法解析为结构化 JSON。"],
                final_explanation="系统触发了AI推测，但当前仅返回保守建议，请补全信息后重判。",
            )

        path = str(parsed.get("recommended_path") or "scc_or_certification")
        if path not in {"security_assessment", "scc_or_certification", "exemption"}:
            path = "scc_or_certification"
        legal_basis = [str(item) for item in parsed.get("legal_basis", []) if str(item).strip()]
        if not legal_basis:
            legal_basis = self._tree["default"]["legal_basis"]
        action_items = [str(item) for item in parsed.get("action_items", []) if str(item).strip()][:4]
        uncertainty_notes = [str(item) for item in parsed.get("uncertainty_notes", []) if str(item).strip()]
        if not uncertainty_notes:
            uncertainty_notes = ["该结论由AI推测生成，需人工复核。"]
        confidence = str(parsed.get("confidence") or "LOW").upper()
        if confidence not in {"LOW", "MEDIUM"}:
            confidence = "LOW"

        result = self._build_result(
            answers,
            recommended_path=path,
            legal_basis=legal_basis,
            rationale=str(parsed.get("rationale") or "关键字段不完整，系统给出推测结论。"),
            conclusion_source="ai_inference",
            confidence=confidence,
            uncertainty_notes=uncertainty_notes,
            final_explanation=str(
                parsed.get("final_explanation")
                or "本结论为推测结论，请在补充关键字段后再次执行规则判定。"
            ),
        )
        if action_items:
            result.action_items = action_items
        risk = str(parsed.get("risk_level") or "").upper()
        if risk in {"LOW", "MEDIUM", "HIGH"}:
            result.risk_level = risk
        return result

    @staticmethod
    def _parse_json_object(raw: str) -> dict | None:
        text = (raw or "").strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
        # 兼容模型外层包裹说明文字的情况。
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
